import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import re

# Define stock keywords
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

def extract_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([^&?/]+)", url)
    return match.group(1) if match else None

def get_stock_mentions(title):
    title = title.lower()
    matched_stocks = []
    for stock, keywords in stock_keywords.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', title):
                matched_stocks.append(stock)
                break
    return matched_stocks

def filter_transcript(transcript, stock_name, query):
    results = []
    stock_keywords_in_transcript = stock_keywords[stock_name]
    for entry in transcript:
        text = entry['text'].lower()
        if any(kw in text for kw in stock_keywords_in_transcript) and query.lower() in text:
            results.append(entry['text'])
    return results

def main():
    url = input("Enter YouTube URL: ").strip()
    video_id = extract_video_id(url)
    if not video_id:
        print("❌ Invalid YouTube URL.")
        return

    # Fetch video details using yt-dlp
    ydl_opts = {
        'quiet': True,
        'extract_audio': False,
        'force_generic_extractor': False,
        'noplaylist': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get("title", "")
        print(f"\n🎬 Video Title: {title}")
    except Exception as e:
        print(f"❌ Failed to fetch video: {e}")
        return

    matched_stocks = get_stock_mentions(title)
    if not matched_stocks:
        print("⚠️ No stock mentions detected in title.")
        return

    print(f"📈 Detected Stock(s): {', '.join(matched_stocks)}")
    query = input("Enter what data you want to extract (e.g., 'earnings'): ").strip().lower()

    # Check if the query corresponds to one of the detected stocks
    if query not in stock_keywords:
        print(f"⚠️ The stock '{query}' is not mentioned in the video title or is not available in our stock list.")
        return

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except TranscriptsDisabled:
        print("❌ Transcript is disabled for this video.")
        return
    except Exception as e:
        print(f"❌ Failed to fetch transcript: {e}")
        return

    # Now we only process the stock that the user has asked for
    stock = query.lower()
    print(f"\n🔎 Extracting info for: {stock.upper()} | Topic: {query}")

    results = filter_transcript(transcript, stock, query)
    if results:
        for line in results:
            print(f"📌 {line}")
    else:
        print("⚠️ No relevant data found in transcript for this stock and query.")

if __name__ == "__main__":
    main()
