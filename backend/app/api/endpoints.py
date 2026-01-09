from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db.models import Recording as RecordingModel
from app.core.audio_processor import AudioProcessor
from app.services.recorder import AudioRecorder, RECORDINGS_DIR
from app.schemas.recording import Recording
from app.schemas.websocket import WebSocketCommand
from app.core.logger import get_logger
import json
from typing import List

router = APIRouter()
recorder = AudioRecorder()
logger = get_logger(__name__)


@router.websocket("/ws/audio")
async def audio_websocket(
    websocket: WebSocket, session_id: str | None = None, db: Session = Depends(get_db)
):
    """Handle audio streaming and processing.
    Args:
        websocket (WebSocket): The WebSocket connection.
        session_id (str | None, optional): The session ID. Defaults to None.
        db (Session, optional): The database session. Defaults to Depends(get_db).
    """
    await websocket.accept()

    if not session_id:
        logger.warning("No session_id provided in WebSocket connection")
        await websocket.close(code=4000)
        return

    logger.info(f"WebSocket connected: {session_id}")

    # Initialize processor with default settings to avoid unbound variable errors
    processor = AudioProcessor()

    try:
        while True:
            # We need to handle both text (commands) and binary (audio)
            # receive() returns a dict with 'type', 'bytes' or 'text'
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))

            if message["type"] == "websocket.receive":
                if "bytes" in message and message["bytes"]:
                    # Audio Data
                    audio_chunk = message["bytes"]

                    # 1. Process
                    processed_chunk, rms_db, spectrum, panning = (
                        processor.process_chunk(audio_chunk)
                    )

                    # 2. Record if active
                    if recorder.is_recording:
                        await recorder.write_chunk(processed_chunk)

                    # 3. Send feedback (RMS + Spectrum + Panning)
                    await websocket.send_json(
                        {
                            "type": "meter",
                            "rms": rms_db,
                            "spectrum": spectrum,
                            "panning": panning,
                        }
                    )

                elif "text" in message and message["text"]:
                    # Command
                    try:
                        data = json.loads(message["text"])
                        action = data.get("action")

                        if action == "init":
                            sample_rate = int(data.get("sample_rate", 44100))
                            channels = int(data.get("channels", 2))
                            # Re-initialize processor with correct params
                            processor = AudioProcessor(
                                sample_rate=sample_rate, channels=channels
                            )
                            logger.info(
                                f"Initialized AudioProcessor with sample_rate={sample_rate}, channels={channels}"
                            )

                        elif action == "start_record":
                            # Update params if provided, otherwise use current
                            sample_rate = int(
                                data.get("sample_rate", processor.sample_rate)
                            )
                            channels = int(data.get("channels", processor.channels))

                            recorder.start_recording(
                                settings={
                                    "gain": processor.gain,
                                    "cutoff": processor.cutoff_freq,
                                    "filter": processor.filter_enabled,
                                },
                                session_id=session_id,
                                sample_rate=sample_rate,
                                channels=channels,
                            )
                            logger.info(
                                f"Started recording for session {session_id} at {sample_rate}Hz, {channels}ch"
                            )

                        elif action == "stop_record":
                            entry = await recorder.stop_recording(db)
                            if entry:
                                await websocket.send_json(
                                    {
                                        "type": "recording_saved",
                                        "id": entry.id,
                                        "filename": entry.filename,
                                    }
                                )
                                logger.info(
                                    f"Stopped recording. Saved to {entry.filename}"
                                )

                        elif action == "set_params":
                            cmd = WebSocketCommand(**data)
                            processor.update_settings(
                                gain=cmd.gain,
                                filter_enabled=cmd.filter_enabled,
                                cutoff_freq=cmd.cutoff_freq,
                                integration_time=cmd.integration_time,
                            )
                            logger.debug(f"Updated params: {data}")

                    except Exception as e:
                        logger.error(f"Error processing command: {e}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
        if recorder.is_recording:
            await recorder.stop_recording(db)

        # Auto-delete recordings for this session
        if session_id:
            logger.info(f"Cleaning up recordings for session: {session_id}")
            recordings = (
                db.query(RecordingModel)
                .filter(RecordingModel.session_id == session_id)
                .all()
            )
            for rec in recordings:
                file_path = RECORDINGS_DIR / rec.filename
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except OSError as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
                db.delete(rec)
            db.commit()

    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        # Try close if possible
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/recordings", response_model=List[Recording])
def get_recordings(
    session_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[RecordingModel]:
    """Get recordings for a specific session or all sessions.

    Args:
        session_id (str | None, optional): The session ID. Defaults to None.
        skip (int, optional): The number of records to skip. Defaults to 0.
        limit (int, optional): The maximum number of records to return. Defaults to 100.
        db (Session, optional): The database session. Defaults to Depends(get_db).
    Returns:
        List[Recording]: List of recordings.
    """
    query = db.query(RecordingModel)
    if session_id:
        query = query.filter(RecordingModel.session_id == session_id)
    recordings = (
        query.order_by(RecordingModel.timestamp.desc()).offset(skip).limit(limit).all()
    )
    return recordings


@router.get("/recordings/{filename}")
def download_recording(filename: str) -> FileResponse:
    """Download a specific recording.

    Args:
        filename (str): The filename of the recording.
    Returns:
        FileResponse: The file response.
    """
    file_path = RECORDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav", filename=filename)


@router.delete("/recordings/{filename}")
def delete_recording(filename: str, db: Session = Depends(get_db)) -> dict:
    """Delete a specific recording.

    Args:
        filename (str): The filename of the recording.
        db (Session, optional): The database session. Defaults to Depends(get_db).
    Returns:
        dict: The deletion status.
    """
    # 1. Delete from DB
    recording = (
        db.query(RecordingModel).filter(RecordingModel.filename == filename).first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    db.delete(recording)
    db.commit()

    # 2. Delete from Filesystem
    file_path = RECORDINGS_DIR / filename
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    return {"status": "ok", "filename": filename}
