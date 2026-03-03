"""
Duygu Analizi - Türkçe BERT modeli ile sentiment analysis
"""
from transformers import pipeline

_sentiment_pipeline = None


def _get_pipeline():
    """Modeli lazy-load et (ilk kullanımda yükle, sonra cache'den)."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="savasy/bert-base-turkish-sentiment-cased",
            tokenizer="savasy/bert-base-turkish-sentiment-cased",
            truncation=True,
            max_length=512,
        )
    return _sentiment_pipeline


def analyze_sentiment(text: str) -> dict:
    """Tek bir metin için duygu analizi yap.
    
    Args:
        text: Analiz edilecek metin
    
    Returns:
        dict: {"label": "positive"|"negative", "score": float, "emoji": "🟢"|"🔴"}
    """
    pipe = _get_pipeline()
    result = pipe(text[:512])[0]
    label = result["label"].lower()
    
    return {
        "label": label,
        "score": result["score"],
        "emoji": "🟢" if label == "positive" else "🔴",
    }


def analyze_replies(replies: list[dict]) -> dict:
    """Bir tweet'in tüm yorumlarını analiz et ve istatistik döndür.
    
    Args:
        replies: [{"text": str, ...}, ...]
    
    Returns:
        dict: {
            "total": int,
            "positive": int,
            "negative": int,
            "positive_pct": float,
            "negative_pct": float,
            "details": [{"text": str, "label": str, "score": float, "emoji": str}, ...]
        }
    """
    if not replies:
        return {
            "total": 0, "positive": 0, "negative": 0,
            "positive_pct": 0.0, "negative_pct": 0.0, "details": []
        }
    
    positive = 0
    negative = 0
    details = []
    
    for reply in replies:
        text = reply.get("text", "")
        if not text or len(text) < 3:
            continue
        
        result = analyze_sentiment(text)
        
        if result["label"] == "positive":
            positive += 1
        else:
            negative += 1
        
        details.append({
            "text": text[:150],
            "user": reply.get("user", ""),
            "label": result["label"],
            "score": result["score"],
            "emoji": result["emoji"],
        })
    
    total = positive + negative
    
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "positive_pct": round(positive / total * 100, 1) if total > 0 else 0.0,
        "negative_pct": round(negative / total * 100, 1) if total > 0 else 0.0,
        "details": details,
    }
