"""Media Transcription Strategies.

Implements capabilities to read audio/video files and return transcripts (OpenAI Whisper, Mock).
"""

from __future__ import annotations

import abc
import os
from typing import Any

from app.config import get_settings


class ITranscriptionStrategy(abc.ABC):
    """Base interface for transcribing audio strings from media assets."""

    @abc.abstractmethod
    def transcribe(self, file_path: str) -> str:
        """Reads a local asset file and returns the full transcript text."""
        raise NotImplementedError


class OpenAITranscriptionStrategy(ITranscriptionStrategy):
    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        import openai
        self.client = openai.Client(api_key=settings.openai_api_key)

    def transcribe(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Asset does not exist: {file_path}")
            
        with open(file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
            return str(transcript)


class MockTranscriptionStrategy(ITranscriptionStrategy):
    """Fallback Transcription strategy returning dummy text."""
    def transcribe(self, file_path: str) -> str:
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"Asset does not exist: {file_path}")
        return "This is a mock transcription of the video. The user talks about editing and cutting."


def get_transcription_strategy(provider: str = "openai") -> ITranscriptionStrategy:
    """Factory for selecting Transcription strategy."""
    if provider == "openai":
        return OpenAITranscriptionStrategy()
    return MockTranscriptionStrategy()
