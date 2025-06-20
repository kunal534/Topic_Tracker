
# 🔄 Request Flow & Architecture

This note shows how the system processes a user request, step-by-step.

## 🔁 System Request Flow (End-to-End)

```mermaid
sequenceDiagram
    participant User
    participant UI as Web UI (/)
    participant API as Flask API (/api)
    participant DB as MongoDB
    participant Scheduler as TaskScheduler
    participant Crawler as Crawlers (Reddit/YouTube/Google)
    participant Summarizer as SummaryGenerator

    User->>UI: Fill Task Form (Topic, Interval)
    UI->>API: POST /api/tasks
    API->>DB: Store task
    Scheduler->>DB: Check for due tasks (interval)
    Scheduler->>Crawler: Fetch content for task topic
    Crawler->>DB: Save fetched content
    Scheduler->>Summarizer: Summarize content
    Summarizer->>DB: Save summary
    User->>UI: View updated dashboard
    UI->>API: GET /api/summaries
    API->>DB: Fetch summaries
    API->>UI: Return summaries to render
```

## 🧱 Components Breakdown

- [[README]]
- [[Architecture]]
- [[Development Flow]]
- [[API Endpoints]]
- [[Notes and Issues]]

---
➡ Return to [[README]]
