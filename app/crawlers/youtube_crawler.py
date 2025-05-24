from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import requests
import re
import os
import requests
from app.db.mongodb import save_video_insight
from app.db.mongodb import db
from datetime import datetime

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

def fetch_transcripts(query):
    url_search = "https://youtube138.p.rapidapi.com/search/"
    headers = {
        "x-rapidapi-host": "youtube138.p.rapidapi.com",
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
    }
    params = {"q": query, "hl": "en", "gl": "US"}
    response = requests.get(url_search, headers=headers, params=params)
    data = response.json()
    video_ids = []

    for item in data.get("contents", []):
        video = item.get("video")
        if video:
            video_ids.append(video.get("videoId"))

    print(f"Extracted video IDs via RapidAPI for '{query}':", video_ids)

    insights = []

    for vid in video_ids[:5]:
        print(f"Processing video ID: {vid}")
        try:
            subtitles_resp = requests.get(
                f"https://youtube-v2.p.rapidapi.com/video/subtitles?video_id={vid}",
                headers={
                    "x-rapidapi-host": "youtube-v2.p.rapidapi.com",
                    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
                }
            )
            subtitles = subtitles_resp.json().get("subtitles", [])

            details_resp = requests.get(
                f"https://youtube-v2.p.rapidapi.com/video/details?video_id={vid}",
                headers={
                    "x-rapidapi-host": "youtube-v2.p.rapidapi.com",
                    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
                }
            )
            details = details_resp.json()

            comments_resp = requests.get(
                f"https://youtube-v2.p.rapidapi.com/video/comments?video_id={vid}",
                headers={
                    "x-rapidapi-host": "youtube-v2.p.rapidapi.com",
                    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
                }
            )
            comments = comments_resp.json().get("comments", [])
            top_comments = [c.get("text", "") for c in comments[:3]]

            insight = {
                "video_id": vid,
                "title": details.get("title", ""),
                "channel": details.get("author", ""),
                "subtitles": subtitles,
                "top_comments": top_comments,
                "summary": None,
                "topic": query
            }

            insights.append(insight)

        except Exception as e:
            print(f"[ERROR] Failed to fetch data for video {vid}: {e}")
            continue

    save_raw_youtube_data(query, insights)
    return insights

def save_raw_youtube_data(topic, insights):
    youtube_collection = db.youtube_videos
    for insight in insights:
        youtube_collection.insert_one({
            "topic": topic,
            "source": "youtube",
            "video_id": insight["video_id"],
            "title": insight["title"],
            "channel": insight["channel"],
            "subtitles": insight["subtitles"],
            "top_comments": insight["top_comments"],
            "summary": None,
            "created_at": datetime.utcnow()
        })