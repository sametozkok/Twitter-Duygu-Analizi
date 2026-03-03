"""Full pipeline test: tweet fetch + Gemini matching"""
import time
from backend.scraper.tweets import fetch_user_tweets, fetch_multiple_channels
from backend.analyzer.matcher import match_news
from config import GEMINI_API_KEY

print("=" * 60)
print("STEP 1: Tweet Fetching")
print("=" * 60)

channels = ["pusholder", "bpthaber"]
channels_data = fetch_multiple_channels(channels, count=5)

for ch in channels_data:
    username = ch["username"]
    tweets = ch["tweets"]
    error = ch["error"]
    print(f"\n@{username}: {len(tweets)} tweets, error={error}")
    for t in tweets[:2]:
        print(f"  - [{t['id']}] {t['clean_text'][:100]}")

# Check if we have tweets from at least 2 channels
tweet_counts = [len(ch["tweets"]) for ch in channels_data]
print(f"\nTweet counts: {tweet_counts}")

if all(c > 0 for c in tweet_counts):
    print("\n" + "=" * 60)
    print("STEP 2: Gemini Matching")
    print("=" * 60)
    print(f"API Key: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:]}")
    
    try:
        results = match_news(channels_data, GEMINI_API_KEY, min_channels=2)
        print(f"\nFound {len(results)} matching topics:")
        for r in results:
            print(f"\n  Topic: {r['topic']}")
            print(f"  Channels: {r['channels']} ({r['channel_count']})")
            for tw in r["tweets"]:
                print(f"    - @{tw['channel']}: {tw['text'][:80]}...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\nNot enough tweets to test matching!")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
