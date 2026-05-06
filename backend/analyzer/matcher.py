"""
Haber Eşleştirme - Google Gemini API ile haberleri karşılaştır
(Optimizasyon: ön filtreleme, metin budama, duplicate eleme, kompakt prompt)
"""
import json
import re
import requests
import time
from config import (
    GEMINI_API_DISABLED,
    GEMINI_API_KEY,
    GROK_API_BASE,
    GROK_API_KEY,
    GROK_MODEL,
    LLM_PROVIDER,
)


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_for_api(text: str, max_len: int = 120) -> str:
    """Tweet metnini API'ye göndermeden önce budayıp kısalt."""
    text = re.sub(r"https?://\S+", "", text)           # URL kaldır
    text = re.sub(r"@\w+", "", text)                    # mention kaldır
    text = re.sub(r"#(\w+)", r"\1", text)               # # işaretini kaldır, kelimeyi bırak
    text = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ.,;:!?'\"-]", "", text)  # emoji/özel karakter
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _tokenize_tr(text: str) -> set[str]:
    stop_words = {
        "ve", "ile", "de", "da", "bir", "bu", "şu", "o", "için", "gibi", "çok", "daha",
        "son", "dakika", "rt", "ama", "fakat", "ancak", "olan", "oldu", "olarak", "göre",
        "ait", "yeni", "paylaştı", "açıklama", "açıklaması", "dedi", "edildi", "etti", "var",
        "yok", "en", "kez", "mi", "mı", "mu", "mü", "ki", "ya", "veya", "hem", "ile",
    }
    tokens = []
    for token in _normalize_text(text).split():
        if len(token) < 3:
            continue
        if token.isdigit():
            continue
        if token in stop_words:
            continue
        tokens.append(token)
    return set(tokens)


def _tweet_quality_score(tweet: dict) -> float:
    """Gruplama sırasında kanal başına en güçlü tweeti seçmek için kalite skoru."""
    text_len = len(str(tweet.get("text", "")))
    likes = max(0, int(tweet.get("likes", 0) or 0))
    replies = max(0, int(tweet.get("replies", 0) or 0))
    retweets = max(0, int(tweet.get("retweets", 0) or 0))
    return (likes * 0.1) + (replies * 0.35) + (retweets * 0.25) + (text_len * 0.03)


def _pair_similarity_score(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    if not intersection:
        return 0.0

    union = tokens_a | tokens_b
    jaccard = len(intersection) / max(1, len(union))
    long_overlap = sum(1 for token in intersection if len(token) >= 5)

    return jaccard + min(0.18, long_overlap * 0.04) + (0.06 if len(intersection) >= 3 else 0.0)


def _is_pair_same_event(tokens_a: set[str], tokens_b: set[str]) -> bool:
    if not tokens_a or not tokens_b:
        return False

    intersection = tokens_a & tokens_b
    if len(intersection) >= 5:
        return True

    score = _pair_similarity_score(tokens_a, tokens_b)
    long_overlap = sum(1 for token in intersection if len(token) >= 5)

    if len(intersection) >= 3 and score >= 0.2:
        return True
    if len(intersection) >= 2 and long_overlap >= 2 and score >= 0.24:
        return True

    return False


def _dedup_channels_by_quality(tweets: list[dict]) -> list[dict]:
    """Aynı grupta aynı kanaldan birden fazla tweet varsa en kaliteli olanı tut."""
    best_by_channel: dict[str, dict] = {}
    for tw in tweets:
        channel = tw.get("channel", "")
        if channel not in best_by_channel or _tweet_quality_score(tw) > _tweet_quality_score(best_by_channel[channel]):
            best_by_channel[channel] = tw

    return list(best_by_channel.values())


def _is_group_coherent(tweets: list[dict], min_channels: int) -> bool:
    """Gemini çıktısını korumak için grup içi olay tutarlılığı kontrolü."""
    if len(tweets) < min_channels:
        return False

    channels = {tw.get("channel", "") for tw in tweets}
    if len(channels) < min_channels:
        return False

    token_sets = [_tokenize_tr(str(tw.get("text", ""))) for tw in tweets]
    n = len(token_sets)

    if n < 2:
        return False

    links = [0] * n
    strong_pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            if _is_pair_same_event(token_sets[i], token_sets[j]):
                links[i] += 1
                links[j] += 1
                strong_pairs += 1

    # Her tweetin en az bir güçlü partneri olmalı.
    if any(link_count == 0 for link_count in links):
        return False

    # Grup boyutuna göre minimum güçlü bağ.
    if strong_pairs < max(1, n - 1):
        return False

    return True


def _safe_float(value) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return parsed


def _dedup_same_channel(tweets: list[dict]) -> list[dict]:
    """Aynı kanaldan gelen çok benzer tweetleri ele (en uzununu tut)."""
    by_channel: dict[str, list[dict]] = {}
    for tw in tweets:
        by_channel.setdefault(tw["channel"], []).append(tw)

    result = []
    for channel, ch_tweets in by_channel.items():
        token_sets = [_tokenize_tr(tw["text"]) for tw in ch_tweets]
        keep = [True] * len(ch_tweets)

        for i in range(len(ch_tweets)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(ch_tweets)):
                if not keep[j]:
                    continue
                a, b = token_sets[i], token_sets[j]
                normalized_a = _normalize_text(ch_tweets[i]["text"])
                normalized_b = _normalize_text(ch_tweets[j]["text"])

                overlap = 0.0
                containment = 0.0
                if a and b:
                    overlap = len(a & b) / max(1, len(a | b))
                    containment = len(a & b) / max(1, min(len(a), len(b)))

                is_near_duplicate = (
                    normalized_a == normalized_b
                    or (len(normalized_a) > 24 and normalized_a in normalized_b)
                    or (len(normalized_b) > 24 and normalized_b in normalized_a)
                    or overlap >= 0.56
                    or containment >= 0.76
                )

                if is_near_duplicate:
                    if _tweet_quality_score(ch_tweets[i]) >= _tweet_quality_score(ch_tweets[j]):
                        keep[j] = False
                    else:
                        keep[i] = False
                        break

        result.extend(tw for tw, k in zip(ch_tweets, keep) if k)
    return result


def _prefilter_candidates(all_tweets: list[dict]) -> list[dict]:
    """Keyword kesişimi ile Gemini'ye gönderilecek aday tweetleri filtrele.
    
    En az 1 başka kanaldan bir tweet ile 2+ ortak kelimesi olan tweetleri tut.
    Hiç eşleşme potansiyeli olmayanları ele.
    """
    n = len(all_tweets)
    if n < 2:
        return all_tweets

    token_sets = [_tokenize_tr(tw["text"]) for tw in all_tweets]
    has_potential = [False] * n

    for i in range(n):
        if has_potential[i]:
            continue
        for j in range(i + 1, n):
            if all_tweets[i]["channel"] == all_tweets[j]["channel"]:
                continue
            a, b = token_sets[i], token_sets[j]
            if not a or not b:
                continue
            inter = a & b
            if len(inter) >= 2:
                has_potential[i] = True
                has_potential[j] = True

    filtered = [tw for tw, pot in zip(all_tweets, has_potential) if pot]
    return filtered if filtered else all_tweets  # Hiç kalmadıysa hepsini gönder


def _fallback_match_by_keywords(all_tweets: list[dict], min_channels: int) -> list[dict]:
    """Gemini boş/bozuk dönerse anahtar kelime kesişimiyle eşleşme üret."""
    n = len(all_tweets)
    if n < 2:
        return []

    token_sets = [_tokenize_tr(tw["text"]) for tw in all_tweets]

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Farklı kanallardaki tweetleri benzerlik skoruyla bağla
    for i in range(n):
        for j in range(i + 1, n):
            if all_tweets[i]["channel"] == all_tweets[j]["channel"]:
                continue
            a, b = token_sets[i], token_sets[j]
            if not a or not b:
                continue
            inter = a & b
            if len(inter) < 2:
                continue
            score = len(inter) / max(1, len(a | b))
            long_inter_count = sum(1 for token in inter if len(token) >= 5)
            if (
                score >= 0.18
                or len(inter) >= 5
                or (len(inter) >= 3 and long_inter_count >= 2 and score >= 0.14)
            ):
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for idx in range(n):
        root = find(idx)
        clusters.setdefault(root, []).append(idx)

    results = []
    for members in clusters.values():
        if len(members) < 2:
            continue

        cluster_tweets = [all_tweets[i] for i in members]
        cluster_tweets = _dedup_channels_by_quality(cluster_tweets)
        channels = {tw["channel"] for tw in cluster_tweets}
        if len(channels) < min_channels:
            continue

        if not _is_group_coherent(cluster_tweets, min_channels):
            continue

        common_tokens = None
        for i in members:
            if common_tokens is None:
                common_tokens = set(token_sets[i])
            else:
                common_tokens &= token_sets[i]

        if common_tokens:
            topic_tokens = sorted(common_tokens, key=lambda x: (-len(x), x))[:4]
            topic = " / ".join(topic_tokens).title()
        else:
            topic = cluster_tweets[0]["text"][:60].strip() + "..."

        results.append({
            "topic": topic,
            "tweets": cluster_tweets,
            "channel_count": len(channels),
            "channels": list(channels),
        })

    results.sort(key=lambda x: x["channel_count"], reverse=True)
    return results


def _parse_gemini_json(raw_text: str) -> list:
    """Gemini'nin döndürdüğü metinden JSON array'i güvenli şekilde çıkar.
    
    Gemini bazen:
    - ```json ... ``` bloğu ile sarar
    - Thinking block ekler
    - Trailing comma bırakır
    - Tek tırnak kullanır
    - Ekstra metin/açıklama ekler
    - Satır sonu virgülü eksik bırakır
    """
    text = raw_text.strip()
    
    # 1) ```json ... ``` bloğunu çıkar
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    
    # 2) JSON array'i bul (en dış [ ... ] bloğu)
    # Nested brackets'ı doğru handle et
    start_idx = text.find('[')
    if start_idx == -1:
        return []
    
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    
    if end_idx == -1:
        # Kapanmamış bracket — sonuna ] ekle
        text = text[start_idx:] + ']'
    else:
        text = text[start_idx:end_idx + 1]
    
    # 3) İlk deneme — doğrudan parse et
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 4) Yaygın sorunları düzelt
    cleaned = text
    # Trailing comma: }, ] veya } ] 
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    # Tek tırnakları çift tırnağa çevir (JSON string dışındakileri)
    # Basit yaklaşım: tüm tek tırnakları çift tırnağa çevir
    # (tweet metinlerinde tek tırnak varsa sorun olabilir, ama Gemini genelde çift kullanır)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # 5) Satır satır temizle — her satırdan kontrolsüz karakterleri at
    lines = cleaned.split('\n')
    fixed_lines = []
    for line in lines:
        line = line.rstrip()
        # Satır sonundaki eksik virgülleri ekle
        stripped = line.rstrip()
        if stripped and stripped[-1] in ('"', '}') and not stripped.endswith(','):
            # Sonraki satıra bakamayız ama genellikle virgül eksikliği sorun
            pass  # bu adımda müdahale etmiyoruz
        fixed_lines.append(line)
    cleaned = '\n'.join(fixed_lines)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # 6) Son çare: Her {...} objesini ayrı ayrı parse et
    objects = []
    for m in re.finditer(r'\{[^{}]*\}', cleaned):
        obj_text = m.group(0)
        obj_text = re.sub(r',\s*}', '}', obj_text)
        try:
            obj = json.loads(obj_text)
            objects.append(obj)
        except json.JSONDecodeError:
            continue
    
    if objects:
        return objects
    
    # 7) Hiçbiri işe yaramadıysa boş döndür
    return []

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _resolve_provider() -> str:
    if LLM_PROVIDER in {"grok", "groq"}:
        return "grok" if GROK_API_KEY else "none"
    if LLM_PROVIDER == "gemini":
        if GEMINI_API_DISABLED or not GEMINI_API_KEY:
            return "none"
        return "gemini"
    if GROK_API_KEY:
        return "grok"
    if GEMINI_API_DISABLED or not GEMINI_API_KEY:
        return "none"
    return "gemini"


def _call_grok(prompt: str, system_instruction: str, max_tokens: int) -> str | None:
    if not GROK_API_KEY:
        return None

    base_url = GROK_API_BASE.rstrip("/")
    api_url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "top_p": 0.7,
        "max_tokens": max_tokens,
    }

    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
        except requests.RequestException:
            last_error = "request-error"
            time.sleep(1 + attempt)
            continue

        if response.status_code == 200:
            try:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError, ValueError):
                last_error = "invalid-response"
                break

        if response.status_code in (429, 503):
            last_error = str(response.status_code)
            time.sleep(2 + attempt)
            continue

        last_error = str(response.status_code)
        break

    if last_error is not None:
        print(f"Grok API Error: {last_error}")
    return None


def match_news(channels_data: list[dict], api_key: str, min_channels: int = 2) -> list[dict]:
    """Farklı kanallardan gelen tweetleri Gemini ile karşılaştırıp eşle.
    
    Optimizasyonlar:
    - Aynı kanaldan gelen benzer tweetler elenir (duplicate)
    - Keyword ön filtresi ile eşleşme potansiyeli olmayanlar çıkarılır
    - Tweet metinleri budanıp kısaltılır (token tasarrufu)
    - Kompakt satır formatı ile prompt boyutu azaltılır
    
    Args:
        channels_data: fetch_multiple_channels çıktısı
        api_key: Gemini API key
        min_channels: En az kaç kanalda geçmeli (default 2)
    
    Returns:
        list[dict]: Eşleşen haber grupları
    """
    # 1) Tüm tweetleri kanal bilgisiyle birlikte topla
    all_tweets = []
    for ch in channels_data:
        username = ch["username"]
        for tw in ch.get("tweets", []):
            all_tweets.append({
                "channel": username,
                "tweet_id": tw["id"],
                "text": tw["clean_text"],
                "url": tw["url"],
                "likes": tw.get("likes", 0),
                "replies": tw.get("replies", 0),
                "retweets": tw.get("retweets", 0),
                "date_formatted": tw.get("date_formatted", ""),
            })
    
    if not all_tweets:
        return []

    provider = _resolve_provider()
    if provider == "none":
        return _fallback_match_by_keywords(all_tweets, min_channels)
    
    # 2) Aynı kanaldan gelen duplicate tweetleri ele
    all_tweets = _dedup_same_channel(all_tweets)
    
    # 3) Keyword ön filtresi — eşleşme potansiyeli olmayanları çıkar
    candidates = _prefilter_candidates(all_tweets)
    
    # Aday yoksa fallback
    if len(candidates) < 2:
        return _fallback_match_by_keywords(all_tweets, min_channels)
    
    # 4) Kompakt prompt oluştur — tweet metinlerini budayarak satır formatında gönder
    channel_names = list({tw["channel"] for tw in candidates})
    
    tweet_lines = []
    for tw in candidates:
        clean = _clean_for_api(tw["text"])
        tweet_lines.append(f'{tw["tweet_id"]}|{tw["channel"]}|{clean}')
    
    tweet_block = "\n".join(tweet_lines)
    
    system_instruction = (
        "Sen haber eşleştirme doğrulama motorusun. "
        "Yalnızca aynı somut olayı anlatan tweetleri grupla. "
        "Genel gündem benzerliğini asla eşleşme sayma. "
        "Şüpheli durumda eşleştirme yapma."
    )

    prompt = f"""Aşağıda {len(channel_names)} haber kanalından {len(candidates)} tweet var (ID|kanal|metin).

DETAYLI DEĞERLENDİRME KURALLARI:
1) Tweetleri eşleştirmeden önce her tweet için olay imzası çıkar:
   - ana aktör(ler)
   - olayın fiili (ne oldu)
   - bağlam (yer, zaman, resmi açıklama, sayı vb.)
2) Eşleşme için olay imzasının omurgası aynı olmalı.
3) Sadece aynı genel konuya ait farklı haberler AYRI kalmalı.
4) Her grupta aynı kanaldan en fazla 1 tweet olmalı.
5) Her grupta en az {min_channels} farklı kanal olmalı.
6) Düşük güvenli eşleşmeleri çıkar. Emin değilsen boş bırak.

Veri:
{tweet_block}

ÇIKTI KURALI:
- SADECE JSON döndür.
- Format:
[{{"topic":"Kısa ve somut haber başlığı","tweet_ids":["id1","id2"],"confidence":0.0}}]
- confidence 0-1 arasında olmalı.
- Eşleşme yoksa []"""
    
    if provider == "grok":
        grok_text = _call_grok(prompt, system_instruction, max_tokens=4096)
        if not grok_text:
            return _fallback_match_by_keywords(all_tweets, min_channels)
        matched_groups = _parse_gemini_json(grok_text)
    else:
        # 5) Gemini API çağrısı
        headers = {"Content-Type": "application/json"}
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.7,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            }
        }
        
        response = None
        rate_limited = False
        for model in GEMINI_MODELS:
            api_url = GEMINI_API_BASE.format(model=model)

            # Ağ kopmaları (RemoteDisconnected vb.) için model başına kısa retry uygula.
            for attempt in range(3):
                try:
                    response = requests.post(
                        f"{api_url}?key={api_key}",
                        headers=headers,
                        json=payload,
                        timeout=60,
                    )
                except requests.RequestException:
                    response = None
                    time.sleep(1 + attempt)
                    continue

                if response.status_code == 200:
                    break

                if response.status_code in (429, 503):
                    rate_limited = True
                    break

                if response.status_code >= 500:
                    time.sleep(1)
                    continue

                if response.status_code == 404:
                    break

                break

            if rate_limited:
                break

            if response is not None and response.status_code == 200:
                break

        # Gemini kotası (429) veya geçici API hatalarında akışı düşürme.
        # Uygulama çalışmaya devam etsin diye keyword fallback'e geç.
        if rate_limited or response is None or response.status_code != 200:
            return _fallback_match_by_keywords(all_tweets, min_channels)
        
        # 6) Yanıtı parse et
        try:
            resp_data = response.json()
            text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError):
            return _fallback_match_by_keywords(all_tweets, min_channels)
        
        matched_groups = _parse_gemini_json(text)
    
    if not matched_groups:
        return _fallback_match_by_keywords(all_tweets, min_channels)

    matched_groups = sorted(
        matched_groups,
        key=lambda item: _safe_float(item.get("confidence")) or 0.0,
        reverse=True,
    )

    # 7) Tweet ID'lerini gerçek tweet verisiyle eşle (orijinal all_tweets'ten)
    tweet_map = {tw["tweet_id"]: tw for tw in all_tweets}
    
    results = []
    used_tweet_ids: set[str] = set()
    seen_group_keys: set[tuple[str, ...]] = set()

    for group in matched_groups:
        topic = group.get("topic", "Bilinmeyen Konu")
        tweet_ids = group.get("tweet_ids", [])
        confidence = _safe_float(group.get("confidence"))

        if confidence is not None and confidence < 0.72:
            continue
        
        matched_tweets = []
        
        for tid in tweet_ids:
            if tid in used_tweet_ids:
                continue
            if tid in tweet_map:
                matched_tweets.append(tweet_map[tid])
        
        matched_tweets = _dedup_channels_by_quality(matched_tweets)
        channels_in_group = {tw["channel"] for tw in matched_tweets}

        if not _is_group_coherent(matched_tweets, min_channels):
            continue

        group_key = tuple(sorted(tw["tweet_id"] for tw in matched_tweets if tw.get("tweet_id")))
        if not group_key or group_key in seen_group_keys:
            continue
        
        if len(channels_in_group) >= min_channels:
            seen_group_keys.add(group_key)
            used_tweet_ids.update(group_key)
            results.append({
                "topic": topic,
                "tweets": matched_tweets,
                "channel_count": len(channels_in_group),
                "channels": list(channels_in_group),
            })
    
    if not results:
        return _fallback_match_by_keywords(all_tweets, min_channels)

    results.sort(key=lambda x: x["channel_count"], reverse=True)
    
    return results
