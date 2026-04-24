import json
import re
import requests
import time
from config import GEMINI_API_KEY

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def _clean_for_api(text: str, max_len: int = 150) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _raw_for_api(text: str) -> str:
    return text.strip()

def _parse_gemini_json(raw_text: str) -> list:
    text = raw_text.strip()
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    
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
        text = text[start_idx:] + ']'
    else:
        text = text[start_idx:end_idx + 1]
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    cleaned = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(cleaned)
    except Exception:
        return []

def bulk_analyze_sentiment_with_gemini(replies: list[dict]) -> dict[str, tuple[str, float]]:
    """
    Returns a mapping of reply ID/index to (label, score).
    """
    if not GEMINI_API_KEY or not replies:
        return {}

    prompt_lines = []
    # Create a mapping to easily assign results back
    mapping = {}
    for i, reply in enumerate(replies):
        raw_text = _raw_for_api(str(reply.get("text") or reply.get("clean_text") or ""))
        if not raw_text or len(raw_text) < 2:
            continue
        prompt_lines.append(f"{i}|{raw_text}")
        mapping[i] = reply

    if not prompt_lines:
        return {}

    # Gemini has limits, if we have too many, we might need to batch, but for ~20-50 replies, it's fine.
    tweet_block = "\n".join(prompt_lines)

    system_instruction = (
        "Sen bir duygu analizi motorusun. Sana verilen metinlerin (yorumların) duygusunu analiz et. "
        "Yalnızca Türkçe metinleri analiz et. "
        "Her metni 'positive', 'negative' veya 'neutral' olarak sınıflandır. "
        "Confidence skoru (0.0 ile 1.0 arası) belirle."
    )

    prompt = f"""Aşağıda {len(prompt_lines)} adet yorum var (ID|metin formatında).
Her bir yorumun duygu analizini yap ve JSON array olarak döndür.

Veri:
{tweet_block}

ÇIKTI KURALI:
- SADECE JSON döndür.
- Format:
[{{"id": 0, "label": "positive|negative|neutral", "score": 0.95}}]
"""

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
    for model in GEMINI_MODELS:
        api_url = GEMINI_API_BASE.format(model=model)
        for attempt in range(2):
            try:
                response = requests.post(
                    f"{api_url}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
            except requests.RequestException:
                response = None
                if attempt == 0:
                    time.sleep(1)
                    continue
                break
            if response.status_code == 200:
                break
            if response.status_code == 429:
                time.sleep(2)
                continue
            break
        if response is not None and response.status_code == 200:
            break

    if response is None or response.status_code != 200:
        return {}

    try:
        resp_data = response.json()
        text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return {}

    parsed_results = _parse_gemini_json(text)
    
    result_map = {}
    for item in parsed_results:
        idx = item.get("id")
        if idx is not None:
            label = str(item.get("label", "neutral")).lower()
            if label not in ("positive", "negative", "neutral"):
                label = "neutral"
            score = float(item.get("score", 0.5))
            result_map[idx] = (label, score)

    return result_map
