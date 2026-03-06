"""
Haber Eşleştirme - Google Gemini API ile haberleri karşılaştır
(Optimizasyon: ön filtreleme, metin budama, duplicate eleme, kompakt prompt)
"""
import json
import re
import requests


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
                if not a or not b:
                    continue
                overlap = len(a & b) / max(1, len(a | b))
                if overlap >= 0.6:  # %60+ benzerlik → duplicate
                    # Kısa olanı ele
                    if len(ch_tweets[i]["text"]) >= len(ch_tweets[j]["text"]):
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
            if score >= 0.12 or len(inter) >= 4:
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
        channels = {tw["channel"] for tw in cluster_tweets}
        if len(channels) < min_channels:
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
            })
    
    if not all_tweets:
        return []
    
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
    
    prompt = f"""Aşağıda {len(channel_names)} haber kanalından {len(candidates)} tweet var (ID|kanal|metin formatında).

KURALLAR:
- Sadece BİREBİR AYNI olayı/haberi anlatan tweetleri eşleştir
- "ABD-İran" gibi genel konu benzerliği YETERSİZ, somut olay aynı olmalı
- Bir gruba aynı kanaldan en fazla 1 tweet koy
- Her grupta en az {min_channels} FARKLI kanal olmalı
- Emin olmadığın eşleşmeleri KOYMA

{tweet_block}

JSON yanıt:
[{{"topic":"Kısa haber başlığı","tweet_ids":["id1","id2"]}}]
Eşleşme yoksa: []"""
    
    # 5) Gemini API çağrısı
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.8,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        }
    }
    
    response = None
    last_error = ""
    for model in GEMINI_MODELS:
        api_url = GEMINI_API_BASE.format(model=model)
        response = requests.post(
            f"{api_url}?key={api_key}",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code == 200:
            break
        last_error = f"{model}: {response.status_code} - {response.text[:150]}"
        if response.status_code == 429:
            import time
            time.sleep(2)
            continue
        elif response.status_code >= 500:
            continue
        else:
            break

    if response is None or response.status_code != 200:
        raise Exception(f"Gemini API hatası: {last_error}")
    
    # 6) Yanıtı parse et
    resp_data = response.json()
    text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
    
    matched_groups = _parse_gemini_json(text)
    
    if not matched_groups:
        return _fallback_match_by_keywords(all_tweets, min_channels)

    # 7) Tweet ID'lerini gerçek tweet verisiyle eşle (orijinal all_tweets'ten)
    tweet_map = {tw["tweet_id"]: tw for tw in all_tweets}
    
    results = []
    for group in matched_groups:
        topic = group.get("topic", "Bilinmeyen Konu")
        tweet_ids = group.get("tweet_ids", [])
        
        matched_tweets = []
        channels_in_group = set()
        
        for tid in tweet_ids:
            if tid in tweet_map:
                tw = tweet_map[tid]
                matched_tweets.append(tw)
                channels_in_group.add(tw["channel"])
        
        # Post-processing: Aynı kanaldan birden fazla tweet varsa sadece ilkini tut
        seen_channels = set()
        deduped_tweets = []
        for tw in matched_tweets:
            if tw["channel"] not in seen_channels:
                seen_channels.add(tw["channel"])
                deduped_tweets.append(tw)
        matched_tweets = deduped_tweets
        channels_in_group = seen_channels
        
        if len(channels_in_group) >= min_channels:
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
