"""YouTube source provider backed by RapidAPI."""

from typing import Any

import requests

from app.config import settings

REQUEST_TIMEOUT_SECONDS = 15


def _headers(host: str) -> dict[str, str]:
    if not settings.rapidapi_key:
        raise RuntimeError("RAPIDAPI_KEY is not configured")
    return {"x-rapidapi-host": host, "x-rapidapi-key": settings.rapidapi_key}


def _get(url: str, host: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.get(url, headers=_headers(host), timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
    response.raise_for_status()
    return response.json()


def fetch_transcripts(query: str, limit: int = 5) -> list[dict[str, Any]]:
    search = _get(
        "https://youtube138.p.rapidapi.com/search/",
        "youtube138.p.rapidapi.com",
        params={"q": query, "hl": "en", "gl": "US"},
    )
    video_ids = [item["video"]["videoId"] for item in search.get("contents", []) if item.get("video", {}).get("videoId")]
    insights = []
    for video_id in video_ids[:limit]:
        details = _get(
            "https://youtube-v2.p.rapidapi.com/video/details",
            "youtube-v2.p.rapidapi.com",
            params={"video_id": video_id},
        )
        subtitles = _get(
            "https://youtube-v2.p.rapidapi.com/video/subtitles",
            "youtube-v2.p.rapidapi.com",
            params={"video_id": video_id},
        ).get("subtitles", [])
        comments = _get(
            "https://youtube-v2.p.rapidapi.com/video/comments",
            "youtube-v2.p.rapidapi.com",
            params={"video_id": video_id},
        ).get("comments", [])
        insights.append({
            "external_id": video_id,
            "title": details.get("title", ""),
            "channel": details.get("author", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "subtitles": subtitles,
            "top_comments": [comment.get("text", "") for comment in comments[:3]],
        })
    return insights
