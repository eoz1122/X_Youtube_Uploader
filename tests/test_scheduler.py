import pytest
import datetime
from src.bot import Bot
from src.config import Config
from unittest.mock import MagicMock

class MockConfig:
    START_HOUR = 10
    END_HOUR = 19
    CHECK_INTERVAL_SECONDS = 3600
    TIMEZONE = "UTC" # easier to test

    # Dummy credentials to satisfy Bot.__init__
    YOUTUBE_API_KEY = "dummy_yt"
    YOUTUBE_CHANNEL_ID = "dummy_ch"
    TWITTER_CONSUMER_KEY = "dummy_ck"
    TWITTER_CONSUMER_SECRET = "dummy_cs"
    TWITTER_ACCESS_TOKEN = "dummy_at"
    TWITTER_ACCESS_TOKEN_SECRET = "dummy_ats"
    TWITTER_BEARER_TOKEN = "dummy_bt"
    COOKIES_FILE = "dummy_cookies.txt"
    STATE_FILE = "dummy_state.json"

@pytest.fixture
def bot_instance():
    # We create a dummy bot and inject a mock config
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.config.Config.load", lambda: MockConfig())
        m.setattr("src.logger.setup_logging", lambda: MagicMock())
        # Also mock services to avoid init errors or side effects
        m.setattr("src.youtube_client.YouTubeClient", MagicMock())
        m.setattr("src.twitter_client.TwitterClient", MagicMock())
        m.setattr("src.downloader.VideoDownloader", MagicMock())
        m.setattr("src.state_manager.StateManager", MagicMock())

        bot = Bot()
        bot.config = MockConfig()
        return bot

def test_is_within_window(bot_instance):
    # 12:00 -> True (10 <= 12 <= 19)
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    assert bot_instance.is_within_window(dt) is True

    # 09:00 -> False
    dt = datetime.datetime(2023, 1, 1, 9, 0, 0)
    assert bot_instance.is_within_window(dt) is False

    # 19:59 -> True (19 is inclusive)
    dt = datetime.datetime(2023, 1, 1, 19, 59, 59)
    assert bot_instance.is_within_window(dt) is True

    # 20:00 -> False
    dt = datetime.datetime(2023, 1, 1, 20, 0, 0)
    assert bot_instance.is_within_window(dt) is False

def test_seconds_until_next_window_before_start(bot_instance):
    # Now is 08:00. Start is 10:00. Should be 2 hours (7200s).
    now = datetime.datetime(2023, 1, 1, 8, 0, 0)
    seconds = bot_instance.seconds_until_next_window(now)
    assert seconds == 7200

def test_seconds_until_next_window_after_end(bot_instance):
    # Now is 20:00. Start is 10:00 tomorrow.
    now = datetime.datetime(2023, 1, 1, 20, 0, 0)
    seconds = bot_instance.seconds_until_next_window(now)
    # 4 hours to midnight + 10 hours to 10am = 14 hours = 50400s
    assert seconds == 14 * 3600
