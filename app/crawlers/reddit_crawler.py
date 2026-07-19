"""Reddit source provider."""

from typing import Any

import praw

from app.config import settings


def fetch_reddit_posts(topic: str, limit: int = 5) -> list[dict[str, Any]]:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        raise RuntimeError("Reddit credentials are not configured")
    reddit = praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent="topic-tracker/1.0",
    )
    posts = []
    for submission in reddit.subreddit("all").search(topic, sort="new", limit=limit):
        posts.append({
            "external_id": submission.id,
            "title": submission.title,
            "url": submission.url,
            "created_utc": submission.created_utc,
            "subreddit": submission.subreddit.display_name,
        })
    return posts
