
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.recorder import AudioRecorder

@pytest.fixture
def recorder():
    return AudioRecorder()

@pytest.mark.asyncio
async def test_write_chunk_while_recording(recorder):
    recorder.start_recording(settings={}, session_id="test_session")   
    async_mock = MagicMock()
    async_mock.write = AsyncMock()
    
    with patch('aiofiles.open', new_callable=AsyncMock) as mock_open:
        mock_open.return_value = async_mock
        
        chunk = b'\x00\x00'
        await recorder.write_chunk(chunk)
        
        # Should verify aiofiles.open called
        mock_open.assert_awaited_once()
        # Verify write called
        async_mock.write.assert_awaited_with(chunk)

def test_start_recording(recorder):
    recorder.start_recording(settings={}, session_id="test_sess", sample_rate=44100, channels=2)
    assert recorder.is_recording
    assert recorder.session_id == "test_sess"
    assert recorder.sample_rate == 44100
    assert recorder.channels == 2
    assert recorder.filepath_raw is not None

@pytest.mark.asyncio
async def test_stop_recording(recorder):
    # Setup
    recorder.start_recording(settings={}, session_id="test_sess", sample_rate=44100, channels=1)
    recorder.filepath_raw = MagicMock()
    recorder.filepath_raw.exists.return_value = True
    
    # Mock raw file read
    with patch('builtins.open', new_callable=MagicMock) as mock_builtin_open:
        files = MagicMock()
        files.read.return_value = b'\x00\x00' * 100
        mock_builtin_open.return_value.__enter__.return_value = files
        
        # Mock wave open
        with patch('wave.open', new_callable=MagicMock) as mock_wave_open:
            wav_file = MagicMock()
            mock_wave_open.return_value.__enter__.return_value = wav_file
            
            # Mock file handle close
            mock_handle = MagicMock()
            mock_handle.close = AsyncMock()
            recorder.file_handle = mock_handle
            
            # Mock unlink
            recorder.filepath_raw.unlink = MagicMock()

            # Mock DB
            db = MagicMock()
            db.add = MagicMock()
            db.commit = MagicMock()
            db.refresh = MagicMock()
            
            # Action
            entry = await recorder.stop_recording(db)
            
            # Assertions
            assert not recorder.is_recording
            mock_handle.close.assert_awaited()
            wav_file.setnchannels.assert_called_with(1)
            assert entry is not None
            assert entry.session_id == "test_sess"

@pytest.mark.asyncio
async def test_write_chunk_while_not_recording(recorder):
    recorder.is_recording = False
    chunk = b'\x00\x00'
    await recorder.write_chunk(chunk)
    # Should do nothing

@pytest.mark.asyncio
async def test_stop_recording_while_not_recording(recorder):
    recorder.is_recording = False
    db = MagicMock()
    entry = await recorder.stop_recording(db)
    assert entry is None

@pytest.mark.asyncio
async def test_stop_recording_with_invalid_raw_file(recorder):
    recorder.start_recording(settings={}, session_id="test_sess", sample_rate=44100, channels=1)
    recorder.filepath_raw = MagicMock()
    recorder.filepath_raw.exists.return_value = False
    db = MagicMock()
    entry = await recorder.stop_recording(db)
    assert entry is None