import pytest
import numpy as np
from app.core.audio_processor import AudioProcessor


@pytest.fixture
def processor():
    return AudioProcessor(sample_rate=44100, channels=2)


def test_initialization(processor):
    assert processor.sample_rate == 44100
    assert processor.channels == 2
    assert processor.gain == 0.0
    assert not processor.filter_enabled


def test_stereo_processing(processor):
    # Create fake stereo data: 2 samples per frame * 2 channels * 1024 frames = 4096 bytes
    # Value 1000 for all
    data = np.full(1024 * 2 * 2, 0, dtype=np.int16)
    # Add some signal
    data[0] = 16000  # L
    data[1] = 16000  # R

    chunk_bytes = data.tobytes()

    processed_bytes, rms, spectrum, panning = processor.process_chunk(chunk_bytes)

    assert isinstance(processed_bytes, bytes)
    assert len(processed_bytes) == len(chunk_bytes)
    assert isinstance(rms, float)
    assert isinstance(spectrum, list)
    assert isinstance(panning, float)


def test_stereo_truncation(processor):
    # Create fake stereo data: 2 samples per frame * 2 channels * 1024 frames + 1 = 4097 bytes
    # Value 1000 for all
    data = np.full(1024 * 2 * 2 + 1, 0, dtype=np.int16)
    # Add some signal
    data[0] = 16000  # L
    data[1] = 16000  # R

    chunk_bytes = data.tobytes()

    processed_bytes, rms, spectrum, panning = processor.process_chunk(chunk_bytes)

    assert isinstance(processed_bytes, bytes)
    assert len(processed_bytes) == len(chunk_bytes) - 2
    assert isinstance(rms, float)
    assert isinstance(spectrum, list)
    assert isinstance(panning, float)


def test_mono_processing():
    processor = AudioProcessor(channels=1)
    # Mono data: 1024 samples * 2 bytes = 2048 bytes
    data = np.full(1024, 0, dtype=np.int16)
    data[0] = 16000

    chunk_bytes = data.tobytes()

    processed_bytes, rms, spectrum, panning = processor.process_chunk(chunk_bytes)

    # Output should be stereo! (2 channels)
    # 1024 frames * 2 channels * 2 bytes = 4096 bytes
    assert len(processed_bytes) == 1024 * 2 * 2
    assert len(processed_bytes) == 2 * len(chunk_bytes)


def test_dsp_gain(processor):
    processor.update_settings(
        gain=6.0, filter_enabled=False, cutoff_freq=1000, integration_time=0
    )
    # 6dB gain ~= 2x amplitude

    data = np.array([1000, 1000], dtype=np.int16)  # L, R
    chunk_bytes = data.tobytes()

    processed_bytes, _, _, _ = processor.process_chunk(chunk_bytes)
    result = np.frombuffer(processed_bytes, dtype=np.int16)

    # Expected: 2000
    # Tolerance due to float conversion
    assert 1990 <= result[0] <= 2010


def test_panning_left(processor):
    # Disable smoothing for instant response
    processor.update_settings(
        gain=0.0, filter_enabled=False, cutoff_freq=1000, integration_time=0
    )

    # Left channel has signal, Right is silence
    data = np.array([16000, 0, 16000, 0], dtype=np.int16)
    chunk_bytes = data.tobytes()

    _, _, _, panning = processor.process_chunk(chunk_bytes)

    # Pan should be negative (Left)
    assert panning < -0.9


def test_panning_right(processor):
    # Disable smoothing
    processor.update_settings(
        gain=0.0, filter_enabled=False, cutoff_freq=1000, integration_time=0
    )

    # Right channel has signal
    data = np.array([0, 16000, 0, 16000], dtype=np.int16)
    chunk_bytes = data.tobytes()

    _, _, _, panning = processor.process_chunk(chunk_bytes)

    # Pan should be positive (Right)
    assert panning > 0.9


def test_update_filter_params(processor):
    # Enable filter
    processor.update_settings(
        filter_enabled=True, cutoff_freq=2000, integration_time=0.1
    )
    assert processor.filter_enabled
    assert processor.cutoff_freq == 2000
    assert processor.zi is not None

    # Change params
    old_zi = processor.zi.copy()
    processor.update_settings(filter_enabled=True, cutoff_freq=500)
    assert processor.cutoff_freq == 500
    # Zi should be re-initialized or updated.
    assert processor.b is not None


def test_signal_clipping(processor):
    # Gain huge to force clipping
    processor.update_settings(gain=20.0, filter_enabled=False, integration_time=0)

    # Input max value
    data = np.full(100, 32000, dtype=np.int16)
    chunk_bytes = data.tobytes()

    processed_bytes, _, _, _ = processor.process_chunk(chunk_bytes)
    result = np.frombuffer(processed_bytes, dtype=np.int16)

    # Check max and min
    # If it wrapped around, it would be negative or small.
    # Since we clip, it should be 32767.
    assert np.all(result >= 32700)  # Tolerate slight precision diffs
    assert np.max(result) <= 32767


def test_smoothing(processor):
    # 1. With smoothing
    processor.update_settings(integration_time=0.5)

    # Initial silence
    processor.process_chunk(np.zeros(1024, dtype=np.int16).tobytes())

    # Burst of loud noise
    loud_chunk = np.full(1024, 20000, dtype=np.int16).tobytes()
    _, rms_smoothed, _, _ = processor.process_chunk(loud_chunk)

    # 2. Without smoothing
    processor.update_settings(integration_time=0.0)
    # Reset internal state is not exposed, but update_settings with 0 should make alpha=1 (instant)

    _, rms_instant, _, _ = processor.process_chunk(loud_chunk)

    # Smoothed value should be significantly lower than instant value (it's rising)
    assert rms_smoothed < rms_instant


def test_filter_zi_initialization_fallback(processor):
    # 1. Enable filter
    processor.update_settings(filter_enabled=True, cutoff_freq=1000)

    # 2. Force zi to None to simulate lost state or initial condition bypass
    processor.zi = None

    # 3. Process a chunk
    # Stereo data
    chunk_bytes = np.full(1024 * 2 * 2, 1000, dtype=np.int16).tobytes()
    processor.process_chunk(chunk_bytes)

    # 4. Assert zi was re-initialized
    # Shape should be (order, 2) where order is max(len(a), len(b)) - 1
    # Butterworth order 2 -> len(a)=3, len(b)=3 -> order=2. Shape (2, 2)
    assert processor.zi is not None
    assert processor.zi.shape[1] == 2  # Stereo
