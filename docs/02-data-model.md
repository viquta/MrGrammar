# Data Model

This document describes the persistent data model of MrGrammar. The system uses seven Django models across five applications, backed by a PostgreSQL 16 database. The custom user model is configured via `AUTH_USER_MODEL = 'accounts.User'`.

> **UML Class Diagram**: Open [`diagrams/class-diagram.drawio`](diagrams/class-diagram.drawio) in the Draw.io VS Code extension or at [diagrams.net](https://app.diagrams.net) to view the full class diagram with associations and cardinalities.
>
> ![Class Diagram](diagrams/exported/class-diagram.png)

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
| `role` | String(10) | choices: `UserRole` | `STUDENT` | User role within the system |
| `is_active` | Boolean | — | `True` | Account active flag |
| `is_staff` | Boolean | — | `False` | Django admin access |
| `date_joined` | DateTime | auto | — | Registration timestamp |

### Properties & Methods

| Member | Returns | Description |
|--------|---------|-------------|
| `is_student` | Boolean | `True` if `role == STUDENT` |
| `is_teacher` | Boolean | `True` if `role == TEACHER` |
| `is_admin_user` | Boolean | `True` if `role == ADMIN` |
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

Represents a student's text submission within a classroom. The `status` field tracks the submission through its lifecycle: submitted → analyzing → in review → completed.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `student` | FK → `User` | CASCADE | — | Submitting student |
| `classroom` | FK → `Classroom` | CASCADE | — | Target classroom |
| `title` | String(300) | — | — | Submission title |
| `content` | Text | — | — | Full text body |
| `language` | String(10) | — | `'de'` | Text language for NLP |
| `status` | String(15) | choices: `SubmissionStatus` | `SUBMITTED` | Current lifecycle stage |
| `submitted_at` | DateTime | auto_now_add | — | Submission timestamp |
| `updated_at` | DateTime | auto_now | — | Last modification timestamp |

### Status Workflow

```
SUBMITTED  →  ANALYZING  →  IN_REVIEW  →  COMPLETED
   (new)      (NLP running)  (errors found) (all resolved)
```

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

Represents a single error detected in a student's text by the NLP pipeline. Character offsets allow precise in-text highlighting. The `hint_text` and `correct_solution` fields support the progressive disclosure workflow — they are not exposed to the student until appropriate in the correction process.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `submission` | FK → `TextSubmission` | CASCADE | — | Parent submission |
| `error_category` | String(20) | choices: `ErrorCategory` | — | Classified error type |
| `severity` | String(10) | choices: `Severity` | `MEDIUM` | Error severity level |
| `start_offset` | Integer | ≥ 0 | — | Start character offset in `content` |
| `end_offset` | Integer | ≥ 0 | — | End character offset in `content` |
| `original_text` | Text | — | — | Erroneous text span |
| `hint_text` | Text | blank allowed | — | Pedagogical hint (from LanguageTool message) |
| `correct_solution` | Text | — | — | Correct replacement text |
| `languagetool_rule_id` | String(100) | blank allowed | — | LanguageTool rule identifier for traceability |
| `spacy_pos_tag` | String(20) | blank allowed | `''` | spaCy POS tag of the token at the error offset (e.g. `NOUN`, `VERB`) |
| `error_context` | JSON | blank allowed | `{}` | Linguistic context from spaCy: surrounding POS tags, dependency relations, named entities |
| `is_resolved` | Boolean | — | `False` | Whether the student has successfully corrected this error |
| `created_at` | DateTime | auto_now_add | — | Detection timestamp |

### Relationships

| Related Model | FK Field | related_name | Cardinality |
|---------------|----------|-------------|-------------|
| `TextSubmission` | `submission` | `errors` | Many-to-One |
| `CorrectionAttempt` | — | `attempts` | One-to-Many (reverse) |

### Ordering

`['start_offset']` (document order)

---

## 6. CorrectionAttempt

**App**: `feedback` · **Table**: `feedback_correctionattempt`

Records each student attempt to correct a detected error. Tracks the progression through the guided correction workflow including whether hints and solutions were shown.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | Integer | PK, auto-increment | — | Primary key |
| `error` | FK → `DetectedError` | CASCADE | — | Target error being corrected |
| `student` | FK → `User` | CASCADE | — | Student making the attempt |
| `attempt_number` | SmallInteger | ≥ 0 | — | Sequential attempt counter (1-based) |
| `attempted_text` | Text | — | — | Student's proposed correction |
| `is_correct` | Boolean | — | `False` | Whether the attempt was accepted |
| `hint_shown` | Boolean | — | `False` | Whether a hint was revealed on this attempt |
| `solution_shown` | Boolean | — | `False` | Whether the solution was revealed on this attempt |
| `created_at` | DateTime | auto_now_add | — | Attempt timestamp |

### Constraints

- **unique_together**: `[error, attempt_number]` — Ensures sequential, non-duplicate attempt numbering per error.

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
| `first_attempt_successes` | Integer | ≥ 0 | `0` | Errors corrected on the first attempt |
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

---

## 8. Enumerations

### UserRole

| Value | Label | Description |
|-------|-------|-------------|
| `STUDENT` | Student | Can submit texts and attempt corrections |
| `TEACHER` | Teacher | Can create classrooms, manage members, view analytics |
| `ADMIN` | Admin | Full system access across all classrooms |

### SubmissionStatus

| Value | Label | Description |
|-------|-------|-------------|
| `SUBMITTED` | Submitted | Initial state after student submits text |
| `ANALYZING` | Analyzing | NLP pipeline is processing the text |
| `IN_REVIEW` | In Review | Errors detected and awaiting student correction |
| `COMPLETED` | Completed | All detected errors have been resolved |

### ErrorCategory

| Value | Label | LanguageTool Mapping |
|-------|-------|---------------------|
| `GRAMMAR` | Grammar | `GRAMMAR` |
| `SPELLING` | Spelling | `TYPOS`, `SPELLING`, `CASING` |
| `ARTICLE` | Article | `ARTICLE`, `DER_DIE_DAS` |
| `PREPOSITION` | Preposition | `PREPOSITION`, `PRAEP` |
| `VERB_TENSE` | Verb Tense | `TENSE`, `VERB` |
| `PUNCTUATION` | Punctuation | `PUNCTUATION`, `TYPOGRAPHY` |
| `OTHER` | Other | all other rule categories |

### Severity

| Value | Label | Description |
|-------|-------|-------------|
| `LOW` | Low | Minor stylistic issue |
| `MEDIUM` | Medium | Standard grammatical error (default) |
| `HIGH` | High | Significant error affecting comprehension |

### MembershipRole

| Value | Label | Description |
|-------|-------|-------------|
| `STUDENT` | Student | Student member of a classroom |
| `TEACHER` | Teacher | Teacher/instructor in a classroom |

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

- **TextSubmission → DetectedError → CorrectionAttempt**: This is the core pedagogical chain. Each submission generates zero or more detected errors (via NLP analysis), and each error collects zero or more correction attempts (via student interaction). All use `CASCADE` deletion — removing a submission removes all associated errors and attempts.

- **LearnerErrorSummary**: A denormalised aggregation model that summarises error statistics per student × submission × category. It exists for query performance in the analytics layer and is recomputed rather than manually maintained.
