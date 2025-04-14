import pandas as pd
import os
import re
import json
from collections import defaultdict

# --- Stock keywords for detection ---
stock_keywords = {
    "tesla": ["tsla", "tesla"],
    "nvidia": ["nvda", "nvidia"],
    "apple": ["aapl", "apple"],
    "meta": ["meta", "facebook", "fb"],
    "amazon": ["amzn", "amazon"],
    "google": ["googl", "google", "alphabet"],
    "microsoft": ["msft", "microsoft"],
    "netflix": ["nflx", "netflix"],
    "amd": ["amd"],
    "pltr": ["pltr", "palantir"],
    "smci": ["smci"],
    "mu": ["mu", "micron"],
    "qqq": ["qqq"],
    "spy": ["spy"]
}

# --- Helper functions ---
def get_matched_stocks(title):
    title = title.lower()
    matched = []
    for stock, keywords in stock_keywords.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', title):
                matched.append(stock)
                break
    return matched

def extract_channel_name_from_path(file_path):
    raw_name = os.path.basename(file_path).split("_-_")[0]
    return raw_name.lower().replace("_", "").replace(" ", "")

def cluster_channel_videos(csv_file_path):
    df = pd.read_csv(csv_file_path)
    print(f"[INFO] Loaded {len(df)} rows from CSV.")

    df.rename(columns={
        'Title': 'title',
        'Video ID': 'video_id',
        'Upload Date': 'upload_date',
        'View Count': 'view_count',
        'Description': 'description'
    }, inplace=True)

    if 'title' not in df.columns or 'video_id' not in df.columns:
        raise ValueError("CSV must contain 'title' and 'video_id' columns")

    channel_name = extract_channel_name_from_path(csv_file_path)
    print(f"[INFO] Channel name extracted: {channel_name}")

    if 'Channel Name' in df.columns:
        df = df[df['Channel Name'].str.lower().str.replace(" ", "").str.replace("_", "") == channel_name]
        print(f"[INFO] Filtered by channel name, remaining videos: {len(df)}")

    if df.empty:
        print("[WARNING] No videos found after filtering.")
        return

    # Grouping buckets
    clusters = defaultdict(list)
    multi_asset_videos = []
    others_videos = []

    for _, row in df.iterrows():
        title = str(row['title'])
        matched_stocks = get_matched_stocks(title)

        video_info = {
            "video_id": row["video_id"],
            "title": title,
            "description": row.get("description", ""),
            "upload_date": row.get("upload_date", ""),
            "view_count": int(row.get("view_count", 0))
        }

        print(f"[DEBUG] Title: '{title}' | Matched Stocks: {matched_stocks}")

        if not matched_stocks:
            others_videos.append(video_info)
        elif len(matched_stocks) == 1:
            clusters[matched_stocks[0]].append(video_info)
        else:
            multi_asset_videos.append(video_info)

    # Save single-asset stockname_channelname.json
    for stock_name, videos in clusters.items():
        filename = f"{stock_name}_{channel_name}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(videos, f, indent=2)
        print(f"[INFO] Saved {len(videos)} videos to {filename}")

    # Save multi-asset videos
    if multi_asset_videos:
        with open("multi_asset.json", "w", encoding="utf-8") as f:
            json.dump(multi_asset_videos, f, indent=2)
        print(f"[INFO] Saved {len(multi_asset_videos)} multi-stock videos to multi_asset.json")

    # Save unmatched videos
    if others_videos:
        with open(f"others_{channel_name}.json", "w", encoding="utf-8") as f:
            json.dump(others_videos, f, indent=2)
        print(f"[INFO] Saved {len(others_videos)} videos to others_{channel_name}.json")

    print(f"[SUCCESS] Clustering complete for channel: {channel_name}")

# --- Example usage ---
csv_file_path = "C:/Users/shubh/OneDrive/Desktop/Youtube_Analysis/results/StockWhale_-_Videos.csv"
cluster_channel_videos(csv_file_path)
