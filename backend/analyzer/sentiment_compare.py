"""Multi-algorithm sentiment comparison utilities."""
from __future__ import annotations

from collections import Counter

from config import GEMINI_API_DISABLED, GEMINI_API_KEY, GROK_API_BASE, GROK_API_KEY, LLM_PROVIDER


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

    if GEMINI_API_DISABLED or not GEMINI_API_KEY:
        normalized_algorithms = [alg for alg in normalized_algorithms if alg != "api"]
        if not normalized_algorithms:
            normalized_algorithms = ["bert", "hybrid"]

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


def compare_group_replies(replies_by_channel: dict[str, list[dict]], algorithms: list[str]) -> dict[str, dict]:
    """
    Analyzes replies for all channels in a group efficiently using batch processing.
    Returns: { channel_name: { algorithms: {...}, best_algorithm: "..." } }
    """
    normalized_algorithms = [item.strip().lower() for item in algorithms if item.strip()]
    if not normalized_algorithms:
        normalized_algorithms = ["bert", "hybrid", "api"]

    if GEMINI_API_DISABLED or not GEMINI_API_KEY:
        normalized_algorithms = [alg for alg in normalized_algorithms if alg != "api"]
        if not normalized_algorithms:
            normalized_algorithms = ["bert", "hybrid"]

    def _api_engine_name() -> str:
        if LLM_PROVIDER == "groq":
            return "groq-api"
        if LLM_PROVIDER == "grok":
            return "grok-api"
        if GROK_API_KEY:
            base = GROK_API_BASE.lower()
            if "groq.com" in base:
                return "groq-api"
            if "x.ai" in base:
                return "grok-api"
            return "llm-api"
        return "gemini-api"

    all_replies = []
    mapping = {}
    
    for channel_name, replies in replies_by_channel.items():
        for local_idx, reply in enumerate(replies):
            global_idx = len(all_replies)
            all_replies.append(reply)
            mapping[global_idx] = (channel_name, local_idx)

    api_results_map = {}
    api_failed = False
    
    if "api" in normalized_algorithms:
        try:
            from backend.analyzer.gemini_sentiment import bulk_analyze_sentiment_with_gemini
            api_results_map = bulk_analyze_sentiment_with_gemini(all_replies)
            if not api_results_map and all_replies:
                api_failed = True
        except Exception:
            api_failed = True
            api_results_map = {}

    try:
        from backend.analyzer.sentiment import analyze_sentiment_bulk, get_sentiment_backend_name
        bert_engine = get_sentiment_backend_name()
    except Exception:
        analyze_sentiment_bulk = lambda texts: [{"label": "neutral", "score": 0.5, "emoji": "N"} for _ in texts]
        bert_engine = "fallback-rule"
    
    clean_texts = []
    for r in all_replies:
        t = str(r.get("clean_text") or r.get("text") or "").strip()
        clean_texts.append(t if len(t) >= 2 else "")
        
    bulk_results = analyze_sentiment_bulk(clean_texts)
    
    channel_results = {ch: {"algorithms": {}, "best_algorithm": "hybrid" if "hybrid" in normalized_algorithms else normalized_algorithms[0]} for ch in replies_by_channel.keys()}
    
    channel_alg_data = {
        ch: {
            alg: {"items": [], "counts": Counter()} for alg in normalized_algorithms
        } for ch in replies_by_channel.keys()
    }
    
    for global_idx, reply in enumerate(all_replies):
        channel_name, local_idx = mapping[global_idx]
        text = clean_texts[global_idx]
        
        if not text:
            continue
            
        bert_res = bulk_results[global_idx]
        bert_label = bert_res["label"]
        bert_score = bert_res["score"]
        
        hybrid_label = bert_label
        hybrid_score = bert_score
        if hybrid_label in {"positive", "negative"} and hybrid_score < 0.75:
            hybrid_label = "neutral"
            
        for alg in normalized_algorithms:
            if alg == "api":
                if api_failed:
                    label, score = bert_label, bert_score
                else:
                    label, score = api_results_map.get(global_idx, (bert_label, bert_score))
            elif alg == "bert":
                label, score = bert_label, bert_score
            elif alg == "hybrid":
                label, score = hybrid_label, hybrid_score
            else:
                label, score = "neutral", 0.5
                
            channel_alg_data[channel_name][alg]["counts"][label] += 1
            channel_alg_data[channel_name][alg]["items"].append({
                "user": reply.get("user", ""),
                "name": reply.get("name", ""),
                "text": text,
                "label": label,
                "score": round(float(score), 4)
            })

    for channel_name in replies_by_channel.keys():
        for alg in normalized_algorithms:
            counts = channel_alg_data[channel_name][alg]["counts"]
            items = channel_alg_data[channel_name][alg]["items"]
            total = len(items)
            
            if alg == "bert":
                engine_name = bert_engine
            elif alg == "hybrid":
                engine_name = f"hybrid({bert_engine}+confidence-gate)"
            elif alg == "api":
                if api_failed:
                    engine_name = f"API başarısız oldu, yerel model ({bert_engine}) sonuçları kullanılıyor"
                else:
                    engine_name = _api_engine_name()
            else:
                engine_name = "unknown"
                
            channel_results[channel_name]["algorithms"][alg] = {
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
            
    return channel_results
