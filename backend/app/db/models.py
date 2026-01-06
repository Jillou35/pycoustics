
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from .base import Base
from datetime import datetime, timezone

class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    duration_seconds = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    settings = Column(JSON) # Store gain, filter params used
    session_id = Column(String, index=True)
    channels = Column(Integer, default=2)
