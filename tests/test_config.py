import os
import pytest
from src.config import Config

def test_load_valid_config(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "dummy_yt")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "dummy_channel")
    monkeypatch.setenv("TWITTER_CONSUMER_KEY", "dummy_ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "dummy_cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "dummy_at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "dummy_ats")
    monkeypatch.setenv("TWITTER_BEARER_TOKEN", "dummy_bt")

    config = Config.load()
    assert config.YOUTUBE_API_KEY == "dummy_yt"
    assert config.START_HOUR == 10  # default

def test_missing_config_raises_error(monkeypatch):
    # clear env
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Missing required environment variables"):
        Config.load()
