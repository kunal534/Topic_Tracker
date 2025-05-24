from celery import Celery
from app.crawlers.reddit_crawler import fetch_reddit_posts
from app.crawlers.youtube_crawler import fetch_transcripts
from datetime import datetime
from app.db.mongodb import db
from openai import OpenAI
import os

celery = Celery("tasks", broker="redis://localhost:6379/0")

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def summarize_text_in_chunks(text, chunk_size=1000, overlap=200):
    summaries = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        
        prompt = f"Summarize the following content in 4-6 sentences:\n\n{chunk}"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You're a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=100
            )
            summary = response.choices[0].message.content if response.choices else ""
            summaries.append(summary or "")
        except Exception as e:
            print(f"Failed to summarize chunk: {e}")
            summaries.append("")
        
        start += chunk_size - overlap
    
    return " ".join(summaries)

def summarize_raw_data(source, topic):
    collection_name = "reddit_posts" if source == "reddit" else "youtube_videos"
    collection = db[collection_name]
    docs = collection.find({"topic": topic, "summary": None})

    for doc in docs:
        if source == "reddit":
            text = " ".join([post["title"] for post in doc.get("data", [])])
            prompt = f"Summarize the following content in 4-6 sentences:\n\n{text}"
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=100
                )
                summary = response.choices[0].message.content if response.choices else None
                if summary:
                    collection.update_one({"_id": doc["_id"]}, {
                        "$set": {
                            "summary": summary,
                            "summarized_at": datetime.utcnow()
                        }
                    })
                    print(f"[OK] Saved summary for doc {doc['_id']}")
                else:
                    print(f"[WARN] Empty summary for doc {doc['_id']}")
            except Exception as e:
                print(f"Failed to summarize doc {doc['_id']}: {e}")
        elif source == "youtube":
            import requests
            video_id = doc.get("video_id", "")
            payload = {
                "video_id": video_id,
                "media_type": "youtube",
                "language_code": "en",
                "summary_type": "default"
            }
            headers = {
                "Content-Type": "application/json",
                "x-rapidapi-host": "youtube-video-summarizer-gpt-ai.p.rapidapi.com",
                "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
            }
            try:
                res = requests.post(
                    "https://youtube-video-summarizer-gpt-ai.p.rapidapi.com/api/summary/generate-free",
                    json=payload,
                    headers=headers
                )
                summary = res.json().get("summary")
                if summary:
                    collection.update_one({"_id": doc["_id"]}, {
                        "$set": {
                            "summary": summary,
                            "summarized_at": datetime.utcnow()
                        }
                    })
                    print(f"[OK] Saved summary for doc {doc['_id']}")
                else:
                    print(f"[WARN] Empty summary for doc {doc['_id']}")
            except Exception as e:
                print(f"Failed to summarize doc {doc['_id']}: {e}")

@celery.task
def fetch_topic_data(topic: str):
    reddit_data = fetch_reddit_posts(topic)
    yt_data = fetch_transcripts(topic)
    timestamp = datetime.utcnow().isoformat()
    print(f"\n[{timestamp}] Fetched data for topic: {topic}")
    print("Reddit:", reddit_data)
    print("YouTube:", yt_data)

@celery.task
def summarize_topic_data(topic: str):
    summarize_raw_data("reddit", topic)
    summarize_raw_data("youtube", topic)


@celery.task
def summarize_topic_data_chunks(topic: str):
    summarize_text_in_chunks("reddit", topic)
    summarize_text_in_chunks("youtube", topic)