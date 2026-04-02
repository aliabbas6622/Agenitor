"""Text-to-Speech (TTS) Strategies.

Implements multiple AI voiceover providers (ElevenLabs, OpenAI, Local Mock).
"""

from __future__ import annotations

import abc
import os
import uuid
from typing import Any

from elevenlabs.client import ElevenLabs

from app.config import get_settings


class ITTSStrategy(abc.ABC):
    """Base interface for generating speech from text."""

    @abc.abstractmethod
    def generate_speech(self, text: str, voice_id: str = "default") -> str:
        """Generates audio and returns the local file path to the audio asset."""
        raise NotImplementedError


class ElevenLabsTTSStrategy(ITTSStrategy):
    def __init__(self):
        settings = get_settings()
        if not settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY is not configured.")
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    def generate_speech(self, text: str, voice_id: str = "Rachel") -> str:
        # We perform sync generation for now as a tool execution step
        audio_generator = self.client.generate(text=text, voice=voice_id)
        
        # Save to a temporary asset directory
        os.makedirs("/tmp/assets/audio", exist_ok=True)
        out_path = f"/tmp/assets/audio/{uuid.uuid4()}.mp3"
        with open(out_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
                
        return out_path


class OpenAITTSStrategy(ITTSStrategy):
    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        import openai
        self.client = openai.Client(api_key=settings.openai_api_key)

    def generate_speech(self, text: str, voice_id: str = "alloy") -> str:
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice_id,  # alloy, echo, fable, onyx, nova, shimmer
            input=text
        )
        os.makedirs("/tmp/assets/audio", exist_ok=True)
        out_path = f"/tmp/assets/audio/{uuid.uuid4()}.mp3"
        response.stream_to_file(out_path)
        return out_path


class MockTTSStrategy(ITTSStrategy):
    """Fallback TTS strategy that just creates a dummy empty audio file."""
    def generate_speech(self, text: str, voice_id: str = "dummy") -> str:
        os.makedirs("/tmp/assets/audio", exist_ok=True)
        out_path = f"/tmp/assets/audio/mock-{uuid.uuid4()}.mp3"
        with open(out_path, "wb") as f:
            f.write(b"MOCK_AUDIO_DATA")
        return out_path


def get_tts_strategy(provider: str = "elevenlabs") -> ITTSStrategy:
    """Factory for selecting TTS strategy."""
    if provider == "elevenlabs":
        return ElevenLabsTTSStrategy()
    elif provider == "openai":
        return OpenAITTSStrategy()
    return MockTTSStrategy()
