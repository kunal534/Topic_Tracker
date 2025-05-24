import requests
import tiktoken
from datetime import datetime
from app.db.mongodb import db
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def summarize_text_in_chunks(text_chunks, encoding, model="gpt-4"):
    partial_summaries = []
    for chunk in text_chunks:
        prompt = f"Summarize the following chunk in 2-3 sentences:\n\n{chunk}"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You're a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=150
            )
            summary = response.choices[0].message.content
            if summary:
                partial_summaries.append(summary)
        except Exception as e:
            print(f"[ERROR] Failed to summarize chunk: {e}")
    return partial_summaries

def summarize_raw_data(source, topic):
    collection_name = "reddit_posts" if source == "reddit" else "youtube_videos"
    collection = db[collection_name]
    docs = collection.find({"topic": topic, "summary": None})
    encoding = tiktoken.encoding_for_model("gpt-4")
    max_tokens_per_chunk = 150

    for doc in docs:
        try:
            if source == "youtube":
                video_id = doc.get("video_id")
                headers = {
                    "Content-Type": "application/json",
                    "x-rapidapi-host": "youtube-video-summarizer-gpt-ai.p.rapidapi.com",
                    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", "e60d9a8844msh430396f611b5f24p13609ajsn19036d6a37dc")
                }
                payload = {
                    "video_id": video_id,
                    "media_type": "youtube",
                    "language_code": "en",
                    "summary_type": "default"
                }
                response = requests.post(
                    "https://youtube-video-summarizer-gpt-ai.p.rapidapi.com/api/summary/generate-free",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                summary = response.json().get("summary", "")
            else:
                raw_parts = [post.get("title", "") for post in doc.get("data", [])]

                chunks = []
                current_chunk = ""
                current_tokens = 0

                for part in raw_parts:
                    part_tokens = encoding.encode(part)
                    if current_tokens + len(part_tokens) > max_tokens_per_chunk:
                        chunks.append(current_chunk)
                        current_chunk = part
                        current_tokens = len(part_tokens)
                    else:
                        current_chunk += " " + part
                        current_tokens += len(part_tokens)

                if current_chunk:
                    chunks.append(current_chunk)

                partial_summaries = summarize_text_in_chunks(chunks, encoding)
                combined_summary_text = " ".join(partial_summaries)

                final_prompt = f"Combine and summarize the following content into 4-6 sentences:\n\n{combined_summary_text}"
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're a helpful assistant."},
                        {"role": "user", "content": final_prompt}
                    ],
                    temperature=0.5,
                    max_tokens=100
                )
                summary = response.choices[0].message.content

            if not summary:
                print(f"[WARN] Final summary was empty for doc {doc['_id']}")
                continue

            collection.update_one({"_id": doc["_id"]}, {
                "$set": {
                    "summary": summary,
                    "summarized_at": datetime.utcnow()
                }
            })
            print(f"[OK] Saved summary for doc {doc['_id']}")

        except Exception as e:
            print(f"[ERROR] Failed for doc {doc.get('_id')}: {e}")