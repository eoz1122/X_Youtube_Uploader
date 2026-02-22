import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file
load_dotenv()

@dataclass(frozen=True)
class Config:
    # YouTube
    YOUTUBE_API_KEY: str
    YOUTUBE_CHANNEL_ID: str

    # Twitter / X
    TWITTER_CONSUMER_KEY: str
    TWITTER_CONSUMER_SECRET: str
    TWITTER_ACCESS_TOKEN: str
    TWITTER_ACCESS_TOKEN_SECRET: str
    TWITTER_BEARER_TOKEN: str

    # Scheduling
    TIMEZONE: str = "Europe/Istanbul"
    START_HOUR: int = 10
    END_HOUR: int = 19
    CHECK_INTERVAL_SECONDS: int = 3600  # 1 hour

    # Files
    STATE_FILE: str = "processed_videos.json"
    COOKIES_FILE: str = "cookies.txt"

    @classmethod
    def load(cls):
        # YouTube
        yt_api_key = os.getenv("YOUTUBE_API_KEY")
        yt_channel_id = os.getenv("YOUTUBE_CHANNEL_ID")

        # Twitter
        tw_consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("X_API_KEY")
        tw_consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET") or os.getenv("X_API_SECRET")
        tw_access_token = os.getenv("TWITTER_ACCESS_TOKEN") or os.getenv("X_ACCESS_TOKEN")
        tw_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET") or os.getenv("X_ACCESS_SECRET")
        tw_bearer_token = os.getenv("TWITTER_BEARER_TOKEN") or os.getenv("X_BEARER_TOKEN")

        # Validation
        missing = []
        if not yt_api_key: missing.append("YOUTUBE_API_KEY")
        if not yt_channel_id: missing.append("YOUTUBE_CHANNEL_ID")
        if not tw_consumer_key: missing.append("TWITTER_CONSUMER_KEY")
        if not tw_consumer_secret: missing.append("TWITTER_CONSUMER_SECRET")
        if not tw_access_token: missing.append("TWITTER_ACCESS_TOKEN")
        if not tw_access_token_secret: missing.append("TWITTER_ACCESS_TOKEN_SECRET")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            YOUTUBE_API_KEY=yt_api_key,
            YOUTUBE_CHANNEL_ID=yt_channel_id,
            TWITTER_CONSUMER_KEY=tw_consumer_key,
            TWITTER_CONSUMER_SECRET=tw_consumer_secret,
            TWITTER_ACCESS_TOKEN=tw_access_token,
            TWITTER_ACCESS_TOKEN_SECRET=tw_access_token_secret,
            TWITTER_BEARER_TOKEN=tw_bearer_token or "",

            TIMEZONE=os.getenv("TIMEZONE", "Europe/Istanbul"),
            START_HOUR=int(os.getenv("START_HOUR", 10)),
            END_HOUR=int(os.getenv("END_HOUR", 19)),
            CHECK_INTERVAL_SECONDS=int(os.getenv("CHECK_INTERVAL_SECONDS", 3600)),

            STATE_FILE=os.getenv("STATE_FILE", "processed_videos.json"),
            COOKIES_FILE=os.getenv("COOKIES_FILE", "cookies.txt")
        )
