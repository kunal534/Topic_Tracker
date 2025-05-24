# Topic Tracker

A backend system that periodically fetches and summarizes topic-related content from Reddit and YouTube.

---

## ✅ Features Implemented

### 🔍 Topic Data Collection

* **Reddit**:

  * Fetches top post titles related to a given topic.
* **YouTube**:

  * Uses RapidAPI (youtube138, youtube-v2) to fetch video metadata, subtitles, and top comments.
  * Stores `video_id`, `title`, `channel`, `subtitles`, and `top_comments`.

### 🧠 Summarization

* **Reddit**:

  * Summarized using OpenAI GPT-4 (via OpenRouter).
  * Chunked input handled manually using `tiktoken`.

* **YouTube**:

  * Uses `youtube-video-summarizer-gpt-ai` via RapidAPI to save OpenAI credits.

### 🗃️ MongoDB Storage

* Collections: `reddit_posts`, `youtube_videos`
* Fields: `topic`, `source`, `video_id`, `subtitles`, `top_comments`, `summary`, `created_at`, `summarized_at`

### ⚙️ Celery Tasks

* `fetch_topic_data(topic)`:

  * Fetches and stores raw Reddit and YouTube content for a given topic.
* `summarize_topic_data(topic)`:

  * Reddit content summarized using OpenAI.
  * YouTube content summarized using RapidAPI.

---

## 🔄 Switching Summarization Source

* OpenAI used only for Reddit (due to token cost).
* YouTube switched to `youtube-video-summarizer-gpt-ai` (RapidAPI).

---

## 🐞 Latest Issue

### May 24, 2025

```plaintext
Task summarize_topic_data_chunks raised:
TypeError: unsupported operand type(s) for +: 'int' and 'str'
Cause: `chunk_size` passed as a string instead of integer.
Fix: Ensure chunk_size is cast or passed as an integer when used.
```

---

## 🧪 Running the App

### 1. Start MongoDB and Redis

### 2. Run Celery Worker

```bash
celery -A app.tasks worker --loglevel=info
```

### 3. Trigger Tasks

```python
from app.tasks import fetch_topic_data, summarize_topic_data
fetch_topic_data.delay("amazon SDE interview")
summarize_topic_data.delay("amazon SDE interview")
```

---

## 📌 Environment Variables Required

* `OPENROUTER_API_KEY`
* `RAPIDAPI_KEY`

---

## ⏭️ Next Steps

* [ ] Move YouTube summarization API call to `summarize_raw_data`
* [ ] Add deduplication for fetched videos and posts
* [ ] Expose summaries via REST API
* [ ] Add user-specific topic registration and history
* [ ] Add retry/fallback logic for failed summarizations

---

## 🧠 Tech Stack

* Python 3.13
* MongoDB
* Redis
* Celery
* OpenAI API (via OpenRouter)
* RapidAPI endpoints

---

*Last updated: May 24, 2025*
