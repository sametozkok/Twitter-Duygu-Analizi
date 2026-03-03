"""
Tweet Scraper - Twitter GraphQL API (Guest Token) ile tweet çekme
"""
import requests
import re
import json
import time
from datetime import datetime

from config import TWITTER_BEARER_TOKEN

# Twitter bearer token ortam değişkeninden okunur
BEARER_TOKEN = TWITTER_BEARER_TOKEN

GRAPHQL_USER_BY_SCREEN_NAME = "xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName"
GRAPHQL_USER_TWEETS = "V7H0Ap3_Hh2FyS75OCDO3Q/UserTweets"

USER_FEATURES = {
    "hidden_profile_subscriptions_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "highlights_tweets_tab_ui_enabled": True,
    "responsive_web_twitter_article_notes_tab_enabled": True,
    "subscriptions_feature_can_gift_premium": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

TWEET_FEATURES = {
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

# Guest token cache
_guest_session = {"session": None, "token": None, "time": 0}


def _get_guest_session() -> requests.Session:
    """Guest token ile oturum oluştur (cache'li)."""
    if not BEARER_TOKEN:
        raise RuntimeError(
            "Twitter BEARER token yapılandırılmamış. Lütfen proje kökündeki .env dosyanıza "
            "TWITTER_BEARER_TOKEN değişkenini ekleyin."
        )
    now = time.time()
    # Token 15 dakika geçerliliğini korur
    if _guest_session["session"] and (now - _guest_session["time"]) < 840:
        return _guest_session["session"]

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    })

    r = session.post("https://api.x.com/1.1/guest/activate.json", timeout=10)
    r.raise_for_status()
    guest_token = r.json()["guest_token"]
    session.headers["x-guest-token"] = guest_token

    _guest_session["session"] = session
    _guest_session["token"] = guest_token
    _guest_session["time"] = now
    return session


def _get_user_id(session: requests.Session, username: str) -> str:
    """GraphQL ile kullanıcı ID'sini al."""
    params = {
        "variables": json.dumps({"screen_name": username, "withSafetyModeUserFields": True}),
        "features": json.dumps(USER_FEATURES),
    }
    url = f"https://api.x.com/graphql/{GRAPHQL_USER_BY_SCREEN_NAME}"
    r = session.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["data"]["user"]["result"]["rest_id"]


def extract_username(url_or_username: str) -> str:
    """URL veya kullanıcı adından username çıkar."""
    url_or_username = url_or_username.strip().rstrip("/")
    if "/" in url_or_username:
        username = url_or_username.split("/")[-1]
    else:
        username = url_or_username
    username = username.lstrip("@")
    if "?" in username:
        username = username.split("?")[0]
    return username


def fetch_user_tweets(username_or_url: str, count: int = 10) -> dict:
    """Bir Twitter kullanıcısının son tweetlerini GraphQL API ile çeker.

    Args:
        username_or_url: Kullanıcı adı, @mention veya profil URL'si
        count: Çekilecek tweet sayısı

    Returns:
        dict: username, tweets listesi, error
    """
    username = extract_username(username_or_url)
    result = {"username": username, "tweets": [], "error": None}

    try:
        session = _get_guest_session()

        # 1) Kullanıcı ID'sini al
        user_id = _get_user_id(session, username)

        # 2) Tweetleri çek
        variables = {
            "userId": user_id,
            "count": max(count + 5, 20),  # biraz fazla iste, pinned/promoted çıkabilir
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(TWEET_FEATURES),
        }
        url = f"https://api.x.com/graphql/{GRAPHQL_USER_TWEETS}"
        r = session.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        # 3) Tweetleri parse et
        instructions = data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
        tweet_count = 0

        for inst in instructions:
            for entry in inst.get("entries", []):
                if tweet_count >= count:
                    break

                content = entry.get("content", {})
                item = content.get("itemContent", {})
                tweet_results = item.get("tweet_results", {})
                tw_result = tweet_results.get("result", {})

                # TweetWithVisibilityResults wrapper'ını aç
                if tw_result.get("__typename") == "TweetWithVisibilityResults":
                    tw_result = tw_result.get("tweet", {})

                legacy = tw_result.get("legacy", {})
                text = legacy.get("full_text", "")
                if not text:
                    continue

                tweet_id = legacy.get("id_str", tw_result.get("rest_id", ""))
                clean_text = re.sub(r"https?://t\.co/\S+", "", text).strip()
                created = legacy.get("created_at", "")

                try:
                    dt = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
                    date_formatted = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    date_formatted = created

                # Medya
                media = []
                for m in legacy.get("entities", {}).get("media", []):
                    media.append({
                        "type": m.get("type", ""),
                        "url": m.get("media_url_https", ""),
                    })

                tweet_count += 1
                result["tweets"].append({
                    "id": tweet_id,
                    "text": text,
                    "clean_text": clean_text,
                    "date": created,
                    "date_formatted": date_formatted,
                    "likes": legacy.get("favorite_count", 0),
                    "retweets": legacy.get("retweet_count", 0),
                    "replies": legacy.get("reply_count", 0),
                    "quotes": legacy.get("quote_count", 0),
                    "url": f"https://x.com/{username}/status/{tweet_id}",
                    "media": media,
                })

    except Exception as e:
        result["error"] = str(e)

    return result


def fetch_multiple_channels(urls: list[str], count: int = 10) -> list[dict]:
    """Birden fazla kanalın tweetlerini çeker.

    Args:
        urls: Kanal URL'leri veya kullanıcı adları listesi
        count: Her kanal için çekilecek tweet sayısı

    Returns:
        list[dict]: Her kanal için fetch_user_tweets sonucu
    """
    results = []
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(1)  # rate limit'e takılmamak için
        result = fetch_user_tweets(url, count)
        results.append(result)
    return results
