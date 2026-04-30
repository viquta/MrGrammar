# Architecture Overview
This architecture overview has current and depricated notes, which need to be updated. I will need to review the code and do this properly for version 0.0.8.
## 1. System Purpose

**MrGrammar** is a pedagogically driven grammar-feedback platform for German-language learners. It addresses a core problem in language education: teachers cannot deliver ideal corrective feedback — highlight → hint → answer with explanation — to large cohorts at scale. Unlike consumer tools such as Grammarly, MrGrammar enforces an **active-learning workflow** with three learner-facing phases: phase 1 analysis and grammatical-role highlighting, phase 2 second-try correction with hint unlock, and phase 3 third-try correction or gated answer reveal. The platform also provides teachers with longitudinal error-pattern analytics.

### Design Goals

| Goal | Description |
|------|-------------|
| **Active Learning** | Students must move through analyze → second try → third try / gated reveal instead of seeing the answer immediately. |
| **Scalable and Effective Feedback** | Automated low-level error detection (grammar, spelling, articles, prepositions, verb tense, punctuation) reduces teacher workload, while increasing learning efficiency. |
| **Longitudinal Tracking [still in progress, not functional as of 0.0.7]** | Error-pattern aggregation enables teachers to identify persistent weaknesses at the student and classroom level. |
| **Role-Based Access** | Three distinct roles — Student, Teacher, Admin — with fine-grained permission enforcement at the API layer. |
| **Extensible NLP Pipeline [work in progress as of 0.0.7]** | Pluggable error-detection backends allow future integration of additional NLP services beyond LanguageTool. |
| **Configurable Explanation Layer** | Final explanations are generated on demand through a local Ollama-hosted LLM so the reveal step can stay pedagogical rather than static. |

---

## 2. Technology Stack [this is from an older version, below 0.0.7]

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | SvelteKit | 2.57 | Single-page application framework |
| | Svelte | 5.55 | Reactive UI components |
| | Tailwind CSS | 4.2 | Utility-first CSS framework |
| | TypeScript | 6.0 | Type-safe frontend code |
| | Vite | 8.0 | Build tooling and dev server |
| **Backend** | Django | 6.0 | Web framework and ORM |
| | Django REST Framework (DRF) | 3.17 | RESTful API layer |
| | SimpleJWT | 5.5 | JSON Web Token authentication |
| | Celery | 5.3 | Background job execution for async submission analysis |
| | django-cors-headers | — | Cross-origin request support |
| **NLP** | LanguageTool | self-hosted | Grammar and spell checking (German) |
| | spaCy | 3.8 | Text cleaning, sentence splitting, POS tagging, OOV spell detection |
| | `de_core_news_md` | 3.8 | German spaCy model (~40 MB) with word vectors, POS, NER |
| | Ollama + Gemma 4 26B | local network | On-demand final explanation generation for phase 3 reveals |
| | RapidFuzz / Levenshtein | — | Fuzzy string matching for correction validation and spell suggestions |
| **Database** | PostgreSQL | 16 | Relational data persistence |
| **Cache / Queue** | Redis | 7 | Django cache, Celery broker, and Celery result backend |
| **Infrastructure** | Docker Compose | — | Multi-container orchestration |
| | Node 22 (Alpine) | — | Frontend container runtime |
| | Python 3.12 (Slim) | — | Backend container runtime |

---

## 3. Layered Architecture [this is from an older version, below 0.0.7]

The system follows a four-layer architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│            SvelteKit SPA (Browser, port 5173)            │
│ Routes: /, /login, /register, /submissions, /submissions/:id, /progress │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP / JSON (REST)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   API Gateway Layer                      │
│           Django REST Framework Views (port 8000)        │
│     URL Routing · Serialization · Permission Checks      │
│  /api/auth/ · /api/classrooms/ · /api/submissions/       │
│  /api/feedback/ · /api/nlp/ · /api/analytics/            │
└────────────────────────┬────────────────────────────────┘
                         │  queue jobs / call services
            ┌────────────┴────────────┐
            ▼                         ▼
┌──────────────────────────────┐  ┌────────────────────────┐
│     Async Worker Layer       │  │     Service Layer      │
│  Celery worker + beat        │  │  CorrectionWorkflow... │
│  analyze_submission_async    │  │  ErrorDetectionService │
│  analytics recomputation     │  │  AnalyticsService      │
└──────────────┬───────────────┘  └───────────┬────────────┘
               │ Redis broker/result          │ ORM / cache / HTTP
               ▼                              ▼
┌──────────────────────────────┐  ┌─────────────────────────────┐
│   Data / Queue Layer         │  │   External Services         │
│ PostgreSQL 16 + Redis 7      │  │ LanguageTool REST API       │
│ submissions, errors, cache,  │  │ Ollama REST API             │
│ task state                   │  │ (configured host)           │
└──────────────────────────────┘  └─────────────────────────────┘
```

### Layer Responsibilities

**Presentation Layer** — The SvelteKit single-page application handles routing, form rendering, authentication state management (JWT tokens in `localStorage`), and the interactive correction UI. The currently implemented routes are `/`, `/login`, `/register`, `/submissions`, `/submissions/[id]`, and `/progress`. The submission detail page is phase-led: phase 1 shows grammatical-role highlights, phase 2 collects the learner's second try, and phase 3 supports the final retry or gated answer reveal. Submission analysis is now asynchronous: the frontend queues analysis, polls the status endpoint every 500 ms, and renders errors once the submission reaches `in_review`.

**API Gateway Layer** — DRF views handle HTTP request/response serialisation, input validation, and permission enforcement. Each Django app (`accounts`, `classrooms`, `submissions`, `feedback`, `nlp`, `analytics`) exposes its own URL namespace under `/api/`. Role-based permissions are enforced via custom permission classes. The NLP API now exposes both a queueing endpoint (`POST /api/nlp/submissions/{id}/analyze/`) and a polling endpoint (`GET /api/nlp/submissions/{id}/status/`).

**Service Layer** — Business logic is encapsulated in service classes that are independent of the HTTP layer. This includes the correction workflow (Levenshtein similarity checking, hint gating, answer reveal policy, and learner-facing phase metadata), NLP error detection (a multi-backend pipeline combining LanguageTool, spaCy, and bounded advanced German checks), on-demand explanation generation through Ollama, and analytics aggregation. The heavy NLP analysis path now runs in a Celery task so API requests can return quickly while workers perform the expensive detection pass in the background.

**Data Layer** — PostgreSQL stores all persistent state via Django's ORM. Redis is used alongside PostgreSQL for Django caching, the Celery broker, and the Celery result backend. The schema comprises seven models across five apps (see [Data Model](02-data-model.md)).

---

## 4. Role-Based Access Control

MrGrammar defines three user roles through a custom `User` model extending Django's `AbstractUser`:

| Role | Code | Capabilities |
|------|------|-------------|
| **Student** | `student` | Submit texts, view own submissions, attempt corrections, view own progress analytics |
| **Teacher** | `teacher` | Create/manage classrooms, add members, view classroom submissions, access classroom-level analytics |
| **Admin** | `admin` | Full access to all classrooms, submissions, and analytics |

### Custom Permission Classes

Permission enforcement is implemented in `accounts/permissions.py` as reusable DRF permission classes:

| Permission Class | Grants Access To |
|-----------------|-----------------|
| `IsStudent` | Users with `role = 'student'` |
| `IsTeacher` | Users with `role = 'teacher'` |
| `IsAdminUser` | Users with `role = 'admin'` |
| `IsTeacherOrAdmin` | Users with `role ∈ {'teacher', 'admin'}` |

Additionally, several views implement **queryset-level filtering** — for example, the submissions list view returns only the requesting student's own submissions, or all submissions in a teacher's classrooms, or the full set for admins.

---

## 5. Authentication Flow

Authentication uses **JSON Web Tokens (JWT)** via the `djangorestframework-simplejwt` library.

| Parameter | Value |
|-----------|-------|
| Access token lifetime | 15 minutes |
| Refresh token lifetime | 1 day |
| Rotate refresh tokens | Enabled |
| Blacklist after rotation | Disabled |

The frontend stores the access and refresh tokens in `localStorage`. Every API request includes the access token in the `Authorization: Bearer <token>` header. The backend exposes `/api/auth/token/refresh/`, but the current frontend client only injects the stored bearer token and does not yet implement automatic refresh-and-retry on `401 Unauthorized` responses.

---

## 6. Design Patterns

### Strategy Pattern — NLP Error Detection

The `ErrorDetectionService` in `nlp/services.py` accepts pluggable detector backends via the Strategy pattern. Two backends are always active, and a third bounded German detector is enabled when `MRGRAMMAR['ENABLE_ADVANCED_GERMAN_CHECKS']` is true. In the checked-in Docker Compose setup, that flag is enabled for the backend container.

1. **`LanguageToolClient`** — calls the self-hosted LanguageTool REST API for grammar rule-based detection. Supports per-sentence detection via `detect_by_sentences()`, where spaCy splits the text into sentences and each sentence is checked individually to avoid cross-sentence confusion.
2. **`SpacyGrammarDetector`** — uses the spaCy German model (`de_core_news_md`) to catch errors that LanguageTool misses, particularly out-of-vocabulary (OOV) misspellings common in learner German (e.g., "hauptjobb" → "Hauptjob") and missing noun capitalisation. Suggestions are generated via Levenshtein distance over the model's vector vocabulary.
3. **`AdvancedGermanGrammarDetector`** — adds bounded B1/B2-oriented checks for subordinate-clause word order, feminine noun-phrase agreement, and `würde` + infinitive patterns.

Both backends feed into a shared post-processing step where `SpacyTextProcessor` enriches each error with POS-based category overrides and linguistic context metadata.

```
ErrorDetectionService
    ├── analyze(submission) → List[DetectedError]
    ├── SpacyTextProcessor       (pre/post-processing)
    └── detectors: List[ErrorDetector]
            ├── LanguageToolClient            (grammar rules)
            │       └── detect_by_sentences() (spaCy sentence split)
            ├── SpacyGrammarDetector          (OOV, capitalisation)
            └── AdvancedGermanGrammarDetector (bounded German checks)
```

#### SpacyTextProcessor (`nlp/spacy_processor.py`)

Provides all spaCy operations used by the pipeline:

| Method | Purpose |
|--------|---------|
| `clean_text(text)` | Normalise Unicode (NFC), collapse whitespace, strip invisible characters |
| `make_doc(text)` | Create a spaCy `Doc` for POS/NER analysis |
| `split_sentences(text)` | Sentence tokenisation with character offsets mapped back to the original text |
| `categorize_error(…)` | Override LanguageTool's category using POS/morphology (DET→ARTICLE, ADP→PREPOSITION, VERB/AUX→VERB_TENSE) |
| `extract_error_context(…)` | Return surrounding POS tags, dependency relations, and named entities as a JSON dict |
| `get_pos_tag(doc, offset)` | Return the POS tag for the token at a character offset |

The spaCy model is loaded once via a thread-safe singleton (`_SpacyModelHolder`) to avoid reloading the ~40 MB model on every request.

The `LanguageToolClient` maps LanguageTool's internal rule categories to the application's seven error categories:

| LanguageTool Pattern | MrGrammar Category |
|---------------------|--------------------|
| `ARTICLE`, `DER_DIE_DAS` | `ARTICLE` |
| `PREPOSITION`, `PRAEP` | `PREPOSITION` |
| `TENSE`, `VERB` | `VERB_TENSE` |
| `GRAMMAR` | `GRAMMAR` |
| `TYPOS`, `SPELLING`, `CASING` | `SPELLING` |
| `PUNCTUATION`, `TYPOGRAPHY` | `PUNCTUATION` |
| (other) | `OTHER` |

### Phase-Led Guided Correction Workflow

The `CorrectionWorkflowService` in `feedback/services.py` implements a guided correction loop controlled by two `settings.MRGRAMMAR` configuration parameters plus one service constant. The backend stores correction attempts as a 1-based internal counter, while the frontend maps those attempts to the learner-facing second-try and third-try phases.

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `SIMILARITY_THRESHOLD` | 0.85 | Service constant in `CorrectionWorkflowService`; Levenshtein ratio above which an attempt is accepted as correct |
| `HINT_THRESHOLD` | 1 | Internal attempt number at which a hint is revealed and manual reveal becomes available |
| `MAX_CORRECTION_ATTEMPTS` | 2 | Internal attempt number at which the final answer and explanation are revealed |

The workflow proceeds as follows:

1. **Phase 1** — The NLP layer analyses the submission and the frontend renders grammatical-role highlights derived from stored error metadata.
2. **Phase 2 / internal attempt 1** — The learner submits the second try. If Levenshtein similarity ≥ 0.85, the error is resolved. Otherwise, the service returns the hint, unlocks phase 3, and allows gated manual reveal.
3. **Phase 3 / internal attempt 2** — The learner submits the third try. On success, the error is resolved. On failure, the service returns the hint, answer, and a short explanation, then marks the error as resolved.

After phase 2 has been failed once, the learner may use a separate gated reveal endpoint instead of typing the third try. That endpoint returns the hint, answer, and explanation and resolves the error without creating a new `CorrectionAttempt` row.

The final explanation text is generated on demand by `ExplanationGenerationService` in `feedback/explanations.py`, which calls the local-network Ollama host configured in `settings.MRGRAMMAR`.

### Role-Based Queryset Filtering

Views in `submissions` and `classrooms` dynamically filter querysets based on the authenticated user's role. This pattern centralises access control at the ORM level rather than relying solely on object-level permission checks:

- **Student** → `queryset.filter(student=request.user)`
- **Teacher** → `queryset.filter(classroom__memberships__user=request.user, classroom__memberships__role='teacher')`
- **Admin** → unfiltered queryset

---

## 7. Application Structure

The backend is organised into six Django apps, each with a focused domain responsibility:

| App | Domain | Key Components |
|-----|--------|---------------|
| `accounts` | Authentication & user management | Custom `User` model, JWT endpoints, role-based permissions |
| `classrooms` | Classroom & membership management | `Classroom`, `ClassroomMembership` models, member CRUD |
| `submissions` | Student text submissions | `TextSubmission` model with async analysis tracking |
| `feedback` | Error records, correction workflow, explanation integration | `DetectedError`, `CorrectionAttempt` models, `CorrectionWorkflowService`, `ExplanationGenerationService` |
| `nlp` | NLP error detection pipeline | `ErrorDetectionService`, `LanguageToolClient`, `SpacyGrammarDetector`, `SpacyTextProcessor`, `analyze_submission_async` |
| `analytics` | Progress tracking & statistics | `LearnerErrorSummary` model, `AnalyticsService`, Redis-backed cached views |

The frontend is a SvelteKit application with six implemented routes:

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Role-dependent landing page |
| `/login` | Login | JWT authentication form |
| `/register` | Registration | User creation with role selection |
| `/submissions` | Submission list | View all submissions with creation form |
| `/submissions/[id]` | Submission detail | Error-highlighted text with guided correction UI |
| `/progress` | Progress dashboard | Student analytics view |

Teacher-facing dashboard links for `/classrooms` and `/analytics` are present in the root page, but those frontend routes are still planned rather than implemented.

---

## 8. External Integrations

### LanguageTool

MrGrammar integrates with a **self-hosted LanguageTool instance** running as a Docker container. The NLP service calls the `/v2/check` endpoint with the submitted text and target language (`de`), then maps returned matches to `DetectedError` records.

| Property | Value |
|----------|-------|
| Endpoint | `POST /v2/check` |
| Container image | `erikvl87/languagetool` |
| Default port | `8010` |
| Request timeout | 30 seconds |
| JVM memory | 256 MB min, 512 MB max |

### Ollama

MrGrammar also integrates with an **Ollama host on the local network** for phase-3 explanation generation. The feedback layer sends a non-streaming generation request only when the learner reaches the final reveal path or uses the gated manual reveal action.

| Property | Value |
|----------|-------|
| Endpoint | `POST /api/generate` |
| Host | Configured via `OLLAMA_BASE_URL` |
| Model | `gemma4:26b` by default |
| Timeout | 15 seconds by default |
| Fallback | If Ollama is unavailable, the backend returns a deterministic explanation assembled from `hint_text` and `correct_solution` |

### PostgreSQL

The relational database stores all application state. Connection parameters are configurable via environment variables with sensible development defaults.

| Parameter | Default |
|-----------|---------|
| Database name | `mrgrammar` |
| User | `mrgrammar` |
| Password | Configured via `POSTGRES_PASSWORD` |
| Host | `localhost` (or `db` in Docker) |
| Port | `5432` |




Additional notes from gitnexus:
The **MrGrammar** project follows a distributed, multi-tier architecture designed for heavy-duty Natural Language Processing (NLP) tasks. It utilizes a decoupled frontend and backend, with an asynchronous task processing layer to handle computationally expensive grammar analysis.

### 🏗️ System Architecture Overview

![System Architecture](./diagrams/Architecture.svg)

---

### 🛠️ Component Breakdown

#### 1. Client Layer (Frontend)
*   **Technology**: [SvelteKit](https://kit.svelte.dev/) [[frontend/package.json]]
*   **Role**: Provides a reactive user interface for submitting text, viewing grammar corrections, and tracking analysis progress.
*   **Key Features**: Uses Svelte stores for authentication state [[frontend/src/lib/stores/auth.ts]] and communicates with the backend via a RESTful API [[frontend/src/api.ts]].

#### 2. API & Orchestration Layer (Backend)
*   **Technology**: [Django](https://www.djangoproject.com/) [[mrgrammar/settings.py]]
*   **Role**: Acts as the central orchestrator. It manages user authentication, handles API requests, manages the database schema, and dispatches heavy NLP tasks to the worker queue.
*   **Key Modules**:
    *   `accounts`: Handles user registration and permissions [[accounts/views.py]].
    *   `submissions`: Manages the lifecycle of text submissions and analysis tasks [[submissions/models.py]].
    *   `analytics`: Provides insights into usage and performance [[analytics/services.py]].

#### 3. Asynchronous Processing Layer
*   **Technology**: [Celery](https://docs.celeryq.dev/) & [Redis](https://redis.io/) [[docker-compose.yml]]
*   **Role**: Offloads long-running NLP computations from the request-response cycle to prevent API timeouts.
*   **Workflow**:
    1.  The Django API receives a submission and creates a task in **PostgreSQL**.
    2.  A task is pushed to **Redis** (the broker).
    3.  **Celery Workers** pick up the task, execute the NLP pipeline (Spacy, LanguageTool, or Ollama), and write the results back to the database.

#### 4. External Intelligence & NLP
*   **LanguageTool**: A rule-based engine used for deterministic grammar and style checking [[docker-compose.yml]].
*   **Ollama**: Provides Large Language Model (LLM) capabilities (e.g., `gemma4:26b`) for advanced semantic analysis and context-aware corrections [[docker-compose.py]].
*   **Spacy**: Used within the worker for tokenization, POS tagging, and linguistic feature extraction [[nlp/spacy_processor.py]].

#### 5. Data & Messaging Layer
*   **PostgreSQL**: The primary relational database for storing users, submissions, classroom data, and analysis results [[docker-compose.yml]].
*   **Redis**: Serves a dual purpose:
    1.  **Message Broker**: Facilitates communication between Django and Celery.
    2.  **Cache**: Stores transient data and session information to improve performance.

---

### 📊 Summary Table

| Layer | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Frontend** | SvelteKit | User Interface & Interaction |
| **API** | Django REST Framework | Request Handling & Orchestration |
| **Task Queue** | Celery | Asynchronous NLP Execution |
| **Database** | PostgreSQL | Persistent Data Storage |
| **Broker/Cache** | Redis | Task Distribution & Caching |
| **NLP Engine** | LanguageTool / Spacy | Rule-based Grammar Analysis |
| **Generative AI** | Ollama (LLM) | Semantic & Contextual Analysis |

**TL;DR**: The project is a **distributed micro-service architecture** using **Django** for the API, **SvelteKit** for the UI, and **Celery/Redis** for asynchronous processing of heavy NLP tasks powered by **LanguageTool** and **Ollama (LLM)**.