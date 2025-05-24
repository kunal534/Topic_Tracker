import praw
import os
from dotenv import load_dotenv
from app.db.mongodb import save_reddit_data

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="insight-tracker-bot"
)

def fetch_reddit_posts(topic: str, limit=5):
    posts = []
    for submission in reddit.subreddit("all").search(topic, sort='new', limit=limit):
        posts.append({
            "title": submission.title,
            "url": submission.url,
            "created_utc": submission.created_utc,
            "subreddit": submission.subreddit.display_name
        })
    save_reddit_data(topic, posts)
    return posts