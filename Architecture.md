
# 🧠 Architecture Overview

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

## Components

- **RedditCrawler**: Uses PRAW to search Reddit for topics.
- **YouTubeCrawler**: Uses fixed video IDs (RapidAPI limitation).
- **GoogleCrawler**: Uses RapidAPI Google Search.
- **SummaryGenerator**: Uses GPT-4.1-Mini via RapidAPI to summarize.
- **TaskScheduler**: Periodically runs crawlers + summarizer.
- **DatabaseManager**: Saves all tasks, summaries, and content.
