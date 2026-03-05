# AGENTS.md

# 🧠 PROJECT OVERVIEW

This project is a SaaS AI Content Automation Engine.

The system automatically:
- analyzes a client’s website
- builds SEO content clusters
- generates blog topics
- schedules articles
- generates optimized articles
- performs internal linking
- optionally publishes to WordPress
- runs continuously (not one-time generation)

This is NOT a simple blog generator.
This is a long-running automated content pipeline with scheduling and background workers.

---

# 🏗 ARCHITECTURE OVERVIEW

Frontend:
- Next.js (dashboard SaaS UI)

Backend:
- FastAPI (async API layer)
- PostgreSQL (main database)
- Redis (queue + cache)
- Celery (background tasks + scheduler)
- LLM provider (OpenAI / Claude)

Core Principle:
API layer MUST be thin.
Business logic MUST be in services/.
Long-running tasks MUST run in Celery.
No LLM calls inside routes.

---

# 📦 BACKEND STRUCTURE

app/
│
├── main.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── database.py
│
├── models/
├── schemas/
├── api/
│   └── routes/
├── services/
├── tasks/
├── scheduler/
└── admin/

---

# 🔥 DESIGN PRINCIPLES

1. STRICT LAYER SEPARATION

Routes:
- Only request/response handling
- No business logic
- No LLM calls

Services:
- Pure business logic
- AI orchestration
- SEO logic
- Content planning

Tasks:
- Call services
- Handle retries
- Update DB

Models:
- SQLAlchemy models only

Schemas:
- Pydantic validation only

---

# 🔁 SYSTEM CONTINUITY MODEL

The system must NOT regenerate everything repeatedly.

It works in 3 layers:

LAYER A – Persistent Analysis (monthly refresh)
- Website crawling
- Keyword detection
- Cluster creation
- Internal link mapping
- AI context creation

LAYER B – Content Queue
- Topics stored in DB
- Prioritized
- Scheduled
- Reorderable by user

LAYER C – Production Engine
- Scheduler checks daily
- Generates article only if required
- Updates topic status
- Tracks word count and link count
- Stores logs

---

# 🧠 AI CONTEXT MEMORY

Each project has:

ProjectAnalysis.ai_context

This is a compressed strategic summary of:
- company description
- tone
- positioning
- unique advantages

This context MUST be reused.
Do NOT resend full company description every time.

---

# 🗃 DATABASE CORE TABLES

Users
SubscriptionPlans
UserSubscriptions
Projects
ProjectAnalysis
ContentSchedules
Topics
Articles
WordpressIntegrations
GenerationLogs

Topics != Articles

Topics represent future ideas.
Articles represent generated outputs.

Articles may have versions.

---

# ⏱ SCHEDULER LOGIC

Celery Beat runs daily scheduler task.

Scheduler must:

1. Check active projects
2. Verify schedule settings
3. Verify available topic
4. If no topics available -> generate new topics
5. Generate article for highest priority eligible topic

Topic selection logic:
- status in ('queued', 'scheduled')
- scheduled_date <= today
- ordered by priority DESC

---

# 🧩 ARTICLE GENERATION PIPELINE

1. Load AI context
2. Generate outline
3. Generate sections
4. Merge content
5. SEO optimization
6. Internal linking
7. Generate metadata
8. Compute word count & link count
9. Save
10. Update topic status

Each step must be modular.

---

# 🚫 FORBIDDEN PRACTICES

- No LLM calls in API routes
- No DB logic inside routes
- No business logic inside models
- No synchronous long tasks in FastAPI
- No global state for project data
- No mixing scheduler logic with API logic

---

# 🔐 SECURITY RULES

- Passwords must be hashed (bcrypt)
- JWT authentication required
- Role-based access (user/admin)
- WordPress credentials encrypted

---

# 📊 BILLING CONSTRAINTS

System must:
- Track articles generated per month
- Track token usage
- Respect subscription limits
- Prevent generation if limits exceeded

---

# 🧪 TESTABILITY REQUIREMENTS

Services must:
- Be testable without FastAPI
- Not depend on request object
- Accept pure parameters

Tasks must:
- Be retry-safe
- Idempotent where possible

---

# 📊 ENTERPRISE LOGGING REQUIREMENTS

All AI operations must:

- Use structured JSON logging
- Include request_id
- Include project_id and topic_id
- Record duration
- Record token usage
- Record model used
- Log retries
- Log errors to Sentry

No silent failures allowed.

Celery must be monitored via Flower.
Errors must be captured in Sentry.
Business-level logs must be stored in generation_logs table.

---

# 🎯 MVP SCOPE

Phase 1:
- Project creation
- Content schedule
- Topic generation
- Article generation
- Dashboard visibility
- Manual publish

Phase 2:
- Website crawling
- Internal link automation
- WordPress auto publish
- Admin panel
- Billing system

---

# 🧠 FUTURE SCALABILITY

System must allow:
- Separate AI worker scaling
- Separate crawler worker
- Moving to microservices if needed

Code should be written in modular and decoupled way.

---

# 🏁 END GOAL

Build a scalable AI-powered SEO content automation SaaS
with persistent memory, scheduling engine,
and production-grade architecture.

This is NOT a demo project.
This is production-grade architecture.

All code must follow this document strictly.