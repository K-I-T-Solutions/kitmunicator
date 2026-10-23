"""Eigene Voicemail-Ansagen.

Der Browser liefert fertiges WAV (16 kHz, 16 bit, mono) — genau das Format, das
Asterisk als .wav16 ohne Umrechnung abspielt. Das Backend prüft nur und legt ab.
Asterisk sieht das Verzeichnis read-only, der Dialplan spielt
<dir>/<durchwahl>.wav16 statt der Standardansage, wenn die Datei existiert.
"""
import io
import os
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import get_settings

SAMPLE_RATE = 16_000
MIN_SECONDS = 1
MAX_SECONDS = 60
MAX_BYTES = 44 + SAMPLE_RATE * 2 * MAX_SECONDS + 1024


class GreetingError(ValueError):
    pass


@dataclass
class GreetingInfo:
    duration_seconds: int
    updated_at: datetime


def greeting_path(extension: str) -> Path:
    return Path(get_settings().GREETINGS_DIR) / f"{extension}.wav16"


def _duration(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data)) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, SAMPLE_RATE):
                raise GreetingError("Erwartet WAV mit 16 kHz, 16 bit, mono")
            return wav.getnframes() / SAMPLE_RATE
    except (wave.Error, EOFError) as exc:
        raise GreetingError("Keine gültige WAV-Datei") from exc


def save_greeting(extension: str, data: bytes) -> GreetingInfo:
    if len(data) > MAX_BYTES:
        raise GreetingError(f"Ansage zu lang (max. {MAX_SECONDS} s)")
    seconds = _duration(data)
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise GreetingError(f"Ansage muss {MIN_SECONDS}–{MAX_SECONDS} Sekunden lang sein")

    path = greeting_path(extension)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Erst komplett schreiben, dann umbenennen — Asterisk liest nie eine halbe Datei
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.chmod(tmp, 0o644)
    tmp.replace(path)
    return GreetingInfo(round(seconds), datetime.now(timezone.utc))


def read_greeting(extension: str) -> GreetingInfo | None:
    path = greeting_path(extension)
    if not path.is_file():
        return None
    with wave.open(str(path)) as wav:
        seconds = wav.getnframes() / wav.getframerate()
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return GreetingInfo(round(seconds), mtime)


def delete_greeting(extension: str) -> None:
    greeting_path(extension).unlink(missing_ok=True)
