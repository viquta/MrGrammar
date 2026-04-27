# Data Model

This document describes the persistent data model of MrGrammar. The system uses seven Django models across five applications, backed by a PostgreSQL 16 database. The custom user model is configured via `AUTH_USER_MODEL = 'accounts.User'`.

The learner workflow also exposes several **derived presentation fields** through DRF serializers, such as grammatical-role highlight groups and phase labels. Those values are not stored as database columns unless explicitly noted below.

> **UML Class Diagram**: Open [`diagrams/class-diagram.drawio`](diagrams/class-diagram.drawio) in the Draw.io VS Code extension or at [diagrams.net](https://app.diagrams.net) to view the full class diagram with associations and cardinalities.

---

## Table of Contents

1. [User](#1-user)
2. [Classroom](#2-classroom)
3. [ClassroomMembership](#3-classroommembership)
4. [TextSubmission](#4-textsubmission)
5. [DetectedError](#5-detectederror)
6. [CorrectionAttempt](#6-correctionattempt)
7. [LearnerErrorSummary](#7-learnererrorsummary)
8. [Enumerations](#8-enumerations)
9. [Relationship Summary](#9-relationship-summary)

---

## 1. User

**App**: `accounts` · **Table**: `accounts_user` · **Extends**: `django.contrib.auth.models.AbstractUser`

The custom user model adds a `role` field to Django's built-in user to distinguish students, teachers, and administrators.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `username` | String | Unique, max 150 | — | Login identifier |
| `email` | String | max 254 | — | Email address |
| `password` | String | hashed | — | Password (via `create_user()`) |
| `first_name` | String | max 150 | `''` | Given name |
| `last_name` | String | max 150 | `''` | Family name |
| `role` | String(10) | choices: `UserRole` | `student` | User role within the system |
| `is_active` | Boolean | — | `True` | Account active flag |
| `is_staff` | Boolean | — | `False` | Django admin access |
| `date_joined` | DateTime | auto | — | Registration timestamp |

### Properties & Methods

| Member | Returns | Description |
|--------|---------|-------------|
| `is_student` | Boolean | `True` if `role == 'student'` |
| `is_teacher` | Boolean | `True` if `role == 'teacher'` |
| `is_admin_user` | Boolean | `True` if `role == 'admin'` |
| `__str__()` | String | `"{full_name} ({role})"` |

### Ordering

`['last_name', 'first_name']`

---

## 2. Classroom

**App**: `classrooms` · **Table**: `classrooms_classroom`

Represents a teaching group. Each classroom is created by a teacher and can contain multiple students and teachers via `ClassroomMembership`.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `name` | String(200) | — | — | Classroom display name |
| `language` | String(10) | — | `'de'` | Target language for NLP analysis |
| `created_by` | FK → `User` | CASCADE | — | Teacher who created the classroom |
| `created_at` | DateTime | auto_now_add | — | Creation timestamp |

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `User` | `created_by` | `created_classrooms` | Many-to-One |
| `ClassroomMembership` | — | `memberships` | One-to-Many (reverse) |
| `TextSubmission` | — | `submissions` | One-to-Many (reverse) |

### Ordering

`['name']`

---

## 3. ClassroomMembership

**App**: `classrooms` · **Table**: `classrooms_classroommembership`

Association model that links users to classrooms with a specific role. Implements a many-to-many relationship between `User` and `Classroom` with additional metadata.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `user` | FK → `User` | CASCADE | — | Member user |
| `classroom` | FK → `Classroom` | CASCADE | — | Target classroom |
| `role` | String(10) | choices: `MembershipRole` | — | Role within this classroom |
| `joined_at` | DateTime | auto_now_add | — | Membership creation timestamp |

### Constraints

- **unique_together**: `[user, classroom]` — A user can only be a member of a classroom once.

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `User` | `user` | `classroom_memberships` | Many-to-One |
| `Classroom` | `classroom` | `memberships` | Many-to-One |

### Ordering

`['classroom', 'role', 'user']`

---

## 4. TextSubmission

**App**: `submissions` · **Table**: `submissions_textsubmission`

Represents a student's text submission within a classroom. The `status` field tracks the submission through its lifecycle. Async NLP analysis is queued via Celery and tracked on the model through `analysis_task_id`.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `student` | FK → `User` | CASCADE | — | Submitting student |
| `classroom` | FK → `Classroom` | CASCADE | — | Target classroom |
| `title` | String(300) | — | — | Submission title |
| `content` | Text | — | — | Full text body |
| `language` | String(10) | — | `'de'` | Text language for NLP |
| `status` | String(15) | choices: `SubmissionStatus` | `submitted` | Current lifecycle stage |
| `analysis_task_id` | String(255) | null/blank allowed | `null` | Celery task ID used by the polling endpoint while analysis is running |
| `submitted_at` | DateTime | auto_now_add | — | Submission timestamp |
| `updated_at` | DateTime | auto_now | — | Last modification timestamp |

### Status Workflow

```
submitted  →  analyzing  →  in_review  →  completed
   (new)      (Celery task running)  (analysis complete) (all errors resolved)
```

### Async Analysis Notes

- `in_review` is the terminal status for completed NLP analysis. It means the submission is ready for the learner-facing correction flow.
- `completed` is a later pedagogical state reached only after all detected errors have been resolved.
- `analysis_task_id` exists to support API-level task tracking and frontend polling; it is operational metadata rather than learner-facing domain data.

### Indexes

- Composite index on `['student', 'submitted_at']` to accelerate the student progress queries added for the analytics dashboard.

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `User` | `student` | `submissions` | Many-to-One |
| `Classroom` | `classroom` | `submissions` | Many-to-One |
| `DetectedError` | — | `errors` | One-to-Many (reverse) |
| `LearnerErrorSummary` | — | `error_summaries` | One-to-Many (reverse) |

### Ordering

`['-submitted_at']` (most recent first)

---

## 5. DetectedError

**App**: `feedback` · **Table**: `feedback_detectederror`

Represents a single error detected in a student's text by the NLP pipeline. Character offsets allow precise in-text highlighting. The `hint_text` and `correct_solution` fields support the phase-led correction workflow and are not exposed to the learner until the correction process reaches the appropriate phase.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `submission` | FK → `TextSubmission` | CASCADE | — | Parent submission |
| `error_category` | String(20) | choices: `ErrorCategory` | — | Classified error type |
| `severity` | String(10) | choices: `Severity` | `medium` | Error severity level |
| `start_offset` | Integer | ≥ 0 | — | Start character offset in `content` |
| `end_offset` | Integer | ≥ 0 | — | End character offset in `content` |
| `original_text` | Text | — | — | Erroneous text span |
| `hint_text` | Text | blank allowed | — | Pedagogical hint (from LanguageTool message) |
| `correct_solution` | Text | — | — | Correct replacement text |
| `languagetool_rule_id` | String(100) | blank allowed | — | LanguageTool rule identifier for traceability |
| `spacy_pos_tag` | String(20) | blank allowed | `''` | spaCy POS tag of the token at the error offset (e.g. `NOUN`, `VERB`) |
| `error_context` | JSON | blank allowed | `{}` | Linguistic context from spaCy: surrounding POS tags, dependency relations, named entities |
| `is_resolved` | Boolean | — | `False` | Whether the student has successfully corrected this error |
| `resolution_method` | String(20) | blank allowed, choices: `ResolutionMethod` | `''` | How the error was resolved (`correct`, `solution_revealed`, `manual_reveal`) |
| `resolved_at` | DateTime | null/blank allowed | `null` | Timestamp set when the error becomes resolved |
| `created_at` | DateTime | auto_now_add | — | Detection timestamp |

### Derived API Presentation Fields (Not Persisted)

The feedback serializers compute several fields from the stored `DetectedError`, its related `CorrectionAttempt` rows, and the current workflow configuration. These fields are API-facing only and are **not** stored in `feedback_detectederror`.

| Field | Source | Description |
|-------|--------|-------------|
| `display_group` | Derived from `error_category`, `spacy_pos_tag`, `languagetool_rule_id` | Grammatical-role grouping used for colour-coded highlights (`verb_phrase`, `noun_phrase`, `adjective`, `spelling_word_choice`, `syntax`) |
| `display_label` | Derived from `display_group` | Human-readable label shown in the frontend |
| `can_request_solution` | Derived from `attempts.count()` and `HINT_THRESHOLD` | Whether the gated manual reveal endpoint is available for this error |
| `next_try_number` | Derived from `attempts.count()` | Learner-facing upcoming try label (`2` for second try, `3` for third try) |

### Workflow Notes

- `hint_text` is reused both for the phase-2 hint response and as fallback explanation context if the Ollama host is unavailable.
- `correct_solution` is persisted so the backend can validate typed corrections, reveal the final answer, and seed the final explanation prompt.
- `resolution_method` and `resolved_at` are set by `CorrectionWorkflowService._mark_resolved()` for both successful corrections and reveal-driven completions.
- Final explanation text itself is **not** persisted on `DetectedError`; it is generated on demand in the feedback layer.

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `TextSubmission` | `submission` | `errors` | Many-to-One |
| `CorrectionAttempt` | — | `attempts` | One-to-Many (reverse) |

### Ordering

`['start_offset']` (document order)

### Indexes

- Composite index on `['submission', 'error_category']` to accelerate grouped analytics rollups and summary recomputation.

---

## 6. CorrectionAttempt

**App**: `feedback` · **Table**: `feedback_correctionattempt`

Records each typed learner attempt to correct a detected error. Tracks the progression through the guided correction workflow including whether hints and solutions were shown on that stored attempt.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `error` | FK → `DetectedError` | CASCADE | — | Target error being corrected |
| `student` | FK → `User` | CASCADE | — | Student making the attempt |
| `attempt_number` | SmallInteger | ≥ 0 | — | Sequential internal correction-attempt counter (1-based) |
| `attempted_text` | Text | — | — | Student's proposed correction |
| `is_correct` | Boolean | — | `False` | Whether the attempt was accepted |
| `hint_shown` | Boolean | — | `False` | Whether a hint was revealed on this attempt |
| `solution_shown` | Boolean | — | `False` | Whether the solution was revealed on this attempt |
| `created_at` | DateTime | auto_now_add | — | Attempt timestamp |

### Constraints

- **unique_together**: `[error, attempt_number]` — Ensures sequential, non-duplicate attempt numbering per error.

### Workflow Interpretation

`attempt_number` is an internal backend counter rather than the exact learner-facing label:

| `attempt_number` | Learner-Facing Meaning | Typical Response |
|------------------|------------------------|------------------|
| `1` | Second try / phase 2 | Correct answer or hint unlock |
| `2` | Third try / phase 3 | Correct answer or final answer + explanation |

The gated manual reveal path does **not** create a `CorrectionAttempt` row. It resolves the `DetectedError` directly and returns the hint, answer, and explanation response payload through the feedback API.

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `DetectedError` | `error` | `attempts` | Many-to-One |
| `User` | `student` | `correction_attempts` | Many-to-One |

### Ordering

`['error', 'attempt_number']`

---

## 7. LearnerErrorSummary

**App**: `analytics` · **Table**: `analytics_learnererrorsummary`

Pre-computed aggregation of error statistics per student, per submission, per error category. Updated by `AnalyticsService.compute_summary_for_submission()` after correction attempts are processed.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `student` | FK → `User` | CASCADE | — | Target student |
| `submission` | FK → `TextSubmission` | CASCADE | — | Target submission |
| `error_category` | String(20) | — | — | Error category being summarised |
| `total_errors` | Integer | ≥ 0 | `0` | Total errors in this category |
| `first_attempt_successes` | Integer | ≥ 0 | `0` | Errors corrected on the first stored correction attempt (learner-facing second try) |
| `avg_hints_used` | Float | — | `0.0` | Average number of hints consumed per error |
| `computed_at` | DateTime | auto_now | — | Last computation timestamp |

### Constraints

- **unique_together**: `[student, submission, error_category]` — One summary row per student × submission × category combination (upsert semantics).

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `User` | `student` | `error_summaries` | Many-to-One |
| `TextSubmission` | `submission` | `error_summaries` | Many-to-One |

### Ordering

`['-submission__submitted_at', 'error_category']`

### Analytics Scope Notes

- Summaries are currently grouped by persistent `error_category`, not by the derived `display_group` used in the frontend.
- Manual reveal versus final failed third try is persisted indirectly through `DetectedError.resolution_method`, and the analytics layer reconstructs counts from that field plus related attempts.

---

## 8. Enumerations

### UserRole

| Value | Label | Description |
|-------|-------|-------------|
| `student` | Student | Can submit texts and attempt corrections |
| `teacher` | Teacher | Can create classrooms, manage members, view analytics |
| `admin` | Admin | Full system access across all classrooms |

### SubmissionStatus

| Value | Label | Description |
|-------|-------|-------------|
| `submitted` | Submitted | Initial state after student submits text |
| `analyzing` | Analyzing | NLP pipeline is processing the text |
| `in_review` | In Review | Errors detected and awaiting student correction |
| `completed` | Completed | All detected errors have been resolved |

### ErrorCategory

| Value | Label | LanguageTool Mapping |
|-------|-------|---------------------|
| `grammar` | Grammar | `GRAMMAR` |
| `spelling` | Spelling | `TYPOS`, `SPELLING`, `CASING` |
| `article` | Article | `ARTICLE`, `DER_DIE_DAS` |
| `preposition` | Preposition | `PREPOSITION`, `PRAEP` |
| `verb_tense` | Verb Tense | `TENSE`, `VERB` |
| `punctuation` | Punctuation | `PUNCTUATION`, `TYPOGRAPHY` |
| `other` | Other | all other rule categories |

### Severity

| Value | Label | Description |
|-------|-------|-------------|
| `low` | Low | Minor stylistic issue |
| `medium` | Medium | Standard grammatical error (default) |
| `high` | High | Significant error affecting comprehension |

### MembershipRole

| Value | Label | Description |
|-------|-------|-------------|
| `student` | Student | Student member of a classroom |
| `teacher` | Teacher | Teacher/instructor in a classroom |

### ResolutionMethod

| Value | Label | Description |
|-------|-------|-------------|
| `correct` | Corrected by student | The learner submitted an accepted correction |
| `solution_revealed` | Revealed after max attempts | The final failed stored attempt revealed the answer |
| `manual_reveal` | Manually revealed by student | The learner used the gated reveal endpoint |

---

## 9. Relationship Summary

The following diagram shows all inter-model relationships with cardinality:

```
User (accounts.User)
 │
 ├──[1]──created_by──[0..*]──→ Classroom
 │
 ├──[1]──user──[0..*]──→ ClassroomMembership ←──[0..*]──classroom──[1]── Classroom
 │
 ├──[1]──student──[0..*]──→ TextSubmission ←──[0..*]──classroom──[1]── Classroom
 │                              │
 │                              ├──[1]──submission──[0..*]──→ DetectedError
 │                              │                                │
 │                              │                                └──[1]──error──[0..*]──→ CorrectionAttempt
 │                              │
 │                              └──[1]──submission──[0..*]──→ LearnerErrorSummary
 │
 ├──[1]──student──[0..*]──→ CorrectionAttempt
 │
 └──[1]──student──[0..*]──→ LearnerErrorSummary
```

### Key Relationship Semantics

- **User ↔ Classroom (through ClassroomMembership)**: Many-to-many with role metadata. A user can belong to multiple classrooms, each with a distinct role (student or teacher). The `unique_together` constraint on `[user, classroom]` prevents duplicate memberships.

- **TextSubmission → DetectedError → CorrectionAttempt**: This is the core pedagogical chain. Each submission generates zero or more detected errors (via NLP analysis), and each error collects zero or more stored correction attempts (via typed learner interaction). A gated manual reveal can resolve an error without creating another `CorrectionAttempt` row. All use `CASCADE` deletion — removing a submission removes all associated errors and attempts.

- **LearnerErrorSummary**: A denormalised aggregation model that summarises error statistics per student × submission × category. It exists for query performance in the analytics layer and is recomputed rather than manually maintained. It currently reflects persistent error categories and attempt rows, not the derived grammatical-role display groups used in the frontend.
