"""Text cleaning helpers for reply preprocessing."""
from __future__ import annotations

import re


def clean_reply_text(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"https?://\\S+", " ", value)
    value = re.sub(r"@\\w+", " ", value)
    value = re.sub(r"\\s+", " ", value).strip()
    return value


def prepare_replies(replies: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for reply in replies:
        original_text = str(reply.get("text") or "").strip()
        cleaned_text = clean_reply_text(original_text)
        if len(cleaned_text) < 2:
            continue

        item = dict(reply)
        item["clean_text"] = cleaned_text
        prepared.append(item)

    return prepared
