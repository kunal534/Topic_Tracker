"""Persist in-app notifications with idempotent per-user/update delivery."""

from typing import Any

from pymongo.errors import DuplicateKeyError

from app.db.mongodb import db, utcnow


def create_in_app_notifications(topic_id: Any, topic_update_id: Any) -> int:
    created = 0
    for subscription in db.subscriptions.find({"topic_id": topic_id, "active": True}):
        document = {
            "user_id": subscription["user_id"],
            "subscription_id": subscription["_id"],
            "topic_update_id": topic_update_id,
            "channel": "in_app",
            "read_at": None,
            "created_at": utcnow(),
        }
        try:
            db.notification_deliveries.insert_one(document)
            db.notifications.insert_one(document)
            created += 1
        except DuplicateKeyError:
            continue
    return created
