from pydantic import BaseModel


class WebSocketCommand(BaseModel):
    action: str
    gain: float = 0.0
    filter_enabled: bool = False
    cutoff_freq: float = 1000.0
    integration_time: float = 0.5
    sample_rate: int = 44100
    channels: int = 2
