import numpy as np
import scipy.signal as signal
from typing import Optional, Tuple


class AudioProcessor:
    def __init__(
        self, sample_rate: int = 44100, channels: int = 2, chunk_size: int = 1024
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.filter_enabled = False
        self.gain = 0.0  # 0 dB default
        self.cutoff_freq = 1000.0  # Default 1kHz low-pass
        self.smoothing = 0.5  # Default smoothing factor

        # Initialize filter state (for continuity between chunks)
        self.zi: Optional[np.ndarray] = None
        self._update_filter()

        # Smoothing state
        self._rms_db_smooth: float = -100.0
        self._spectrum_smooth: Optional[list[float]] = None
        self._panning_smooth: float = 0.0

    def _update_filter(self):
        """Precompute filter coefficients."""
        nyquist = 0.5 * self.sample_rate
        normal_cutoff = self.cutoff_freq / nyquist
        # 4th order butterworth low-pass
        self.b, self.a = signal.butter(4, normal_cutoff, btype="low", analog=False)
        if self.zi is None:
            zi_proto = signal.lfilter_zi(self.b, self.a)
            # Initialize for stereo (2 channels)
            # zi dimensions must range from (order, 2)
            self.zi = np.tile(zi_proto[:, np.newaxis], (1, 2))

    def update_settings(
        self,
        gain: float = 0.0,
        filter_enabled: bool = False,
        cutoff_freq: float | None = None,
        integration_time: float = 0.5,
    ):
        self.gain = gain
        self.filter_enabled = False if cutoff_freq is None else filter_enabled
        # Calculate smoothing alpha based on integration time
        # alpha = exp(-dt / tau)
        # dt = chunk_size / sample_rate
        dt = self.chunk_size / self.sample_rate
        if integration_time <= 0.001:
            self.smoothing = 0.0  # No smoothing
        else:
            self.smoothing = np.exp(-dt / integration_time)

        if cutoff_freq is not None and self.cutoff_freq != cutoff_freq:
            self.cutoff_freq = cutoff_freq
            self.zi = None  # Reset filter state on frequency change to avoid artifacts, or handle arguably smoother
            self._update_filter()

    def process_chunk(
        self, chunk_bytes: bytes
    ) -> Tuple[bytes, float, list[float], float]:
        """
        Process raw PCM 16-bit bytes.
        Input: Interleaved Stereo (L, R, L, R...) OR Mono (M, M...)
        Returns: (processed_bytes, rms_db_level, spectrum, panning)
        """
        # 1. Convert Input
        audio_stereo = self._convert_to_stereo_float(chunk_bytes)

        # 2. Apply DSP (Gain, Filter)
        audio_stereo = self._apply_dsp_effects(audio_stereo)

        # 3. Analyze (RMS, Spectrum, Panning)

        # Clipping protection for output
        audio_clamped = np.clip(audio_stereo, -1.0, 1.0)

        rms_db, spectrum, panning = self._analyze_audio(audio_stereo)

        # 4. Convert Output
        processed_bytes = self._convert_to_output_bytes(audio_clamped)

        return processed_bytes, rms_db, spectrum, panning

    def _convert_to_stereo_float(self, chunk_bytes: bytes) -> np.ndarray:
        # Convert bytes to numpy array (int16)
        audio_data_flat = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32)

        # Normalize to -1.0 to 1.0
        audio_data_flat /= 32768.0

        if self.channels == 1:
            # Mono input: (N,) -> Expand to (N, 2) by duplication
            audio_stereo = np.column_stack((audio_data_flat, audio_data_flat))
        else:
            # Stereo input: (2N,) -> Reshape to (N, 2)
            if len(audio_data_flat) % 2 != 0:
                audio_data_flat = audio_data_flat[:-1]  # Truncate odd sample
            audio_stereo = audio_data_flat.reshape(-1, 2)

        return audio_stereo

    def _apply_dsp_effects(self, audio_stereo: np.ndarray) -> np.ndarray:
        # Apply Gain
        linear_gain = 10 ** (self.gain / 20.0)
        audio_stereo *= linear_gain

        # Apply Filter if enabled (Apply to both channels)
        if self.filter_enabled:
            # lfilter with zi state for continuity
            if self.zi is None:
                zi_proto = signal.lfilter_zi(self.b, self.a)
                self.zi = np.tile(zi_proto[:, np.newaxis], (1, 2))

            # Filter along axis 0 (time)
            audio_stereo, self.zi = signal.lfilter(
                self.b, self.a, audio_stereo, axis=0, zi=self.zi
            )

        return audio_stereo

    def _analyze_audio(
        self, audio_stereo: np.ndarray
    ) -> Tuple[float, list[float], float]:
        # Calculate RMS for each channel
        rms_channels = np.sqrt(np.mean(audio_stereo**2, axis=0))  # [rms_L, rms_R]
        rms_L, rms_R = rms_channels[0], rms_channels[1]

        # Mono Mix for Spectrum & VuMeter
        mono_mix = np.mean(audio_stereo, axis=1)

        # 1. RMS (dB)
        rms = np.sqrt(np.mean(mono_mix**2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -96.0

        # 2. Panning
        denominator = rms_L + rms_R
        if denominator > 0.0001:
            panning = (rms_R - rms_L) / denominator
        else:
            panning = 0.0
        panning = max(-1.0, min(1.0, panning))

        # 3. Spectrum
        fft_spectrum = np.fft.rfft(mono_mix * np.hanning(len(mono_mix)))
        fft_magnitude = np.abs(fft_spectrum)

        # Normalize: |X[k]| / N * 2 (because mono_mix len is N, not separate)
        fft_magnitude = fft_magnitude / len(mono_mix) * 2

        fft_db = 20 * np.log10(fft_magnitude + 1e-10)

        # Resample to 32 bins
        n_bins = 32
        fft_len = len(fft_db)
        effective_len = int(fft_len * 0.5)

        if effective_len < 2:
            indices = np.zeros(n_bins, dtype=int)
        else:
            indices = np.geomspace(1, effective_len - 1, n_bins, dtype=int)

        indices = np.clip(indices, 0, fft_len - 1)
        spectrum_db = fft_db[indices].tolist()

        # Normalize Spectrum (0.0 to 1.0) for UI
        min_db, max_db = -80.0, 0.0
        spectrum_normalized = [
            max(0.0, min(1.0, (val - min_db) / (max_db - min_db)))
            for val in spectrum_db
        ]

        # Apply Smoothing
        return self._apply_smoothing(rms_db, spectrum_normalized, panning)

    def _apply_smoothing(
        self, rms_db: float, spectrum: list[float], panning: float
    ) -> Tuple[float, list[float], float]:
        alpha = self.smoothing

        # Smooth RMS
        if self._rms_db_smooth < -99.0:
            self._rms_db_smooth = rms_db
        else:
            self._rms_db_smooth = (alpha * self._rms_db_smooth) + (
                (1.0 - alpha) * rms_db
            )

        # Smooth Panning
        self._panning_smooth = (alpha * self._panning_smooth) + (
            (1.0 - alpha) * panning
        )

        # Smooth Spectrum
        if self._spectrum_smooth is None or len(self._spectrum_smooth) != len(spectrum):
            self._spectrum_smooth = spectrum
        else:
            self._spectrum_smooth = [
                (alpha * prev) + ((1.0 - alpha) * curr)
                for prev, curr in zip(self._spectrum_smooth, spectrum)
            ]

        return (
            float(self._rms_db_smooth),
            self._spectrum_smooth,
            float(self._panning_smooth),
        )

    def _convert_to_output_bytes(self, audio_clamped: np.ndarray) -> bytes:
        # Convert back to int16 (Interleaved)
        # Flatten back to 1D array: [L0, R0, L1, R1, ...]
        processed_int16 = (audio_clamped * 32767.0).astype(np.int16).flatten()
        return processed_int16.tobytes()
