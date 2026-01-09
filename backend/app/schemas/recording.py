from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class RecordingBase(BaseModel):
    filename: str
    duration_seconds: float
    timestamp: datetime
    session_id: Optional[str] = None
    settings: Optional[dict[str, Any]] = None
    channels: int = 2


class Recording(RecordingBase):
    id: int

    class ConfigDict:
        from_attributes = True
