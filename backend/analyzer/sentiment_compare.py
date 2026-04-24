"""Multi-algorithm sentiment comparison utilities."""
from __future__ import annotations

from collections import Counter


def _load_bert_analyzer():
    try:
        from backend.analyzer.sentiment import analyze_sentiment, get_sentiment_backend_name  # type: ignore

        return analyze_sentiment, get_sentiment_backend_name
    except Exception:
        return None, None


_BERT_ANALYZER, _BERT_BACKEND_NAME = _load_bert_analyzer()


def _bert_label(text: str) -> tuple[str, float]:
    if _BERT_ANALYZER is not None:
        try:
            result = _BERT_ANALYZER(text)
            raw_label = str(result.get("label", "")).lower()
            score = float(result.get("score", 0.0))

            if score < 0.60:
                return "neutral", score

            if "pos" in raw_label:
                return "positive", score
            if "neg" in raw_label:
                return "negative", score
            if raw_label == "neutral":
                return "neutral", score
        except Exception:
            pass

    return "neutral", 0.5


def _hybrid_label(text: str) -> tuple[str, float]:
    bert_label, bert_score = _bert_label(text)

    # Confidence-gated BERT: uncertain positive/negative turns into neutral.
    if bert_label in {"positive", "negative"} and bert_score < 0.75:
        return "neutral", bert_score

    return bert_label, bert_score


def _classify(name: str, text: str) -> tuple[str, float]:
    if name == "bert":
        return _bert_label(text)
    if name == "hybrid":
        return _hybrid_label(text)
    raise ValueError(f"Unknown algorithm: {name}")


def compare_replies(replies: list[dict], algorithms: list[str]) -> dict:
    normalized_algorithms = [item.strip().lower() for item in algorithms if item.strip()]
    if not normalized_algorithms:
        normalized_algorithms = ["bert", "hybrid", "api"]

    algorithm_results: dict[str, dict] = {}
    if _BERT_ANALYZER is None:
        bert_engine = "fallback-rule"
    elif callable(_BERT_BACKEND_NAME):
        try:
            bert_engine = str(_BERT_BACKEND_NAME())
        except Exception:
            bert_engine = "fallback-rule"
    else:
        bert_engine = "fallback-rule"

    # API için tüm yorumları tek seferde değerlendir.
    api_results_map = {}
    if "api" in normalized_algorithms:
        try:
            from backend.analyzer.gemini_sentiment import bulk_analyze_sentiment_with_gemini
            api_results_map = bulk_analyze_sentiment_with_gemini(replies)
        except Exception:
            pass

    for algorithm in normalized_algorithms:
        items = []
        counts = Counter()

        for i, reply in enumerate(replies):
            clean_text = str(reply.get("clean_text") or reply.get("text") or "").strip()
            if len(clean_text) < 2:
                continue

            if algorithm == "api":
                label, score = api_results_map.get(i, ("neutral", 0.5))
            else:
                label, score = _classify(algorithm, clean_text)
                
            counts[label] += 1
            items.append({
                "user": reply.get("user", ""),
                "name": reply.get("name", ""),
                "text": clean_text,
                "label": label,
                "score": round(float(score), 4),
            })

        total = len(items)
        if algorithm == "bert":
            engine_name = bert_engine
        elif algorithm == "hybrid":
            engine_name = f"hybrid({bert_engine}+confidence-gate)"
        elif algorithm == "api":
            engine_name = "gemini-api"
        else:
            engine_name = "unknown"

        algorithm_results[algorithm] = {
            "engine": engine_name,
            "summary": {
                "total": total,
                "positive": int(counts.get("positive", 0)),
                "negative": int(counts.get("negative", 0)),
                "neutral": int(counts.get("neutral", 0)),
                "dominant": counts.most_common(1)[0][0] if total > 0 else "neutral",
            },
            "items": items,
        }

    best_algorithm = "hybrid" if "hybrid" in algorithm_results else normalized_algorithms[0]

    return {
        "algorithms": algorithm_results,
        "best_algorithm": best_algorithm,
    }
