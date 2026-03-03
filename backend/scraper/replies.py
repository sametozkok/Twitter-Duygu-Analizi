"""
Reply Scraper - Tweet yorumlarını çekme
Syndication CDN API kullanır (auth gerektirmez).
"""
import requests
import re
import json
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def fetch_tweet_replies(tweet_id: str, username: str = "") -> list[dict]:
    """Bir tweet'in yanıtlarını çeker.
    
    Önce syndication embed sayfasından, sonra CDN endpoint'inden dener.
    
    Args:
        tweet_id: Tweet ID
        username: Kullanıcı adı (opsiyonel, URL oluşturmak için)
    
    Returns:
        list[dict]: [{"text": str, "user": str, "date": str}, ...]
    """
    replies = []
    
    # Yöntem 1: Syndication embed conversation
    replies = _try_syndication_conversation(tweet_id)
    
    if not replies:
        # Yöntem 2: CDN tweet result  
        replies = _try_cdn_tweet(tweet_id)
    
    return replies


def _try_syndication_conversation(tweet_id: str) -> list[dict]:
    """Syndication timeline-profile üzerinden conversation çek."""
    replies = []
    
    try:
        # Tweet embed sayfası
        url = f"https://syndication.twitter.com/srv/timeline-tweet/conversation/{tweet_id}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        if resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        
        if not script_tag:
            return []
        
        data = json.loads(script_tag.string)
        props = data.get("props", {}).get("pageProps", {})
        timeline = props.get("timeline", {})
        
        if isinstance(timeline, dict):
            entries = timeline.get("entries", [])
            for entry in entries:
                if entry.get("type") == "tweet":
                    tw = entry.get("content", {}).get("tweet", {})
                    tw_id = tw.get("id_str", "")
                    
                    if tw_id != tweet_id:
                        text = tw.get("text", "")
                        text = re.sub(r'https?://t\.co/\S+', '', text).strip()
                        text = re.sub(r'@\w+\s*', '', text).strip()
                        
                        if text and len(text) > 2:
                            user = tw.get("user", {})
                            replies.append({
                                "text": text,
                                "user": user.get("screen_name", ""),
                                "name": user.get("name", ""),
                                "date": tw.get("created_at", ""),
                                "likes": tw.get("favorite_count", 0),
                            })
    except Exception:
        pass
    
    return replies


def _try_cdn_tweet(tweet_id: str) -> list[dict]:
    """CDN syndication endpoint'inden tweet detayını çek."""
    replies = []
    
    try:
        url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=tr&token=x"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        
        # conversation_threads varsa
        threads = data.get("conversation_threads", [])
        for thread in threads:
            for tweet in thread.get("tweets", []):
                text = tweet.get("text", "")
                text = re.sub(r'https?://t\.co/\S+', '', text).strip()
                text = re.sub(r'@\w+\s*', '', text).strip()
                
                if text and len(text) > 2:
                    user = tweet.get("user", {})
                    replies.append({
                        "text": text,
                        "user": user.get("screen_name", ""),
                        "name": user.get("name", ""),
                        "date": tweet.get("created_at", ""),
                        "likes": tweet.get("favorite_count", 0),
                    })
    except Exception:
        pass
    
    return replies


def fetch_replies_for_tweets(tweets: list[dict]) -> dict:
    """Birden fazla tweet için yorumları toplu çeker.
    
    Args:
        tweets: [{"id": "...", "username": "...", ...}, ...]
    
    Returns:
        dict: {tweet_id: [replies], ...}
    """
    all_replies = {}
    for tweet in tweets:
        tweet_id = tweet.get("id", "")
        username = tweet.get("username", "")
        replies = fetch_tweet_replies(tweet_id, username)
        all_replies[tweet_id] = replies
    return all_replies
