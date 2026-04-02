import pytest
import os
from unittest.mock import patch, MagicMock

from app.services.ai.tools import transcribe_media
from app.services.ai.transcription import MockTranscriptionStrategy


def test_mock_transcription(tmp_path):
    # Mock file must exist to pass Mock validation
    dummy_file = tmp_path / "dummy.mp4"
    dummy_file.write_text("dummy binary data")
    
    result_str = transcribe_media(str(dummy_file), provider="mock")
    assert "success" in result_str
    assert "mock transcription" in result_str


@patch("openai.Client")
def test_openai_whisper_transcription(mock_openai_client, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    from app.config import get_settings
    get_settings.cache_clear()

    # Mock the client response
    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.audio.transcriptions.create.return_value = "The transcribed text."

    dummy_file = tmp_path / "actual.mp3"
    dummy_file.write_text("audio contents")

    result_str = transcribe_media(str(dummy_file), provider="openai")
    
    assert "The transcribed text" in result_str
    assert mock_client_instance.audio.transcriptions.create.called
    kwargs = mock_client_instance.audio.transcriptions.create.call_args[1]
    assert kwargs["model"] == "whisper-1"
