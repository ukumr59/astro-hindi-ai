"""Unit tests for the resilient TTS engine."""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from video_engine.tts_engine import speak_with_retry, PRIMARY_VOICE, FALLBACK_VOICE


@pytest.mark.asyncio
async def test_empty_text_raises_value_error(tmp_path):
    target = tmp_path / "empty.mp3"
    with pytest.raises(ValueError, match="empty text"):
        await speak_with_retry("   ", target)


@pytest.mark.asyncio
async def test_tts_retry_and_success(tmp_path):
    target = tmp_path / "success.mp3"

    mock_comm = MagicMock()
    # First attempt fails, second attempt succeeds and writes a file
    attempt = 0

    async def fake_save(dest):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise ConnectionError("Transient network failure")
        Path(dest).write_bytes(b"dummy mp3 data" * 20)

    mock_comm.save = AsyncMock(side_effect=fake_save)

    with patch("edge_tts.Communicate", return_value=mock_comm):
        result = await speak_with_retry(
            "परीक्षण पाठ",
            target,
            max_retries=3,
            initial_delay=0.01,
        )
        assert result == target
        assert target.exists()
        assert target.stat().st_size > 100
        assert attempt == 2


@pytest.mark.asyncio
async def test_tts_exhaust_retries_raises_runtime_error(tmp_path):
    target = tmp_path / "fail.mp3"

    mock_comm = MagicMock()
    mock_comm.save = AsyncMock(side_effect=ConnectionError("Persistent server error"))

    with patch("edge_tts.Communicate", return_value=mock_comm):
        with pytest.raises(RuntimeError, match="TTS synthesis failed after 2 attempts"):
            await speak_with_retry(
                "परीक्षण पाठ",
                target,
                max_retries=2,
                initial_delay=0.01,
            )
