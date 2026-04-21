# Architecture Overview

## 1. System Purpose

**MrGrammar** is a pedagogically driven grammar-feedback platform for German-language learners. It addresses a core problem in language education: teachers cannot deliver ideal corrective feedback — highlight → hint → answer with explanation — to large cohorts at scale. Unlike consumer tools such as Grammarly, MrGrammar enforces an **active-learning workflow** with three learner-facing phases: phase 1 analysis and grammatical-role highlighting, phase 2 second-try correction with hint unlock, and phase 3 third-try correction or gated answer reveal. The platform also provides teachers with longitudinal error-pattern analytics.

### Design Goals

| Goal | Description |
|------|-------------|
| **Active Learning** | Students must move through analyze → second try → third try / gated reveal instead of seeing the answer immediately. |
| **Scalable Feedback** | Automated low-level error detection (grammar, spelling, articles, prepositions, verb tense, punctuation) reduces teacher workload. |
| **Longitudinal Tracking** | Error-pattern aggregation enables teachers to identify persistent weaknesses at the student and classroom level. |
| **Role-Based Access** | Three distinct roles — Student, Teacher, Admin — with fine-grained permission enforcement at the API layer. |
| **Extensible NLP Pipeline** | Pluggable error-detection backends allow future integration of additional NLP services beyond LanguageTool. |
| **Configurable Explanation Layer** | Final explanations are generated on demand through a local Ollama-hosted LLM so the reveal step can stay pedagogical rather than static. |

---

## 2. Technology Stack

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
| | django-cors-headers | — | Cross-origin request support |
| **NLP** | LanguageTool | self-hosted | Grammar and spell checking (German) |
| | spaCy | 3.8 | Text cleaning, sentence splitting, POS tagging, OOV spell detection |
| | `de_core_news_md` | 3.8 | German spaCy model (~40 MB) with word vectors, POS, NER |
| | Ollama + Gemma 4 26B | local network | On-demand final explanation generation for phase 3 reveals |
| | RapidFuzz / Levenshtein | — | Fuzzy string matching for correction validation and spell suggestions |
| **Database** | PostgreSQL | 16 | Relational data persistence |
| **Infrastructure** | Docker Compose | — | Multi-container orchestration |
| | Node 22 (Alpine) | — | Frontend container runtime |
| | Python 3.12 (Slim) | — | Backend container runtime |

---

## 3. Layered Architecture

The system follows a four-layer architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│            SvelteKit SPA (Browser, port 5173)            │
│    Routes: /, /login, /register, /submissions, /sub/:id  │
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
                         │  Python method calls
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                         │
│  CorrectionWorkflowService · ExplanationGenerationService│
│  ErrorDetectionService · LanguageToolClient              │
│  SpacyGrammarDetector · SpacyTextProcessor               │
│  AnalyticsService                                        │
│  (feedback/services.py, feedback/explanations.py,        │
│   nlp/services.py, nlp/spacy_processor.py,               │
│   analytics/services.py)                                 │
└───────────┬─────────────────────────────┬───────────────┘
            │  Django ORM                 │  HTTP
            ▼                             ▼
┌───────────────────────┐   ┌─────────────────────────────┐
│     Data Layer        │   │   External Services         │
│  PostgreSQL 16        │   │   LanguageTool REST API     │
│  (port 5432)          │   │   Ollama REST API           │
│                       │   │   (configured host)         │
└───────────────────────┘   └─────────────────────────────┘
```

### Layer Responsibilities

**Presentation Layer** — The SvelteKit single-page application handles routing, form rendering, authentication state management (JWT tokens in `localStorage`), and the interactive correction UI. The submission detail page is phase-led: phase 1 shows grammatical-role highlights, phase 2 collects the learner's second try, and phase 3 supports the final retry or gated answer reveal.

**API Gateway Layer** — DRF views handle HTTP request/response serialisation, input validation, and permission enforcement. Each Django app (`accounts`, `classrooms`, `submissions`, `feedback`, `nlp`, `analytics`) exposes its own URL namespace under `/api/`. Role-based permissions are enforced via custom permission classes.

**Service Layer** — Business logic is encapsulated in service classes that are independent of the HTTP layer. This includes the correction workflow (Levenshtein similarity checking, hint gating, answer reveal policy, and learner-facing phase metadata), NLP error detection (a dual-backend pipeline combining LanguageTool for grammar rules and spaCy for OOV spelling detection, POS-based error categorisation, and linguistic context extraction), on-demand explanation generation through Ollama, and analytics aggregation.

**Data Layer** — PostgreSQL stores all persistent state via Django's ORM. The schema comprises seven models across five apps (see [Data Model](02-data-model.md)).

---

## 4. Role-Based Access Control

MrGrammar defines three user roles through a custom `User` model extending Django's `AbstractUser`:

| Role | Code | Capabilities |
|------|------|-------------|
| **Student** | `STUDENT` | Submit texts, view own submissions, attempt corrections, view own progress analytics |
| **Teacher** | `TEACHER` | Create/manage classrooms, add members, view classroom submissions, access classroom-level analytics |
| **Admin** | `ADMIN` | Full access to all classrooms, submissions, and analytics |

### Custom Permission Classes

Permission enforcement is implemented in `accounts/permissions.py` as reusable DRF permission classes:

| Permission Class | Grants Access To |
|-----------------|-----------------|
| `IsStudent` | Users with `role = STUDENT` |
| `IsTeacher` | Users with `role = TEACHER` |
| `IsAdminUser` | Users with `role = ADMIN` |
| `IsTeacherOrAdmin` | Users with `role ∈ {TEACHER, ADMIN}` |

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

The frontend stores the access and refresh tokens in `localStorage`. Every API request includes the access token in the `Authorization: Bearer <token>` header. When an access token expires, the frontend obtains a new one via the `/api/auth/token/refresh/` endpoint.

---

## 6. Design Patterns

### Strategy Pattern — NLP Error Detection

The `ErrorDetectionService` in `nlp/services.py` accepts pluggable detector backends via the Strategy pattern. Two backends are active by default:

1. **`LanguageToolClient`** — calls the self-hosted LanguageTool REST API for grammar rule-based detection. Supports per-sentence detection via `detect_by_sentences()`, where spaCy splits the text into sentences and each sentence is checked individually to avoid cross-sentence confusion.
2. **`SpacyGrammarDetector`** — uses the spaCy German model (`de_core_news_md`) to catch errors that LanguageTool misses, particularly out-of-vocabulary (OOV) misspellings common in learner German (e.g., "hauptjobb" → "Hauptjob") and missing noun capitalisation. Suggestions are generated via Levenshtein distance over the model's vector vocabulary.

Both backends feed into a shared post-processing step where `SpacyTextProcessor` enriches each error with POS-based category overrides and linguistic context metadata.

```
ErrorDetectionService
    ├── analyze(submission) → List[DetectedError]
    ├── SpacyTextProcessor       (pre/post-processing)
    └── detectors: List[ErrorDetector]
            ├── LanguageToolClient         (grammar rules)
            │       └── detect_by_sentences()  (spaCy sentence split)
            └── SpacyGrammarDetector       (OOV, capitalisation)
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

The `CorrectionWorkflowService` in `feedback/services.py` implements a guided correction loop controlled by three configuration parameters. The backend stores correction attempts as a 1-based internal counter, while the frontend maps those attempts to the learner-facing second-try and third-try phases.

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `SIMILARITY_THRESHOLD` | 0.85 | Levenshtein ratio above which an attempt is accepted as correct |
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
- **Teacher** → `queryset.filter(classroom__memberships__user=request.user, classroom__memberships__role='TEACHER')`
- **Admin** → unfiltered queryset

---

## 7. Application Structure

The backend is organised into six Django apps, each with a focused domain responsibility:

| App | Domain | Key Components |
|-----|--------|---------------|
| `accounts` | Authentication & user management | Custom `User` model, JWT endpoints, role-based permissions |
| `classrooms` | Classroom & membership management | `Classroom`, `ClassroomMembership` models, member CRUD |
| `submissions` | Student text submissions | `TextSubmission` model with status workflow |
| `feedback` | Error records, correction workflow, explanation integration | `DetectedError`, `CorrectionAttempt` models, `CorrectionWorkflowService`, `ExplanationGenerationService` |
| `nlp` | NLP error detection pipeline | `ErrorDetectionService`, `LanguageToolClient`, `SpacyGrammarDetector`, `SpacyTextProcessor` |
| `analytics` | Progress tracking & statistics | `LearnerErrorSummary` model, `AnalyticsService` |

The frontend is a SvelteKit application with five routes:

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Role-dependent landing page |
| `/login` | Login | JWT authentication form |
| `/register` | Registration | User creation with role selection |
| `/submissions` | Submission list | View all submissions with creation form |
| `/submissions/[id]` | Submission detail | Error-highlighted text with guided correction UI |

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
