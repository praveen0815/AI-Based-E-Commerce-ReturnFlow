<<<<<<< HEAD
# ReturnFlow

ReturnFlow is a returns and refund platform. Phase 1 is the React client, FastAPI service, PostgreSQL, Redis, and local Docker infrastructure. Phase 2 adds accounts, stores, membership roles, and access tokens. Phase 3 adds orders, return requests, and a server-validated return lifecycle. Phase 4 adds per-store policy and knowledge document upload, text extraction, and a knowledge center UI. Phase 5 adds Chroma-backed RAG indexing, semantic search, and a grounded policy assistant (Gemini or mock LLM). Phase 6 adds a hybrid eligibility engine: deterministic policy rules plus optional AI explanations. Phase 7 adds a LangGraph multi-agent return review workflow with persisted runs, agent history, and human approval checkpoints. Phase 8 adds mock refund and return-logistics workflows with idempotent APIs, audit trails, and customer notification records. It does not move real money or contact carriers. Phase 9 adds store admin and customer dashboards backed by analytics APIs, chart views, and enhanced return operations lists. Phase 10 is an integration and security audit: test matrix documentation, security hardening, and deployment readiness notes — see [docs/PHASE10_REPORT.md](docs/PHASE10_REPORT.md). Phase 11 (v0.11.0) adds Docker full-stack deployment, nginx API proxy, persistent volumes, and GitHub release docs — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/PHASE11_REPORT.md](docs/PHASE11_REPORT.md).

## Architecture

```text
Browser (React, TypeScript, Vite, Tailwind)
        |  sessionStorage: access token and selected store id
        |  Authorization: Bearer, X-Store-ID, X-Request-ID
        v
   nginx (Docker full stack)  OR  direct http://localhost:8000 (Vite dev)
        |
FastAPI (Python 3.12)
        |-- PostgreSQL 16   users, stores, orders, returns, knowledge, fulfillment, analytics
        |-- Redis 7         access-token allowlist and auth rate limits
        |-- Volumes       knowledge uploads, Chroma indexes (Docker / data/)
```

The API process can start when PostgreSQL or Redis is down. `GET /api/v1/health` only proves the process is alive. `GET /api/v1/ready` returns 200 when both dependencies answer and 503 when either does not. Dependency failures report an exception type, not a connection string. Authenticated routes fail closed if Redis cannot confirm the token.

### Backend modules

| Module | Responsibility |
| --- | --- |
| `app/core` | Settings, structured logging, error and response envelopes |
| `app/api` | Versioned routes, dependencies, exception handlers |
| `app/database` | Async SQLAlchemy engine and Redis client lifecycle |
| `app/models` | Users, stores, memberships, and append-only audit logs |
| `app/schemas` | Auth, store, membership, and audit payloads |
| `app/services` | Readiness, registration, sessions, stores, and audit writes |
| `app/repositories` | User, store, membership, and audit queries |
| `app/middleware` | Request ids and access logs. Query strings are omitted |
| `alembic` | `0001_baseline` through `0008_fulfillment` |
| `tests` | Foundation tests plus auth, token, role, and tenant checks |

### Frontend modules

| Module | Responsibility |
| --- | --- |
| `components` | Reusable controls, navigation, and status presentation |
| `layouts` | Responsive application shell |
| `pages` | Auth, orders, returns, knowledge center, return queue, profile, members, audit, and foundation screens |
| `services` | Axios client, session storage, and account API |
| `hooks` | Auth state, platform status, local preferences, responsive behavior |
| `types` | API, health, and account payloads |
| `utils` | Class names and display formatting |

### API envelope

Success:

```json
{"success": true, "data": {}, "request_id": "..."}
```

Failure:

```json
{"success": false, "error": {"code": "...", "message": "..."}, "request_id": "..."}
```

Send `X-Request-ID` to correlate a call. The API keeps safe characters and generates an id otherwise. The same id is returned in the header and the body.

## Authentication

Registration and login return a signed access token. The token carries the user id, a token id, and an expiry. It does not carry a store id or a role. Redis stores `auth:session:{token id}` until logout or expiry. A token that is signed but missing from Redis is rejected.

Passwords are hashed with Argon2. Login and registration are rate limited per client address. Failed login uses the same response for an unknown email and a wrong password.

`X-Store-ID` selects among the caller's memberships. The API ignores a store id unless that user is a member. Store queries use the membership loaded on the server. Roles are `OWNER`, `ADMIN`, `MANAGER`, `SUPPORT_AGENT`, and `CUSTOMER`. Permissions are derived from the role in code.

Set `JWT_SECRET` to a unique value of at least 32 characters. Production rejects a missing, short, or placeholder secret. The browser keeps the access token in `sessionStorage` and clears it on logout or when a protected call returns `token_expired` or `not_authenticated`.

## Prerequisites

- Python 3.12
- Node.js 22 or newer
- Docker with Compose v2

## Setup

From `C:\AI-Projects\ReturnFlow`:

```powershell
Copy-Item .env.example .env
```

Edit `.env`. Set `POSTGRES_PASSWORD`, and use that same password in `DATABASE_URL`. The checked-in default `change-me` is a placeholder and will not authenticate.

Run Alembic from `backend` with the `alembic` console script. `python -m alembic` imports the local `backend/alembic` migration package instead of the installed tool.

The API reads the repository-root `.env`. Frontend URLs are public local defaults:

```powershell
Copy-Item frontend\.env.example frontend\.env.local
```

`frontend/.env.local` is gitignored. `npm run dev` and `npm run build` also fall back to `http://localhost:8000` when the variable is absent.

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
```

### Frontend

```powershell
cd frontend
npm install
npm run build
```

### PostgreSQL and Redis

From the repository root, after `.env` exists:

```powershell
docker compose up -d
docker compose ps
```

Apply the migrations and start the API:

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Live dependency test, in another shell:

```powershell
cd backend
$env:RUN_INTEGRATION = "1"
.\.venv\Scripts\python -m pytest -m integration
```

Start the client:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Sign in, create a store, and use the dashboard (live analytics), orders, returns, knowledge, and policy assistant.

## Features (summary)

| Area | What it does |
| --- | --- |
| Auth & tenancy | JWT sessions, store membership, RBAC |
| Returns | Lifecycle, queue, eligibility, AI review, mock fulfillment |
| Knowledge & RAG | Upload policies, Chroma search, grounded chat |
| Analytics | Admin KPIs/charts and customer dashboard |
| Security | Tenant isolation, audit log, rate-limited auth |

Default AI and fulfillment integrations are **mock** unless you configure Gemini and real providers yourself.

## Docker

**Infrastructure only** (local `uvicorn` + `npm run dev`):

```powershell
docker compose up -d postgres redis
```

**Full stack** (API + SPA + migrations on start + persistent knowledge/Chroma):

```powershell
docker compose --profile full build
docker compose --profile full up -d
```

| URL | Purpose |
| --- | --- |
| http://localhost:8080 | Web UI (nginx → API `/api/*`) |
| http://localhost:8000/api/v1/health | Liveness |
| http://localhost:8000/api/v1/ready | Postgres + Redis |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for volumes, env overrides, smoke tests, and production notes. Build images manually if needed: `docker build -t returnflow-api ./backend` and `docker build -t returnflow-web ./frontend` (Compose uses the same Dockerfiles).

## Environment variables

Copy `.env.example` to `.env`. Never commit `.env`. Key values: `JWT_SECRET` (≥32 chars), `POSTGRES_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS`, `LLM_PROVIDER`, `RAG_EMBEDDINGS_PROVIDER`, optional `GEMINI_API_KEY`.

## Screenshots

Add UI captures under `docs/screenshots/` after you run the smoke checklist in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The repository does not ship screenshots by default.

## Limitations

- Mock refund and shipping; no outbound email  
- Policy chat and AI review use mock LLM by default (`LLM_PROVIDER=mock`)  
- No frontend E2E test suite in CI  
- Live Gemini / sentence-transformers require extra setup and are optional  

## Useful endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service name and probe links |
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/ready` | PostgreSQL and Redis readiness |
| GET | `/api/docs` | OpenAPI UI outside production |
| POST | `/api/v1/auth/register` | Create an account and a session |
| POST | `/api/v1/auth/login` | Sign in |
| POST | `/api/v1/auth/logout` | Invalidate the current access token |
| GET | `/api/v1/auth/me` | Current user and memberships |
| GET, PATCH | `/api/v1/profile` | Account display name |
| GET, POST | `/api/v1/stores` | List memberships or create a store |
| GET, PATCH | `/api/v1/stores/current` | Read or rename the selected store |
| GET, POST | `/api/v1/stores/current/members` | List or add members |
| PATCH, DELETE | `/api/v1/stores/current/members/{id}` | Change a role or remove a member |
| GET | `/api/v1/stores/current/audit` | Store-scoped security events |
| GET | `/api/v1/stores/current/orders` | Paginated store or own orders |
| GET | `/api/v1/stores/current/orders/search` | Search by order number or customer |
| GET | `/api/v1/stores/current/orders/{id}` | Order detail and lines |
| GET, POST | `/api/v1/stores/current/returns` | List or create return requests |
| GET | `/api/v1/stores/current/returns/queue` | Open returns for staff |
| PATCH | `/api/v1/stores/current/returns/{id}/status` | Validated status change |
| POST | `/api/v1/stores/current/dev/sample-commerce` | Labeled dev sample data only |
| GET, POST | `/api/v1/stores/current/knowledge/documents` | List or upload policy documents |
| GET, DELETE | `/api/v1/stores/current/knowledge/documents/{id}` | Document detail or delete |
| POST | `/api/v1/stores/current/knowledge/documents/{id}/reprocess` | Re-run text extraction |
| POST | `/api/v1/stores/current/knowledge/rag/index` | Index or reindex documents into Chroma |
| POST | `/api/v1/stores/current/knowledge/rag/reindex` | Reindex all processed documents |
| DELETE | `/api/v1/stores/current/knowledge/rag/index` | Drop vectors for store or one document |
| POST | `/api/v1/stores/current/knowledge/rag/search` | Semantic policy search |
| POST | `/api/v1/stores/current/knowledge/rag/ask` | Grounded policy Q&A with citations |
| GET | `/api/v1/stores/current/knowledge/rag/sources` | Source document metadata |
| POST | `/api/v1/stores/current/knowledge/rag/feedback` | Policy assistant feedback |
| POST | `/api/v1/stores/current/returns/eligibility/evaluate` | Deterministic eligibility check |
| GET | `/api/v1/stores/current/returns/eligibility/{id}` | Eligibility decision detail |
| POST | `/api/v1/stores/current/returns/eligibility/{id}/explain` | AI summary (non-binding) |
| POST | `/api/v1/stores/current/returns/eligibility/{id}/request-review` | Escalate to human review |
| GET, PUT | `/api/v1/stores/current/returns/policy-rules` | Read or publish rule versions |
| GET | `/api/v1/stores/current/returns/{id}/eligibility` | Latest decision for a return |
| POST | `/api/v1/stores/current/returns/{id}/ai-review` | Start LangGraph AI review |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/latest` | Latest review run |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}` | Review status |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}/events` | Agent event history |
| GET | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}/output` | Structured output |
| POST | `/api/v1/stores/current/returns/{id}/ai-review/runs/{run_id}/resume` | Human checkpoint |
| GET | `/api/v1/stores/current/returns/{id}/fulfillment` | Shipment, refund, timeline, notifications |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/label` | Request mock return label (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/shipment/in-transit` | Mark in transit (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/shipment/received` | Mark received (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/refund` | Initiate mock refund (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/refund/finalize` | Complete mock refund (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/exchange` | Start exchange fulfillment (`Idempotency-Key`) |
| POST | `/api/v1/stores/current/returns/{id}/fulfillment/complete` | Close return case |
| GET | `/api/v1/stores/current/analytics/admin` | Store KPIs and charts (`days` query) |
| GET | `/api/v1/stores/current/analytics/me` | Customer dashboard metrics |

Production mode (`APP_ENV=production`) disables the API docs, rejects `DEBUG=true`, rejects a short or placeholder `JWT_SECRET`, and blocks the sample-commerce helper.

## Tests

`pytest` covers settings, health, request ids, CORS, error envelopes, logging, mocked probes, and the auth suite. The auth tests use PostgreSQL database `returnflow_test` and Redis database 15. Create that database, run `alembic upgrade head` against it, and keep Compose running before `pytest`. Redis database 0 is not flushed.

`RUN_INTEGRATION=1 pytest -m integration` checks a real `SELECT 1` and `PING` after Compose is healthy.

Phase reports: [docs/PHASE1_REPORT.md](docs/PHASE1_REPORT.md) through [docs/PHASE11_REPORT.md](docs/PHASE11_REPORT.md).  
Release checklist: [docs/GITHUB_RELEASE_CHECKLIST.md](docs/GITHUB_RELEASE_CHECKLIST.md).

## Deployment readiness

- Run `pytest` with Docker Postgres/Redis and migrated `returnflow_test` (see Phase 10 report).
- Configure production `JWT_SECRET`, `CORS_ORIGINS`, and database credentials.
- Frontend: `npm run build`; full stack: `docker compose --profile full up -d`.
=======
# 🔄 ReturnFlow
## AI-Powered E-Commerce Returns & Refund Management Platform

ReturnFlow is an AI-powered e-commerce returns and refund management platform designed to simplify and automate the product return lifecycle using **Artificial Intelligence, Retrieval-Augmented Generation (RAG), and Multi-Agent Orchestration**.

The platform provides a centralized environment where customers can submit return requests, check order eligibility, understand store-specific return policies, and track return progress. Administrators can review AI-generated recommendations, manage return requests, and monitor return operations through an administrative dashboard.

ReturnFlow combines deterministic business rules with Generative AI to deliver transparent, context-aware, and efficient return management.

The project includes a customer portal, administrator portal, automated eligibility engine, document-based policy knowledge base, RAG-powered policy assistant, and LangGraph multi-agent review workflow.

---

# 🌟 What Makes This Project Unique

- Hybrid Rule-Based + AI-Assisted Return Evaluation
- Automated Return Eligibility Checking
- Store-Specific Return Policy Knowledge Base
- Retrieval-Augmented Generation (RAG)
- LangGraph Multi-Agent Workflow
- Explainable AI Return Recommendations
- PDF and Document-Based Policy Ingestion
- Customer Order and Return Management
- AI-Assisted Return Request Review
- Simulated Refund Processing
- Return Shipment Tracking Workflow
- Multi-Store Data Isolation
- Centralized Admin Dashboard
- Role-Based Authentication and Authorization
- Audit Logging and Operational Analytics

---

# 🎯 Problem Statement

E-commerce platforms frequently handle large volumes of product returns and refund requests. Managing these requests manually can create several operational challenges.

Common challenges include:

- Different return policies across stores.
- Complex return eligibility conditions.
- Manual verification of return requests.
- Difficulty accessing relevant policy information.
- Delays in return and refund processing.
- Lack of transparency in return decisions.
- High administrative workload.
- Inconsistent customer support responses.

ReturnFlow addresses these challenges through a centralized platform that combines automated eligibility validation, document-based policy retrieval, AI-assisted request analysis, and structured return workflows.

The goal is to make the returns process more transparent, efficient, and manageable for both customers and administrators.

---

# 🚀 Core Features

## 👤 Customer Portal

Customers can access a centralized dashboard to manage their orders and return requests.

### Features

- View available orders.
- Access order details.
- Submit product return requests.
- Select return reasons.
- Provide additional return descriptions.
- Check return eligibility.
- View return request status.
- Track return progress.
- Access refund information.
- Ask questions about store return policies.

The customer portal provides a simplified interface for managing the complete return request lifecycle.

## 📋 Automated Return Eligibility Engine

The Return Eligibility Engine evaluates whether an order or product satisfies predefined return conditions.

### Eligibility Conditions

- Order purchase date.
- Return window.
- Order status.
- Product category.
- Product eligibility.
- Store-specific return conditions.
- Previous return conditions, where supported.

### Evaluation Workflow

```text
Customer Order
      ↓
Return Request
      ↓
Retrieve Order Details
      ↓
Check Return Conditions
      ↓
Evaluate Store Policies
      ↓
Eligibility Result
      ↓
Display Result and Explanation
```

The eligibility engine uses deterministic business rules for consistent and predictable evaluation.

AI recommendations do not override the eligibility engine.

## 🤖 AI-Powered Return Review

ReturnFlow uses AI to assist administrators in understanding and reviewing customer return requests.

### AI Review Capabilities

- Summarize customer return requests.
- Understand return reasons.
- Retrieve relevant store policies.
- Analyze eligibility results.
- Recommend possible resolutions.
- Identify missing information.
- Generate structured review summaries.

AI-generated recommendations are presented for administrator review.

## 🧠 Retrieval-Augmented Generation (RAG)

The RAG engine allows customers and administrators to retrieve relevant information from store-specific return policy documents.

### Knowledge Base Features

- PDF policy document ingestion.
- Document processing and text extraction.
- Text chunking.
- Embedding generation.
- Semantic similarity search.
- Vector-based information retrieval.
- Context-aware AI responses.
- Store-specific knowledge isolation.

### RAG Workflow

```text
Return Policy Documents
          ↓
     PDF Extraction
          ↓
      Text Chunking
          ↓
   Embedding Generation
          ↓
       ChromaDB
          ↓
     Semantic Search
          ↓
   Retrieve Relevant Context
          ↓
       Gemini API
          ↓
    Contextual Response
```

The RAG system uses retrieved policy information to generate more relevant and context-aware answers.

## 📚 Store-Specific Knowledge Base

Each store maintains its own return policy knowledge base.

Administrators can upload policy documents that provide information about:

- Return eligibility conditions.
- Return time limits.
- Refund policies.
- Product-specific restrictions.
- Exchange conditions.
- Required supporting information.
- Return and shipping instructions.

The knowledge retrieval process is designed to respect store-level data isolation.

## 💬 AI Policy Assistant

The AI Policy Assistant helps customers understand return policies through natural-language conversations.

### Features

- Ask questions about return policies.
- Retrieve relevant policy information.
- Provide context-aware responses.
- Explain return conditions.
- Answer store-specific policy questions.
- Use uploaded PDF policy documents as knowledge sources.

The assistant provides policy information and does not independently authorize returns or refunds.

## 🔄 LangGraph Multi-Agent Workflow

ReturnFlow uses LangGraph to coordinate specialized AI agents for structured return request analysis.

### Agent Responsibilities

| Agent | Responsibility |
|---|---|
| Intake Agent | Understands and summarizes the customer request |
| Policy Research Agent | Retrieves relevant policy information |
| Eligibility Agent | Evaluates the deterministic eligibility result |
| Resolution Agent | Recommends possible return resolutions |
| Review Agent | Checks consistency and missing information |
| Finalization Agent | Prepares the final review for administrator approval |

### Multi-Agent Workflow

```text
Customer Return Request
          ↓
      Intake Agent
          ↓
   Policy Research Agent
          ↓
     Eligibility Agent
          ↓
     Resolution Agent
          ↓
       Review Agent
          ↓
    Finalization Agent
          ↓
    Admin Review
          ↓
    Human Approval
```

The multi-agent workflow assists administrators with structured analysis rather than independently executing business-critical operations.

## 💰 Refund Management

The platform includes a simulated refund management workflow.

### Features

- Display refund information.
- Track refund status.
- Associate refunds with return requests.
- Update simulated refund progress.
- Maintain return and refund history.

Actual payment gateway integration is not enabled by default.

## 🚚 Return Shipment Tracking

ReturnFlow supports a simulated return shipment workflow.

### Features

- Return shipment initiation workflow.
- Shipment status tracking.
- Return progress updates.
- Shipment information associated with return requests.

Real-time courier and carrier integrations are not enabled by default.

## 📊 Administrator Dashboard

Administrators can manage and monitor return operations through a centralized dashboard.

### Features

- Overview of return requests.
- Review pending requests.
- View customer order information.
- Review AI-generated recommendations.
- Access relevant policy information.
- Manage return request statuses.
- Monitor refund workflows.
- Monitor return shipment workflows.
- View operational analytics.
- Manage store-specific policy documents.

Administrative permissions are controlled through role-based access control.

## 🏢 Multi-Store Architecture

ReturnFlow supports a multi-store application architecture.

Each store maintains logically isolated operational data and policy knowledge.

### Store-Level Isolation

- Store-specific orders.
- Store-specific return requests.
- Store-specific return policies.
- Store-specific knowledge retrieval.
- Store-level administrative permissions.

This architecture helps prevent unauthorized access to information belonging to other stores.

---

# 🧠 AI & RAG Architecture

ReturnFlow follows a hybrid architecture that combines deterministic business logic with Generative AI.

```text
             Customer Request
                    |
                    ↓
            FastAPI Backend
                    |
          ┌─────────┴─────────┐
          ↓                   ↓
    Eligibility Engine     RAG Engine
          |                   |
          ↓                   ↓
    Business Rules        LangChain
          |                   |
          ↓                   ↓
    Eligibility Result    ChromaDB
          |                   |
          |              Policy Documents
          |                   |
          └─────────┬─────────┘
                    ↓
                Gemini API
                    ↓
             LangGraph Agents
                    ↓
             AI Recommendations
                    ↓
              Admin Review
                    ↓
             Human Approval
```

### Important Architecture Principle

The eligibility engine remains responsible for deterministic return validation.

The RAG system retrieves relevant policy information, while AI agents assist with contextual analysis and recommendations.

AI agents cannot independently approve or execute real refunds.

---

# 🏗️ System Architecture

The project follows a layered web application architecture.

```text
┌──────────────────────────────────────────────┐
│              PRESENTATION LAYER              │
│                                              │
│              React + TypeScript              │
│                                              │
│       Customer Portal | Admin Portal         │
└──────────────────────┬───────────────────────┘
                       │
                       │ REST API
                       ↓
┌──────────────────────────────────────────────┐
│               APPLICATION LAYER              │
│                                              │
│                  FastAPI                     │
│                                              │
│ Authentication and Authorization             │
│ Order Management                             │
│ Return Management                            │
│ Eligibility Validation                       │
│ Refund Workflow                              │
│ Shipment Workflow                            │
│ RAG Services                                 │
│ AI Agent Orchestration                       │
│ Admin Analytics                              │
└──────────────────────┬───────────────────────┘
                       │
                       ↓
┌──────────────────────────────────────────────┐
│                INTELLIGENCE LAYER             │
│                                              │
│             LangChain + Gemini               │
│                                              │
│ Return Eligibility Engine                    │
│ Policy Retrieval Engine                      │
│ ChromaDB Vector Search                       │
│ LangGraph Multi-Agent Workflow               │
│ AI Review and Recommendations                │
└──────────────────────┬───────────────────────┘
                       │
                       ↓
┌──────────────────────────────────────────────┐
│                   DATA LAYER                  │
│                                              │
│                 PostgreSQL                   │
│                   Redis                      │
│                  ChromaDB                    │
│                                              │
│ Orders | Returns | Refunds | Policies        │
│ Users | Stores | Audit Logs                  │
└──────────────────────────────────────────────┘
```

---

# 🖥️ Presentation Layer

The frontend provides the customer and administrator interfaces.

### Customer Portal

- Customer dashboard.
- Order listing.
- Order details.
- Return request submission.
- Eligibility results.
- Return tracking.
- Refund information.
- AI Policy Assistant.

### Administrator Portal

- Admin dashboard.
- Return request management.
- AI review interface.
- Policy document management.
- Refund management.
- Shipment workflow monitoring.
- Analytics and reports.

### Technologies

- React
- TypeScript
- Vite
- Tailwind CSS

---

# ⚙️ Application Layer

The FastAPI backend acts as the central communication layer between the frontend, database, eligibility engine, and AI services.

### Backend Responsibilities

- User authentication.
- Role-based authorization.
- Store management.
- Order management.
- Return request management.
- Eligibility validation.
- Refund workflow management.
- Shipment workflow management.
- Document uploads.
- Policy knowledge retrieval.
- AI assistant integration.
- LangGraph workflow execution.
- Administrative analytics.
- Audit logging.

---

# 🧠 Intelligence Layer

The intelligence layer combines traditional backend logic with Generative AI.

### Components

**1. Return Eligibility Engine**

Evaluates predefined business conditions and determines whether a return request satisfies the configured eligibility rules.

**2. RAG Engine**

Retrieves relevant information from uploaded return policy documents using semantic search.

**3. AI Review Engine**

Analyzes customer requests and generates structured recommendations.

**4. LangGraph Agent Orchestration**

Coordinates specialized agents through a structured review workflow.

**5. Resolution Recommendation**

Provides possible resolutions based on eligibility results, retrieved policies, and customer request information.

---

# 🗄️ Data Layer

ReturnFlow uses multiple storage technologies for application data and AI knowledge retrieval.

### PostgreSQL

Stores structured application information:

- Users.
- Stores.
- Orders.
- Products.
- Return requests.
- Eligibility results.
- Refund records.
- Shipment records.
- Policy metadata.
- Audit logs.

### Redis

Used for caching and supporting backend operations.

### ChromaDB

Stores and retrieves policy document embeddings for semantic search.

### Document Storage

Uploaded policy documents provide the source material for the RAG knowledge base.

---

# 🔄 Complete System Flow

## 1. Authentication Flow

```text
User Opens Application
          ↓
      Login Page
          ↓
  Authentication Request
          ↓
     FastAPI Backend
          ↓
       Validate User
          ↓
   Generate JWT Token
          ↓
     Role Validation
          ↓
     ┌────┴────┐
     ↓         ↓
 Customer     Admin
 Portal       Portal
```

## 2. Customer Return Flow

```text
Customer Dashboard
          ↓
       View Orders
          ↓
     Select an Order
          ↓
    Submit Return Request
          ↓
   Return Eligibility Engine
          ↓
    Validate Business Rules
          ↓
     Eligibility Result
          ↓
     AI-Assisted Review
          ↓
    Administrator Review
          ↓
       Human Approval
          ↓
   Return Workflow Update
          ↓
   Refund / Shipment Simulation
          ↓
     Updated Return Status
```

## 3. RAG Policy Assistant Flow

```text
Administrator Uploads Policy
             ↓
       PDF Processing
             ↓
        Text Extraction
             ↓
         Text Chunking
             ↓
      Embedding Generation
             ↓
           ChromaDB
             ↓
      Customer Asks Question
             ↓
        Semantic Search
             ↓
    Retrieve Relevant Chunks
             ↓
        Gemini API
             ↓
     Contextual AI Response
```

## 4. Multi-Agent Review Flow

```text
Return Request
      ↓
  Intake Agent
      ↓
Policy Research Agent
      ↓
 Eligibility Agent
      ↓
 Resolution Agent
      ↓
   Review Agent
      ↓
Finalization Agent
      ↓
 Administrator Review
      ↓
  Human Approval
```

## 5. Refund Workflow

```text
Approved Return
       ↓
Refund Workflow Initiated
       ↓
Refund Record Created
       ↓
Simulated Processing
       ↓
Refund Status Updated
       ↓
Customer Dashboard Updated
```

---

# 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React, TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Caching | Redis |
| AI Model | Google Gemini API |
| RAG Framework | LangChain |
| Vector Database | ChromaDB |
| Embeddings | Sentence Transformers |
| Agent Framework | LangGraph |
| Authentication | JWT |
| Password Security | Argon2 |
| Testing | Pytest |
| Deployment | Docker, Docker Compose |
| Web Server | Nginx |

---

# 📁 Project Structure

The application is organized into frontend, backend, AI services, and deployment components.

```text
ReturnFlow/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── contexts/
│   │   ├── routes/
│   │   └── App.tsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── rag/
│   │   ├── workflows/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   └── requirements.txt
│
├── knowledge_base/
│   └── policies/
│
├── docker/
│
├── nginx/
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── README.md
```

*Note: This is a representative structure. Adjust folder names to match the actual repository.*

---

# ⚙️ Installation & Setup

## Prerequisites

Install the following tools:

- Python 3.11+
- Node.js and npm
- PostgreSQL
- Redis
- Docker Desktop
- Git
- Google Gemini API Key

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ReturnFlow.git

cd ReturnFlow
```

## 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the required application credentials and services.

Example:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/returnflow

REDIS_URL=redis://localhost:6379/0

GEMINI_API_KEY=your_gemini_api_key

JWT_SECRET_KEY=your_secure_secret_key
```

Refer to `.env.example` for all supported configuration options.

## 3. Build Docker Containers

```bash
docker compose --profile full build
```

## 4. Start the Application

```bash
docker compose --profile full up -d
```

## 5. Access the Application

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:8080/api/v1 |
| Swagger Documentation | http://localhost:8080/docs |

---

# 🧪 Testing & Validation

### Backend Testing

```bash
pytest -v
```

### Frontend Build

```bash
cd frontend

npm install

npm run build
```

Testing helps validate API functionality, eligibility logic, authentication, and application behavior.

---

# 🐳 Docker Management

| Operation | Command |
|---|---|
| Build services | `docker compose --profile full build` |
| Start services | `docker compose --profile full up -d` |
| Stop services | `docker compose --profile full down` |
| View containers | `docker compose ps` |
| View logs | `docker compose logs -f` |
| Restart services | `docker compose --profile full restart` |

---

# 🔐 Security & Data Protection

ReturnFlow incorporates multiple security mechanisms:

- **JWT Authentication:** Token-based authentication.
- **Argon2 Password Hashing:** Secure password storage.
- **Role-Based Access Control:** Customer and administrator permissions.
- **Multi-Store Data Isolation:** Store-level access separation.
- **Input Validation:** Validation of API requests.
- **File Upload Validation:** Validation of uploaded policy documents.
- **Rate Limiting:** Protection against excessive API requests.
- **Audit Logging:** Tracking important application activities.
- **Environment-Based Secrets:** Sensitive configuration stored outside source code.

---

# 🧪 Testing Strategy

The project uses Pytest for backend testing and frontend build validation.

Testing areas include:

- Authentication and authorization.
- Customer and administrator permissions.
- Order management.
- Return request submission.
- Eligibility validation.
- Store-level data isolation.
- Policy document processing.
- RAG retrieval.
- AI review workflow.
- LangGraph agent orchestration.
- Refund workflow.
- Shipment tracking workflow.
- API validation and error handling.

---

# 👨‍💻 Project

**ReturnFlow – AI-Powered E-Commerce Returns & Refund Management Platform**

---

**Project Goal:** Build an intelligent, scalable, and transparent e-commerce returns management platform using modern software engineering and AI technologies.
>>>>>>> 69fa73d8c4e2b38510869f39314f1fb5afcdec5d
