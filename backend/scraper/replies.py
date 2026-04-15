"""
Reply Scraper - Tweet yorumlarını çekme
Cookie-based auth ile GraphQL TweetDetail API kullanır.
Fallback olarak Syndication CDN API dener (auth gerektirmez).
"""
import requests
import re
import json
from bs4 import BeautifulSoup

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


def _safe_int(value: object) -> int:
    try:
        if value is None:
            return 0
        return int(str(value).replace(",", "").strip())
    except Exception:
        return 0


def _extract_view_count(tweet_obj: dict, legacy: dict) -> int:
    views = tweet_obj.get("views", {}) if isinstance(tweet_obj, dict) else {}
    if isinstance(views, dict):
        count = views.get("count") or views.get("state")
        numeric = _safe_int(count)
        if numeric > 0:
            return numeric

    return _safe_int(legacy.get("view_count"))


def _extract_user_fields(raw_user: dict | str | None, fallback_user: str = "") -> tuple[str, str]:
    """Farkli endpoint formatlarindan username/name alanlarini guvenli cikar."""
    if isinstance(raw_user, str):
        user = raw_user.strip().lstrip("@")
        if not user and fallback_user:
            user = str(fallback_user).strip().lstrip("@")
        return user, (f"@{user}" if user else "")

    if not isinstance(raw_user, dict):
        raw_user = {}

    user = (
        raw_user.get("screen_name")
        or raw_user.get("screenName")
        or raw_user.get("username")
        or raw_user.get("user_name")
        or raw_user.get("handle")
        or raw_user.get("userName")
        or raw_user.get("nick")
        or raw_user.get("login")
        or ""
    )
    name = (
        raw_user.get("name")
        or raw_user.get("displayName")
        or raw_user.get("display_name")
        or raw_user.get("full_name")
        or ""
    )

    user = str(user).strip().lstrip("@")
    name = str(name).strip()

    # Bazı yanıt formatlarında username yerine sayısal user id gelebilir.
    # Bunları kullanıcı adı gibi göstermeyelim.
    if user and re.fullmatch(r"\d{8,}", user):
        user = ""
    if name and re.fullmatch(r"\d{8,}", name):
        name = ""

    if not user and fallback_user:
        user = str(fallback_user).strip().lstrip("@")

    if not name and user:
        name = f"@{user}"

    return user, name


def _resolve_user_identity(*candidates: object) -> tuple[str, str]:
    """Birden fazla olası user objesinden ilk geçerli kullanıcı kimliğini bul."""
    for cand in candidates:
        user, name = _extract_user_fields(cand)
        if user:
            return user, name

    # username yoksa en azından isim varsa onu döndür
    for cand in candidates:
        _user, name = _extract_user_fields(cand)
        if name:
            return "", name

    return "", ""


def _build_auth_session(auth_token: str, ct0: str, bearer_token: str) -> requests.Session:
    """Cookie-based auth ile session oluştur."""
    session = requests.Session()
    session.cookies.set("auth_token", auth_token, domain=".x.com")
    session.cookies.set("ct0", ct0, domain=".x.com")
    session.headers.update({
        "Authorization": f"Bearer {bearer_token}",
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
                        bearer_token: str = "",
                        max_replies: int = 20) -> list[dict]:
    """Bir tweet'in yanıtlarını çeker.
    
    auth_token ve ct0 verilmişse GraphQL TweetDetail ile çeker.
    Verilmemişse syndication fallback dener.
    
    Args:
        tweet_id: Tweet ID
        username: Kullanıcı adı (opsiyonel)
        auth_token: Twitter auth_token cookie değeri
        ct0: Twitter ct0 cookie değeri
        bearer_token: Twitter authorization bearer header
        max_replies: Maksimum çekilecek yorum sayısı
    
    Returns:
        list[dict]: [{"text": str, "user": str, "name": str, "date": str, "likes": int}, ...]
    """
    replies = []
    
    # Yöntem 1: Cookie auth ile GraphQL TweetDetail
    if auth_token and ct0 and bearer_token:
        replies = _try_graphql_tweet_detail(tweet_id, auth_token, ct0, bearer_token, max_replies)
    
    # Yöntem 2: Syndication embed conversation (auth gerektirmez)
    if not replies:
        replies = _try_syndication_conversation(tweet_id)
    
    if not replies:
        # Yöntem 3: CDN tweet result
        replies = _try_cdn_tweet(tweet_id)
    
    return replies[:max_replies]


def _try_graphql_tweet_detail(tweet_id: str, auth_token: str, ct0: str, bearer_token: str,
                               max_replies: int = 20) -> list[dict]:
    """GraphQL TweetDetail ile yorumları çek (cookie auth gerekir)."""
    replies = []
    
    try:
        session = _build_auth_session(auth_token, ct0, bearer_token)
        
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
    user, name = _resolve_user_identity(
        user_legacy,
        core,
        core.get("core", {}),
        core.get("profile", {}),
        tw.get("user", {}),
        tw.get("author", {}),
    )

    # Bazı şemalarda fallback username farklı alanlarda olabilir.
    if not user:
        fallback_user = (
            core.get("screen_name")
            or core.get("username")
            or core.get("userName")
            or tw.get("screen_name")
            or tw.get("username")
            or ""
    )
        user, name = _extract_user_fields({"screen_name": fallback_user, "name": name}, fallback_user=fallback_user)
    likes = _safe_int(legacy.get("favorite_count"))
    retweets = _safe_int(legacy.get("retweet_count"))
    replies_count = _safe_int(legacy.get("reply_count"))
    quotes = _safe_int(legacy.get("quote_count"))
    views = _extract_view_count(tw, legacy)
    
    return {
        "text": text,
        "user": user,
        "name": name,
        "date": legacy.get("created_at", ""),
        "likes": likes,
        "retweets": retweets,
        "replies": replies_count,
        "quotes": quotes,
        "views": views,
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
                            user, name = _extract_user_fields(
                                tw.get("user", {}),
                                fallback_user=(
                                    tw.get("screen_name")
                                    or tw.get("username")
                                    or tw.get("user_name")
                                    or ""
                                ),
                            )
                            replies.append({
                                "text": text,
                                "user": user,
                                "name": name,
                                "date": tw.get("created_at", ""),
                                "likes": _safe_int(tw.get("favorite_count", 0)),
                                "retweets": _safe_int(tw.get("retweet_count", 0)),
                                "replies": _safe_int(tw.get("reply_count", 0)),
                                "quotes": _safe_int(tw.get("quote_count", 0)),
                                "views": _safe_int(tw.get("view_count", 0)),
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
                    user, name = _extract_user_fields(
                        tweet.get("user", {}),
                        fallback_user=tweet.get("screen_name", ""),
                    )
                    replies.append({
                        "text": text,
                        "user": user,
                        "name": name,
                        "date": tweet.get("created_at", ""),
                        "likes": _safe_int(tweet.get("favorite_count", 0)),
                        "retweets": _safe_int(tweet.get("retweet_count", 0)),
                        "replies": _safe_int(tweet.get("reply_count", 0)),
                        "quotes": _safe_int(tweet.get("quote_count", 0)),
                        "views": _safe_int(tweet.get("view_count", 0)),
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
