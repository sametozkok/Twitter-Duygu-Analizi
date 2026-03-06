"""
Türkçe duygu (emotion) analizi - emrecan/bert-base-turkish-cased-emotion
"""
from collections import Counter
from transformers import pipeline

_emotion_pipeline = None

PRIMARY_MODEL = "emrecan/bert-base-turkish-cased-emotion"
FALLBACK_MODEL = "zafercavdar/distilbert-base-turkish-cased-emotion"


def _get_pipeline():
    global _emotion_pipeline
    if _emotion_pipeline is None:
        try:
            _emotion_pipeline = pipeline(
                "text-classification",
                model=PRIMARY_MODEL,
                tokenizer=PRIMARY_MODEL,
                truncation=True,
                max_length=512,
            )
        except OSError:
            _emotion_pipeline = pipeline(
                "text-classification",
                model=FALLBACK_MODEL,
                tokenizer=FALLBACK_MODEL,
                truncation=True,
                max_length=512,
            )
    return _emotion_pipeline


def analyze_emotion(text: str) -> dict:
    pipe = _get_pipeline()
    result = pipe(text[:512])[0]
    return {
        "label": str(result.get("label", "unknown")).lower(),
        "score": float(result.get("score", 0.0)),
    }


def analyze_emotions_for_replies(replies: list[dict]) -> dict:
    if not replies:
        return {
            "total": 0,
            "avg_score": 0.0,
            "dominant_emotion": "-",
            "label_counts": {},
            "details": [],
        }

    details = []
    label_counter = Counter()
    score_sum = 0.0

    for reply in replies:
        text = (reply.get("text") or "").strip()
        if len(text) < 3:
            continue

        pred = analyze_emotion(text)
        label_counter[pred["label"]] += 1
        score_sum += pred["score"]

        details.append({
            "user": reply.get("user", ""),
            "text": text,
            "label": pred["label"],
            "score": pred["score"],
        })

    total = len(details)
    if total == 0:
        return {
            "total": 0,
            "avg_score": 0.0,
            "dominant_emotion": "-",
            "label_counts": {},
            "details": [],
        }

    dominant_emotion = label_counter.most_common(1)[0][0] if label_counter else "-"

    return {
        "total": total,
        "avg_score": round(score_sum / total, 4),
        "dominant_emotion": dominant_emotion,
        "label_counts": dict(label_counter),
        "details": details,
    }
