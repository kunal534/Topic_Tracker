from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, mongodb_uri: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.content_aggregator
        
        # Collections
        self.tasks = self.db.tasks
        self.reddit_posts = self.db.reddit_posts
        self.youtube_videos = self.db.youtube_videos
        self.google_results = self.db.google_results
        self.summaries = self.db.summaries

        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            self.tasks.create_index([("user_id", 1), ("is_active", 1)])
            self.tasks.create_index([("next_run", 1), ("is_active", 1)])
            self.reddit_posts.create_index([("task_id", 1), ("created_at", -1)])
            self.youtube_videos.create_index([("task_id", 1), ("created_at", -1)])
            self.google_results.create_index([("task_id", 1), ("created_at", -1)])
            self.summaries.create_index([("task_id", 1), ("created_at", -1)])
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def create_task(self, user_id: str, topic: str, interval_minutes: int = 30) -> str:
        task = {
            'user_id': user_id,
            'topic': topic,
            'interval_minutes': interval_minutes,
            'created_at': datetime.utcnow(),
            'last_run': None,
            'is_active': True,
            'next_run': datetime.utcnow(),
            'total_runs': 0,
            'sources': ['reddit', 'youtube', 'google']
        }
        result = self.tasks.insert_one(task)
        return str(result.inserted_id)
    
    def get_active_tasks(self) -> List[Dict]:
        return list(self.tasks.find({"is_active": True}))
    
    def get_tasks_to_run(self) -> List[Dict]:
        current_time = datetime.utcnow()
        return list(self.tasks.find({
            'is_active': True,
            'next_run': {'$lte': current_time}
        }))
    
    def update_task_run(self, task_id: str, interval_minutes: int):
        self.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {
                '$set': {
                    'last_run': datetime.utcnow(),
                    'next_run': datetime.utcnow() + timedelta(minutes=interval_minutes)
                },
                '$inc': {'total_runs': 1}
            }
        )
    
    def deactivate_task(self, task_id: str) -> bool:
        result = self.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'is_active': False, 'deactivated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    def save_reddit_posts(self, task_id: str, posts: List[Dict]):
        if not posts:
            return
        
        for post in posts:
            doc = {
                'task_id': task_id,
                'post_id': post.get('id'),
                'title': post.get('title'),
                'content': post.get('content', ''),
                'score': post.get('score', 0),
                'created_utc': post.get('created_utc'),
                'url': post.get('url'),
                'subreddit': post.get('subreddit'),
                'author': post.get('author'),
                'num_comments': post.get('num_comments', 0),
                'created_at': datetime.utcnow(),
                'source': 'reddit'
            }
            self.reddit_posts.update_one(
                {'task_id': task_id, 'post_id': doc['post_id']},
                {'$set': doc},
                upsert=True
            )
    
    def save_youtube_videos(self, task_id: str, videos: List[Dict]):
        if not videos:
            return
        
        for video in videos:
            doc = {
                'task_id': task_id,
                'video_id': video.get('id'),
                'title': video.get('title'),
                'description': video.get('description', ''),
                'duration': video.get('duration'),
                'published_at': video.get('published_at'),
                'channel': video.get('channel'),
                'view_count': video.get('view_count', 0),
                'like_count': video.get('like_count', 0),
                'url': f"https://www.youtube.com/watch?v={video.get('id')}",
                'created_at': datetime.utcnow(),
                'source': 'youtube'
            }
            self.youtube_videos.update_one(
                {'task_id': task_id, 'video_id': doc['video_id']},
                {'$set': doc},
                upsert=True
            )
    
    def save_google_results(self, task_id: str, results: List[Dict]):
        if not results:
            return
        
        for result in results:
            doc = {
                'task_id': task_id,
                'result_id': result.get('link'),
                'title': result.get('title'),
                'snippet': result.get('snippet', ''),
                'link': result.get('link'),
                'display_link': result.get('displayLink', ''),
                'created_at': datetime.utcnow(),
                'source': 'google'
            }
            self.google_results.update_one(
                {'task_id': task_id, 'result_id': doc['result_id']},
                {'$set': doc},
                upsert=True
            )
    
    def get_recent_content(self, task_id: str, hours: int = 24) -> Dict[str, List]:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        reddit_posts = list(self.reddit_posts.find({
            'task_id': task_id,
            'created_at': {'$gte': cutoff_time}
        }).sort('created_at', -1))
        
        youtube_videos = list(self.youtube_videos.find({
            'task_id': task_id,
            'created_at': {'$gte': cutoff_time}
        }).sort('created_at', -1))
        
        google_results = list(self.google_results.find({
            'task_id': task_id,
            'created_at': {'$gte': cutoff_time}
        }).sort('created_at', -1))
        
        return {
            'reddit': reddit_posts,
            'youtube': youtube_videos,
            'google': google_results
        }
    
    def save_summary(self, task_id: str, summary: str, content_counts: Dict[str, int]):
        doc = {
            'task_id': task_id,
            'summary': summary,
            'content_counts': content_counts,
            'total_content': sum(content_counts.values()),
            'created_at': datetime.utcnow()
        }
        return self.summaries.insert_one(doc).inserted_id
    
    def get_summaries(self, task_id: str, limit: int = 10) -> List[Dict]:
        summaries = list(self.summaries.find({
            'task_id': task_id
        }).sort('created_at', -1).limit(limit))
        
        for summary in summaries:
            summary['_id'] = str(summary['_id'])
        
        return summaries
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict]:
        try:
            task = self.tasks.find_one({'_id': ObjectId(task_id)})
            if task:
                task['_id'] = str(task['_id'])
            return task
        except:
            return None
    
    def get_user_tasks(self, user_id: str, active_only: bool = True) -> List[Dict]:
        query = {'user_id': user_id}
        if active_only:
            query['is_active'] = True
        
        tasks = list(self.tasks.find(query).sort('created_at', -1))
        for task in tasks:
            task['_id'] = str(task['_id'])
        
        return tasks
    
    def get_all_tasks(self) -> List[Dict]:
        tasks = list(self.tasks.find({}).sort("created_at", -1))
        for task in tasks:
            task['_id'] = str(task['_id'])
        return tasks
    
    def is_connected(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False
    def delete_task(self, task_id: ObjectId) -> bool:
        result = self.tasks.delete_one({'_id': task_id})
        return result.deleted_count > 0
    
    def is_connected(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False
