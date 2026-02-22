import os
import time
import logging
import yt_dlp

logger = logging.getLogger(__name__)

class VideoDownloader:
    """
    Handles video downloading using yt-dlp with retry logic.
    """

    def __init__(self, cookies_file=None):
        self.cookies_file = cookies_file

    def download(self, video_id, retries=3):
        """
        Downloads a video by ID. returns the filepath or None if failed.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        output_filename = f"{video_id}.mp4"

        # Determine format options
        # We prefer 'best[ext=mp4]' to avoid merging if ffmpeg is missing,
        # but often higher quality requires merging.
        # Given the environment constraints, we will try best compatibility.

        # Options for yt-dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_filename,
            'quiet': True,
            'no_warnings': True,
            # 'verbose': True, # Uncomment for debugging
        }

        if self.cookies_file and os.path.exists(self.cookies_file):
            logger.info(f"Using cookies file: {self.cookies_file}")
            ydl_opts['cookiefile'] = self.cookies_file

        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Downloading {video_id} (Attempt {attempt}/{retries})...")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if os.path.exists(output_filename):
                    file_size = os.path.getsize(output_filename)
                    if file_size > 0:
                        logger.info(f"Download successful: {output_filename} ({file_size} bytes)")
                        return output_filename
                    else:
                        logger.warning("Downloaded file is empty.")
                        os.remove(output_filename)

            except Exception as e:
                logger.warning(f"Download error (Attempt {attempt}): {e}")
                # Wait before retry (exponential backoff)
                time.sleep(2 ** attempt)

        logger.error(f"Failed to download {video_id} after {retries} attempts.")
        return None

    def cleanup(self, filepath):
        """Safely removes a file."""
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Deleted file: {filepath}")
            except OSError as e:
                logger.error(f"Error deleting file {filepath}: {e}")
