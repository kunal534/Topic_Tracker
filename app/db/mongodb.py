"""MongoDB access and persistence primitives for the topic-monitoring domain."""

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.services.normalization import normalize_topic

client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5_000)
db: Database = client.topic_tracker_db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_indexes() -> None:
    db.users.create_index("email", unique=True)
    db.topics.create_index("normalized_query", unique=True)
    db.subscriptions.create_index([("user_id", ASCENDING), ("topic_id", ASCENDING)], unique=True)
    db.source_items.create_index([("source", ASCENDING), ("external_id", ASCENDING)], unique=True)
    db.source_items.create_index("canonical_url", unique=True, sparse=True)
    db.source_items.create_index("content_hash", unique=True, sparse=True)
    db.topic_updates.create_index([("topic_id", ASCENDING), ("detected_at", DESCENDING)])
    db.notification_deliveries.create_index(
        [("subscription_id", ASCENDING), ("topic_update_id", ASCENDING), ("channel", ASCENDING)],
        unique=True,
    )
    db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.topic_source_state.create_index([("topic_id", ASCENDING), ("source", ASCENDING)], unique=True)
    db.monitoring_jobs.create_index("idempotency_key", unique=True)


def get_or_create_topic(name: str) -> dict[str, Any]:
    normalized = normalize_topic(name)
    now = utcnow()
    document = {
        "canonical_name": " ".join(name.strip().split()),
        "normalized_query": normalized,
        "aliases": [],
        "monitoring_status": "active",
        "baseline_summary": None,
        "baseline_updated_at": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = db.topics.insert_one(document)
        document["_id"] = result.inserted_id
        return document
    except DuplicateKeyError:
        existing = db.topics.find_one({"normalized_query": normalized})
        if existing is None:
            raise RuntimeError("Topic creation conflicted but no topic was found")
        return existing


def create_subscription(user_id: str, topic_id: Any, cadence: str = "daily") -> dict[str, Any]:
    if cadence not in {"immediate", "daily", "weekly"}:
        raise ValueError("Cadence must be immediate, daily, or weekly")
    now = utcnow()
    document = {
        "user_id": user_id,
        "topic_id": topic_id,
        "cadence": cadence,
        "channels": ["in_app"],
        "included_keywords": [],
        "excluded_keywords": [],
        "relevance_threshold": 0.6,
        "active": True,
        "last_seen_update_at": None,
        "created_at": now,
        "updated_at": now,
    }
    db.subscriptions.update_one(
        {"user_id": user_id, "topic_id": topic_id},
        {"$setOnInsert": document},
        upsert=True,
    )
    return db.subscriptions.find_one({"user_id": user_id, "topic_id": topic_id})


def save_source_item(item: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Insert an item once; returns the stored document and whether it was new."""
    item = {**item, "fetched_at": item.get("fetched_at", utcnow())}
    try:
        result = db.source_items.insert_one(item)
        item["_id"] = result.inserted_id
        return item, True
    except DuplicateKeyError:
        query = {"source": item["source"], "external_id": item["external_id"]}
        existing = db.source_items.find_one(query)
        if existing is None:
            existing = db.source_items.find_one({"content_hash": item.get("content_hash")})
        if existing is None:
            raise
        return existing, False


def create_monitoring_job(topic_id: Any, idempotency_key: str, trigger: str) -> tuple[dict[str, Any], bool]:
    now = utcnow()
    job = {
        "topic_id": topic_id,
        "idempotency_key": idempotency_key,
        "trigger": trigger,
        "status": "queued",
        "queued_at": now,
        "started_at": None,
        "completed_at": None,
        "error": None,
        "result_counters": {"fetched": 0, "new": 0, "updates": 0},
    }
    try:
        result = db.monitoring_jobs.insert_one(job)
        job["_id"] = result.inserted_id
        return job, True
    except DuplicateKeyError:
        existing = db.monitoring_jobs.find_one({"idempotency_key": idempotency_key})
        if existing is None:
            raise
        return existing, False


# Compatibility wrappers for the existing crawler while it is migrated.
def save_reddit_data(topic: str, posts: list[dict[str, Any]]) -> None:
    db.reddit_posts.insert_one({
        "topic": topic,
        "source": "reddit",
        "data": posts,
        "summary": None,
        "created_at": utcnow(),
    })


def save_video_insight(insight: dict[str, Any]) -> None:
    db.video_insights.insert_one({**insight, "created_at": utcnow()})
