"""Lightweight personalization helpers for novelty scoring and subscription tuning."""

from __future__ import annotations

from typing import Any


def compute_novelty_score(item: dict[str, Any], previous_items: list[dict[str, Any]], topic_query: str) -> float:
    """Score how new and material an item looks compared to prior coverage."""
    title = str(item.get("title", "")).casefold()
    body = str(item.get("body", "")).casefold()
    topic_tokens = set(topic_query.casefold().split())
    text = f"{title} {body}"
    event_terms = {"announced", "released", "approved", "cancelled", "launched", "updated", "hiring", "freeze", "policy"}
    has_event_language = bool(event_terms & set(text.split()))
    quality = float(item.get("quality_score", 0.5) or 0.5)
    overlap = sum(1 for token in topic_tokens if token in text) / max(1, len(topic_tokens))
    prior_overlap = sum(
        1
        for previous in previous_items
        if topic_tokens & set(f"{previous.get('title', '')} {previous.get('body', '')}".casefold().split())
    )

    score = min(1.0, 0.35 + quality * 0.4 + overlap * 0.15 + (0.15 if has_event_language else 0.0))
    if prior_overlap:
        score -= 0.1
    return round(max(0.0, score), 2)


def personalize_threshold(current_threshold: float, feedback: str) -> float:
    """Adjust a subscription threshold based on user feedback."""
    feedback = feedback.casefold()
    if feedback == "useful":
        return round(max(0.1, current_threshold - 0.05), 2)
    if feedback in {"not_useful", "too_frequent"}:
        return round(min(0.95, current_threshold + 0.05), 2)
    return current_threshold
