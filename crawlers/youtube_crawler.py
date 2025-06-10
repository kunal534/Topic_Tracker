import requests
from typing import List, Dict
import logging
from config import Config

logger = logging.getLogger(__name__)

class YouTubeCrawler:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.RAPIDAPI_KEY_YOUTUBE
        self.api_host = "youtube-video-summarizer-gpt-ai.p.rapidapi.com"
        self.base_url = f"https://{self.api_host}"

    def fetch_summarized_video(self, video_id: str) -> Dict:
        """Fetch summary info for a single video using RapidAPI"""
        try:
            url = f"{self.base_url}/api/video/info/get?videoId={video_id}&type=youtube&regenerate=false"
            headers = {
                "x-rapidapi-host": self.api_host,
                "x-rapidapi-key": self.api_key
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                'id': video_id,
                'title': data.get('title', ''),
                'summary': data.get('summary', ''),
                'channel': data.get('channelName', ''),
                'published_at': data.get('publishDate', ''),
                'thumbnail_url': data.get('thumbnail', ''),
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'view_count': data.get('viewCount', 0),
                'like_count': data.get('likeCount', 0),
                'comment_count': data.get('commentCount', 0),
                'duration': data.get('duration', 0),
                'source': 'youtube'
            }

        except Exception as e:
            logger.error(f"Failed to fetch summary for video {video_id}: {e}")
            return {}

    def fetch_videos(self, topic: str, max_results: int = 10) -> List[Dict]:
        """
        Fetch summarized videos for a topic.
        In this version, it uses a static list of video IDs as RapidAPI has no search support.
        """
        logger.warning("RapidAPI YouTube endpoint does not support search; using hardcoded IDs for demo")

        # You can replace this with a proper search function or a YouTube scraper
        sample_video_ids = [
            "1LKLZATTT6I",  # Replace with relevant videoIds
            "xvFZjo5PgG0"
        ]

        results = []
        for vid in sample_video_ids[:max_results]:
            summary = self.fetch_summarized_video(vid)
            if summary:
                results.append(summary)

        logger.info(f"Fetched {len(results)} summarized YouTube videos for topic: {topic}")
        return results

    def get_trending_videos(self, topic: str, max_results: int = 10) -> List[Dict]:
        return self.fetch_videos(topic, max_results)

    def get_recent_videos(self, topic: str, max_results: int = 10) -> List[Dict]:
        return self.fetch_videos(topic, max_results)