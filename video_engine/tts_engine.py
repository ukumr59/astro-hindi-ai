"""Resilient Text-to-Speech (TTS) engine for AstroPratidin.

Features:
- Exponential backoff retry logic for transient WebSocket / network errors.
- Automatic fallback voice in case of voice-specific throttling.
- File integrity check to guarantee non-empty, valid audio.
- Support for both async and sync execution.
"""
import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

import edge_tts

logger = logging.getLogger("video_engine.tts")

PRIMARY_VOICE = "hi-IN-SwaraNeural"
FALLBACK_VOICE = "hi-IN-MadhurNeural"


async def speak_with_retry(
    text: str,
    path: Path,
    voice: str = PRIMARY_VOICE,
    fallback_voice: str = FALLBACK_VOICE,
    rate: str = "+5%",
    volume: str = "+0%",
    max_retries: int = 3,
    initial_delay: float = 2.0,
) -> Path:
    """Synthesize speech using edge-tts with exponential backoff and voice fallback.

    Args:
        text: The text string to synthesize into speech.
        path: Path where the resulting MP3 audio file will be saved.
        voice: Primary voice name (default: hi-IN-SwaraNeural).
        fallback_voice: Alternate voice name if primary fails (default: hi-IN-MadhurNeural).
        rate: Speech rate adjustment string (e.g. '+5%').
        volume: Speech volume adjustment string (e.g. '+0%').
        max_retries: Maximum number of attempts before raising an error.
        initial_delay: Initial wait in seconds before first retry.

    Returns:
        Path to the successfully generated audio file.

    Raises:
        RuntimeError: If all retries fail or output file is corrupt/empty.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    text_clean = text.strip()
    if not text_clean:
        raise ValueError("Cannot synthesize speech for empty text")

    last_error: Optional[Exception] = None
    current_voice = voice

    for attempt in range(1, max_retries + 1):
        try:
            # On 2nd retry onwards, switch to fallback voice if available
            if attempt >= 2 and fallback_voice and current_voice != fallback_voice:
                current_voice = fallback_voice
                logger.warning(f"TTS attempt {attempt}: Switching to fallback voice '{current_voice}'")

            # Remove partial file from previous failed attempt
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass

            communicate = edge_tts.Communicate(
                text=text_clean,
                voice=current_voice,
                rate=rate,
                volume=volume,
            )
            await communicate.save(str(path))

            # Integrity check
            if not path.is_file() or path.stat().st_size < 100:
                raise RuntimeError(
                    f"Generated TTS audio file is missing or suspiciously small ({path.stat().st_size if path.exists() else 0} bytes)"
                )

            # Success
            return path

        except Exception as exc:
            last_error = exc
            logger.warning(f"TTS attempt {attempt}/{max_retries} failed for '{path.name}' using '{current_voice}': {exc}")
            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"TTS synthesis failed after {max_retries} attempts for '{path}': {last_error}"
    ) from last_error


def speak(
    text: str,
    path: Path,
    voice: str = PRIMARY_VOICE,
    rate: str = "+5%",
    volume: str = "+0%",
) -> Path:
    """Synchronous convenience wrapper around speak_with_retry."""
    return asyncio.run(
        speak_with_retry(
            text=text,
            path=path,
            voice=voice,
            rate=rate,
            volume=volume,
        )
    )
