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

GEMINI_MODELS = [
    "gemini-3.1-flash-lite-preview",
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
                timeout=45,
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

def bulk_analyze_sentiment_with_gemini(replies: list[dict]) -> dict[int, tuple[str, float]]:
    """
    Returns a mapping of reply ID/index to (label, score).
    """
    if not replies:
        return {}

    provider = _resolve_provider()
    if provider == "none":
        return {}

    all_prompt_lines = []
    for i, reply in enumerate(replies):
        raw_text = _raw_for_api(str(reply.get("text") or reply.get("clean_text") or ""))
        if not raw_text or len(raw_text) < 2:
            continue
        all_prompt_lines.append(f"{i}|{raw_text}")

    if not all_prompt_lines:
        return {}

    system_instruction = (
        "Sen bir duygu analizi motorusun. Sana verilen metinlerin (yorumların) duygusunu analiz et. "
        "Yalnızca Türkçe metinleri analiz et. "
        "Her metni 'positive', 'negative' veya 'neutral' olarak sınıflandır. "
        "Confidence skoru (0.0 ile 1.0 arası) belirle."
    )
    headers = {"Content-Type": "application/json"}

    result_map = {}
    
    # Process in chunks of 100 to avoid confusing the model and hitting limits
    chunk_size = 100
    for chunk_start in range(0, len(all_prompt_lines), chunk_size):
        prompt_lines = all_prompt_lines[chunk_start:chunk_start + chunk_size]
        tweet_block = "\n".join(prompt_lines)

        prompt = f"""Aşağıda {len(prompt_lines)} adet yorum var (ID|metin formatında).
Her bir yorumun duygu analizini yap ve JSON array olarak döndür.

Veri:
{tweet_block}

ÇIKTI KURALI:
- SADECE JSON döndür.
- Format:
[{{"id": 0, "label": "positive|negative|neutral", "score": 0.95}}]
"""

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.7,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            }
        }

        if provider == "grok":
            grok_text = _call_grok(prompt, system_instruction, max_tokens=4096)
            if not grok_text:
                return {}
            parsed_results = _parse_gemini_json(grok_text)

            for item in parsed_results:
                idx = item.get("id")
                if idx is not None:
                    label = str(item.get("label", "neutral")).lower()
                    if label not in ("positive", "negative", "neutral"):
                        label = "neutral"
                    score = float(item.get("score", 0.5))
                    result_map[idx] = (label, score)
            continue

        response = None
        rate_limited = False
        for model in GEMINI_MODELS:
            api_url = GEMINI_API_BASE.format(model=model)
            for attempt in range(3):
                try:
                    response = requests.post(
                        f"{api_url}?key={GEMINI_API_KEY}",
                        headers=headers,
                        json=payload,
                        timeout=45,
                    )
                except requests.RequestException:
                    response = None
                    time.sleep(1 + attempt)
                    continue
                if response is not None and response.status_code == 200:
                    break
                if response is not None and response.status_code in (429, 503):
                    rate_limited = True
                    break
                if response is not None and response.status_code == 404:
                    break
                break
            if rate_limited:
                break
            if response is not None and response.status_code == 200:
                break

        if rate_limited or response is None or response.status_code != 200:
            status_code = response.status_code if response else "No Response"
            print(f"Gemini API Error ({model}): Status Code: {status_code}")
            if response is not None:
                print(f"Response Text: {response.text}")
            return {}

        try:
            resp_data = response.json()
            text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Gemini API Parsing Error from JSON structure: {e}")
            if response is not None:
                print(f"Raw JSON: {response.text}")
            return {}

        parsed_results = _parse_gemini_json(text)
        
        for item in parsed_results:
            idx = item.get("id")
            if idx is not None:
                label = str(item.get("label", "neutral")).lower()
                if label not in ("positive", "negative", "neutral"):
                    label = "neutral"
                score = float(item.get("score", 0.5))
                result_map[idx] = (label, score)

    return result_map
