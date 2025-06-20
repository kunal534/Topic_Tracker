
# 🌐 API Endpoints

## Tasks

- `GET /api/status`: System status
- `GET /api/tasks`: List all tasks
- `POST /api/tasks`: Create new task
- `DELETE /api/tasks/<task_id>`: Delete task

## Summaries

- `GET /api/summaries?user_id=...&topic=...`
- `GET /api/summaries/<summary_id>`
- `POST /api/generate-summary`

## Manual Crawl

```json
POST /api/crawl
{
  "topic": "Amazon",
  "sources": ["reddit", "youtube", "google"]
}
```
