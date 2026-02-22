import os
import json
import logging

logger = logging.getLogger(__name__)

class StateManager:
    """
    Manages the state of processed videos to avoid duplicate processing.
    Currently uses a simple JSON file.
    """

    def __init__(self, state_file="processed_videos.json"):
        self.state_file = state_file
        self.processed = self._load()

    def _load(self):
        """Loads processed video IDs from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
                    logger.warning(f"State file format invalid (expected list), resetting.")
                    return set()
            except json.JSONDecodeError:
                logger.warning(f"State file corrupted, resetting.")
                return set()
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
                return set()
        return set()

    def is_processed(self, video_id):
        return video_id in self.processed

    def mark_processed(self, video_id):
        """Adds a video ID to the processed set and persists to disk."""
        if video_id in self.processed:
            return

        self.processed.add(video_id)
        self._save()

    def _save(self):
        """Persists the processed set to disk atomically."""
        try:
            temp_file = f"{self.state_file}.tmp"
            with open(temp_file, "w") as f:
                json.dump(list(self.processed), f)
            os.replace(temp_file, self.state_file)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")
