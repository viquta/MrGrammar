# REST API Reference

This document specifies all HTTP endpoints exposed by the MrGrammar backend. The API follows RESTful conventions and uses JSON for request and response bodies.

---

## Table of Contents

1. [General Information](#1-general-information)
2. [Authentication — `/api/auth/`](#2-authentication)
3. [Classrooms — `/api/classrooms/`](#3-classrooms)
4. [Submissions — `/api/submissions/`](#4-submissions)
5. [Feedback — `/api/feedback/`](#5-feedback)
6. [NLP — `/api/nlp/`](#6-nlp)
7. [Analytics — `/api/analytics/`](#7-analytics)

---

## 1. General Information

### Base URL

```
http://localhost:8000/api/
```

### Authentication

All endpoints except registration and login require a valid JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

| Token Type | Lifetime | Rotation |
|-----------|----------|----------|
| Access token | 15 minutes | — |
| Refresh token | 1 day | Rotated on each refresh |

### Pagination

Paginated endpoints use Django REST Framework's `PageNumberPagination`:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/submissions/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `page` | 1 | Page number (1-indexed) |
| `page_size` | 20 | Results per page |

> **Note**: The feedback errors endpoint (`GET /api/feedback/submissions/{id}/errors/`) disables pagination to support inline error highlighting in the frontend.

### Error Response Format

Validation errors return field-level messages:

```json
{
  "field_name": ["Error message."]
}
```

Permission and general errors return a `detail` string:

```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## 2. Authentication

### POST `/api/auth/register/`

Create a new user account.

**Permissions**: `AllowAny`

**Request Body**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `username` | string | yes | unique | Login identifier |
| `email` | string | yes | valid email | User email |
| `password` | string | yes | min 8 characters | Password (hashed on storage) |
| `first_name` | string | yes | — | Given name |
| `last_name` | string | yes | — | Family name |
| `role` | string | no | `student` \| `teacher` \| `admin` | Defaults to `student` |

**Response** `201 Created`:

```json
{
  "id": 1,
  "username": "maria.mueller",
  "email": "maria@example.com",
  "first_name": "Maria",
  "last_name": "Müller",
  "role": "student"
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400` | Validation failure (duplicate username, short password, etc.) |

---

### POST `/api/auth/login/`

Obtain a JWT access/refresh token pair.

**Permissions**: `AllowAny`

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | yes | Login identifier |
| `password` | string | yes | Account password |

**Response** `200 OK`:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `401` | Invalid credentials |

---

### POST `/api/auth/token/refresh/`

Obtain a new access token using a valid refresh token.

**Permissions**: `AllowAny`

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh` | string | yes | Valid refresh token |

**Response** `200 OK`:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `401` | Expired or invalid refresh token |

---

### GET `/api/auth/me/`

Retrieve the authenticated user's profile.

**Permissions**: `IsAuthenticated`

**Response** `200 OK`:

```json
{
  "id": 1,
  "username": "maria.mueller",
  "email": "maria@example.com",
  "first_name": "Maria",
  "last_name": "Müller",
  "role": "student"
}
```

---

## 3. Classrooms

### GET `/api/classrooms/`

List classrooms accessible to the authenticated user.

**Permissions**: `IsAuthenticated`

**Behaviour by role**:
- **Student/Teacher**: Returns classrooms where the user is a member.
- **Admin**: Returns all classrooms.

**Response** `200 OK` (paginated):

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Deutsch B2 – Gruppe A",
      "language": "de",
      "created_by": "Ada Lehrer (teacher)",
      "created_at": "2026-03-15T10:30:00Z",
      "student_count": 24
    }
  ]
}
```

---

### POST `/api/classrooms/`

Create a new classroom. The authenticated user is automatically added as a `teacher` member.

**Permissions**: `IsAuthenticated`

**Request Body**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | — | Classroom name |
| `language` | string | no | `"de"` | Target language |

**Response** `201 Created`:

```json
{
  "id": 2,
  "name": "Deutsch A2 – Konversation",
  "language": "de",
  "created_by": "Ada Lehrer (teacher)",
  "created_at": "2026-04-01T14:00:00Z",
  "student_count": 0
}
```

---

### GET `/api/classrooms/{id}/`

Retrieve a single classroom.

**Permissions**: `IsTeacherOrAdmin`

**Response** `200 OK`: Same shape as list item.

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `403` | User is not teacher/admin |
| `404` | Classroom does not exist or user is not a member |

---

### PATCH `/api/classrooms/{id}/`

Update classroom fields.

**Permissions**: `IsTeacherOrAdmin`

**Request Body**: Any subset of `name`, `language`.

**Response** `200 OK`: Updated classroom object.

---

### DELETE `/api/classrooms/{id}/`

Delete a classroom and all associated memberships and submissions (CASCADE).

**Permissions**: `IsTeacherOrAdmin`

**Response** `204 No Content`

---

### GET `/api/classrooms/{id}/members/`

List all members of a classroom.

**Permissions**: `IsAuthenticated` (must be a member of the classroom)

**Response** `200 OK`:

```json
[
  {
    "id": 1,
    "user": 5,
    "classroom": 1,
    "role": "student",
    "username": "maria.mueller",
    "full_name": "Maria Müller",
    "joined_at": "2026-03-16T09:00:00Z"
  }
]
```

---

### POST `/api/classrooms/{id}/members/add/`

Add a user to a classroom.

**Permissions**: `IsTeacherOrAdmin` (teachers must be a teacher member of this classroom)

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | integer | yes | ID of the user to add |
| `role` | string | yes | `student` \| `teacher` |

**Response** `201 Created`:

```json
{
  "id": 12,
  "user": 5,
  "classroom": 1,
  "role": "student",
  "username": "maria.mueller",
  "full_name": "Maria Müller",
  "joined_at": "2026-04-19T10:00:00Z"
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400` | User does not exist |
| `403` | Requester is not teacher/admin in this classroom |
| `409` | User is already a member of this classroom |

---

## 4. Submissions

### GET `/api/submissions/`

List text submissions accessible to the authenticated user.

**Permissions**: `IsAuthenticated` (restricted to errors on submissions owned by the current student)

**Behaviour by role**:
- **Student**: Own submissions only.
- **Teacher**: Submissions from classrooms where the user is a teacher member.
- **Admin**: All submissions.

**Response** `200 OK` (paginated):

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "student": 5,
      "student_name": "Maria Müller",
      "classroom": 1,
      "title": "Mein Wochenende",
      "language": "de",
      "status": "in_review",
      "submitted_at": "2026-04-18T14:30:00Z"
    }
  ]
}
```

> **Note**: The list endpoint uses `TextSubmissionListSerializer` which omits the `content` field for performance.

---

### POST `/api/submissions/`

Create a new text submission. The `student` field is automatically set to the authenticated user.

**Permissions**: `IsAuthenticated` (restricted to errors on submissions owned by the current student)

**Request Body**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `classroom` | integer | yes | — | Classroom ID |
| `title` | string | yes | — | Submission title (max 300 chars) |
| `content` | string | yes | — | Full text body |
| `language` | string | no | `"de"` | Text language |

**Response** `201 Created`:

```json
{
  "id": 6,
  "student": 5,
  "student_name": "Maria Müller",
  "classroom": 1,
  "title": "Mein Wochenende",
  "content": "Am Samstag bin ich ins Kino gegangen...",
  "language": "de",
  "status": "submitted",
  "submitted_at": "2026-04-19T10:00:00Z",
  "updated_at": "2026-04-19T10:00:00Z"
}
```

---

### GET `/api/submissions/{id}/`

Retrieve a single submission with full text content.

**Permissions**: `IsAuthenticated` (same role-based filtering as list)

**Response** `200 OK`: Full submission object including `content` and `updated_at`.

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `404` | Submission does not exist or not accessible to this user |

---

## 5. Feedback

### GET `/api/feedback/submissions/{id}/errors/`

List all detected errors for a submission.

**Permissions**: `IsAuthenticated`

**Pagination**: **Disabled** (all errors returned in a single response to support inline text highlighting).

**Response** `200 OK`:

```json
[
  {
    "id": 1,
    "submission": 6,
    "error_category": "article",
    "severity": "medium",
    "start_offset": 45,
    "end_offset": 48,
    "original_text": "der",
    "is_resolved": false,
    "attempt_count": 0,
    "display_group": "noun_phrase",
    "display_label": "Noun Phrase",
    "can_request_solution": false,
    "next_try_number": 2,
    "created_at": "2026-04-19T10:05:00Z"
  }
]
```

> **Note**: The `hint_text` and `correct_solution` fields are intentionally excluded from this endpoint. They are revealed progressively through the correction workflow.

---

### GET `/api/feedback/errors/{id}/`

Retrieve a single error with all associated correction attempts.

**Permissions**: `IsAuthenticated`

**Response** `200 OK`:

```json
{
  "id": 1,
  "submission": 6,
  "error_category": "article",
  "severity": "medium",
  "start_offset": 45,
  "end_offset": 48,
  "original_text": "der",
  "is_resolved": false,
  "spacy_pos_tag": "DET",
  "error_context": {
    "tokens": [
      {
        "text": "der",
        "pos": "DET",
        "morph": {"Case": "Dat", "Definite": "Def", "Gender": "Fem", "Number": "Sing"},
        "dep": "nk",
        "head": "Schule"
      }
    ],
    "entities": [],
    "prev_token": {"text": "sehe", "pos": "VERB"},
    "next_token": {"text": "Schule", "pos": "NOUN"}
  },
  "display_group": "noun_phrase",
  "display_label": "Noun Phrase",
  "created_at": "2026-04-19T10:05:00Z",
  "attempts": [
    {
      "id": 1,
      "error": 1,
      "attempt_number": 1,
      "attempted_text": "die",
      "is_correct": false,
      "hint_shown": true,
      "solution_shown": false,
      "created_at": "2026-04-19T10:10:00Z"
    }
  ]
}
```

---

### POST `/api/feedback/errors/{id}/attempt/`

Submit a correction attempt for a detected error. This is the primary endpoint for the guided correction workflow.

**Permissions**: `IsAuthenticated`

**Request Body**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `attempted_text` | string | yes | max 1000 chars | Student's proposed correction |

**Response** `200 OK`:

The response varies based on the attempt outcome:

**Correct answer**:
```json
{
  "attempt_number": 1,
  "display_attempt_number": 2,
  "phase": "phase_2",
  "outcome": "correct",
  "is_correct": true,
  "is_resolved": true,
  "can_request_solution": false
}
```

**Incorrect, hint shown and phase 3 unlocked**:
```json
{
  "attempt_number": 1,
  "display_attempt_number": 2,
  "phase": "phase_2",
  "outcome": "hint",
  "is_correct": false,
  "is_resolved": false,
  "can_request_solution": true,
  "hint": "The noun 'Schule' is feminine in German."
}
```

**Incorrect on the final correction attempt**:
```json
{
  "attempt_number": 2,
  "display_attempt_number": 3,
  "phase": "phase_3",
  "outcome": "solution_revealed",
  "is_correct": false,
  "is_resolved": true,
  "can_request_solution": false,
  "hint": "The noun 'Schule' is feminine in German.",
  "solution": "die",
  "explanation": "Your answer does not match the noun gender. Use the feminine article for 'Schule'."
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400` | Error is already resolved |
| `404` | Error does not exist |

**Workflow Configuration**:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `SIMILARITY_THRESHOLD` | `0.85` | Service constant on `CorrectionWorkflowService`; Levenshtein ratio ≥ this value → attempt accepted as correct |
| `HINT_THRESHOLD` | `1` | `settings.MRGRAMMAR` value; attempt number at which hint is revealed on failure |
| `MAX_CORRECTION_ATTEMPTS` | `2` | `settings.MRGRAMMAR` value; attempt number at which solution is revealed and error auto-resolved |

---

### POST `/api/feedback/errors/{id}/solution/`

Reveal the hint, answer, and final explanation for an error once manual reveal has been unlocked. The current backend unlocks this only after the first failed correction attempt.

**Permissions**: `IsAuthenticated` (restricted to errors on submissions owned by the current student)

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `attempted_text` | string | no | The learner's current draft, passed through to the explanation generator |

**Response** `200 OK`:

```json
{
  "attempt_number": 1,
  "display_attempt_number": 2,
  "phase": "phase_3",
  "outcome": "manual_reveal",
  "is_correct": false,
  "is_resolved": true,
  "can_request_solution": false,
  "hint": "The noun 'Schule' is feminine in German.",
  "solution": "die",
  "explanation": "Your answer does not match the noun gender. Use the feminine article for 'Schule'."
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400` | Error is already resolved |
| `400` | Solution reveal is not available yet |
| `404` | Error does not exist or does not belong to the current student |

---

## 6. NLP

### POST `/api/nlp/submissions/{id}/analyze/`

Trigger NLP error detection on a submission. Calls the self-hosted LanguageTool instance, maps detected matches to `DetectedError` records, and transitions the submission status from `submitted` → `analyzing` → `in_review`.

**Permissions**: `IsAuthenticated` (must be the submission's `student`)

**Request Body**: None

**Response** `200 OK`:

```json
{
  "submission_id": 6,
  "errors_found": 4,
  "status": "in_review"
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400` | Submission has already been analyzed (status ≠ `submitted`) |
| `403` | Requester is not the submission's student |
| `404` | Submission does not exist |

**Backend Pipeline**:

1. Validate submission ownership and status
2. Set status to `analyzing`
3. Create a spaCy `Doc` from the original submission text (using `SpacyTextProcessor.make_doc()`)
4. Run **two** error-detection backends in sequence:
   - **LanguageToolClient** — sends `POST /v2/check` to the self-hosted LanguageTool instance (optionally per-sentence via `detect_by_sentences()` using spaCy sentence splitting)
   - **SpacyGrammarDetector** — flags out-of-vocabulary (OOV) misspellings and missing noun capitalisation using the `de_core_news_md` model; generates correction suggestions via Levenshtein distance over the model's vector vocabulary
5. Merge results from both backends and map each match to the application's `ErrorCategory` taxonomy
6. Post-process each error with spaCy: override category using POS tags (`categorize_error()`), extract linguistic context (`extract_error_context()`), and record the POS tag (`get_pos_tag()`)
7. Deduplicate by character offset range
8. Batch-create `DetectedError` records (including `spacy_pos_tag` and `error_context` fields)
9. Set status to `in_review`
10. Return error count

---

## 7. Analytics

### GET `/api/analytics/student/{id}/progress/`

Retrieve a dashboard-ready learner insight payload for a student across their submissions.

**Permissions**: `IsAuthenticated`
- Students can only view their own progress (ID must match `request.user.id`)
- Teachers can view students who belong to one of their classrooms
- Admins can view any student

**Response** `200 OK`:

```json
{
  "student": {
    "id": 12,
    "username": "maria.mueller",
    "full_name": "Maria Müller"
  },
  "overview": {
    "submission_count": 4,
    "total_errors": 19,
    "resolved_errors": 15,
    "resolution_rate": 0.79,
    "first_attempt_successes": 8,
    "first_attempt_success_rate": 0.42,
    "hint_shown_errors": 7,
    "hint_usage_rate": 0.37,
    "manual_reveal_count": 2,
    "solution_reveal_count": 1,
    "avg_attempts_per_error": 1.32,
    "last_submission_at": "2026-04-21T10:15:00Z"
  },
  "submissions": [
    {
      "submission_id": 44,
      "title": "Mein Wochenende",
      "status": "completed",
      "submitted_at": "2026-04-18T09:30:00Z",
      "total_errors": 6,
      "resolved_errors": 5,
      "first_attempt_successes": 3,
      "hint_shown_errors": 2,
      "manual_reveal_count": 1,
      "solution_reveal_count": 0,
      "attempt_count": 7,
      "categories": [
        {
          "error_category": "article",
          "total_errors": 3,
          "resolved_errors": 3,
          "first_attempt_successes": 2,
          "avg_hints_used": 0.33,
          "hint_shown_errors": 1,
          "manual_reveal_count": 0,
          "attempt_count": 3
        }
      ]
    }
  ],
  "category_breakdown": [
    {
      "error_category": "article",
      "total_errors": 7,
      "resolved_errors": 6,
      "first_attempt_successes": 4,
      "first_attempt_success_rate": 0.57,
      "avg_hints_used": 0.29,
      "hint_shown_errors": 2,
      "manual_reveal_count": 1,
      "avg_attempts_per_error": 1.14,
      "timeline": [
        {
          "submission_id": 44,
          "submission_title": "Mein Wochenende",
          "submitted_at": "2026-04-18T09:30:00Z",
          "total_errors": 3,
          "resolved_errors": 3,
          "first_attempt_successes": 2,
          "avg_hints_used": 0.33,
          "hint_shown_errors": 1,
          "manual_reveal_count": 0
        }
      ]
    }
  ]
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `403` | Student attempting to view another student's progress |
| `403` | Teacher attempting to view a student outside their classrooms |

---

### GET `/api/analytics/classroom/{id}/patterns/`

Retrieve a dashboard-ready classroom insight payload across all submissions in a classroom.

**Permissions**: `IsTeacherOrAdmin`

**Response** `200 OK`:

```json
{
  "classroom": {
    "id": 3,
    "name": "Deutsch B2 – Gruppe A",
    "language": "de"
  },
  "overview": {
    "student_count": 24,
    "submission_count": 31,
    "total_errors": 132,
    "resolved_errors": 104,
    "resolution_rate": 0.79,
    "first_attempt_successes": 54,
    "first_attempt_success_rate": 0.41,
    "hint_shown_errors": 38,
    "hint_usage_rate": 0.29,
    "manual_reveal_count": 11,
    "solution_reveal_count": 9,
    "avg_attempts_per_error": 1.47
  },
  "timeline": [
    {
      "submission_id": 44,
      "submission_title": "Mein Wochenende",
      "submitted_at": "2026-04-18T09:30:00Z",
      "student_id": 12,
      "student_name": "Maria Müller",
      "total_errors": 6,
      "resolved_errors": 5,
      "first_attempt_successes": 3,
      "hint_shown_errors": 2,
      "manual_reveal_count": 1
    }
  ],
  "category_breakdown": [
    {
      "error_category": "article",
      "total_errors": 42,
      "resolved_errors": 33,
      "resolution_rate": 0.79,
      "first_attempt_successes": 19,
      "first_attempt_success_rate": 0.45,
      "hint_shown_errors": 14,
      "hint_usage_rate": 0.33,
      "manual_reveal_count": 5,
      "avg_attempts_per_error": 1.36,
      "timeline": [
        {
          "submission_id": 44,
          "submission_title": "Mein Wochenende",
          "submitted_at": "2026-04-18T09:30:00Z",
          "student_id": 12,
          "student_name": "Maria Müller",
          "total_errors": 3,
          "resolved_errors": 3,
          "first_attempt_successes": 2,
          "hint_shown_errors": 1,
          "manual_reveal_count": 0
        }
      ]
    }
  ],
  "students": [
    {
      "student_id": 12,
      "username": "maria.mueller",
      "full_name": "Maria Müller",
      "submission_count": 4,
      "total_errors": 19,
      "resolved_errors": 15,
      "resolution_rate": 0.79,
      "first_attempt_successes": 8,
      "first_attempt_success_rate": 0.42,
      "hint_shown_errors": 7,
      "hint_usage_rate": 0.37,
      "manual_reveal_count": 2,
      "avg_attempts_per_error": 1.32,
      "top_error_category": "article",
      "last_submission_at": "2026-04-21T10:15:00Z"
    }
  ]
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `403` | User is not a teacher or admin |
| `403` | Teacher is not a member of the classroom |
| `404` | Classroom does not exist |
