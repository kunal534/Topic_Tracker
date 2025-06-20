# 🧠 Topic Tracker – MVP Working Version

A backend-powered tool that tracks any topic across Reddit, YouTube, and Google Search — aggregates raw data, summarizes it using AI (via RapidAPI), and stores everything in MongoDB. 

> This MVP is a minimal but functional implementation — ideal for continuous tracking and summarization of any internet topic, powered by scheduled background jobs.

---

## 📸 Demo

![UI Screenshot](https://raw.githubusercontent.com/kunal534/Topic_Tracker/v1-mvp-working/assets/demo.png)  
> Web UI to create & monitor tracked topics in real time.

---

## 🔍 Features

- 🔁 **Multi-source Aggregation**  
  Fetch data from:
  - 🟠 Reddit (via PRAW)
  - 🔴 YouTube (via RapidAPI)
  - 🔵 Google Search (via RapidAPI)

- 🧠 **Smart AI Summaries**  
  Summarizes content using **GPT-4.1-Mini** via RapidAPI.

- ⏰ **Background Scheduler**  
  Runs tasks periodically (30m, 1h, 6h, etc.) to keep data fresh.

- 📁 **MongoDB Storage**  
  Persists raw posts/videos/search results and summaries.

- 🖥️ **Web UI**  
  Create/view/delete tracking tasks easily in your browser.

---

## 🛠️ Tech Stack

| Layer          | Tech/Service                        |
|----------------|-------------------------------------|
| Backend        | Python, Flask                       |
| Crawlers       | Reddit (PRAW), YouTube + Google (via RapidAPI) |
| AI Summarizer  | GPT-4.1-Mini (via RapidAPI)         |
| Scheduler      | Python threading / time loop        |
| Database       | MongoDB (via PyMongo)               |
| Frontend       | Vanilla JS + HTML (Flask template)  |

---

## 🧪 Local Setup

### 🔁 1. Clone & Setup

```bash
git clone https://github.com/kunal534/Topic_Tracker.git
cd Topic_Tracker
git checkout v1-mvp-working
```

### 🧪 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 🔐 3. Setup `.env`

Create a `.env` file with the following (use your actual credentials):

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017/content_aggregator

# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=topic_tracker_bot/1.0

# RapidAPI Keys
RAPIDAPI_KEY_GPT=your_rapidapi_key
RAPIDAPI_KEY_YOUTUBE=your_rapidapi_key
RAPIDAPI_KEY_GOOGLE=your_rapidapi_key

# Flask
FLASK_SECRET_KEY=your_secret_here
FLASK_DEBUG=True
PORT=5050
```

### ▶️ 4. Run the app

```bash
python app.py
```

> App will be served at: [http://localhost:5050](http://localhost:5050)

---

## 🧠 Architecture Overview

```plaintext
[ User ] <-- Web UI --> [ Flask API ]
                             |
    ---------------------------------------------------
    |                    |                   |        |
[ RedditCrawler ]   [ YouTubeCrawler ]   [ GoogleCrawler ]
    |                    |                   |
  Raw Posts          Video Metadata      Search Results
    |                    |                   |
                    [ MongoDB (tasks, summaries, content) ]
                             |
                    [ Summary Generator (GPT via RapidAPI) ]
                             |
                    [ Scheduler Loop (TaskScheduler) ]
```

---

## 📦 Folder Structure

```bash
Topic_Tracker/
│
├── app.py                  # Main Flask application
├── config.py               # Loads environment variables
├── .env                    # API keys (ignored)
├── requirements.txt
│
├── crawlers/
│   ├── reddit_crawler.py
│   ├── youtube_crawler.py
│   └── google_crawler.py
│
├── summary_generator.py    # Uses GPT to summarize
├── task_scheduler.py       # Runs crawler + summarizer loop
├── content_processor.py    # Prepares/cleans content for summarization
├── database_manager.py     # MongoDB handler
```

---

## 📡 API Endpoints

### 🔁 Task Management

| Method | Endpoint                 | Description             |
|--------|--------------------------|-------------------------|
| GET    | `/api/status`            | System status           |
| GET    | `/api/tasks`             | List all tasks          |
| POST   | `/api/tasks`             | Create a new task       |
| DELETE | `/api/tasks/<task_id>`   | Delete a task           |
| GET    | `/api/tasks/<task_id>`   | Get details of a task   |

### 🧠 Summaries

| Method | Endpoint                     | Description               |
|--------|------------------------------|---------------------------|
| GET    | `/api/summaries`             | Get summaries by topic    |
| GET    | `/api/summaries/<summary_id>`| Get summary by ID         |
| POST   | `/api/generate-summary`      | Generate one-off summary  |

### 🔍 Manual Trigger

| Method | Endpoint       | Description               |
|--------|----------------|---------------------------|
| POST   | `/api/crawl`   | Manual fetch from sources |
```json
{
  "topic": "Tesla",
  "sources": ["reddit", "youtube", "google"]
}
```

---

## ⚠️ Known Issues

- ❗ GPT-4.1 Mini via RapidAPI may rate-limit (429) on free tier.
- ❗ YouTube RapidAPI does not support search, uses fixed IDs for now.
- ❗ Google crawler needs cleaner formatting for description fields.
- 🐛 No authentication yet — anyone can create/delete tasks.

---

## 📈 Roadmap

- [x] MVP with full functionality
- [ ] Async crawler migration
- [ ] Add historical trend view
- [ ] User login + auth
- [ ] PDF/CSV export of summaries
- [ ] Redis queue support for crawler jobs

---

## 🙋‍♂️ Author

**Kunal Uttam**  
🔗 [GitHub](https://github.com/kunal534) | [LinkedIn](https://linkedin.com/in/kunaluttam)

---

## 📝 License

This project is licensed under the [MIT License](LICENSE).