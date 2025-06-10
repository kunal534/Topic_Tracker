import praw
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RedditCrawler:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            # Test the connection
            self.reddit.user.me()
            logger.info("Reddit crawler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit crawler: {e}")
            self.reddit = None
    
    def fetch_posts(self, topic: str, limit: int = 50, time_filter: str = "day") -> List[Dict]:
        """Fetch Reddit posts for a given topic"""
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return []
        
        posts = []
        try:
            # Search across all subreddits
            subreddit = self.reddit.subreddit("all")
            
            # Get posts from search
            for submission in subreddit.search(topic, limit=limit, sort="hot"):
                try:
                    post_data = {
                        'id': submission.id,
                        'title': submission.title,
                        'content': submission.selftext if submission.selftext else "",
                        'score': submission.score,
                        'upvote_ratio': submission.upvote_ratio,
                        'num_comments': submission.num_comments,
                        'created_utc': submission.created_utc,
                        'url': submission.url,
                        'subreddit': str(submission.subreddit),
                        'author': str(submission.author) if submission.author else "[deleted]",
                        'permalink': f"https://reddit.com{submission.permalink}",
                        'is_self': submission.is_self,
                        'domain': submission.domain
                    }
                    posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error processing hot Reddit post {submission.id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(posts)} hot Reddit posts for topic: {topic}")
            
        except Exception as e:
            logger.error(f"Error fetching hot Reddit posts: {e}")
        
        return posts