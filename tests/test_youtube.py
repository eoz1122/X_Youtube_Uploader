import datetime
import pytest
from unittest.mock import MagicMock
from src.youtube_client import YouTubeClient

@pytest.fixture
def mock_youtube_service():
    client = YouTubeClient("dummy_key")
    client.youtube = MagicMock()
    return client

def test_get_latest_shorts_filters_duration(mock_youtube_service):
    # Mock playlist items response
    mock_youtube_service.youtube.channels().list().execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU123"}}}]
    }

    mock_youtube_service.youtube.playlistItems().list().execute.return_value = {
        "items": [{"contentDetails": {"videoId": "vid1"}}, {"contentDetails": {"videoId": "vid2"}}]
    }

    # Mock videos list response
    # vid1: 59s (Short)
    # vid2: 300s (Long)
    mock_youtube_service.youtube.videos().list().execute.return_value = {
        "items": [
            {
                "id": "vid1",
                "snippet": {
                    "title": "Short Video",
                    "description": "desc",
                    "publishedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                "contentDetails": {"duration": "PT59S"}
            },
            {
                "id": "vid2",
                "snippet": {
                    "title": "Long Video",
                    "description": "desc",
                    "publishedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                "contentDetails": {"duration": "PT5M"}
            }
        ]
    }

    shorts = mock_youtube_service.get_latest_shorts("channel_id")

    assert len(shorts) == 1
    assert shorts[0]["id"] == "vid1"
    assert shorts[0]["duration"] == 59.0

def test_get_latest_shorts_filters_date(mock_youtube_service):
    # Mock playlist items response
    mock_youtube_service.youtube.channels().list().execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU123"}}}]
    }

    mock_youtube_service.youtube.playlistItems().list().execute.return_value = {
        "items": [{"contentDetails": {"videoId": "old_vid"}}]
    }

    # Mock videos list response
    # old_vid: 48 hours old
    old_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_youtube_service.youtube.videos().list().execute.return_value = {
        "items": [
            {
                "id": "old_vid",
                "snippet": {
                    "title": "Old Video",
                    "description": "desc",
                    "publishedAt": old_date
                },
                "contentDetails": {"duration": "PT30S"}
            }
        ]
    }

    shorts = mock_youtube_service.get_latest_shorts("channel_id", max_age_hours=24)

    assert len(shorts) == 0
