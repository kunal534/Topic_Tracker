
# 🔁 Development Workflow

## 1. Feature Tracking

- [ ] Replace hardcoded YouTube IDs with real search support (via better API or custom parsing)
- [ ] Add frontend dashboard for summaries
- [ ] Improve error handling for summarization failures
- [ ] Deploy on Render/Vercel/EC2
- [ ] Add user login system

## 2. Current MVP Flow

```mermaid
graph TD
A[User] --> B[Create Task via UI]
B --> C[Task stored in MongoDB]
C --> D[TaskScheduler picks due task]
D --> E1[RedditCrawler fetches]
D --> E2[YouTubeCrawler fetches]
D --> E3[GoogleCrawler fetches]
E1 --> F[Database saves raw content]
E2 --> F
E3 --> F
F --> G[SummaryGenerator processes]
G --> H[Save summary to DB]
H --> I[Serve via API/UI]
```

## 3. Branching Strategy

- `main`: stable prod-ready code
- `v1-mvp-working`: current MVP
- `dev`: work-in-progress feature branches
