import pytest
from unittest.mock import patch, MagicMock

from app.services.ai.tools import search_broll
from app.services.ai.assets import MockAssetSearchStrategy


def test_mock_asset_search():
    # Test standard sync wrapper map
    result_str = search_broll("city skyline", provider="mock")
    assert "mock-0" in result_str
    assert "success" in result_str
    assert "city_skyline" in result_str


@patch("app.services.ai.assets.httpx.Client")
def test_pexels_asset_search(mock_httpx_client_class, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "test_pexels_key")
    from app.config import get_settings
    get_settings.cache_clear()

    # Configure context manager for httpx testing
    mock_client_instance = MagicMock()
    mock_httpx_client_class.return_value.__enter__.return_value = mock_client_instance
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 12345,
                "video_files": [{"width": 1920, "height": 1080, "link": "http://hd_video_link.mp4"}],
                "image": "http://preview_img.jpg"
            }
        ]
    }
    mock_client_instance.get.return_value = mock_response

    result_str = search_broll("mountains", provider="pexels")
    
    assert "hd_video_link.mp4" in result_str
    mock_client_instance.get.assert_called_once()
    assert "mountains" in mock_client_instance.get.call_args[1]["params"]["query"]
