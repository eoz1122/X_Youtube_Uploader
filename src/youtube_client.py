import logging
import datetime
import isodate
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class YouTubeClient:
    """
    Wrapper for YouTube Data API v3.
    """

    def __init__(self, api_key):
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def get_channel_uploads_playlist_id(self, channel_id):
        """Fetches the 'uploads' playlist ID for a channel."""
        try:
            res = self.youtube.channels().list(
                id=channel_id,
                part="contentDetails"
            ).execute()

            if not res.get("items"):
                logger.error(f"Channel not found: {channel_id}")
                return None

            return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except HttpError as e:
            logger.error(f"YouTube API Error (get_channel): {e}")
            return None

    def get_latest_shorts(self, channel_id, max_results=10, max_age_hours=24):
        """
        Fetches recent videos from the channel and filters for Shorts.

        Args:
            channel_id (str): The YouTube Channel ID.
            max_results (int): Number of recent videos to inspect.
            max_age_hours (int): Ignore videos older than this.

        Returns:
            list: List of dicts with video details.
        """
        uploads_playlist_id = self.get_channel_uploads_playlist_id(channel_id)
        if not uploads_playlist_id:
            return []

        try:
            # Get recent videos from playlist
            playlist_items = self.youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part="contentDetails",
                maxResults=max_results
            ).execute()

            video_ids = [item["contentDetails"]["videoId"] for item in playlist_items.get("items", [])]
            if not video_ids:
                return []

            # Get details (duration, snippet)
            vid_res = self.youtube.videos().list(
                id=",".join(video_ids),
                part="snippet,contentDetails"
            ).execute()

            shorts = []
            now_utc = datetime.datetime.now(datetime.timezone.utc)

            for item in vid_res.get("items", []):
                vid_id = item["id"]
                title = item["snippet"]["title"]
                description = item["snippet"]["description"]
                published_at_str = item["snippet"]["publishedAt"]
                duration_str = item["contentDetails"]["duration"]

                # Parse Duration
                try:
                    duration = isodate.parse_duration(duration_str)
                    total_seconds = duration.total_seconds()
                except Exception as e:
                    logger.warning(f"Error parsing duration for {vid_id}: {e}")
                    continue

                # Parse Published Date
                try:
                    # ISO 8601 format: 2023-01-01T12:00:00Z
                    # Note: Python's fromisoformat usually handles Z if newer,
                    # but isodate or dateutil is safer. We'll use strptime for standard YouTube format.
                    published_at = datetime.datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
                    published_at = published_at.replace(tzinfo=datetime.timezone.utc)

                    age_hours = (now_utc - published_at).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        logger.debug(f"Skipping {vid_id}: Too old ({age_hours:.1f}h > {max_age_hours}h)")
                        continue
                except ValueError as e:
                    logger.warning(f"Error parsing date for {vid_id}: {e}")
                    # Allow if date parsing fails but duration is good?
                    # Probably better to skip to avoid reposting ancient stuff.
                    continue

                # Filter for Shorts (<= 180s)
                if total_seconds <= 180:
                    shorts.append({
                        "id": vid_id,
                        "title": title,
                        "description": description,
                        "duration": total_seconds
                    })
                else:
                    logger.debug(f"Skipping {vid_id}: Too long ({total_seconds}s)")

            # Sort by published date? The playlist returns most recent first usually.
            # We want to process oldest first if we find multiple new ones,
            # but usually we process most recent.
            # The calling logic should handle order.
            return shorts

        except HttpError as e:
            logger.error(f"YouTube API Error (get_videos): {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in YouTube client: {e}")
            return []
