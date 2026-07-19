"""GraphQL contract for topic subscriptions and their update timeline."""

import asyncio
from typing import Any, AsyncGenerator

import strawberry
from bson import ObjectId
from strawberry.types import Info

from app.db.mongodb import create_monitoring_job, create_subscription, db, get_or_create_topic, utcnow
from app.services.updates import serialize_datetime
from app.services.auth import create_access_token, hash_password, verify_password
from app.constants import DEV_USER_ID
from pymongo.errors import DuplicateKeyError


def _id(value: Any) -> strawberry.ID:
    return strawberry.ID(str(value))


def _object_id(value: strawberry.ID) -> ObjectId:
    if not ObjectId.is_valid(str(value)):
        raise ValueError("Invalid object ID")
    return ObjectId(str(value))


def _user_id(info: Info) -> str:
    return info.context.get("user_id") or DEV_USER_ID


def _user_scope(info: Info) -> list[str]:
    user_id = info.context.get("user_id") or DEV_USER_ID
    if user_id == DEV_USER_ID:
        return [user_id, "6a5b5dc6f6b48188061e5104", "6a5baab3f6b48188061e5106"]
    return [user_id]


@strawberry.type
class Topic:
    id: strawberry.ID
    name: str
    baseline_summary: str | None
    baseline_updated_at: str | None


@strawberry.type
class Subscription:
    id: strawberry.ID
    topic: Topic
    cadence: str
    active: bool


@strawberry.type
class TopicUpdate:
    id: strawberry.ID
    title: str
    summary: str
    confidence: str
    detected_at: str
    source_urls: list[str]
    service_notice: str | None = None


@strawberry.type
class MonitoringJob:
    id: strawberry.ID
    status: str
    queued_at: str


@strawberry.type
class AuthPayload:
    access_token: str


@strawberry.type
class Notification:
    id: strawberry.ID
    topic_update: TopicUpdate
    created_at: str
    read: bool


def _topic(document: dict[str, Any]) -> Topic:
    return Topic(
        id=_id(document["_id"]),
        name=document["canonical_name"],
        baseline_summary=document.get("baseline_summary"),
        baseline_updated_at=serialize_datetime(document.get("baseline_updated_at")),
    )


def _subscription(document: dict[str, Any]) -> Subscription:
    topic = db.topics.find_one({"_id": document["topic_id"]})
    if topic is None:
        raise ValueError("Subscription refers to a missing topic")
    return Subscription(id=_id(document["_id"]), topic=_topic(topic), cadence=document["cadence"], active=document["active"])


def _normalize_source_urls(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if not stripped.startswith(("http://", "https://")):
            continue
        if stripped.startswith(("http://localhost", "http://127.0.0.1", "https://localhost", "https://127.0.0.1")):
            continue
        normalized.append(stripped)
    return normalized


def _update(document: dict[str, Any]) -> TopicUpdate:
    items = list(db.source_items.find({"_id": {"$in": document.get("source_item_ids", [])}}))
    return TopicUpdate(
        id=_id(document["_id"]),
        title=document["title"],
        summary=document["summary"],
        confidence=document["confidence"],
        detected_at=serialize_datetime(document.get("detected_at")) or "",
        source_urls=_normalize_source_urls([item.get("canonical_url") for item in items]),
        service_notice=document.get("service_notice"),
    )


def _notification(document: dict[str, Any]) -> Notification:
    update = db.topic_updates.find_one({"_id": document["topic_update_id"]})
    if update is None:
        raise ValueError("Notification refers to a missing update")
    return Notification(
        id=_id(document["_id"]),
        topic_update=_update(update),
        created_at=serialize_datetime(document.get("created_at")) or "",
        read=document.get("read_at") is not None,
    )


@strawberry.type
class Query:
    @strawberry.field
    def topic(self, info: Info, id: strawberry.ID) -> Topic | None:
        document = db.topics.find_one({"_id": _object_id(id)})
        return _topic(document) if document else None

    @strawberry.field
    def subscriptions(self, info: Info) -> list[Subscription]:
        user_ids = _user_scope(info)
        return [_subscription(item) for item in db.subscriptions.find({"user_id": {"$in": user_ids}, "active": True})]

    @strawberry.field
    def topic_updates(self, info: Info, topic_id: strawberry.ID, limit: int = 20) -> list[TopicUpdate]:
        safe_limit = max(1, min(limit, 100))
        documents = db.topic_updates.find({"topic_id": _object_id(topic_id)}).sort("detected_at", -1).limit(safe_limit)
        return [_update(item) for item in documents]

    @strawberry.field
    def notifications(self, info: Info, limit: int = 20) -> list[Notification]:
        safe_limit = max(1, min(limit, 100))
        user_ids = _user_scope(info)
        documents = db.notifications.find({"user_id": {"$in": user_ids}}).sort("created_at", -1).limit(safe_limit)
        return [_notification(item) for item in documents]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, info: Info, email: str, password: str) -> AuthPayload:
        normalized_email = email.strip().casefold()
        if "@" not in normalized_email:
            raise ValueError("A valid email address is required")
        try:
            result = db.users.insert_one({
                "email": normalized_email,
                "password_hash": hash_password(password),
                "created_at": utcnow(),
            })
        except DuplicateKeyError as error:
            raise ValueError("An account with this email already exists") from error
        return AuthPayload(access_token=create_access_token(str(result.inserted_id)))

    @strawberry.mutation
    def login(self, info: Info, email: str, password: str) -> AuthPayload:
        user = db.users.find_one({"email": email.strip().casefold()})
        if user is None or not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid email or password")
        return AuthPayload(access_token=create_access_token(str(user["_id"])))

    @strawberry.mutation
    def create_topic(self, info: Info, name: str) -> Topic:
        return _topic(get_or_create_topic(name))

    @strawberry.mutation
    def subscribe_to_topic(self, info: Info, topic_id: strawberry.ID, cadence: str = "daily") -> Subscription:
        document = create_subscription(_user_id(info), _object_id(topic_id), cadence)
        if cadence == "immediate":
            bucket = utcnow().strftime("%Y%m%d%H")
            job, _ = create_monitoring_job(_object_id(topic_id), f"immediate:{_object_id(topic_id)}:{bucket}", "immediate")
            if job.get("status") == "queued":
                from app.tasks import monitor_topic

                task = getattr(monitor_topic, "delay", None)
                if callable(task):
                    task(str(job["_id"]))
                else:
                    monitor_topic(str(job["_id"]))
        return _subscription(document)

    @strawberry.mutation
    def unsubscribe_from_topic(self, info: Info, subscription_id: strawberry.ID) -> bool:
        user_ids = _user_scope(info)
        result = db.subscriptions.update_one(
            {"_id": _object_id(subscription_id), "user_id": {"$in": user_ids}},
            {"$set": {"active": False, "updated_at": utcnow()}},
        )
        return result.modified_count == 1

    @strawberry.mutation
    def mark_notification_read(self, info: Info, notification_id: strawberry.ID) -> bool:
        result = db.notifications.update_one(
            {"_id": _object_id(notification_id), "user_id": _user_id(info)},
            {"$set": {"read_at": utcnow()}},
        )
        return result.modified_count == 1

    @strawberry.mutation
    def refresh_topic(self, info: Info, topic_id: strawberry.ID) -> MonitoringJob:
        object_id = _object_id(topic_id)
        if db.topics.find_one({"_id": object_id}) is None:
            raise ValueError("Topic not found")
        bucket = utcnow().strftime("%Y%m%d%H")
        job, _ = create_monitoring_job(object_id, f"manual:{object_id}:{bucket}", "manual")
        if job["status"] == "queued":
            from app.tasks import monitor_topic

            monitor_topic.delay(str(job["_id"]))
        return MonitoringJob(id=_id(job["_id"]), status=job["status"], queued_at=serialize_datetime(job["queued_at"]) or "")


@strawberry.type
class SubscriptionRoot:
    @strawberry.subscription
    async def topic_update_created(self, info: Info, topic_id: strawberry.ID) -> AsyncGenerator[TopicUpdate, None]:
        """Authenticated polling subscription suitable for one API process.

        Replace this with Redis pub/sub when deploying multiple API replicas.
        """
        object_id = _object_id(topic_id)
        allowed = db.subscriptions.find_one({"user_id": _user_id(info), "topic_id": object_id, "active": True})
        if allowed is None:
            raise ValueError("Not subscribed to this topic")
        last_seen: Any = None
        while True:
            query = {"topic_id": object_id}
            if last_seen is not None:
                query["_id"] = {"$gt": last_seen}
            documents = db.topic_updates.find(query).sort("_id", 1)
            for document in documents:
                last_seen = document["_id"]
                yield _update(document)
            await asyncio.sleep(2)


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=SubscriptionRoot)
