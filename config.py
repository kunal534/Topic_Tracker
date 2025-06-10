import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/content_aggregator")
    
    # Reddit (still using official API)
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "content_aggregator_bot/1.0")
    
    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # RapidAPI Keys
    RAPIDAPI_KEY_GPT = os.getenv("RAPIDAPI_KEY_GPT")
    RAPIDAPI_KEY_YOUTUBE = os.getenv("RAPIDAPI_KEY_YOUTUBE")
    RAPIDAPI_KEY_GOOGLE = os.getenv("RAPIDAPI_KEY_GOOGLE")
    
    # Token limits for summarization
    MAX_TOKENS_PER_REQUEST = 4000
    MAX_CHUNK_TOKENS = 400
    SUMMARY_MAX_TOKENS = 200