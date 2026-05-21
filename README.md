# Vunoh AI — Operations Platform

> A production grade AI powered operational assistant for diaspora users.

---

## Project Overview

Vunoh is an internal operations platform that converts natural language customer requests into structured, tracked, and fulfilled operational workflows. It targets diaspora users Kenyans abroad managing money transfers, document verification, service hiring, and travel logistics back home.

The system is deliberately **not a chatbot**. It is an operational workflow engine that happens to use AI as an understanding layer. The output is structured data: risk scores, assigned teams, workflow steps, and multi-channel customer messages all persisted to a database and tracked through a lifecycle.

**What a request looks like end-to-end:**

```
Customer: "I need to send KES 15,000 to my mother in Kisumu urgently"
    ↓
Scope Check (Stage 0)   — Is this in Vunoh's service scope?
    ↓
Intent Extraction       — send_money | confidence: 0.95 | urgency: high
    ↓
Risk Engine             — score: 10/100 | level: low | flags: [urgent_request]
    ↓
Workflow Generator      — 5 operational steps for Finance Team
    ↓
Message Generator       — WhatsApp + Email + SMS drafts
    ↓
Assignment Engine       — Finance Team
    ↓
Database Persistence    — Task record, steps, messages, entities, history
    ↓
Dashboard               — Ops team sees task, risk level, assignment, can send messages
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                 │
│   Vanilla JS + CSS Custom Properties (no framework)            │
│   dashboard.html → task list, filters, live status             │
│   task.html      → full detail, risk card, send messages       │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API (CORS)
┌────────────────────────▼────────────────────────────────────────┐
│                    DJANGO + DRF BACKEND                         │
│                                                                 │
│  apps/tasks/          — models, serializers, views, urls       │
│  services/            — AI client, pipeline stages, messaging  │
│  celery_tasks/        — async pipeline, scheduled jobs         │
│  config/              — settings, urls, celery app             │
└──────┬──────────────────────────────────┬───────────────────────┘
       │                                  │
┌──────▼──────┐                  ┌────────▼────────┐
│ PostgreSQL  │                  │  Redis (DB 1)   │
│ All task    │                  │  Celery broker  │
│ records +   │                  │  + result store │
│ history     │                  └────────┬────────┘
└─────────────┘                           │
                               ┌──────────▼──────────┐
                               │   Celery Worker      │
                               │   process_task       │
                               │   send_channel_msg   │
                               │                      │
                               │   Celery Beat        │
                               │   4 scheduled jobs   │
                               └──────────┬───────────┘
                                          │
                    ┌─────────────────────┼──────────────────────┐
                    │                     │                       │
             ┌──────▼──────┐   ┌──────────▼──────┐   ┌──────────▼──────┐
             │  Groq API   │   │  Google Gemini  │   │  Twilio / Gmail │
             │ (primary)   │   │  (fallback)     │   │  (send messages)│
             └─────────────┘   └─────────────────┘   └─────────────────┘
```

**Technology choices:**

| Layer | Technology | Reason |
|-------|-----------|--------|
| Backend | Django 4.2 + DRF | Mature ORM, admin, serializers |
| Database | PostgreSQL | Relational integrity for task lifecycle |
| Queue | Celery + Redis | Async pipeline without blocking HTTP response |
| Primary AI | Groq (Llama 3.3 70B) | Fast inference, JSON mode |
| Fallback AI | Google Gemini 2.0 Flash | Independent provider for resilience |
| Messages | Twilio WhatsApp + Gmail SMTP | Production-ready APIs |
| Frontend | Vanilla JS ES Modules | No build step, clear file structure |

---

## AI Pipeline — 6 Stages

### Stage 0 — Scope Pre-filter
Before anything expensive runs, one fast AI call checks whether the request falls within Vunoh's 5 service categories. Out-of-scope requests (poems, recipes, coding questions) are rejected immediately with a reason. Ambiguous-but-processable requests get a `clarification_note` added to the task rather than being rejected.

### Stage 1 — Intent Extraction
Extracts structured intent data: intent type, confidence (0–1), urgency level, and key entities (amount, recipient, location, document type, etc.). Uses Pydantic v2 for schema validation — if the AI returns malformed JSON, `parse_with_retry` retries up to 3 times with exponential backoff before failing.

### Stage 2 — Risk Scoring
**Deterministic, not AI-generated.** See the [Risk Scoring Logic](#risk-scoring-logic) section below.

### Stage 3 — Workflow Generation
Generates 4–7 imperative operational steps for the specific intent and context. Temperature is set to `0.1` for consistency — workflows should be deterministic and professional, not creative.

### Stage 4 — Message Generation
Generates customer-facing messages for all 3 channels (WhatsApp, Email, SMS) in a **single AI call** to maintain consistent messaging. Temperature is `0.4` — natural variation in tone is appropriate here. Channel-specific constraints: SMS under 160 chars, WhatsApp conversational, Email formal with structure.

### Stage 5 — Team Assignment
Fully deterministic routing table. No AI involved. Maps intent to team:

```python
ROUTING = {
    "send_money":        "Finance Team",
    "verify_document":   "Legal & Compliance",
    "hire_service":      "Field Operations",
    "airport_transfer":  "Logistics Team",
    "general_inquiry":   "Customer Support",
}
```

---

## Prompt Engineering Decisions

### JSON-only output enforcement
Every prompt ends with explicit instruction: *"Return JSON only — no markdown, no explanation, no extra fields."* This eliminates the most common AI reliability failure: wrapping JSON in markdown code blocks (`\`\`\`json`). Every AI call also sets `response_format={"type": "json_object"}` on Groq (enforced at API level).

### Temperature strategy
| Stage | Temperature | Reason |
|-------|------------|--------|
| Scope check | 0.0 | Binary in/out decision — zero creativity wanted |
| Intent extraction | 0.1 | Deterministic parsing — same request should give same intent |
| Workflow generation | 0.1 | Steps should be consistent and professional |
| Message generation | 0.4 | Slightly warmer — natural variation in tone is fine |

### Retry with backoff (`parse_with_retry`)
AI providers occasionally return valid JSON that doesn't match the Pydantic schema (missing field, wrong type). `parse_with_retry` handles this:
1. Call the AI
2. Try to parse with Pydantic
3. If `ValidationError`: wait 1s, retry
4. If still fails: wait 2s, retry again
5. After 3 failures: raise to Celery, which retries the whole task up to 3×

This gives the system up to 9 parse attempts before a task is marked failed — without those retries, the system would fail on roughly 5% of requests due to AI inconsistency alone.

### Bidirectional provider fallback
```
groq → [rate limit] → gemini → [rate limit] → groq (if 60s cooldown expired) → AllProvidersExhaustedError
```

If `AllProvidersExhaustedError` is raised, the task is saved as `failed` with `error_detail` starting with `"rate_limit_exceeded:"`. The midnight cron job (`retry_api_failures`) detects this prefix and automatically requeues the task — no human intervention needed.

---

## Risk Scoring Logic

Risk is calculated by a **deterministic rule engine** (`services/risk_engine.py`), not by AI.

### Why I Avoided Using AI For Risk Scoring

Using AI for risk assessment in a financial operations system is an architectural mistake for three reasons:

**1. Explainability** — In financial services, regulators and compliance officers require that risk decisions be auditable and explainable. "The AI said so" is not an acceptable answer. A rule engine produces `risk_explanation: ["Amount exceeds KES 100,000", "New recipient never used before"]` — specific, auditable flags that a compliance officer can review and challenge.

**2. Consistency** — AI models produce different risk scores for identical inputs depending on temperature, model version, and prompt context. A deterministic rule engine always produces the same score for the same data. This is critical for fairness and regulatory consistency.

**3. Gaming resistance** — If AI scores risk, sophisticated bad actors can probe the system to find phrasings that produce low risk scores for high-risk requests. A rule engine's scoring criteria can be kept internal to the codebase rather than being inferrable through the model's output.

### How scoring works
Rules are evaluated sequentially. Each matching rule adds to a cumulative score (capped at 100). Key rules:

| Rule | Score added | Trigger |
|------|------------|---------|
| Large amount | +40 | Amount > KES 100,000 |
| Document verification | +30 | Any doc verify intent |
| Urgency flag | +15 | Urgency level = high |
| New recipient | +20 | First-time recipient detected |
| International transfer | +25 | Cross-border transaction |

Score thresholds: `low` < 30 · `medium` 30–69 · `high` ≥ 70

Tasks with `risk_level = "high"` automatically set `escalation_required = True`.

---

## Decisions I Made and Why

**Celery over threading/asyncio**
Django's ORM is not async-safe. Using Celery keeps the HTTP response fast (returns in <100ms with the task code) while the 3–5 second AI pipeline runs in a worker process. This also gives us free retry logic, task state tracking, and scheduled job support.

**Groq as primary, Gemini as fallback (not the reverse)**
Groq's Llama 3.3 70B is significantly faster and has a JSON mode that enforces output format at the API level. Gemini is used as a fallback rather than equal rotation because Groq's json_object mode reduces parse failures. The bidirectional rotation (groq → gemini → groq) means if Groq recovers from rate-limiting within the 60s cooldown, the second attempt hits it directly.

**Manual URL routing instead of DRF Router**
DRF routers auto-generate URLs for standard CRUD but can obscure what routes exist. Since this project has custom nested paths (`/tasks/{code}/messages/send/`, `/tasks/reports/calibration/`), explicit `path()` registrations make the API surface immediately readable in `urls.py`.

**`parse_with_retry` as a utility function, not inline**
Every AI stage needs retry logic. Extracting it into a shared utility ensures consistent retry behavior and avoids duplicating the try/except/backoff pattern across 4+ pipeline stages.

**`transaction.atomic()` around all pipeline DB writes**
If the workflow generator succeeds but the message generator fails, the task would be in a half-written state without atomicity. The entire pipeline's DB writes (task fields, steps, messages, entities, history) commit together or not at all.

---

## Tradeoffs

| Decision | What was simplified | Production alternative |
|----------|--------------------|-----------------------|
| No authentication | API is open | JWT or API key auth |
| Rate limiting only | No per-user limits | User-scoped throttle rates |
| In-memory cooldown | Lost if worker restarts | Redis-backed cooldown tracking |
| Single Celery queue | All tasks share one queue | Priority queues for high-risk tasks |
| No phone validation | Any string accepted as recipient | `phonenumbers` library + E.164 validation |
| Static routing table | Intent → team is hardcoded | Employee availability + skill matching |

---

## Error Handling

### AI rate limits
Both providers expose rate limit errors as distinct exception types. `RateLimitError` starts a 60-second cooldown for that provider and tries the next. `AllProvidersExhaustedError` writes `"rate_limit_exceeded:"` to `error_detail` and skips Celery's normal retry — the midnight cron (`retry_api_failures`) picks it up automatically.

### Parse failures
`parse_with_retry` retries up to 3× with exponential backoff (1s, 2s, 4s). After exhaustion, Celery retries the whole task up to 3× (`max_retries=3, default_retry_delay=5`). Combined: up to 9 parse attempts + 3 full task retries before permanent failure.

### Out-of-scope requests
Stage 0 scope check rejects non-Vunoh requests before any expensive pipeline work. The task is marked `rejected` with the AI's reason stored in `error_detail`. The frontend shows this as "Request Out of Scope" with the specific reason.

### Pipeline partial failures
`transaction.atomic()` ensures no partial data is committed. If any DB write in the pipeline fails, the entire set rolls back and the task stays in `pending` state for retry.

---

## Setup — Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL (Postgres.app on Mac: runs on port 5433)
- Redis
- A `.env` file in `backend/` (see `.env.example`)

### 1. Python environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Environment variables
Copy `backend/.env.example` to `backend/.env` and fill in:
```
DJANGO_SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_DEBUG=True
DB_NAME=vunoh
DB_USER=vunoh_user
DB_PASSWORD=vunoh_pass
DB_HOST=localhost
DB_PORT=5433
REDIS_URL=redis://localhost:6379/1
GROQ_API_KEY=<from console.groq.com>
GEMINI_API_KEY=<from aistudio.google.com>
TWILIO_ACCOUNT_SID=<from console.twilio.com>
TWILIO_AUTH_TOKEN=<from console.twilio.com>
TWILIO_WHATSAPP_FROM=+14155238886
EMAIL_HOST_USER=<your gmail>
EMAIL_HOST_PASSWORD=<16-char app password>
```

### 3. Database
```bash
# Create user and database (adjust for your Postgres setup)
psql -U postgres -p 5433 -c "CREATE USER vunoh_user WITH PASSWORD 'vunoh_pass';"
psql -U postgres -p 5433 -c "CREATE DATABASE vunoh OWNER vunoh_user;"

cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata fixtures/seed.json
```

### 4. Start services
```bash
# Terminal 1 — Django
cd backend
python manage.py runserver

# Terminal 2 — Celery worker
cd backend
celery -A config.celery worker --loglevel=info

# Terminal 3 — Celery Beat (scheduled jobs)
cd backend
celery -A config.celery beat --loglevel=info
```

### 5. Access points
| URL | What |
|-----|------|
| `http://localhost:5500` | Frontend (open with Live Server or file server) |
| `http://localhost:8000/api/tasks/` | REST API (browsable) |
| `http://localhost:8000/admin/` | Django admin |

### 6. Restore from SQL dump
To restore the full schema and seed data on a fresh Postgres instance:
```bash
psql -U vunoh_user -h localhost -p 5433 vunoh < backend/fixtures/schema.sql
```

---

## Scheduled Jobs (Celery Beat)

| Job | Schedule | What it does |
|-----|----------|-------------|
| `auto_escalate_stale` | Every 5 min | Marks tasks stuck in `in_progress` > 30min as escalated |
| `rescore_pending` | Every hour | Re-runs risk engine on pending high-amount transfers |
| `daily_digest` | Daily 8am | Generates summary of high-risk and failed tasks |
| `retry_api_failures` | Daily midnight | Requeues tasks that failed due to AI rate limits |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks/` | List tasks (filter: `?status=`, `?risk_level=`, `?intent=`, `?search=`) |
| `POST` | `/api/tasks/` | Create new task (`{"customer_request": "..."}`) |
| `GET` | `/api/tasks/{code}/` | Get full task detail |
| `PATCH` | `/api/tasks/{code}/status/` | Update task status |
| `POST` | `/api/tasks/{code}/messages/send/` | Send message via WhatsApp or Email |
| `GET` | `/api/tasks/reports/calibration/` | AI accuracy report |
| `GET` | `/api/tasks/reports/digest/` | Latest daily digest |

---

## Future Improvements

- **Authentication** — JWT tokens or API keys; per-user task visibility
- **HTTPS enforcement** — `SECURE_SSL_REDIRECT`, HSTS, secure cookies
- **Phone number validation** — E.164 normalization before Twilio calls
- **Audit logging** — Log who triggered what action, from which IP, when
- **Priority queues** — High-risk tasks processed before low-risk ones
- **Real employee management** — Availability, skills, workload balancing
- **Webhook delivery receipts** — Track whether WhatsApp messages were delivered
- **Rate limiting per user** — Once auth is added, throttle by user not IP
- **Redis-backed cooldown** — Survive worker restarts during AI rate-limit periods
