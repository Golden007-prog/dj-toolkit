"""Connects a Transport to the computer's speakers with Qt's QAudioSink (pull mode)."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QIODevice, QObject
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from ..audio.transport import Transport

BUFFER_SECONDS = 0.05  # small buffer = scrubbing answers your hand quickly


class _Pull(QIODevice):
    """The sink calls readData() whenever it wants more audio; we answer from the transport."""

    def __init__(self, transport: Transport, parent=None):
        super().__init__(parent)
        self.transport = transport
        self.calls = 0
        self.frames_served = 0
        self.open(QIODevice.OpenModeFlag.ReadOnly)

    def isSequential(self) -> bool:  # noqa: N802
        return True

    def bytesAvailable(self) -> int:  # noqa: N802
        return (1 << 20) + super().bytesAvailable()  # always ready: silence is rendered when idle

    def readData(self, maxlen):  # noqa: N802
        frame_bytes = 2 * self.transport.ch
        frames = int(maxlen) // frame_bytes
        if frames <= 0:
            return b""
        self.calls += 1
        self.frames_served += frames
        pcm = (self.transport.render(frames) * 32767.0).astype("<i2")
        return pcm.tobytes()

    def writeData(self, _data):  # noqa: N802
        return 0


class AudioOutput(QObject):
    """Owns the sink. `available` is False when there is no audio device (the UI says so)."""

    def __init__(self, transport: Transport, parent=None):
        super().__init__(parent)
        self.transport = transport
        self.sink: QAudioSink | None = None
        self.device = QMediaDevices.defaultAudioOutput()
        self.available = not self.device.isNull() and self._format_ok()
        self._pull: _Pull | None = None

    def _format_ok(self) -> bool:
        fmt = QAudioFormat()
        fmt.setSampleRate(self.transport.sr)
        fmt.setChannelCount(self.transport.ch)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._fmt = fmt
        return self.device.isFormatSupported(fmt)

    def start(self) -> bool:
        if not self.available or self.sink is not None:
            return self.sink is not None
        self.sink = QAudioSink(self.device, self._fmt, self)
        self.sink.setBufferSize(int(BUFFER_SECONDS * self.transport.sr * 2 * self.transport.ch))
        self._pull = _Pull(self.transport, self)
        self.sink.start(self._pull)
        return True

    def stop(self) -> None:
        if self.sink is not None:
            self.sink.stop()
            self.sink.deleteLater()
            self.sink = None
        self._pull = None

    @property
    def latency_s(self) -> float:
        """How far behind the transport position the speakers are (what you hear vs. what is rendered)."""
        return BUFFER_SECONDS if self.sink is not None else 0.0

    def heard_time(self) -> float:
        """The song position you are hearing right now."""
        return max(0.0, self.transport.time - (self.latency_s if self.transport.playing else 0.0))

    def diagnostics(self) -> dict:
        return {
            "available": self.available,
            "running": self.sink is not None,
            "calls": getattr(self._pull, "calls", 0),
            "frames": getattr(self._pull, "frames_served", 0),
            "device": self.device.description() if not self.device.isNull() else "none",
        }


def fit_for_output(data: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """Return (data, sr) in a format the default speakers accept, resampling or down-mixing if needed."""
    dev = QMediaDevices.defaultAudioOutput()
    if dev.isNull():
        return data, sr
    fmt = QAudioFormat()
    fmt.setSampleRate(sr)
    fmt.setChannelCount(data.shape[1])
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    if dev.isFormatSupported(fmt):
        return data, sr
    pref = dev.preferredFormat()
    target_sr, target_ch = pref.sampleRate() or 48000, min(max(pref.channelCount(), 1), 2)
    import librosa

    if target_sr != sr:
        data = np.stack(
            [librosa.resample(data[:, c], orig_sr=sr, target_sr=target_sr) for c in range(data.shape[1])], axis=1
        )
    if data.shape[1] != target_ch:
        data = (
            data.mean(axis=1, keepdims=True).repeat(target_ch, axis=1)
            if target_ch > 1
            else data.mean(axis=1, keepdims=True)
        )
    return np.ascontiguousarray(data, dtype=np.float32), target_sr
