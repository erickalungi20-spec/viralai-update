# ADR-004: Phase 0 uses in-process Event Bus and Task Scheduler, not Redis/Celery

## Status
Accepted

## Context
The Commercial Development Workflow specifies Redis Streams for the Event Bus and
Celery+Redis/RabbitMQ for the Task Scheduler. Building against that stack from the first
commit requires running Redis (and later a broker) alongside the codebase for every test,
on every machine, including CI — before a single biological engine exists to justify the
operational cost.

## Decision
Phase 0 implements the Event Bus and Task Scheduler as pure-Python, in-process components
with no external services:
- `EventBus` — synchronous topic-based pub/sub, in-memory.
- `TaskScheduler` — a local `ThreadPoolExecutor`-backed job queue.

Both expose the same conceptual interface (publish/subscribe by topic; submit/status/result
for jobs) that their production counterparts will expose. Call sites depend on that
interface, not on threading or in-memory specifics — no engine code should ever import
`concurrent.futures` or do direct pub/sub outside these two modules.

## Consequences
- **Positive:** zero external infrastructure to run tests or develop locally; CI stays
  fast and simple; the foundation layer is provably correct before any scaling concern is
  introduced.
- **Positive:** the swap to Redis Streams / Celery later is a backend substitution behind
  an unchanged interface, not a rewrite of every engine that publishes events or submits
  jobs.
- **Negative:** Phase 0's bus/scheduler do not survive a process restart and do not work
  across multiple machines. This is fine until there's an actual multi-process or
  multi-user deployment need (Phase 11), at which point this ADR should be revisited and
  superseded.
- **Trigger for revisiting this decision:** the first time ViralAI needs to run analytical
  work across more than one process (e.g. a hosted multi-user deployment, or a simulation
  job that needs to survive an API server restart).

## Alternatives considered
- **Build against Redis/Celery from day one.** Rejected for Phase 0 — matches the
  architecture's long-term target but adds operational overhead before there is any load
  or team size that requires it. Revisit at Phase 11 (Deployment) per the Commercial
  Development Workflow.
