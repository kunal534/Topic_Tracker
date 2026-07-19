"""Create explainable topic updates from newly ingested source items."""

from datetime import datetime
from typing import Any

from app.db.mongodb import db, utcnow
from app.service_notice import SERVICE_NOTICE
from app.services.notifications import create_in_app_notifications
from app.services.personalization import compute_novelty_score


def create_topic_update(topic_id: Any, source_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Create one conservative update for a batch of genuinely new items.

    This is intentionally rule-based for the MVP. Semantic novelty can replace
    the selection and summary portions once evaluation data exists.
    """
    eligible = [item for item in source_items if item.get("relevance_score", 0) >= 0.6]
    if not eligible:
        return None

    previous_items = list(db.source_items.find({"topic_id": topic_id}).sort("fetched_at", -1).limit(10))
    scored = [
        (item, compute_novelty_score(item, previous_items, str(topic_id)))
        for item in eligible
    ]
    scored = sorted(scored, key=lambda entry: entry[1], reverse=True)
    selected = [item for item, _ in scored[:3]]
    titles = [item.get("title", "Untitled source") for item in selected]
    summary = "New relevant coverage was found: " + "; ".join(titles) + "."
    event_time = min(
        (item.get("published_at") for item in selected if item.get("published_at")),
        default=utcnow(),
    )
    update = {
        "topic_id": topic_id,
        "type": "source_coverage",
        "title": titles[0],
        "summary": summary,
        "source_item_ids": [item["_id"] for item in selected],
        "novelty_score": round(max(score for _, score in scored[:3]) if scored else 0.0, 2),
        "confidence": "medium",
        "event_time": event_time,
        "detected_at": utcnow(),
        "model_metadata": None,
        "status": "published",
    }
    update["service_notice"] = SERVICE_NOTICE
    result = db.topic_updates.insert_one(update)
    update["_id"] = result.inserted_id
    create_in_app_notifications(topic_id, update["_id"])
    db.topics.update_one(
        {"_id": topic_id},
        {"$set": {"baseline_summary": summary, "baseline_updated_at": utcnow(), "updated_at": utcnow()}},
    )
    return update


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
