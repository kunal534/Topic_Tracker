"""ASGI entry point for Topic Tracker."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db.mongodb import db, ensure_indexes
from app.graphql_schema import schema
from app.config import settings
from app.constants import DEV_USER_ID
from app.services.auth import decode_access_token


async def get_context(request: Any) -> dict[str, str]:
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        user_id = decode_access_token(authorization.removeprefix("Bearer "))
        if user_id:
            return {"user_id": user_id}
    if settings.app_env == "development":
        return {"user_id": request.headers.get("x-user-id", DEV_USER_ID)}
    raise HTTPException(status_code=401, detail="Authentication required")


app = FastAPI(title="Topic Tracker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*list(settings.allowed_origins), "http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-User-ID", "x-user-id"],
)


@app.post("/graphql")
async def graphql_endpoint(request: Request) -> JSONResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="GraphQL payload must be a JSON object")

    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(status_code=400, detail="GraphQL query is required")

    variables = payload.get("variables") or {}
    operation_name = payload.get("operationName")

    result = await schema.execute(
        query,
        variable_values=variables,
        operation_name=operation_name,
        context_value={**await get_context(request), "request": request},
    )

    if result.errors:
        return JSONResponse({"errors": [error.as_dict() for error in result.errors]}, status_code=400)
    return JSONResponse({"data": result.data})


@app.on_event("startup")
def initialize_database() -> None:
    ensure_indexes()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/debug/data")
def debug_data(request: Request) -> dict[str, Any]:
    authorization = request.headers.get("authorization", "")
    user_id = None
    if authorization.startswith("Bearer "):
        user_id = decode_access_token(authorization.removeprefix("Bearer "))
    if not user_id:
        user_id = request.headers.get("x-user-id") or (DEV_USER_ID if settings.app_env == "development" else None)
    if not user_id:
        return {"topics": [], "subscriptions": [], "updates": [], "notifications": []}

    user_ids = [user_id]
    if user_id == DEV_USER_ID:
        user_ids.extend(["6a5b5dc6f6b48188061e5104", "6a5baab3f6b48188061e5106"])

    topics = list(db.topics.find({"monitoring_status": "active"}, {"canonical_name": 1, "baseline_summary": 1, "updated_at": 1}))
    subscriptions = list(db.subscriptions.find({"user_id": {"$in": user_ids}}, {"topic_id": 1, "cadence": 1, "active": 1}))
    updates = list(db.topic_updates.find({}, {"title": 1, "summary": 1, "detected_at": 1, "topic_id": 1}).sort("detected_at", -1).limit(10))
    notifications = list(db.notifications.find({"user_id": {"$in": user_ids}}, {"topic_update_id": 1, "created_at": 1, "read_at": 1}).sort("created_at", -1).limit(10))
    return {
        "topics": [{"id": str(item["_id"]), "name": item.get("canonical_name"), "baseline_summary": item.get("baseline_summary"), "updated_at": item.get("updated_at")} for item in topics],
        "subscriptions": [{"id": str(item["_id"]), "topic_id": str(item.get("topic_id")), "cadence": item.get("cadence"), "active": item.get("active")} for item in subscriptions],
        "updates": [{"id": str(item["_id"]), "topic_id": str(item.get("topic_id")), "title": item.get("title"), "summary": item.get("summary"), "detected_at": item.get("detected_at")} for item in updates],
        "notifications": [{"id": str(item["_id"]), "topic_update_id": str(item.get("topic_update_id")), "created_at": item.get("created_at"), "read": item.get("read_at") is not None} for item in notifications],
    }
