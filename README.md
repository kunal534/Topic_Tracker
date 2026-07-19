# Topic Tracker

Topic Tracker is a proactive topic-monitoring platform that finds new coverage for user-defined topics, deduplicates it, creates explainable updates, and exposes the timeline through a GraphQL API backed by a React Apollo client.

## How it works

- Users create or subscribe to topics they want to follow.
- Topics and subscriptions are stored in MongoDB.
- Celery workers collect new content from external providers such as Reddit and YouTube.
- The backend normalizes, deduplicates, and stores topic updates and in-app notifications.
- The GraphQL API serves completed updates and notification state without making users wait for crawling or processing.
- The web client displays topic timelines, subscription state, and recent notifications.

## Architecture

```text
web/ React + Apollo Client
          ↓
      GraphQL API (FastAPI + Strawberry)
          ↓
        MongoDB

Celery workers -> Reddit / YouTube providers
          ↖
        Redis broker / backend
```

### Main components

- `app/main.py` - FastAPI app exposing the GraphQL API.
- `app/graphql_schema.py` - GraphQL schema for topics, subscriptions, updates, notifications, and auth.
- `app/tasks.py` - Celery tasks for topic refresh and content collection.
- `app/crawlers/` - Source providers for external content.
- `app/db/mongodb.py` - MongoDB connection, collections, and indexes.
- `app/services/` - Business logic for updates, notifications, and personalization.
- `web/` - React + Apollo dashboard.

## Local setup

### 1. Configure environment

Copy `.env.example` to `.env` and fill in required values:

```bash
cp .env.example .env
```

Required values typically include:

- `MONGODB_URI`
- `REDIS_URL`
- `JWT_SECRET`
- `ALLOWED_ORIGINS`
- `RAPIDAPI_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`

### 2. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Start supporting services

Run MongoDB and Redis in Docker:

```bash
docker compose up -d
```

### 4. Run the backend API

```bash
uvicorn app.main:app --reload
```

### 5. Run a Celery worker

In a second terminal:

```bash
celery -A app.tasks worker --loglevel=info --queues=collection
```

### 6. Run Celery Beat for scheduled jobs

In a third terminal:

```bash
celery -A app.tasks beat --loglevel=info
```

### 7. Start the web client

From the `web/` directory:

```bash
npm install
npm run dev
```

Or use the convenience script from the project root:

```bash
./scripts/run-dev.sh
```

### 8. Access the app

- GraphQL explorer: `http://localhost:8000/graphql`
- Web dashboard: usually `http://localhost:5173`

## GraphQL example

Create a topic:

```graphql
mutation {
  createTopic(name: "India AI regulation") {
    id
    name
  }
}
```

Then use the returned topic ID to call `subscribeToTopic`, query `subscriptions`, `topicUpdates`, and `notifications`, or refresh the topic.

## Verification

Run unit tests and compile checks:

```bash
pytest
python -m compileall -q app
```

## Notes

- Local development uses `X-User-ID` to simulate users.
- Production requires a real authentication provider instead of the development identity header.
- GraphQL subscriptions are implemented, but horizontal scaling should use Redis pub/sub or a distributed event bus for live update delivery.

## Security

- Keep secrets in `.env` or a managed secrets store.
- Do not commit provider keys or JWT secrets.
- Rotate any sensitive keys before sharing or deploying.
