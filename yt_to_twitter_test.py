import os
import json
import sys
import time
from datetime import datetime
import googleapiclient.discovery
import yt_dlp
import tweepy
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- CONFIGURATION ---
# Load credentials from environment variables for security
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

# Support both naming conventions (TWITTER_ or X_)
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("X_API_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET") or os.getenv("X_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN") or os.getenv("X_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET") or os.getenv("X_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN") or os.getenv("X_BEARER_TOKEN")

STATE_FILE = "processed_videos.json"

def load_processed_videos():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

def save_processed_video(video_id, processed_set):
    processed_set.add(video_id)
    with open(STATE_FILE, "w") as f:
        json.dump(list(processed_set), f)

def parse_duration(duration_str):
    """
    Parses YouTube ISO 8601 duration string (e.g., PT1M, PT59S) to seconds.
    This is a simplified parser.
    """
    import re
    # Pattern to extract hours, minutes, seconds
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    
    h, m, s = match.groups()
    hours = int(h) if h else 0
    minutes = int(m) if m else 0
    seconds = int(s) if s else 0
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds

def get_latest_shorts(youtube, channel_id, limit=5):
    """
    Fetches latest videos from the channel's uploads playlist and filters for Shorts (<= 60s).
    """
    try:
        # 1. Get Uploads Playlist ID
        res = youtube.channels().list(id=channel_id, part="contentDetails").execute()
        if not res["items"]:
            print("Channel not found.")
            return []
        
        uploads_playlist_id = res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. Get recent videos from that playlist
        playlist_items = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="contentDetails",
            maxResults=limit
        ).execute()

        video_ids = [item["contentDetails"]["videoId"] for item in playlist_items.get("items", [])]
        
        if not video_ids:
            return []

        # 3. Get details for these videos to check duration
        vid_res = youtube.videos().list(
            id=",".join(video_ids),
            part="snippet,contentDetails"
        ).execute()
        
        shorts = []
        for item in vid_res.get("items", []):
            duration_str = item["contentDetails"]["duration"]
            seconds = parse_duration(duration_str)
            title = item["snippet"]["title"]
            vid_id = item["id"]
            
            # Filter: <= 180 seconds (3 minutes)
            if seconds <= 180:
                shorts.append({"id": vid_id, "title": title})
            else:
                print(f"Skipping '{title}' (Duration: {seconds}s) - longer than 180s.")
                
        return shorts

    except Exception as e:
        print(f"Error fetching YouTube videos: {e}")
        return []

def download_video(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_filename = f"{video_id}.mp4"
    
    # Best video+audio that is mp4. 
    # For Shorts, usually 'best' is fine, but we ensure mp4 container.
    # Add oauth2 to fix bot detection
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'username': 'oauth2', 
        'password': '' # This will prompt for code, but since we are headless we might need a cache.
    }
    # REVISION: Interactive oauth2 doesn't work well headless without cache.
    # Better approach: Try to use 'ios' client or just ignore the error if it's transient, 
    # but the error is persistent.
    # We will try adding 'extractor_args' to force a specific client that might be less restricted.
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': False, # Showing output so user can see Auth Code
        'no_warnings': False,
        'username': 'oauth2', 
        'password': '' 
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading {video_id}...")
            ydl.download([url])
        
        if os.path.exists(output_filename):
            return output_filename
    except Exception as e:
        print(f"Error downloading video: {e}")
    
    return None

def upload_to_twitter(video_path, text, client_v2, auth_v1):
    try:
        print("Uploading media to Twitter...")
        # Media upload still requires v1.1 API
        api_v1 = tweepy.API(auth_v1)
        media = api_v1.media_upload(video_path)
        
        print("Posting tweet...")
        # Create Tweet with v2 Client
        client_v2.create_tweet(text=text, media_ids=[media.media_id])
        print("Tweet posted successfully!")
        return True
    except Exception as e:
        print(f"Error uploading to Twitter: {e}")
        return False

def run_check(youtube, client_v2, auth_v1, processed):
    """
    Performs a single check for new videos and processes them.
    """
    try:
        new_videos = get_latest_shorts(youtube, YOUTUBE_CHANNEL_ID)
        
        # Reverse order to post oldest new video first if multiple
        for video in reversed(new_videos):
            if video["id"] in processed:
                continue
                
            print(f"Found new video: {video['title']} ({video['id']})")
            
            # Download
            file_path = download_video(video["id"])
            
            if file_path:
                # Upload
                success = upload_to_twitter(file_path, video["title"], client_v2, auth_v1)
                
                # Cleanup CRITICAL STEP
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Deleted local file: {file_path}")
                    except OSError as e:
                        print(f"Error checking file after deletion: {e}")
                
                if success:
                    save_processed_video(video["id"], processed)
                    print(f"Processed {video['id']}. Waiting 60s before next (if any)...")
                    time.sleep(60) # Rate limit safety
                else:
                    print(f"Failed to upload {video['id']}. Will try again next run.")
                    
    except Exception as e:
        print(f"Error during check cycle: {e}")

def main():
    # 1. Validate Env Vars
    if not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, TWITTER_CONSUMER_KEY, 
                TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("Error: Missing environment variables. Please check your configuration.")
        sys.exit(1)

    # 2. Setup Clients
    # Note: We rebuild clients inside loop or keep them valid? 
    # API clients are usually stable, but let's keep them here.
    try:
        import pytz
    except ImportError:
        print("Error: pytz module is missing. Please run 'pip install pytz'")
        sys.exit(1)

    print("Starting YouTube Monitor (Daily 10:00 - 19:00 TR time)...")
    
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    client_v2 = tweepy.Client(
        consumer_key=TWITTER_CONSUMER_KEY,
        consumer_secret=TWITTER_CONSUMER_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    
    auth_v1 = tweepy.OAuth1UserHandler(
        TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
    )

    tz_tr = pytz.timezone("Europe/Istanbul")

    # NO TIMEZONE OR LOOP CHECK
    print("Executing immediate check...")
    
    # Load state fresh each time to be safe
    processed = load_processed_videos()
    
    # Run the check logic once
    run_check(youtube, client_v2, auth_v1, processed)
    
    print("Test execution finished.")

if __name__ == "__main__":
    main()
