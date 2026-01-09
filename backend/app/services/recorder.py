import aiofiles
from datetime import datetime, timezone
from app.db.models import Recording
from sqlalchemy.orm import Session
from app.constants import APP_DIR
import wave

RECORDINGS_DIR = APP_DIR / "recordings_data"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.current_file = None
        self.start_time = None
        self.settings = {}
        self.frames = []
        self.channels = 2
        self.file_handle = None

    def start_recording(
        self,
        settings: dict,
        session_id: str,
        sample_rate: int = 44100,
        channels: int = 2,
    ):
        self.is_recording = True
        self.settings = settings
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.start_time = datetime.now(timezone.utc)
        self.frames = []
        # Let's stream PCM to a .raw file using aiofiles, then convert to WAV on stop.

        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.filename = f"rec_{timestamp}.wav"
        self.temp_filename = f"rec_{timestamp}.raw"
        self.filepath_raw = RECORDINGS_DIR / self.temp_filename
        self.file_handle = None

    async def write_chunk(self, chunk: bytes):
        if not self.is_recording:
            return

        if self.file_handle is None:
            self.file_handle = await aiofiles.open(self.filepath_raw, "wb")

        if self.file_handle:
            await self.file_handle.write(chunk)

    async def stop_recording(self, db: Session):
        if not self.is_recording:
            return None

        self.is_recording = False
        if self.file_handle:
            await self.file_handle.close()
            self.file_handle = None

        # Convert raw to wav
        final_path = RECORDINGS_DIR / self.filename

        # Read raw data back to write properly with wave lib
        if self.filepath_raw.exists():
            with open(self.filepath_raw, "rb") as raw_f:
                pcm_data = raw_f.read()

            # Cleanup raw
            self.filepath_raw.unlink()

            with wave.open(final_path.as_posix(), "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm_data)

            # Calculate duration
            # 2 bytes per sample, n channels = 2 * n bytes per frame
            duration = len(pcm_data) / (2 * self.channels * self.sample_rate)

            # Save to DB
            recording_entry = Recording(
                filename=self.filename,
                duration_seconds=duration,
                timestamp=self.start_time,
                settings=self.settings,
                session_id=self.session_id,
                channels=self.channels,
            )
            db.add(recording_entry)
            db.commit()
            db.refresh(recording_entry)
            return recording_entry
        return None
