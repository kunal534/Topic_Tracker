import requests
from typing import List, Dict
import logging
from config import Config

logger = logging.getLogger(__name__)

class GoogleCrawler:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.RAPIDAPI_KEY_GOOGLE
        self.api_host = "google-search74.p.rapidapi.com"
        self.base_url = f"https://{self.api_host}/"

    def search(self, topic: str, num_results: int = 10) -> List[Dict]:
        """Fetch Google info using RapidAPI Search 74 endpoint"""
        try:
            url = f"https://{self.api_host}?query={topic}&limit={num_results}&related_keywords=false"
            headers = {
                "x-rapidapi-host": self.api_host,
                "x-rapidapi-key": self.api_key
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []

            # If "results" field exists → traditional list of results
            if "results" in data:
                for item in data["results"]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("description", ""),
                        "link": item.get("url", ""),
                        "displayLink": item.get("source", ""),
                        "formattedUrl": item.get("url", ""),
                        "source": "google"
                    })

            # If structured data like "search_term", "text", etc.
            elif "search_term" in data and "text" in data:
                results.append({
                    "title": data.get("name", data["search_term"]),
                    "snippet": data.get("text", ""),
                    "link": data.get("url", ""),
                    "displayLink": data.get("site", ""),
                    "formattedUrl": data.get("url", ""),
                    "source": "google"
                })

            logger.info(f"Fetched {len(results)} Google search result(s) for topic: {topic}")
            return results

        except Exception as e:
            logger.error(f"Error fetching Google search results: {e}")
            return []