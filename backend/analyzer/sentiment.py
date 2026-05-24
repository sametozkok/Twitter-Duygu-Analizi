"""Turkish sentiment analysis utilities with robust model fallback."""

from __future__ import annotations

import os

from transformers import pipeline

_sentiment_pipeline = None
_sentiment_pipeline_checked = False

_roberta_pipeline = None
_roberta_pipeline_checked = False

POSITIVE_WORDS = {
    "iyi",
    "guzel",
    "harika",
    "super",
    "tebrik",
    "helal",
    "bravo",
    "mukemmel",
    "mutlu",
    "sevdim",
    "begendim",
    "efsane",
    "muhtesem",
    "basarili",
}

NEGATIVE_WORDS = {
    "kotu",
    "berbat",
    "sacma",
    "rezalet",
    "yalan",
    "nefret",
    "utanc",
    "sinir",
    "fena",
    "vasat",
    "korkunc",
    "bok",
    "cop",
    "hata",
    "uzucu",
}


def _get_pipeline():
    """Lazy-load model pipeline once and cache result (including failure)."""

    global _sentiment_pipeline, _sentiment_pipeline_checked
    if _sentiment_pipeline_checked:
        return _sentiment_pipeline

    _sentiment_pipeline_checked = True
    try:
        allow_download = os.getenv("SENTIMENT_ALLOW_MODEL_DOWNLOAD", "1") == "1"
        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="savasy/bert-base-turkish-sentiment-cased",
            tokenizer="savasy/bert-base-turkish-sentiment-cased",
            truncation=True,
            max_length=512,
            local_files_only=not allow_download,
        )
    except Exception:
        _sentiment_pipeline = None

    return _sentiment_pipeline


def _fallback_rule_sentiment(text: str) -> dict:
    tokens = [token.strip(".,!?;:\"'()[]{}<>-_").lower() for token in text.split()]
    positive = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative = sum(1 for token in tokens if token in NEGATIVE_WORDS)

    if positive == 0 and negative == 0:
        return {"label": "neutral", "score": 0.5, "emoji": "N"}

    if positive > negative:
        score = 0.55 + min(0.4, (positive - negative) * 0.1)
        return {"label": "positive", "score": round(score, 4), "emoji": "+"}

    if negative > positive:
        score = 0.55 + min(0.4, (negative - positive) * 0.1)
        return {"label": "negative", "score": round(score, 4), "emoji": "-"}

    return {"label": "neutral", "score": 0.5, "emoji": "N"}


def analyze_sentiment(text: str) -> dict:
    """Analyze one text and return label/score."""

    pipe = _get_pipeline()
    if pipe is None:
        return _fallback_rule_sentiment(text)

    try:
        result = pipe(text[:512])[0]
    except Exception:
        return _fallback_rule_sentiment(text)

    raw_label = str(result.get("label", "")).lower()
    score = round(float(result.get("score", 0.0)), 4)

    if score < 0.60:
        return {"label": "neutral", "score": score, "emoji": "N"}

    if "pos" in raw_label:
        label = "positive"
    elif "neg" in raw_label:
        label = "negative"
    else:
        label = "neutral"

    return {
        "label": label,
        "score": score,
        "emoji": "+" if label == "positive" else "-" if label == "negative" else "N",
    }


def analyze_replies(replies: list[dict]) -> dict:
    """Analyze a list of replies and return aggregate sentiment stats."""

    if not replies:
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 0.0,
            "details": [],
        }

    positive = 0
    negative = 0
    neutral = 0
    details = []

    for reply in replies:
        text = str(reply.get("text", "")).strip()
        if len(text) < 3:
            continue

        result = analyze_sentiment(text)
        label = result["label"]

        if label == "positive":
            positive += 1
        elif label == "negative":
            negative += 1
        else:
            neutral += 1

        details.append(
            {
                "text": text[:150],
                "user": reply.get("user", ""),
                "label": label,
                "score": result["score"],
                "emoji": result["emoji"],
            }
        )

    total = positive + negative + neutral

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "positive_pct": round(positive / total * 100, 1) if total > 0 else 0.0,
        "negative_pct": round(negative / total * 100, 1) if total > 0 else 0.0,
        "neutral_pct": round(neutral / total * 100, 1) if total > 0 else 0.0,
        "details": details,
    }


def get_sentiment_backend_name() -> str:
    """Return active engine for sentiment analysis in current runtime."""

    return "bert-model" if _get_pipeline() is not None else "fallback-rule"


def analyze_sentiment_bulk(texts: list[str]) -> list[dict]:
    """Analyze a list of texts using batch processing and return list of label/score dicts."""
    if not texts:
        return []

    pipe = _get_pipeline()
    if pipe is None:
        return [_fallback_rule_sentiment(text) for text in texts]

    cleaned_texts = [text[:512] for text in texts]
    results = []
    
    try:
        batch_results = pipe(cleaned_texts, batch_size=16)
        
        for result in batch_results:
            raw_label = str(result.get("label", "")).lower()
            score = round(float(result.get("score", 0.0)), 4)

            if score < 0.60:
                results.append({"label": "neutral", "score": score, "emoji": "N"})
                continue

            if "pos" in raw_label:
                label = "positive"
            elif "neg" in raw_label:
                label = "negative"
            else:
                label = "neutral"

            results.append({
                "label": label,
                "score": score,
                "emoji": "+" if label == "positive" else "-" if label == "negative" else "N",
            })
            
    except Exception:
        return [_fallback_rule_sentiment(text) for text in texts]
        
    return results


def _get_roberta_pipeline():
    """Lazy-load Cardiff RoBERTa pipeline once and cache result (including failure)."""
    global _roberta_pipeline, _roberta_pipeline_checked
    if _roberta_pipeline_checked:
        return _roberta_pipeline

    _roberta_pipeline_checked = True
    try:
        from transformers import AutoModelForSequenceClassification, XLMRobertaTokenizer
        allow_download = os.getenv("SENTIMENT_ALLOW_MODEL_DOWNLOAD", "1") == "1"
        model_id = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
        tokenizer = XLMRobertaTokenizer.from_pretrained(model_id, local_files_only=not allow_download)
        model = AutoModelForSequenceClassification.from_pretrained(model_id, local_files_only=not allow_download)
        
        _roberta_pipeline = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            truncation=True,
            max_length=512,
            framework="pt",
            device=-1,
        )
    except Exception:
        _roberta_pipeline = None

    return _roberta_pipeline


def analyze_roberta(text: str) -> dict:
    """Analyze one text using RoBERTa and return label/score."""
    pipe = _get_roberta_pipeline()
    if pipe is None:
        return _fallback_rule_sentiment(text)

    try:
        result = pipe(text[:512])[0]
    except Exception:
        return _fallback_rule_sentiment(text)

    raw_label = str(result.get("label", "")).lower().strip()
    score = round(float(result.get("score", 0.0)), 4)

    if "pos" in raw_label or raw_label in {"label_2", "2"}:
        label = "positive"
    elif "neg" in raw_label or raw_label in {"label_0", "0"}:
        label = "negative"
    else:
        label = "neutral"

    return {
        "label": label,
        "score": score,
        "emoji": "+" if label == "positive" else "-" if label == "negative" else "N",
    }


def analyze_roberta_bulk(texts: list[str]) -> list[dict]:
    """Analyze a list of texts using batch processing with RoBERTa and return list of label/score dicts."""
    if not texts:
        return []

    pipe = _get_roberta_pipeline()
    if pipe is None:
        return [_fallback_rule_sentiment(text) for text in texts]

    cleaned_texts = [text[:512] for text in texts]
    results = []
    
    try:
        batch_results = pipe(cleaned_texts, batch_size=16)
        
        for result in batch_results:
            raw_label = str(result.get("label", "")).lower().strip()
            score = round(float(result.get("score", 0.0)), 4)

            if "pos" in raw_label or raw_label in {"label_2", "2"}:
                label = "positive"
            elif "neg" in raw_label or raw_label in {"label_0", "0"}:
                label = "negative"
            else:
                label = "neutral"

            results.append({
                "label": label,
                "score": score,
                "emoji": "+" if label == "positive" else "-" if label == "negative" else "N",
            })
            
    except Exception:
        return [_fallback_rule_sentiment(text) for text in texts]
        
    return results
