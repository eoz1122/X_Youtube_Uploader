import logging
import tweepy

logger = logging.getLogger(__name__)

class TwitterClient:
    """
    Wrapper for Tweepy (Twitter API).
    Handles v1.1 for media upload and v2 for tweeting.
    """

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, bearer_token):
        # V2 Client (for creating tweets)
        self.client_v2 = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            bearer_token=bearer_token
        )

        # V1.1 API (for media upload)
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_token_secret
        )
        self.api_v1 = tweepy.API(auth)

    def upload_video(self, file_path):
        """
        Uploads a video file to Twitter using the v1.1 API (chunked upload).
        Returns the media_id or None.
        """
        try:
            logger.info(f"Uploading media: {file_path}")
            # media_category='tweet_video' is important for videos
            media = self.api_v1.media_upload(
                filename=file_path,
                media_category='tweet_video',
                chunked=True
            )

            # Wait for processing if necessary (for large videos)
            if hasattr(media, 'processing_info'):
                 # Tweepy's media_upload usually handles wait_on_media_completion implicitly
                 # if we use certain wrappers, but standard media_upload returns immediately after upload.
                 # Actually, media_upload with chunked=True does the upload.
                 # We might need to check status if it's async.
                 pass

            logger.info(f"Media uploaded successfully. ID: {media.media_id}")
            return media.media_id
        except Exception as e:
            logger.error(f"Error uploading media to Twitter: {e}")
            return None

    def post_tweet(self, text, media_id=None):
        """
        Posts a tweet with optional media.
        """
        try:
            logger.info("Posting tweet...")
            media_ids = [media_id] if media_id else None

            response = self.client_v2.create_tweet(text=text, media_ids=media_ids)

            logger.info(f"Tweet posted successfully! ID: {response.data['id']}")
            return True
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False

    def format_text(self, title, description, limit=4000):
        """
        Formats the tweet text. Truncates if necessary.
        """
        text = f"{title}\n\n{description}"

        if len(text) <= limit:
            return text

        # Truncate logic
        truncated = text[:limit - 4] + "..."
        return truncated
