"""Tools exposed to the AI Agent via LiteLLM function calling."""

from __future__ import annotations

import json
from enum import Enum

from pydantic import BaseModel, Field

from app.services.ai.tts import get_tts_strategy
from app.services.ai.assets import get_asset_strategy
from app.services.ai.transcription import get_transcription_strategy


class TranscribeMediaParams(BaseModel):
    """Parameters for transcribing a media file (audio/video)."""
    file_path: str = Field(..., description="Absolute local path to the media file needing transcription.")
    provider: str = Field("openai", description="Transcription provider to use: 'openai', or 'mock'")


def transcribe_media(file_path: str, provider: str = "openai") -> str:
    """
    Transcribes a media file to text via ASR algorithms like Whisper.
    """
    try:
        strategy = get_transcription_strategy(provider)
        transcript = strategy.transcribe(file_path)
        return json.dumps({
            "status": "success",
            "transcript": transcript,
            "message": "Transcription successful."
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })


class SearchBRollParams(BaseModel):
    """Parameters for looking up stock b-roll assets based on a query."""
    query: str = Field(..., description="Keywords representing the visual requested (e.g., 'forest sunset').")
    limit: int = Field(1, description="Number of video clips to return.")
    provider: str = Field("mock", description="Asset provider to use: 'pexels', 'pixabay', or 'mock'")


def search_broll(query: str, limit: int = 1, provider: str = "mock") -> str:
    """
    Looks up external B-Roll video metadata based on keyword querying.
    Must return a JSON string outlining available paths.
    """
    try:
        strategy = get_asset_strategy(provider)
        assets = strategy.search_video(query, limit)
        return json.dumps({
            "status": "success",
            "assets": assets,
            "message": f"Found {len(assets)} videos based on {query}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })


class GenerateVoiceoverParams(BaseModel):
    """Parameters for generating an audio voiceover from text."""
    text: str = Field(..., description="The script or text to be spoken.")
    voice_id: str = Field("Rachel", description="The voice ID or name to use. E.g., Rachel, alloy")
    provider: str = Field("elevenlabs", description="TTS provider to use: 'elevenlabs', 'openai', or 'mock'")


def generate_voiceover_track(text: str, voice_id: str = "Rachel", provider: str = "elevenlabs") -> str:
    """
    Generates a voiceover audio file.
    Must return a JSON string containing the file path for the LLM.
    """
    try:
        strategy = get_tts_strategy(provider)
        file_path = strategy.generate_speech(text, voice_id)
        return json.dumps({
            "status": "success",
            "asset_path": file_path,
            "duration": 5.0, # Mock duration for simplicity
            "message": "Generated audio file successfully."
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

# Mapping used by our engine to dynamically dispatch calls
AVAILABLE_TOOLS_MAP = {
    "generate_voiceover_track": generate_voiceover_track,
    "search_broll": search_broll,
    "transcribe_media": transcribe_media,
}

# Python definitions matching OpenAI's JSON Schema for tool injection
LITELLM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_voiceover_track",
            "description": "Generate an audio voiceover file from text string and return the asset path.",
            "parameters": GenerateVoiceoverParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_broll",
            "description": "Searches for stock video b-roll footage and returns URLs of matching content.",
            "parameters": SearchBRollParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_media",
            "description": "Transcribes an audio or video file located on disk into raw text, allowing content analysis.",
            "parameters": TranscribeMediaParams.model_json_schema()
        }
    }
]
