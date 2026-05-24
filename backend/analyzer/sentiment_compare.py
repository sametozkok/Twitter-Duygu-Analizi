"""Multi-algorithm sentiment comparison utilities."""
from __future__ import annotations

from collections import Counter

from config import GEMINI_API_DISABLED, GEMINI_API_KEY, GROK_API_KEY


def _load_bert_analyzer():
    try:
        from backend.analyzer.sentiment import analyze_sentiment, get_sentiment_backend_name  # type: ignore

        return analyze_sentiment, get_sentiment_backend_name
    except Exception:
        return None, None


_BERT_ANALYZER, _BERT_BACKEND_NAME = _load_bert_analyzer()


def _load_roberta_analyzer():
    try:
        from backend.analyzer.sentiment import analyze_roberta
        return analyze_roberta
    except Exception:
        return None


_ROBERTA_ANALYZER = _load_roberta_analyzer()


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


def _roberta_label(text: str) -> tuple[str, float]:
    if _ROBERTA_ANALYZER is not None:
        try:
            result = _ROBERTA_ANALYZER(text)
            label = str(result.get("label", "neutral")).lower()
            score = float(result.get("score", 0.5))
            return label, score
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
    if name == "roberta":
        return _roberta_label(text)
    raise ValueError(f"Unknown algorithm: {name}")


# LLM algorithm keys we expose to the frontend.
_LLM_ALGORITHMS = {"groq", "gemini"}
# Legacy single-LLM key; auto-resolves to first available provider.
_LEGACY_API_ALGORITHM = "api"


def _llm_unavailable_reason(algorithm: str) -> str | None:
    """Return Turkish reason if algorithm is unavailable from config, else None."""
    if algorithm == "gemini":
        if GEMINI_API_DISABLED:
            return "Gemini API devre dışı bırakıldı (GEMINI_API_DISABLED)"
        if not GEMINI_API_KEY:
            return "GEMINI_API_KEY tanımlı değil"
        return None
    if algorithm == "groq":
        if not GROK_API_KEY:
            return "GROQ_API_KEY tanımlı değil"
        return None
    return None


def _empty_summary() -> dict:
    return {
        "total": 0,
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "dominant": "neutral",
    }


def compare_replies(replies: list[dict], algorithms: list[str]) -> dict:
    normalized_algorithms = [item.strip().lower() for item in algorithms if item.strip()]
    if not normalized_algorithms:
        normalized_algorithms = ["bert", "roberta", "hybrid", "groq", "gemini"]

    # Expand legacy "api" into both LLMs for backwards compatibility.
    if _LEGACY_API_ALGORITHM in normalized_algorithms:
        normalized_algorithms = [a for a in normalized_algorithms if a != _LEGACY_API_ALGORITHM]
        for k in ("groq", "gemini"):
            if k not in normalized_algorithms:
                normalized_algorithms.append(k)

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

    # Run each LLM provider once for the whole set.
    llm_results: dict[str, dict[int, tuple[str, float]]] = {}
    llm_errors: dict[str, str | None] = {}
    for alg in normalized_algorithms:
        if alg not in _LLM_ALGORITHMS:
            continue
        config_err = _llm_unavailable_reason(alg)
        if config_err:
            llm_results[alg] = {}
            llm_errors[alg] = config_err
            continue
        try:
            from backend.analyzer.gemini_sentiment import bulk_analyze_sentiment
            res, err = bulk_analyze_sentiment(replies, provider=alg)
            llm_results[alg] = res
            llm_errors[alg] = err
        except Exception as exc:
            llm_results[alg] = {}
            llm_errors[alg] = f"Beklenmeyen hata: {exc.__class__.__name__}"

    for algorithm in normalized_algorithms:
        items = []
        counts = Counter()

        if algorithm in _LLM_ALGORITHMS and llm_errors.get(algorithm):
            algorithm_results[algorithm] = {
                "engine": f"{algorithm}-api",
                "available": False,
                "error": llm_errors.get(algorithm),
                "summary": _empty_summary(),
                "items": [],
            }
            continue

        for i, reply in enumerate(replies):
            clean_text = str(reply.get("clean_text") or reply.get("text") or "").strip()
            if len(clean_text) < 2:
                continue

            if algorithm in _LLM_ALGORITHMS:
                label, score = llm_results.get(algorithm, {}).get(i, ("neutral", 0.5))
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
        elif algorithm == "roberta":
            engine_name = "roberta-model"
        elif algorithm == "hybrid":
            engine_name = f"hybrid({bert_engine}+confidence-gate)"
        elif algorithm == "groq":
            engine_name = "groq-api"
        elif algorithm == "gemini":
            engine_name = "gemini-api"
        else:
            engine_name = "unknown"

        algorithm_results[algorithm] = {
            "engine": engine_name,
            "available": True,
            "summary": {
                "total": total,
                "positive": int(counts.get("positive", 0)),
                "negative": int(counts.get("negative", 0)),
                "neutral": int(counts.get("neutral", 0)),
                "dominant": counts.most_common(1)[0][0] if total > 0 else "neutral",
            },
            "items": items,
        }

    if "hybrid" in algorithm_results:
        best_algorithm = "hybrid"
    elif normalized_algorithms:
        best_algorithm = normalized_algorithms[0]
    else:
        best_algorithm = "bert"

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
        normalized_algorithms = ["bert", "roberta", "hybrid", "groq", "gemini"]

    if _LEGACY_API_ALGORITHM in normalized_algorithms:
        normalized_algorithms = [a for a in normalized_algorithms if a != _LEGACY_API_ALGORITHM]
        for k in ("groq", "gemini"):
            if k not in normalized_algorithms:
                normalized_algorithms.append(k)

    all_replies = []
    mapping = {}

    for channel_name, replies in replies_by_channel.items():
        for local_idx, reply in enumerate(replies):
            global_idx = len(all_replies)
            all_replies.append(reply)
            mapping[global_idx] = (channel_name, local_idx)

    # Run each requested LLM provider exactly once over the whole batch.
    llm_results: dict[str, dict[int, tuple[str, float]]] = {}
    llm_errors: dict[str, str | None] = {}
    for alg in normalized_algorithms:
        if alg not in _LLM_ALGORITHMS:
            continue
        config_err = _llm_unavailable_reason(alg)
        if config_err:
            llm_results[alg] = {}
            llm_errors[alg] = config_err
            continue
        try:
            from backend.analyzer.gemini_sentiment import bulk_analyze_sentiment
            res, err = bulk_analyze_sentiment(all_replies, provider=alg)
            llm_results[alg] = res
            llm_errors[alg] = err
            if not res and not err and all_replies:
                llm_errors[alg] = "Sağlayıcı sonuç döndürmedi"
        except Exception as exc:
            llm_results[alg] = {}
            llm_errors[alg] = f"Beklenmeyen hata: {exc.__class__.__name__}"

    try:
        from backend.analyzer.sentiment import analyze_sentiment_bulk, analyze_roberta_bulk, get_sentiment_backend_name
        bert_engine = get_sentiment_backend_name()
    except Exception:
        analyze_sentiment_bulk = lambda texts: [{"label": "neutral", "score": 0.5, "emoji": "N"} for _ in texts]
        analyze_roberta_bulk = lambda texts: [{"label": "neutral", "score": 0.5, "emoji": "N"} for _ in texts]
        bert_engine = "fallback-rule"

    clean_texts = []
    for r in all_replies:
        t = str(r.get("clean_text") or r.get("text") or "").strip()
        clean_texts.append(t if len(t) >= 2 else "")

    bulk_results = analyze_sentiment_bulk(clean_texts)
    roberta_bulk_results = []
    if "roberta" in normalized_algorithms:
        roberta_bulk_results = analyze_roberta_bulk(clean_texts)

    channel_results = {
        ch: {
            "algorithms": {},
            "best_algorithm": "hybrid" if "hybrid" in normalized_algorithms else (normalized_algorithms[0] if normalized_algorithms else "bert"),
        }
        for ch in replies_by_channel.keys()
    }

    channel_alg_data = {
        ch: {alg: {"items": [], "counts": Counter()} for alg in normalized_algorithms}
        for ch in replies_by_channel.keys()
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
            if alg in _LLM_ALGORITHMS:
                if llm_errors.get(alg):
                    continue
                label, score = llm_results.get(alg, {}).get(global_idx, (bert_label, bert_score))
            elif alg == "bert":
                label, score = bert_label, bert_score
            elif alg == "roberta":
                if roberta_bulk_results:
                    res = roberta_bulk_results[global_idx]
                    label, score = res["label"], res["score"]
                else:
                    label, score = "neutral", 0.5
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
                "score": round(float(score), 4),
            })

    for channel_name in replies_by_channel.keys():
        for alg in normalized_algorithms:
            counts = channel_alg_data[channel_name][alg]["counts"]
            items = channel_alg_data[channel_name][alg]["items"]
            total = len(items)

            if alg == "bert":
                engine_name = bert_engine
                available = True
                error_msg = None
            elif alg == "roberta":
                engine_name = "roberta-model"
                available = True
                error_msg = None
            elif alg == "hybrid":
                engine_name = f"hybrid({bert_engine}+confidence-gate)"
                available = True
                error_msg = None
            elif alg == "groq":
                engine_name = "groq-api"
                error_msg = llm_errors.get(alg)
                available = error_msg is None
            elif alg == "gemini":
                engine_name = "gemini-api"
                error_msg = llm_errors.get(alg)
                available = error_msg is None
            else:
                engine_name = "unknown"
                available = True
                error_msg = None

            entry = {
                "engine": engine_name,
                "available": available,
                "summary": {
                    "total": total,
                    "positive": int(counts.get("positive", 0)),
                    "negative": int(counts.get("negative", 0)),
                    "neutral": int(counts.get("neutral", 0)),
                    "dominant": counts.most_common(1)[0][0] if total > 0 else "neutral",
                },
                "items": items,
            }
            if error_msg:
                entry["error"] = error_msg
            channel_results[channel_name]["algorithms"][alg] = entry

    return channel_results
