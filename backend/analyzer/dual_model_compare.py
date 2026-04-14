"""Dual-model sentiment comparison utilities for Turkish comments."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from backend.preprocess.text_cleaner import clean_reply_text

MODEL_REGISTRY = {
    "savasy_bert": "savasy/bert-base-turkish-sentiment-cased",
    "cardiff_xlm_roberta": "cardiffnlp/twitter-xlm-roberta-base-sentiment",
}

DEFAULT_MODEL_WEIGHTS = {
    "savasy_bert": 0.55,
    "cardiff_xlm_roberta": 0.45,
}

_PIPELINES: dict[str, object] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_source_path(source_file: str) -> Path:
    candidate = Path(source_file)
    if candidate.is_absolute():
        return candidate
    return _project_root() / source_file


def _load_comments(source_file: str, limit: int) -> list[dict]:
    file_path = _resolve_source_path(source_file)
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Yorum kaynagi liste formatinda olmali.")

    loaded: list[dict] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue

        text = str(item.get("yorum") or item.get("text") or "").strip()
        clean_text = clean_reply_text(text)
        if len(clean_text) < 2:
            continue

        loaded.append(
            {
                "index": idx,
                "user": str(item.get("kullanici") or item.get("user") or ""),
                "text": text,
                "clean_text": clean_text,
            }
        )

        if len(loaded) >= max(1, int(limit)):
            break

    return loaded


def _normalize_label(raw_label: str) -> str:
    label = raw_label.strip().lower()

    if "pos" in label:
        return "positive"
    if "neg" in label:
        return "negative"
    if "neu" in label:
        return "neutral"

    # Some checkpoints return id-like labels.
    if label in {"label_0", "0"}:
        return "negative"
    if label in {"label_1", "1"}:
        return "neutral"
    if label in {"label_2", "2"}:
        return "positive"

    return "neutral"


def _label_to_score(label: str) -> float:
    if label == "positive":
        return 1.0
    if label == "negative":
        return -1.0
    return 0.0


def _get_pipeline(model_key: str):
    if model_key in _PIPELINES:
        return _PIPELINES[model_key]

    if model_key not in MODEL_REGISTRY:
        raise ValueError(f"Desteklenmeyen model anahtari: {model_key}")

    allow_download = os.getenv("SENTIMENT_ALLOW_MODEL_DOWNLOAD", "1") == "1"
    if not allow_download:
        raise ValueError("SENTIMENT_ALLOW_MODEL_DOWNLOAD=0 iken yeni model indirilemez.")

    model_id = MODEL_REGISTRY[model_key]
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    pipe = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        truncation=True,
        max_length=512,
        framework="pt",
        device=-1,
    )
    _PIPELINES[model_key] = pipe
    return pipe


def _predict(model_key: str, text: str) -> dict:
    pipe = _get_pipeline(model_key)
    raw = pipe(text[:512])[0]

    raw_label = str(raw.get("label", "neutral"))
    confidence = float(raw.get("score", 0.0))
    label = _normalize_label(raw_label)
    signed_score = _label_to_score(label)

    return {
        "raw_label": raw_label,
        "label": label,
        "confidence": round(confidence, 4),
        "signed_score": signed_score,
    }


def _ensemble_label(score: float) -> str:
    if score >= 0.20:
        return "positive"
    if score <= -0.20:
        return "negative"
    return "neutral"


def compare_two_models(
    source_file: str = "data/yorumlar.json",
    limit: int = 50,
    model_weights: dict[str, float] | None = None,
) -> dict:
    comments = _load_comments(source_file=source_file, limit=limit)
    if not comments:
        raise ValueError("Karsilastirma icin uygun yorum bulunamadi.")

    weights = dict(DEFAULT_MODEL_WEIGHTS)
    if model_weights:
        for key, value in model_weights.items():
            if key in MODEL_REGISTRY:
                weights[key] = float(value)

    model_keys = ["savasy_bert", "cardiff_xlm_roberta"]
    model_counters = {key: Counter() for key in model_keys}
    model_conf_sums = {key: 0.0 for key in model_keys}
    model_weighted_score_sums = {key: 0.0 for key in model_keys}
    model_raw_score_sums = {key: 0.0 for key in model_keys}

    ensemble_counter = Counter()
    ensemble_scores: list[float] = []
    comment_results: list[dict] = []

    for comment in comments:
        item = {
            "index": comment["index"],
            "user": comment["user"],
            "text": comment["text"],
            "clean_text": comment["clean_text"],
            "models": {},
        }

        weighted_numerator = 0.0
        weighted_denominator = 0.0

        for model_key in model_keys:
            pred = _predict(model_key, comment["clean_text"])
            confidence = float(pred["confidence"])
            signed_score = float(pred["signed_score"])
            weight = float(weights.get(model_key, 1.0))

            model_counters[model_key][pred["label"]] += 1
            model_conf_sums[model_key] += confidence
            model_raw_score_sums[model_key] += signed_score
            model_weighted_score_sums[model_key] += signed_score * confidence

            item["models"][model_key] = {
                **pred,
                "weight": weight,
                "weighted_component": round(weight * confidence * signed_score, 6),
            }

            weighted_numerator += weight * confidence * signed_score
            weighted_denominator += weight * confidence

        ensemble_score = weighted_numerator / weighted_denominator if weighted_denominator > 0 else 0.0
        ensemble_label = _ensemble_label(ensemble_score)
        ensemble_scores.append(ensemble_score)
        ensemble_counter[ensemble_label] += 1

        item["ensemble"] = {
            "score": round(ensemble_score, 6),
            "label": ensemble_label,
        }
        comment_results.append(item)

    model_summaries: dict[str, dict] = {}
    total_count = len(comment_results)
    for model_key in model_keys:
        conf_sum = model_conf_sums[model_key]
        model_summaries[model_key] = {
            "model_id": MODEL_REGISTRY[model_key],
            "weight": float(weights.get(model_key, 1.0)),
            "avg_raw_score": round(model_raw_score_sums[model_key] / total_count, 6),
            "avg_confidence_weighted_score": round(
                model_weighted_score_sums[model_key] / conf_sum if conf_sum > 0 else 0.0,
                6,
            ),
            "avg_confidence": round(conf_sum / total_count, 6),
            "label_counts": {
                "positive": int(model_counters[model_key].get("positive", 0)),
                "negative": int(model_counters[model_key].get("negative", 0)),
                "neutral": int(model_counters[model_key].get("neutral", 0)),
            },
        }

    return {
        "source_file": source_file,
        "requested_limit": int(limit),
        "compared_count": total_count,
        "models": model_summaries,
        "ensemble": {
            "avg_score": round(sum(ensemble_scores) / total_count, 6),
            "label_counts": {
                "positive": int(ensemble_counter.get("positive", 0)),
                "negative": int(ensemble_counter.get("negative", 0)),
                "neutral": int(ensemble_counter.get("neutral", 0)),
            },
            "decision_threshold": 0.20,
        },
        "comments": comment_results,
    }
