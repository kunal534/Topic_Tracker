"""Idempotent Celery tasks for collecting and processing topic changes."""

from datetime import datetime, timezone
from typing import Any

from celery import Celery
from bson import ObjectId

from app.config import settings
from app.crawlers.reddit_crawler import fetch_reddit_posts
from app.crawlers.youtube_crawler import fetch_transcripts
from app.db.mongodb import db, save_source_item, utcnow
from app.service_notice import SERVICE_NOTICE
from app.services.normalization import canonicalize_url, content_fingerprint
from app.services.updates import create_topic_update


def _fallback_source_items(topic: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    name = topic.get("canonical_name", "topic")
    return [("fallback", {
        "external_id": f"fallback-{topic['_id']}-{utcnow().strftime('%Y%m%d%H%M%S')}",
        "title": f"Live update for {name}",
        "url": "",
        "created_utc": utcnow().timestamp(),
        "subreddit": "local",
        "channel": "local",
        "subtitles": f"A local fallback update was generated for {name} because external providers are unavailable.",
    })]

celery = Celery("topic_tracker", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.task_routes = {
    "app.tasks.monitor_topic": {"queue": "collection"},
}
celery.conf.beat_schedule = {
    "dispatch-due-topics": {
        "task": "app.tasks.dispatch_due_topics",
        "schedule": settings.topic_check_interval_minutes * 60,
    },
}


def _source_item(topic_id: ObjectId, source: str, raw: dict[str, Any]) -> dict[str, Any]:
    body = " ".join(raw.get("top_comments", []))
    if raw.get("subtitles"):
        body = f"{body} {str(raw['subtitles'])[:5000]}"
    published_at = raw.get("created_utc")
    if published_at:
        published_at = datetime.fromtimestamp(published_at, tz=timezone.utc)
    return {
        "topic_id": topic_id,
        "source": source,
        "external_id": raw["external_id"],
        "canonical_url": canonicalize_url(raw["url"]),
        "title": raw.get("title", ""),
        "body": body,
        "author": raw.get("channel") or raw.get("subreddit"),
        "published_at": published_at,
        "content_hash": content_fingerprint(raw.get("title", ""), body),
        "quality_score": 0.7,
        "relevance_score": 0.7,
        "processing_status": "complete",
    }


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def monitor_topic(self: Any, job_id: str) -> dict[str, int]:
    """Collect one topic, suppress repeats, and publish an update for new content."""
    job = db.monitoring_jobs.find_one_and_update(
        {"_id": ObjectId(job_id), "status": "queued"},
        {"$set": {"status": "running", "started_at": utcnow()}},
        return_document=True,
    )
    if job is None:
        return {"fetched": 0, "new": 0, "updates": 0}
    try:
        topic = db.topics.find_one({"_id": job["topic_id"]})
        if topic is None:
            raise ValueError("Monitoring job has no topic")
        raw_items: list[tuple[str, dict[str, Any]]] = []
        try:
            raw_items.extend(("reddit", item) for item in fetch_reddit_posts(topic["canonical_name"]))
        except Exception as exc:
            db.monitoring_jobs.update_one(
                {"_id": job["_id"]},
                {"$push": {"errors": {"source": "reddit", "message": str(exc)}}},
            )
        try:
            raw_items.extend(("youtube", item) for item in fetch_transcripts(topic["canonical_name"]))
        except Exception as exc:
            db.monitoring_jobs.update_one(
                {"_id": job["_id"]},
                {"$push": {"errors": {"source": "youtube", "message": str(exc)}}},
            )

        if not raw_items:
            raw_items = _fallback_source_items(topic)
            db.monitoring_jobs.update_one(
                {"_id": job["_id"]},
                {"$push": {"errors": {"source": "providers", "message": SERVICE_NOTICE}}},
            )
        new_items = []
        for source, raw in raw_items:
            item, inserted = save_source_item(_source_item(topic["_id"], source, raw))
            if inserted:
                new_items.append(item)
        update = create_topic_update(topic["_id"], new_items)
        counters = {"fetched": len(raw_items), "new": len(new_items), "updates": int(update is not None)}
        db.monitoring_jobs.update_one(
            {"_id": job["_id"]},
            {"$set": {"status": "completed", "completed_at": utcnow(), "result_counters": counters}},
        )
        return counters
    except Exception as exc:
        next_attempt = self.request.retries + 1
        status = "failed" if next_attempt > self.max_retries else "queued"
        db.monitoring_jobs.update_one(
            {"_id": job["_id"]},
            {"$set": {
                "status": status,
                "completed_at": utcnow() if status == "failed" else None,
                "error": str(exc),
            }},
        )
        raise


@celery.task
def dispatch_due_topics() -> int:
    """Queue active topics; beat scheduling controls how often this runs."""
    from app.db.mongodb import create_monitoring_job

    queued = 0
    bucket = utcnow().strftime("%Y%m%d%H")
    for topic in db.topics.find({"monitoring_status": "active"}):
        job, created = create_monitoring_job(topic["_id"], f"scheduled:{topic['_id']}:{bucket}", "scheduled")
        if created:
            monitor_topic.delay(str(job["_id"]))
            queued += 1
    return queued
