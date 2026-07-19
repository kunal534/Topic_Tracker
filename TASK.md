# Implementation Tracker

## Current objective

Turn Topic Tracker from a one-off crawler into a reliable, proactive topic
subscription service with a GraphQL API and an Apollo Client-ready contract.

## Progress

| Status | Work item | Notes |
| --- | --- | --- |
| Completed | Foundation and security hardening | Added configuration, environment template, ignored runtime files, Docker services, and removed source-level credentials. |
| Completed | Data model and persistence layer | Implemented indexed topics, subscriptions, source items, updates, and monitoring jobs. |
| Completed | Collection and change-detection pipeline | Implemented idempotent jobs, provider timeouts, duplicate suppression, scoring placeholders, and conservative update creation. |
| Completed | GraphQL API | Added topic, subscription, update, and refresh operations designed for Apollo Client caching. Live GraphQL subscription events remain a follow-up. |
| Completed | Tests and verification | Installed dependencies in an isolated `.venv`; 4 unit tests, GraphQL schema import, compile checks, and whitespace checks pass. |
| Completed | Production backend completion | Added JWT login/register, Argon2 password hashing, user-scoped notification records, and authenticated live update subscriptions. |
| Completed | Apollo Client web UI | Built and production-verified the React dashboard with auth, topic subscriptions, cached timelines, alert state, and responsive layout. |

## Completed

- Created the product and architecture plan in `PLAN.md`.
- Added GraphQL/Apollo cache strategy to `PLAN.md`.
- Added local setup instructions and the initial GraphQL contract to `README.md`.
- Added `.gitignore` and removed generated caches/local runtime files from Git tracking (the local files remain available but will no longer be committed).
- Verified the backend with `pytest`, schema generation, Python compilation, and Git whitespace checks.
- Added JWT-based authentication, Argon2 password hashing, in-app notifications, and authenticated GraphQL update subscriptions.
- Added the `web/` React + Apollo Client application, configured CORS, and verified its production build.

## Remaining after this implementation pass

- Replace the development `X-User-ID` identity simulation with a real production identity provider and secure login flow.
- Add production notification delivery channels and providers, with idempotent delivery logs, retries, and user preference controls.
- Configure live third-party provider credentials for Reddit, YouTube/RapidAPI, AI summarization, and other sources; validate rate limits, quotas, and terms of service.
- Implement true live GraphQL subscription delivery for topic updates and notifications; remove client polling and use Redis pub/sub or another scalable event bus for replica-safe delivery.
- Harden production deployment: secrets management, HTTPS/CORS policy, structured logging, health checks, observability, and a repeatable Docker/hosting deployment pipeline.
- Add semantic novelty scoring, personalization/feedback loops, alert fatigue controls, and quality gating before delivering user-facing updates.
- Complete end-to-end production verification tests for authentication, crawling/workflow processing, GraphQL APIs, subscriptions, and notification delivery.
- Rotate placeholder credentials and secrets in `.env.example` and move real secrets into a managed store before launch.
