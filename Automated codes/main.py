from mistral_api import process_transcript_with_mistral
from pymongo import MongoClient
import yt_dlp
import datetime
import json
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import T5Tokenizer, T5ForConditionalGeneration

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["youtube_data"]
collection = db["videos"]

# Define the date range for filtering videos
START_DATE = datetime.datetime(2024, 6, 1)
END_DATE = datetime.datetime(2025, 3, 12)

# Load T5 model and tokenizer for summarization
model_name = "t5-small"  # Can be changed to "t5-base" or "t5-large" for better results
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

def summarize_transcript(transcript):
    """Summarizes a given transcript using the T5 model."""
    max_input_length = 512  # T5 model input limit
    tokenized_text = tokenizer.encode(transcript, return_tensors="pt", truncation=True, max_length=max_input_length)
    summary_ids = model.generate(tokenized_text, max_length=150, min_length=50, length_penalty=2.0, num_beams=4)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def get_video_metadata(video_url):
    """Extracts metadata of a YouTube video."""
    ydl_opts = {"quiet": True, "format": "best"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(video_url, download=False)

def format_date(yyyymmdd):
    """Converts a date string (YYYYMMDD) into a datetime object."""
    try:
        return datetime.datetime.strptime(yyyymmdd, "%Y%m%d") + datetime.timedelta(days=1)
    except ValueError:
        return None

def get_transcript(video_id):
    """Fetches the transcript of a YouTube video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        print(f"⚠️ Transcript not available for {video_id}: {e}")
        return None

def analyze_transcript(transcript):
    """Processes the transcript using Mistral API for financial insights."""
    try:
        response = process_transcript_with_mistral(transcript)
        if not response:
            return None

        # Format structured insights
        return {
            "narrative": response.get("narrative", "NON-DECISIVE"),
            "direction": response.get("direction", "LONG"),
            "Support": sorted(response.get("Support", []), reverse=True),
            "Resistance": sorted(response.get("Resistance", [])),
            "Buy_Area": [tuple(sorted(buy_range, reverse=True)) for buy_range in response.get("Buy_Area", [])],
            "Sell_Area": [tuple(sorted(sell_range)) for sell_range in response.get("Sell_Area", [])]
        }
    except Exception as e:
        print(f"❌ Error processing transcript with Mistral: {e}")
        return None

def process_channel_videos(channel_url):
    """Processes all videos from a given YouTube channel."""
    ydl_opts = {"quiet": True, "extract_flat": True, "force_generic_extractor": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
    
    video_urls = [entry["url"] for entry in info.get("entries", []) if "url" in entry]

    for video_url in video_urls:
        metadata = get_video_metadata(video_url)
        video_id = metadata.get("id", "N/A")
        upload_date = format_date(metadata.get("upload_date", "N/A"))
        
        # Skip videos outside the date range
        if not upload_date or not (START_DATE <= upload_date <= END_DATE):
            print(f"⏭️ Skipping '{metadata.get('title', 'N/A')}' (Out of Date Range)")
            continue
        
        # Skip already processed videos
        if collection.find_one({"Video URL": metadata.get("webpage_url", "N/A")}):
            print(f"⚠️ Already processed: '{metadata.get('title', 'N/A')}'. Skipping...")
            continue
        
        # Skip Nvidia-related videos, process only Tesla-related videos
        video_title = metadata.get("title", "").lower()
        if "nvidia" in video_title or "nvda" in video_title:
            print(f"⏭️ Skipping Nvidia-related video: '{metadata.get('title', 'N/A')}'")
            continue
        if "tsla" not in video_title and "tesla" not in video_title:
            print(f"⏭️ Skipping unrelated video: '{metadata.get('title', 'N/A')}'")
            continue
        
        # Get video transcript
        transcript = get_transcript(video_id)
        if not transcript:
            continue
        
        # Summarize the transcript
        summarized_text = summarize_transcript(transcript)
        
        # Analyze the transcript for financial insights
        structured_insights = analyze_transcript(summarized_text)
        if structured_insights is None:
            continue
        
        # Store video details and insights in MongoDB
        video_data = {
            "Video Title": metadata.get("title", "N/A"),
            "Upload Date": upload_date.strftime("%d/%m/%Y"),
            "Video URL": metadata.get("webpage_url", "N/A"),
            "Financial Insights": structured_insights
        }
        collection.insert_one(video_data)
        print(f"✅ Stored: '{metadata.get('title', 'N/A')}'")

if __name__ == "__main__":
    # Process all videos from the specified YouTube channel
    channel_url = "https://www.youtube.com/@theteslaguy3247"
    process_channel_videos(channel_url)