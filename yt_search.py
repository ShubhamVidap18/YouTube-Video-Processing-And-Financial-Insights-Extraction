import argparse
import csv
import logging
import yt_dlp
import os
import sys
import re
import time
import random
from datetime import datetime
import io

# ✅ Logging setup
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("youtube_channel_scraper.log", encoding="utf-8"),
            logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
        ]
    )

# ✅ Sanitize file/folder name
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name.replace(' ', '_'))

# ✅ Load already processed URLs to resume
def load_processed_urls(progress_file):
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            return set(row[0] for row in reader if row)
    return set()

# ✅ Save processed URL to resume file
def save_processed_url(progress_file, url):
    with open(progress_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([url])

# ✅ Create header for resume file
def save_progress_header(progress_file):
    if not os.path.exists(progress_file):
        with open(progress_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Processed URL"])

# ✅ Create CSV header for output data
def save_header_to_csv(filename):
    if not os.path.exists(filename):
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Video ID", "Title", "URL", "Duration", "Uploader",
                "Channel Name", "Upload Date", "View Count", "Like Count",
                "Description", "Channel URL", "Thumbnail"
            ])

# ✅ Append video row to CSV
def append_video_to_csv(filename, video):
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            video["video_id"], video["title"], video["url"], video["duration"],
            video["uploader"], video["channel_name"], video["upload_date"],
            video["view_count"], video["like_count"], video["description"],
            video["channel_url"], video["thumbnail"]
        ])

# ✅ Retry wrapper
def retry_extract_info(ydl, url, retries=3):
    for attempt in range(retries):
        try:
            return ydl.extract_info(url, download=False)
        except Exception as e:
            logging.warning(f"Retry {attempt+1}/{retries} failed for {url}: {e}")
            time.sleep(2 * (attempt + 1) + random.uniform(0, 2))
    return None

# ✅ Extract all videos and save to CSV
def extract_channel_videos(channel_id):
    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    progress_file = f"{sanitize_filename(channel_id)}_progress.csv"
    save_progress_header(progress_file)
    processed_urls = load_processed_urls(progress_file)

    ydl_opts_flat = {
        'quiet': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'extractor_args': {'youtube': {'playlist_items': 'all'}},
        'sleep_requests': 2
    }

    ydl_opts_detailed = {
        'quiet': True,
        'ignoreerrors': True,
        'skip_download': True,
        'sleep_requests': 2
    }

    videos = []
    channel_title = "channel"

    try:
        with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
            logging.info("🔍 Fetching video list...")
            info = ydl.extract_info(channel_url, download=False)
            if not info or 'entries' not in info:
                logging.warning("⚠ No videos found or failed to fetch channel.")
                return

            channel_title = sanitize_filename(info.get('title', 'channel'))
            entries = info['entries']
            logging.info(f"📦 Found {len(entries)} videos.")

        output_dir = "results"
        os.makedirs(output_dir, exist_ok=True)
        output_csv = os.path.join(output_dir, f"{channel_title}.csv")
        save_header_to_csv(output_csv)

        with yt_dlp.YoutubeDL(ydl_opts_detailed) as ydl:
            for index, entry in enumerate(entries, start=1):
                if not entry or 'id' not in entry:
                    continue
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                if video_url in processed_urls:
                    continue

                video_info = retry_extract_info(ydl, video_url)
                if video_info is None:
                    logging.warning(f"⚠ Skipping failed video: {video_url}")
                    continue

                video_data = {
                    "video_id": video_info.get("id"),
                    "title": video_info.get("title"),
                    "url": video_info.get("webpage_url"),
                    "duration": video_info.get("duration"),
                    "uploader": video_info.get("uploader"),
                    "channel_name": video_info.get("channel"),
                    "upload_date": datetime.strptime(video_info.get("upload_date", "19700101"), "%Y%m%d").strftime("%Y-%m-%d") if video_info.get("upload_date") else None,
                    "view_count": video_info.get("view_count"),
                    "like_count": video_info.get("like_count"),
                    "description": video_info.get("description"),
                    "channel_url": video_info.get("channel_url"),
                    "thumbnail": video_info.get("thumbnail")
                }

                append_video_to_csv(output_csv, video_data)
                save_processed_url(progress_file, video_url)
                logging.info(f"[{index}/{len(entries)}] [OK] Saved: {video_data['title']}")


        logging.info(f"🎉 Completed extraction. CSV saved at: {output_csv}")

    except Exception as e:
        logging.error(f"❌ Failed to extract videos from channel {channel_id}: {e}")

# ✅ CLI entry point
def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Download all videos from a YouTube channel as CSV.")
    parser.add_argument("channel_id", type=str, help="YouTube Channel ID")
    args = parser.parse_args()

    logging.info(f"📡 Starting scrape for Channel ID: {args.channel_id}")
    extract_channel_videos(args.channel_id)

# ✅ Run the script
if __name__ == "__main__":
    main()
