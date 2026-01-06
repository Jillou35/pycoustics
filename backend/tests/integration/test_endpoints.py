
import pytest
from app.main import app
from unittest.mock import patch


def test_read_main(client):
    response = client.get("/docs")
    assert response.status_code == 200

def test_get_recordings_empty(client):
    # Assuming valid session_id
    response = client.get("/recordings?session_id=test_session")
    assert response.status_code == 200
    assert response.json() == []

def test_websocket_connect(client):
    with client.websocket_connect("/ws/audio?session_id=test_ws") as websocket:
        # Send Init
        websocket.send_json({"action": "init", "sample_rate": 44100, "channels": 2})
        
        # Send dummy audio
        # Send text command first
        websocket.send_json({"action": "start_record", "sample_rate": 44100})
        
        # Send minimal audio packet
        websocket.send_bytes(b'\x00\x00\x00\x00')
        
        # Receive meter response
        data = websocket.receive_json()
        assert data["type"] == "meter"
        assert "rms" in data

def test_delete_recording_not_found(client):
    response = client.delete("/recordings/non_existent_file.wav")
    # Should be 404
    assert response.status_code == 404
    assert response.json()["detail"] == "Recording not found"

def test_download_recording_not_found(client):
    response = client.get("/recordings/non_existent_file.wav")
    assert response.status_code == 404

def test_websocket_recording_flow(client, test_db):
    with client.websocket_connect("/ws/audio?session_id=rec_flow") as websocket:
        # 1. Init
        websocket.send_json({"action": "init", "sample_rate": 44100, "channels": 2})
        
        # 2. Start Record
        websocket.send_json({"action": "start_record", "sample_rate": 44100})
        
        # 3. Send Data (needs to be enough to write something?)
        # Send 10 chunks
        chunk = b'\x00\x00' * 1024 * 2 * 2 # 1024 frames stereo
        for _ in range(5):
            websocket.send_bytes(chunk)
            # Consume meter
            websocket.receive_json()
            
        # 4. Stop Record
        websocket.send_json({"action": "stop_record"})
        
        # Should receive recording_saved
        response = websocket.receive_json()
        assert response["type"] == "recording_saved"
        rec_id = response["id"]
        filename = response["filename"]
        
        # Verify in DB
        # Can use client to get list
        resp = client.get("/recordings?session_id=rec_flow")
        assert resp.status_code == 200
        recordings = resp.json()
        assert len(recordings) == 1
        assert recordings[0]["filename"] == filename
        
        # Clean up (Delete)
        client.delete(f"/recordings/{filename}")

def test_websocket_commands(client):
    with client.websocket_connect("/ws/audio?session_id=cmd_test") as websocket:
        # Init
        websocket.send_json({"action": "init", "sample_rate": 44100, "channels": 2})
        # Set params
        websocket.send_json({
            "action": "set_params", 
            "gain": 5.0, 
            "filter_enabled": True, 
            "cutoff_freq": 1500, 
            "integration_time": 0.5
        })
        
        # Invalid JSON (should not disconnect, just log error)
        websocket.send_text("INVALID JSON")
        # Keep alive check
        websocket.send_bytes(b'\x00\x00\x00\x00')
        data = websocket.receive_json()
        assert data["type"] == "meter"

def test_websocket_no_session(client):
    from starlette.websockets import WebSocketDisconnect
    # It should close with code 4000
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/audio") as websocket:
            # It accepts then closes. We try to receive to trigger the close exception.
            websocket.receive_text()
    assert exc.value.code == 4000


def test_file_lifecycle(client, test_db, mock_recordings_dir):
    # 1. Create dummy file
    filename = "manual_test.wav"
    file_path = mock_recordings_dir / filename
    with open(file_path, "wb") as f:
        f.write(b"RIFF....WAVEfmt ...data....")
        
    # 2. Create DB entry
    from app.db.models import Recording
    rec = Recording(
        filename=filename, 
        duration_seconds=1.0, 
        session_id="manual_sess",
        settings={}, 
        channels=2
    )
    test_db.add(rec)
    test_db.commit()
    
    # 3. Download
    resp = client.get(f"/recordings/{filename}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    
    # 4. Delete
    resp = client.delete(f"/recordings/{filename}")
    assert resp.status_code == 200
    
    # 5. Verify gone
    assert not file_path.exists()
    resp = client.get(f"/recordings/{filename}")
    assert resp.status_code == 404

def test_session_cleanup_error(client, test_db, mock_recordings_dir):
    # Setup: Create a session recording
    from app.db.models import Recording
    session_id = "cleanup_error_test"
    filename = "cleanup_error.wav"
    rec = Recording(
        filename=filename, 
        duration_seconds=1.0, 
        session_id=session_id,
        settings={}, 
        channels=2
    )
    test_db.add(rec)
    test_db.commit()
    
    # Ensure file exists so logic attempts to delete it
    file_path = mock_recordings_dir / filename
    with open(file_path, "wb") as f:
        f.write(b"data")

    # Mock unlink to raise OSError
    with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
         # Trigger disconnect flow
         with client.websocket_connect(f"/ws/audio?session_id={session_id}") as websocket:
             pass
    
    # Verify DB entry is removed even if file delete failed (or check specific behavior)
    # The code deletes DB entry *after* file unlink attempt.
    check = test_db.query(Recording).filter_by(filename=filename).first()
    assert check is None

def test_delete_endpoint_os_error(client, test_db, mock_recordings_dir):
    # Setup
    filename = "delete_error.wav"
    file_path = mock_recordings_dir / filename
    with open(file_path, "wb") as f:
        f.write(b"data")
        
    from app.db.models import Recording
    rec = Recording(filename=filename, duration_seconds=1.0, session_id="del_u", settings={}, channels=2)
    test_db.add(rec)
    test_db.commit()
    with patch("pathlib.Path.unlink", side_effect=OSError("Disk failure")):
        response = client.delete(f"/recordings/{filename}")
        
    assert response.status_code == 500
    assert "Disk failure" in response.json()["detail"]

def test_websocket_generic_exception(client):
    # Patch receive to raise a generic Exception
    with patch("app.api.endpoints.AudioProcessor.process_chunk", side_effect=RuntimeError("Unexpected Boom")):
        with client.websocket_connect("/ws/audio?session_id=generic_exc") as websocket:
             # Send data to trigger process_chunk
             websocket.send_bytes(b'\x00' * 100)
             # Should close or handle error
             try:
                websocket.receive_json()
             except Exception:
                pass



