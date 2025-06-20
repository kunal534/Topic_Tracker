
# ⚙️ Local Setup Guide

## 1. Clone the repo

```bash
git clone https://github.com/kunal534/Topic_Tracker.git
cd Topic_Tracker
git checkout v1-mvp-working
```

## 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure .env

```
MONGODB_URI=mongodb://localhost:27017/content_aggregator
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
RAPIDAPI_KEY_GPT=...
RAPIDAPI_KEY_YOUTUBE=...
RAPIDAPI_KEY_GOOGLE=...
FLASK_SECRET_KEY=...
FLASK_DEBUG=True
PORT=5050
```

## 4. Run the App

```bash
python app.py
```
