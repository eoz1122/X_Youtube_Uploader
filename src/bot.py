import time
import datetime
import pytz
import logging
from .config import Config
from .logger import setup_logging
from .youtube_client import YouTubeClient
from .twitter_client import TwitterClient
from .downloader import VideoDownloader
from .state_manager import StateManager

class Bot:
    def __init__(self):
        self.logger = setup_logging()
        self.config = Config.load()

        # Initialize components
        self.youtube = YouTubeClient(self.config.YOUTUBE_API_KEY)
        self.twitter = TwitterClient(
            consumer_key=self.config.TWITTER_CONSUMER_KEY,
            consumer_secret=self.config.TWITTER_CONSUMER_SECRET,
            access_token=self.config.TWITTER_ACCESS_TOKEN,
            access_token_secret=self.config.TWITTER_ACCESS_TOKEN_SECRET,
            bearer_token=self.config.TWITTER_BEARER_TOKEN
        )
        self.downloader = VideoDownloader(cookies_file=self.config.COOKIES_FILE)
        self.state_manager = StateManager(self.config.STATE_FILE)

        self.tz = pytz.timezone(self.config.TIMEZONE)

    def run(self):
        self.logger.info(f"Starting Bot (Timezone: {self.config.TIMEZONE})")

        while True:
            try:
                now = datetime.datetime.now(self.tz)

                if self.is_within_window(now):
                    self.logger.info(f"Current time {now.strftime('%H:%M')} is within window ({self.config.START_HOUR}-{self.config.END_HOUR}). Running cycle...")
                    self.process_cycle()

                    self.logger.info(f"Cycle complete. Sleeping for {self.config.CHECK_INTERVAL_SECONDS} seconds...")
                    time.sleep(self.config.CHECK_INTERVAL_SECONDS)
                else:
                    sleep_seconds = self.seconds_until_next_window(now)
                    next_start = now + datetime.timedelta(seconds=sleep_seconds)
                    self.logger.info(f"Outside operating hours. Sleeping until {next_start.strftime('%Y-%m-%d %H:%M:%S')} ({sleep_seconds/3600:.2f} hours)...")
                    time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                self.logger.info("Bot stopped by user.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                time.sleep(60)  # Prevent rapid error looping

    def is_within_window(self, dt):
        """Checks if the given datetime is within the configured operating hours."""
        # Inclusive range [START, END] to match original behavior (10-19 means up to 19:59)
        return self.config.START_HOUR <= dt.hour <= self.config.END_HOUR

    def seconds_until_next_window(self, dt):
        """Calculates seconds until the next start time (10:00)."""
        target_hour = self.config.START_HOUR

        # If currently before start hour today
        if dt.hour < target_hour:
            next_start = dt.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        else:
            # If after start hour (and presumably after end hour since we checked is_within_window),
            # or if currently within window but logic called incorrectly (safe fallback)
            # Schedule for tomorrow
            next_start = dt + datetime.timedelta(days=1)
            next_start = next_start.replace(hour=target_hour, minute=0, second=0, microsecond=0)

        return (next_start - dt).total_seconds()

    def process_cycle(self):
        """
        Main logic: Fetch -> Filter -> Download -> Upload -> Cleanup
        """
        # 1. Fetch recent shorts
        shorts = self.youtube.get_latest_shorts(
            self.config.YOUTUBE_CHANNEL_ID,
            max_results=5,
            max_age_hours=24 # Configurable?
        )

        # 2. Process (Reverse order to handle oldest new video first)
        for video in reversed(shorts):
            vid_id = video["id"]
            title = video["title"]

            if self.state_manager.is_processed(vid_id):
                continue

            self.logger.info(f"Found new candidate: {title} ({vid_id})")

            filepath = None
            try:
                # 3. Download
                filepath = self.downloader.download(vid_id)
                if not filepath:
                    self.logger.warning(f"Skipping {vid_id} due to download failure.")
                    continue

                # 4. Upload
                # Format text
                text = self.twitter.format_text(title, video["description"])

                # Upload Media
                media_id = self.twitter.upload_video(filepath)
                if not media_id:
                     self.logger.warning(f"Skipping {vid_id} due to media upload failure.")
                     continue

                # Post Tweet
                if self.twitter.post_tweet(text, media_id):
                    self.state_manager.mark_processed(vid_id)
                    self.logger.info(f"Successfully processed {vid_id}. Waiting 60s...")
                    time.sleep(60) # Safety buffer between tweets
                else:
                    self.logger.error(f"Failed to post tweet for {vid_id}")

            except Exception as e:
                self.logger.error(f"Error processing video {vid_id}: {e}", exc_info=True)
            finally:
                # 5. Cleanup (Crucial)
                if filepath:
                    self.downloader.cleanup(filepath)

if __name__ == "__main__":
    bot = Bot()
    bot.run()
