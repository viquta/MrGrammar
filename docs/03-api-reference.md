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
      "created_by": 3,
      "created_at": "2026-03-15T10:30:00Z",
      "student_count": 24
    }
  ]
}
```

---

### POST `/api/classrooms/`

Create a new classroom. The authenticated user is automatically added as a `TEACHER` member.

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
  "created_by": 3,
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
    "role": "STUDENT",
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
| `role` | string | yes | `STUDENT` \| `TEACHER` |

**Response** `201 Created`:

```json
{
  "id": 12,
  "user": 5,
  "classroom": 1,
  "role": "STUDENT",
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

**Permissions**: `IsAuthenticated`

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

**Permissions**: `IsAuthenticated`

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
  "attempt_count": 1,
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
  "attempt_number": 2,
  "is_correct": true,
  "is_resolved": true
}
```

**Incorrect, below hint threshold**:
```json
{
  "attempt_number": 1,
  "is_correct": false,
  "is_resolved": false
}
```

**Incorrect, hint threshold reached** (attempt ≥ `HINT_THRESHOLD`):
```json
{
  "attempt_number": 2,
  "is_correct": false,
  "is_resolved": false,
  "hint": "The noun 'Schule' is feminine in German."
}
```

**Incorrect, max attempts reached** (attempt ≥ `MAX_CORRECTION_ATTEMPTS`):
```json
{
  "attempt_number": 3,
  "is_correct": false,
  "is_resolved": true,
  "hint": "The noun 'Schule' is feminine in German.",
  "solution": "die"
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400` | Error is already resolved |
| `404` | Error does not exist |

**Workflow Configuration** (from `settings.MRGRAMMAR`):

| Parameter | Default | Effect |
|-----------|---------|--------|
| `SIMILARITY_THRESHOLD` | `0.85` | Levenshtein ratio ≥ this value → attempt accepted as correct |
| `HINT_THRESHOLD` | `1` | Attempt number at which hint is revealed on failure |
| `MAX_CORRECTION_ATTEMPTS` | `3` | Attempt number at which solution is revealed and error auto-resolved |

---

### POST `/api/feedback/errors/{id}/solution/`

Immediately reveal the hint and solution for an error, marking it as resolved. This bypasses the correction workflow.

**Permissions**: `IsAuthenticated`

**Request Body**: None

**Response** `200 OK`:

```json
{
  "hint": "The noun 'Schule' is feminine in German.",
  "solution": "die"
}
```

---

## 6. NLP

### POST `/api/nlp/submissions/{id}/analyze/`

Trigger NLP error detection on a submission. Calls the self-hosted LanguageTool instance, maps detected matches to `DetectedError` records, and transitions the submission status from `SUBMITTED` → `ANALYZING` → `IN_REVIEW`.

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
| `400` | Submission has already been analyzed (status ≠ `SUBMITTED`) |
| `403` | Requester is not the submission's student |
| `404` | Submission does not exist |

**Backend Pipeline**:

1. Validate submission ownership and status
2. Set status to `ANALYZING`
3. Create a spaCy `Doc` from the original submission text (using `SpacyTextProcessor.make_doc()`)
4. Run **two** error-detection backends in sequence:
   - **LanguageToolClient** — sends `POST /v2/check` to the self-hosted LanguageTool instance (optionally per-sentence via `detect_by_sentences()` using spaCy sentence splitting)
   - **SpacyGrammarDetector** — flags out-of-vocabulary (OOV) misspellings and missing noun capitalisation using the `de_core_news_md` model; generates correction suggestions via Levenshtein distance over the model's vector vocabulary
5. Merge results from both backends and map each match to the application's `ErrorCategory` taxonomy
6. Post-process each error with spaCy: override category using POS tags (`categorize_error()`), extract linguistic context (`extract_error_context()`), and record the POS tag (`get_pos_tag()`)
7. Deduplicate by character offset range
8. Batch-create `DetectedError` records (including `spacy_pos_tag` and `error_context` fields)
9. Set status to `IN_REVIEW`
10. Return error count

---

## 7. Analytics

### GET `/api/analytics/student/{id}/progress/`

Retrieve error-category trends for a student across their submissions.

**Permissions**: `IsAuthenticated`
- Students can only view their own progress (ID must match `request.user.id`)
- Teachers and admins can view any student

**Response** `200 OK`:

```json
[
  {
    "error_category": "article",
    "total_errors": 12,
    "first_attempt_successes": 7,
    "avg_hints_used": 0.8,
    "submission_date": "2026-04-18"
  },
  {
    "error_category": "grammar",
    "total_errors": 5,
    "first_attempt_successes": 3,
    "avg_hints_used": 1.2,
    "submission_date": "2026-04-18"
  }
]
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `403` | Student attempting to view another student's progress |

---

### GET `/api/analytics/classroom/{id}/patterns/`

Retrieve aggregated error patterns across all submissions in a classroom.

**Permissions**: `IsTeacherOrAdmin`

**Response** `200 OK`:

```json
[
  {
    "error_category": "article",
    "total_count": 87,
    "resolved_count": 62
  },
  {
    "error_category": "spelling",
    "total_count": 45,
    "resolved_count": 41
  }
]
```

Results are ordered by `total_count` descending, showing the most common error categories first.

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `403` | User is not a teacher or admin |
| `404` | Classroom does not exist |
