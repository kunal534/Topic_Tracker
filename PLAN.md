# Topic Tracker: Product and Implementation Plan

## 1. Product direction

Topic Tracker should be a proactive intelligence service, not a one-time search
tool. A person subscribes to a topic they care about (for example, "Amazon SDE
interview", "India AI regulation", or "Taylor Swift tour dates") and receives
an update when credible, materially new information appears.

The core promise is:

> Tell us what you want to stay informed about; we continuously monitor it,
> separate meaningful changes from repeated noise, and notify you with a concise
> explanation and sources.

This differs from following a page or a person: a topic may evolve across many
sources, entities, and communities. The app should assemble that changing view
for the subscriber.

## 2. Target user flow

1. A user creates an account and subscribes to a topic.
2. They choose alert preferences: immediate, daily digest, or weekly digest;
   source types; language/region; and optional keyword exclusions.
3. The system performs an initial collection and produces a topic baseline:
   a short current-state summary and a set of source items.
4. A scheduled monitor fetches fresh content for the topic at an appropriate
   interval.
5. The system normalizes, deduplicates, scores, and compares new items with the
   prior baseline and previously seen items.
6. Only material changes create an update event. The user sees an explanation,
   links to source material, and why it matters.
7. The user can open a topic timeline, inspect sources, adjust subscriptions,
   or pause/delete a topic.

## 3. Definition of a meaningful update

An update should be sent only when the new content is both relevant and new.
The initial rules can be deterministic and later be improved with model-assisted
classification.

An item is eligible when it:

- matches the topic after filtering;
- has not already been stored (canonical URL, provider ID, or content hash);
- is recent enough for the topic's monitoring window;
- clears a source-quality and relevance threshold; and
- adds a fact, event, decision, sentiment shift, release, deadline, or notable
  discussion that is absent from the current baseline.

Low-value items (duplicates, reuploads, promotional content, generic mentions,
and minor restatements) should be stored only when useful for auditability and
must not trigger an alert.

Each delivered alert should contain:

- a title and 2-5 sentence change summary;
- the event date and detection date;
- 1-3 primary supporting sources;
- a confidence/relevance label; and
- a link to the topic timeline.

## 4. Scope and delivery phases

### Phase 0: Secure and stabilize the existing prototype

Goal: make the current worker safe and reproducible before adding product
features.

1. Revoke and rotate the exposed RapidAPI credential. Remove it from source and
   scrub it from Git history if this repository has been shared.
2. Add `.gitignore` for `.env`, Python cache files, local databases, Redis dumps,
   and Celery schedule files. Stop tracking generated artifacts.
3. Add `pyproject.toml` or `requirements.txt` with pinned Python dependencies,
   supported Python version, and documented setup steps.
4. Consolidate the duplicated summarization logic into one module. Remove unused
   imports and functions.
5. Fix or remove the broken `summarize_topic_data_chunks` task. It currently
   passes a topic string as a numeric chunk size.
6. Add request timeouts, `raise_for_status`, structured logs, Celery retries with
   backoff, and explicit failure states for external API calls.
7. Add a local development stack (Docker Compose for MongoDB and Redis) and a
   sample `.env.example` containing names only, never credentials.
8. Write unit tests for parsing, chunking, deduplication helpers, and task error
   handling; add a minimal CI check for formatting, linting, and tests.

Exit criteria: a clean checkout can be configured and tested without hidden
local state; no credentials or generated runtime files are committed.

### Phase 1: Establish the core data model and API

Goal: support durable users, topics, subscriptions, and a browseable history.

Expose the product API through GraphQL, using a Python GraphQL framework that
fits the chosen web framework (for example Strawberry with FastAPI). Add
authentication before production release. GraphQL fits the topic detail page,
timeline, and subscription settings because they need related data in a single
request and the client benefits from a normalized cache.

Initial GraphQL operations:

- Queries: `me`, `topics`, `topic(id)`, `subscriptions`, and
  `topicUpdates(topicId, cursor)`.
- Mutations: `createTopic`, `subscribeToTopic`, `updateSubscription`,
  `unsubscribeFromTopic`, `refreshTopic`, and `markUpdateRead`.
- Subscriptions: `topicUpdateCreated(topicId)` and `notificationCreated` for
  live in-app updates. Add WebSockets or server-sent events after the normal
  query/mutation flow works reliably.

Apollo Client should manage frontend access to GraphQL:

- configure normalized-cache identity policies for `Topic`, `Subscription`,
  `TopicUpdate`, and `SourceItem` using stable IDs;
- use cursor pagination and Apollo field merge policies for update timelines,
  preventing duplicate cards as more pages load;
- update or invalidate only affected cached records after mutations;
- write a delivered `TopicUpdate` into the cached topic timeline when a GraphQL
  subscription event arrives;
- use optimistic UI only for reversible actions such as marking an update read
  or changing notification preferences; and
- reset the cache on logout so private subscription data cannot bleed between
  users.

Keep Celery worker communication internal. Workers write validated data and
update records to MongoDB; GraphQL resolvers read those records. Do not make the
browser wait for crawler or summarization jobs. `refreshTopic` enqueues an
idempotent task and returns its current job/status record.

For a single-service MVP, MongoDB can remain the primary store. Enforce indexes
and uniqueness at the database level rather than relying on worker behavior.

### Phase 2: Build the ingestion pipeline

Goal: continuously collect source items without creating duplicates.

1. Define a source-provider interface with `search(topic, cursor)` and a
   normalized result schema.
2. Keep Reddit and YouTube as the initial providers, but collect only fields
   necessary for the MVP: provider ID, canonical URL, title, text/transcript
   excerpt, author/channel, published time, fetched time, engagement metadata,
   and raw provider payload (optional, TTL-controlled).
3. Add providers incrementally based on user value and API terms: news/RSS feeds,
   official blogs, government notices, product release notes, and selected
   websites. Favor primary sources for high-stakes topics.
4. Store provider cursors or last-successful-fetch times per topic/source so jobs
   fetch incrementally.
5. Use a unique index on `(source, external_id)` and a secondary content hash /
   canonical URL index to stop both provider and cross-provider duplicates.
6. Record ingestion failures separately from empty results so monitoring health
   is visible.

### Phase 3: Detect changes and create updates

Goal: turn source items into useful, non-repetitive topic events.

Processing pipeline:

```text
Scheduled topic run
  -> source collection
  -> normalization and validation
  -> deduplication
  -> relevance and quality scoring
  -> novelty comparison with topic baseline
  -> event clustering and summary generation
  -> update record
  -> notification eligibility check
```

Initial novelty strategy:

1. Exact deduplication using source IDs, canonical URLs, and normalized title
   hashes.
2. Near-duplicate detection using title/text fingerprints (for example SimHash)
   or embeddings.
3. Rule-based event indicators such as dates, named entities, terms like
   "announced", "released", "approved", "cancelled", and source recency.
4. Semantic comparison of an item/event against the prior baseline. Generate an
   update only if the comparison identifies a material addition or contradiction.
5. Require at least one trusted source or corroboration for high-impact claims.

Use the language model to summarize and classify already-filtered content, not
as the only deduplication or truth mechanism. Persist the source item IDs and
model/version metadata used to produce each update for traceability.

### Phase 4: Notifications and preferences

Goal: deliver timely information without alert fatigue.

Notification channels should be introduced in this order:

1. In-app update feed and unread state.
2. Email digests and high-priority immediate email alerts.
3. Browser/mobile push notifications when clients exist.

Notification rules:

- respect each subscription's cadence and quiet hours;
- collapse related events into a digest;
- cap alerts per topic/day by default;
- permit a user to mark alerts useful/not useful;
- use idempotency keys so retries cannot send duplicate notifications; and
- keep a delivery log with provider response, status, and retry count.

### Phase 5: Personalization and quality improvement

Goal: adapt alerts to what each subscriber finds useful.

1. Gather explicit feedback (useful, not useful, too frequent, wrong topic).
2. Learn per-subscription source weights and relevance thresholds.
3. Support topic aliases, included/excluded entities, regional filters, and
   preferred source types.
4. Provide a topic briefing that shows current state, what changed since a
   selected date, and unresolved/contested claims.
5. Measure alert precision, duplicate rate, latency, source coverage, and
   unsubscribe/mute rates.

## 5. Proposed data model

### `users`

`_id`, email/identity-provider subject, display name, timezone, notification
settings, created_at.

### `topics`

`_id`, canonical_name, normalized_query, aliases, description, monitoring
status, baseline_summary, baseline_updated_at, source configuration,
created_at, updated_at.

Unique index: `normalized_query`.

### `subscriptions`

`_id`, user_id, topic_id, cadence, channels, quiet_hours, locale, included
keywords, excluded_keywords, relevance_threshold, active, last_seen_update_at,
created_at, updated_at.

Unique index: `(user_id, topic_id)`.

### `source_items`

`_id`, topic_id, source, external_id, canonical_url, title, body/excerpt,
author, published_at, fetched_at, engagement, content_hash, quality_score,
relevance_score, raw_payload_reference, processing_status.

Unique indexes: `(source, external_id)`, plus partial unique indexes for
canonical URL/content hash where populated.

### `topic_updates`

`_id`, topic_id, type, title, summary, source_item_ids, novelty_score,
confidence, event_time, detected_at, model_metadata, status.

Index: `(topic_id, detected_at DESC)`.

### `notification_deliveries`

`_id`, subscription_id, topic_update_id, channel, idempotency_key, scheduled_at,
sent_at, status, provider_message_id, error, retry_count.

Unique index: `(subscription_id, topic_update_id, channel)`.

### `topic_source_state`

`topic_id`, source, cursor/last_fetched_at, last_success_at, consecutive_errors,
next_retry_at. Unique index: `(topic_id, source)`.

### `monitoring_jobs`

`_id`, topic_id, idempotency_key, trigger (`scheduled` or `manual`), status,
queued_at, started_at, completed_at, error, and result counters. This lets
`refreshTopic` show progress without coupling the client directly to Celery.

## 6. Scheduling and worker design

Use Celery with Redis initially, separating queues by workload:

- `collection`: fetch content from providers;
- `processing`: normalize, deduplicate, score, and form updates;
- `summarization`: model/API calls with tighter concurrency and rate limiting;
- `notification`: email/push delivery and retries.

Celery Beat should schedule a lightweight dispatcher, not one static task per
topic. The dispatcher finds active topics whose `next_check_at` is due and
enqueues idempotent per-topic jobs. Start with a default interval (for example,
every six hours), then allow frequency based on topic volatility and plan tier.

Every job must have an idempotency key such as `topic_id + source + time bucket`.
Store job progress/status so overlapping schedules and retries do not generate
duplicate source items or alerts.

## 7. Security, privacy, and operations

- Keep secrets in environment variables or a managed secret store; validate all
  required settings at application startup.
- Never log API keys, raw authorization headers, or private user data.
- Add authentication, authorization checks, rate limiting, and input validation
  before exposing the API publicly.
- Encrypt sensitive configuration at rest where applicable and define retention
  periods for raw source payloads.
- Respect provider terms, robots rules, rate limits, attribution requirements,
  and content licensing. Link users to original content rather than reproducing
  large source text.
- Monitor queue depth, task failure rate, fetch latency, external API errors,
  duplicate rate, update latency, and notification success rate.
- Add backups, restore verification, and health/readiness endpoints.

## 8. MVP boundaries

The first usable release should deliberately stay narrow:

- authenticated users;
- a web client using Apollo Client against a GraphQL API;
- topic creation and subscriptions;
- Reddit, YouTube, and one primary-source/news provider;
- scheduled collection at a fixed cadence;
- duplicate suppression and rule-based relevance scoring;
- a web/API update timeline plus daily email digest;
- manual refresh with limits; and
- observability for failed monitoring runs.

Do not start with real-time streaming, arbitrary website crawling, mobile apps,
fully automated truth verification, or complex personalization. Those depend on
a reliable baseline pipeline and feedback data.

## 9. Acceptance criteria for the MVP

1. A user can subscribe to a new topic and see an initial baseline within the
   defined processing window.
2. Re-running collection with identical content creates no duplicate item,
   update, or notification.
3. A material new source item creates one explainable topic update linked to its
   sources.
4. A subscriber receives the update according to their selected cadence, once.
5. A failed external API call is retried safely and appears in monitoring rather
   than silently succeeding.
6. Users can inspect, pause, edit, and remove their subscriptions.
7. Tests cover the core deduplication, eligibility, and notification idempotency
   rules.

## 10. Suggested implementation order

1. Complete Phase 0 and establish a testable application skeleton.
2. Add the database models/indexes and topic/subscription API in Phase 1.
3. Refactor the existing Reddit/YouTube crawlers behind the provider interface.
4. Add scheduler state and idempotent collection jobs.
5. Implement exact deduplication, then basic relevance and update creation.
6. Build the in-app timeline and daily email digest.
7. Add near-duplicate/semantic novelty analysis and feedback-driven tuning.

This order produces a useful subscription loop early while avoiding premature
investment in AI sophistication before the source data and delivery guarantees
are dependable.
