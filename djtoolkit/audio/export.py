"""Write processed audio to disk and tag it with the BPM."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def output_name(src: Path, bpm: float, fmt: str) -> str:
    bpm_txt = f"{bpm:.1f}".rstrip("0").rstrip(".")
    return f"{src.stem} - {bpm_txt}bpm.{fmt}"


def write_audio(path: Path, data: np.ndarray, sr: int, fmt: str, bpm: float) -> list[str]:
    """Write `data` to `path`. Returns a list of non-fatal warnings (e.g. tagging)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    if fmt == "wav" or fmt == "flac":
        sf.write(str(path), data, sr, subtype="PCM_24")
    elif fmt == "mp3":
        import imageio_ffmpeg

        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "in.wav"
            sf.write(str(wav), data, sr, subtype="PCM_24")
            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(),
                    "-y",
                    "-i",
                    str(wav),
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "320k",
                    str(path),
                ],
                check=True,
                capture_output=True,
            )
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    try:
        _tag_bpm(path, fmt, bpm)
    except Exception as e:  # tagging must never lose the export
        warnings.append(f"Exported, but could not write BPM tag: {e}")
    return warnings


def _tag_bpm(path: Path, fmt: str, bpm: float) -> None:
    value = str(int(round(bpm)))
    if fmt == "flac":
        from mutagen.flac import FLAC

        f = FLAC(str(path))
        f["bpm"] = value
        f.save()
    else:  # mp3 and wav both carry ID3 TBPM
        from mutagen.id3 import TBPM

        if fmt == "wav":
            from mutagen.wave import WAVE

            f = WAVE(str(path))
        else:
            from mutagen.mp3 import MP3

            f = MP3(str(path))
        if f.tags is None:
            f.add_tags()
        f.tags.add(TBPM(encoding=3, text=value))
        f.save()
