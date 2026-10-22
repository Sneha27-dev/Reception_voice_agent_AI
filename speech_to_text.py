"""
speech_to_text.py
------------------
Converts an audio file into a plain-text transcript using OpenAI's
Whisper model, run locally (no audio ever leaves the machine).

Why Whisper: it is free, runs offline after the model is downloaded once,
handles varied accents and background noise reasonably well, and is the
most common practical choice for a project like this (see README ->
Design Decisions).

The whisper model is loaded lazily and cached, so it is only downloaded /
loaded once per process even if multiple calls are transcribed.
"""

import os
import wave
from pathlib import Path
from typing import Optional

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}

_model = None  # cached whisper model, loaded on first use


class TranscriptionError(Exception):
    """Raised for anything that goes wrong turning audio into text:
    missing file, unsupported format, empty audio, or a model failure."""


def _load_model():
    """Lazily imports and loads the Whisper model.

    Kept as a separate function (rather than a module-level import) so
    that the rest of the app can still be imported and unit-tested even
    in environments where the `openai-whisper` package or its model
    weights are not available (for example, a sandboxed CI runner with
    no internet access) - only transcription itself will fail there.
    """
    global _model
    if _model is not None:
        return _model

    try:
        import whisper  # openai-whisper package
    except ImportError as exc:
        raise TranscriptionError(
            "The 'openai-whisper' package is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    model_size = os.getenv("WHISPER_MODEL", "base")
    try:
        _model = whisper.load_model(model_size)
    except Exception as exc:  # noqa: BLE001 - whisper can raise many error types
        raise TranscriptionError(
            f"Could not load Whisper model '{model_size}'. This usually means "
            f"either the model could not be downloaded (no internet access on "
            f"first run) or it is corrupted. Original error: {exc}"
        ) from exc

    return _model


def _validate_audio_file(audio_path: str) -> Path:
    path = Path(audio_path)

    if not path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise TranscriptionError(
            f"Unsupported audio format '{path.suffix}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if path.stat().st_size == 0:
        raise TranscriptionError(f"Audio file is empty: {audio_path}")

    # For WAV files we can cheaply sanity-check that they contain audio
    # frames before handing them to Whisper, which gives a clearer error
    # message than whatever whisper/ffmpeg would raise internally.
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wav_file:
                if wav_file.getnframes() == 0:
                    raise TranscriptionError(f"Audio file has no audio frames: {audio_path}")
        except wave.Error as exc:
            raise TranscriptionError(f"Invalid or corrupted WAV file: {audio_path} ({exc})") from exc

    return path


def transcribe_audio(audio_path: str) -> str:
    """Transcribes an audio file to text.

    Raises TranscriptionError with a human-readable message on any
    failure (missing file, bad format, empty audio, or model failure).
    Never returns an empty/whitespace-only string silently.
    """
    path = _validate_audio_file(audio_path)

    model = _load_model()

    try:
        result = model.transcribe(str(path), fp16=False)
    except Exception as exc:  # noqa: BLE001 - surface any whisper/ffmpeg failure
        raise TranscriptionError(f"Transcription failed for {audio_path}: {exc}") from exc

    transcript: Optional[str] = (result or {}).get("text", "").strip()

    if not transcript:
        raise TranscriptionError(
            f"Transcription produced an empty transcript for {audio_path}. "
            f"The audio may be silent, too noisy, or too short."
        )

    return transcript
