"""Asset Search Strategies.

Implements multiple AI asset lookups for stock videos/images (Pexels, Pixabay, Mock).
"""

from __future__ import annotations

import abc
import json
from typing import Any

import httpx
from app.config import get_settings


class IAssetSearchStrategy(abc.ABC):
    """Base interface for fetching external stock assets."""

    @abc.abstractmethod
    def search_video(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        """Returns a list of asset metadata dictionaries containing download URLs."""
        raise NotImplementedError


class PexelsSearchStrategy(IAssetSearchStrategy):
    def __init__(self):
        settings = get_settings()
        if not settings.pexels_api_key:
            raise ValueError("PEXELS_API_KEY is not configured.")
        self.api_key = settings.pexels_api_key
        self.base_url = "https://api.pexels.com/videos/search"

    def search_video(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        headers = {"Authorization": self.api_key}
        params = {"query": query, "per_page": limit, "orientation": "landscape"}

        # For a sync tool call wrapper, we block with httpx.Client
        with httpx.Client() as client:
            response = client.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for video in data.get("videos", []):
                # Grab arguably the highest quality or first fallback link
                video_files = video.get("video_files", [])
                if not video_files:
                    continue
                    
                # Sort to find an HD link if possible
                sd_files = sorted(video_files, key=lambda x: x.get("width", 0), reverse=True)
                download_url = sd_files[0].get("link")
                
                results.append({
                    "id": str(video["id"]),
                    "provider": "pexels",
                    "width": sd_files[0].get("width"),
                    "height": sd_files[0].get("height"),
                    "download_url": download_url,
                    "preview_image": video.get("image")
                })
            return results


class PixabaySearchStrategy(IAssetSearchStrategy):
    def __init__(self):
        settings = get_settings()
        if not settings.pixabay_api_key:
            raise ValueError("PIXABAY_API_KEY is not configured.")
        self.api_key = settings.pixabay_api_key
        self.base_url = "https://pixabay.com/api/videos/"

    def search_video(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        params = {"key": self.api_key, "q": query, "per_page": max(3, limit)}  # Pixabay requires min 3 per_page

        with httpx.Client() as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for video in data.get("hits", [])[:limit]:
                # Grab the medium or large link
                videos = video.get("videos", {})
                best_video = videos.get("large") or videos.get("medium") or videos.get("small")
                if not best_video:
                    continue
                
                results.append({
                    "id": str(video["id"]),
                    "provider": "pixabay",
                    "width": best_video.get("width"),
                    "height": best_video.get("height"),
                    "download_url": best_video.get("url"),
                    "preview_image": video.get("picture_id")
                })
            return results


class MockAssetSearchStrategy(IAssetSearchStrategy):
    """Fallback Asset strategy returning mock URL paths."""
    def search_video(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        return [{
            "id": f"mock-{i}",
            "provider": "mock",
            "width": 1920,
            "height": 1080,
            "download_url": f"https://mock-asset-library.com/video/{query.replace(' ', '_')}_{i}.mp4",
            "preview_image": "https://mock-asset-library.com/preview.jpg"
        } for i in range(limit)]


def get_asset_strategy(provider: str = "mock") -> IAssetSearchStrategy:
    """Factory for selecting Asset Search strategy."""
    if provider == "pexels":
        return PexelsSearchStrategy()
    elif provider == "pixabay":
        return PixabaySearchStrategy()
    return MockAssetSearchStrategy()
