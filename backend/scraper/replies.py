"""
Reply Scraper - Tweet yorumlarını çekme
Cookie-based auth ile GraphQL TweetDetail API kullanır.
Fallback olarak Syndication CDN API dener (auth gerektirmez).
"""
import requests
import re
import json
from bs4 import BeautifulSoup

from config import TWITTER_BEARER_TOKEN


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

TWEET_DETAIL_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

GRAPHQL_TWEET_DETAIL = "16nxv6mC_2VaBvBwY2V85g/TweetDetail"


def _build_auth_session(auth_token: str, ct0: str) -> requests.Session:
    """Cookie-based auth ile session oluştur."""
    session = requests.Session()
    session.cookies.set("auth_token", auth_token, domain=".x.com")
    session.cookies.set("ct0", ct0, domain=".x.com")
    session.headers.update({
        "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
        "User-Agent": HEADERS["User-Agent"],
        "x-csrf-token": ct0,
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "tr",
        "Referer": "https://x.com/",
    })
    return session


def fetch_tweet_replies(tweet_id: str, username: str = "",
                        auth_token: str = "", ct0: str = "",
                        max_replies: int = 20) -> list[dict]:
    """Bir tweet'in yanıtlarını çeker.
    
    auth_token ve ct0 verilmişse GraphQL TweetDetail ile çeker.
    Verilmemişse syndication fallback dener.
    
    Args:
        tweet_id: Tweet ID
        username: Kullanıcı adı (opsiyonel)
        auth_token: Twitter auth_token cookie değeri
        ct0: Twitter ct0 cookie değeri
        max_replies: Maksimum çekilecek yorum sayısı
    
    Returns:
        list[dict]: [{"text": str, "user": str, "name": str, "date": str, "likes": int}, ...]
    """
    replies = []
    
    # Yöntem 1: Cookie auth ile GraphQL TweetDetail
    if auth_token and ct0:
        replies = _try_graphql_tweet_detail(tweet_id, auth_token, ct0, max_replies)
    
    # Yöntem 2: Syndication embed conversation (auth gerektirmez)
    if not replies:
        replies = _try_syndication_conversation(tweet_id)
    
    if not replies:
        # Yöntem 3: CDN tweet result
        replies = _try_cdn_tweet(tweet_id)
    
    return replies[:max_replies]


def _try_graphql_tweet_detail(tweet_id: str, auth_token: str, ct0: str,
                               max_replies: int = 20) -> list[dict]:
    """GraphQL TweetDetail ile yorumları çek (cookie auth gerekir)."""
    replies = []
    
    try:
        session = _build_auth_session(auth_token, ct0)
        
        variables = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "rankingMode": "Relevance",
            "includePromotedContent": False,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        
        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(TWEET_DETAIL_FEATURES),
        }
        
        url = f"https://api.x.com/graphql/{GRAPHQL_TWEET_DETAIL}"
        r = session.get(url, params=params, timeout=20)
        
        if r.status_code != 200:
            return []
        
        data = r.json()
        instructions = data.get("data", {}).get("threaded_conversation_with_injections_v2", {}).get("instructions", [])
        
        for inst in instructions:
            for entry in inst.get("entries", []):
                entry_id = entry.get("entryId", "")
                
                # Ana tweet'i atla, sadece yorumları al
                if f"tweet-{tweet_id}" == entry_id:
                    continue
                
                # Promoted/cursor entry'leri atla
                if "cursor" in entry_id or "promoted" in entry_id:
                    continue
                
                # Tek yorum entry'si
                content = entry.get("content", {})
                item = content.get("itemContent", {})
                if item:
                    reply = _parse_tweet_result(item, tweet_id)
                    if reply:
                        replies.append(reply)
                
                # Conversation thread (yanıt zincirleri)
                items = content.get("items", [])
                for sub in items:
                    sub_item = sub.get("item", {}).get("itemContent", {})
                    if sub_item:
                        reply = _parse_tweet_result(sub_item, tweet_id)
                        if reply:
                            replies.append(reply)
                
                if len(replies) >= max_replies:
                    break
            
            if len(replies) >= max_replies:
                break
    
    except Exception:
        pass
    
    return replies[:max_replies]


def _parse_tweet_result(item: dict, original_tweet_id: str) -> dict | None:
    """GraphQL tweet result'ından yorum bilgisi çıkar."""
    tweet_results = item.get("tweet_results", {})
    tw = tweet_results.get("result", {})
    
    if tw.get("__typename") == "TweetWithVisibilityResults":
        tw = tw.get("tweet", {})
    
    if tw.get("__typename") != "Tweet":
        return None
    
    legacy = tw.get("legacy", {})
    tw_id = legacy.get("id_str", tw.get("rest_id", ""))
    
    # Ana tweeti atla
    if tw_id == original_tweet_id:
        return None
    
    text = legacy.get("full_text", "")
    text = re.sub(r'https?://t\.co/\S+', '', text).strip()
    text = re.sub(r'@\w+\s*', '', text).strip()
    
    if not text or len(text) < 3:
        return None
    
    # Kullanıcı bilgisi
    core = tw.get("core", {}).get("user_results", {}).get("result", {})
    user_legacy = core.get("legacy", {})
    
    return {
        "text": text,
        "user": user_legacy.get("screen_name", ""),
        "name": user_legacy.get("name", ""),
        "date": legacy.get("created_at", ""),
        "likes": legacy.get("favorite_count", 0),
    }


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
