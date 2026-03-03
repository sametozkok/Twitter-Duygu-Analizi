import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path, override=True)

# ─── Gemini API ───
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Twitter API ───
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# ─── Twitter Scraping ───
SYNDICATION_URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# ─── Model ───
SENTIMENT_MODEL = "savasy/bert-base-turkish-sentiment-cased"

# ─── Uygulama ───
TWEETS_PER_CHANNEL = 10
MIN_CHANNELS_FOR_MATCH = 2  # En az kaç kanalda geçmesi gerekir (default: hepsi)
