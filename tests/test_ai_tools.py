import pytest
from unittest.mock import patch

from app.services.ai.tools import generate_voiceover_track
from app.services.ai.tts import MockTTSStrategy


def test_mock_tts_generation():
    # Force the strategy to use mock
    result_str = generate_voiceover_track("Hello world", provider="mock")
    assert "mock-" in result_str
    assert "success" in result_str


@patch("app.services.ai.tts.ElevenLabs")
def test_elevenlabs_tts_strategy(mock_elevenlabs_cls, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
    # Need to clear cache so it builds a new Settings object with the env var
    from app.config import get_settings
    get_settings.cache_clear()

    # Mock the generator response from elevenlabs
    mock_instance = mock_elevenlabs_cls.return_value
    mock_instance.generate.return_value = [b"audio_data_chunk"]

    result_str = generate_voiceover_track("Test script", provider="elevenlabs")
    
    assert "asset_path" in result_str
    assert mock_instance.generate.called
    assert mock_instance.generate.call_args[1]["text"] == "Test script"

