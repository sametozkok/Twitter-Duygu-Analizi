"""
Haber Eşleştirme - Google Gemini API ile haberleri karşılaştır
"""
import json
import re
import requests


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    
    Args:
        channels_data: fetch_multiple_channels çıktısı
            [{"username": "x", "tweets": [...]}, ...]
        api_key: Gemini API key
        min_channels: En az kaç kanalda geçmeli (default 2)
    
    Returns:
        list[dict]: [
            {
                "topic": "Haber başlığı/konusu",
                "tweets": [
                    {"channel": "pusholder", "tweet_id": "...", "text": "...", "url": "..."},
                    {"channel": "vaikigundem", "tweet_id": "...", "text": "...", "url": "..."},
                    ...
                ],
                "channel_count": 3
            },
            ...
        ]
    """
    # Tüm tweetleri kanal bilgisiyle birlikte topla
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
    
    # Gemini'ye gönderilecek prompt
    channel_names = [ch["username"] for ch in channels_data]
    
    prompt = f"""Aşağıda {len(channel_names)} farklı Twitter haber kanalından ({', '.join(channel_names)}) alınmış toplam {len(all_tweets)} tweet var.

Görevin:
1. Bu tweetleri konu bazında grupla
2. Aynı olaydan/haberden bahseden tweetleri eşleştir
3. Sadece en az {min_channels} farklı kanalda geçen haberleri döndür
4. Her grup için kısa bir konu başlığı yaz

Tweet listesi:
{json.dumps(all_tweets, ensure_ascii=False, indent=2)}

SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:
[
  {{
    "topic": "Konu başlığı",
    "tweet_ids": ["id1", "id2", "id3"]
  }}
]

Eşleşme bulamazsan boş liste döndür: []
"""

    # Gemini API çağrısı
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
    
    # Birden fazla model dene (rate limit / uyumluluk için)
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
            time.sleep(2)  # rate limit bekle
            continue
        elif response.status_code >= 500:
            continue  # server error, sonraki modeli dene
        else:
            break  # 400, 401, 403 gibi hatalar için durma

    if response is None or response.status_code != 200:
        raise Exception(f"Gemini API hatası: {last_error}")
    
    # Yanıtı parse et
    resp_data = response.json()
    text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
    
    matched_groups = _parse_gemini_json(text)
    
    # Gemini boş/bozuk sonuç döndürürse fallback uygula
    if not matched_groups:
        return _fallback_match_by_keywords(all_tweets, min_channels)

    # Tweet ID'lerini gerçek tweet verisiyle eşle
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
        
        if len(channels_in_group) >= min_channels:
            results.append({
                "topic": topic,
                "tweets": matched_tweets,
                "channel_count": len(channels_in_group),
                "channels": list(channels_in_group),
            })
    
    # Gemini parse oldu ama filtre sonrası boş kaldıysa fallback uygula
    if not results:
        return _fallback_match_by_keywords(all_tweets, min_channels)

    # Kanal sayısına göre sırala (çoktan aza)
    results.sort(key=lambda x: x["channel_count"], reverse=True)
    
    return results
