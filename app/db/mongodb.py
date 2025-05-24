import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGODB_URI)
db = client.topic_tracker_db
video_insights_collection = db.video_insights

def save_video_insight(insight):
    """
    insight: dict containing video info & summary
    """
    video_insights_collection.insert_one(insight)

def save_reddit_data(topic, posts):
    reddit_collection = db.reddit_posts
    reddit_collection.insert_one({
        "topic": topic,
        "source": "reddit",
        "data": posts,
        "summary": None,
        "created_at": datetime.utcnow()
    })