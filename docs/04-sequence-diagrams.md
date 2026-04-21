# Sequence Diagrams

This document describes the core workflows of MrGrammar using UML sequence diagrams and workflow diagrams. Each subsection provides a narrative explanation alongside the corresponding source diagram files.

> **Diagram files**: Open the `.drawio` files in the Draw.io VS Code extension or at [diagrams.net](https://app.diagrams.net).

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Submission & NLP Analysis Flow](#2-submission--nlp-analysis-flow)
3. [Guided Correction Workflow](#3-guided-correction-workflow)

---

## 1. Authentication Flow

**Diagram**: [`diagrams/sequence-auth.drawio`](diagrams/sequence-auth.drawio)

![Authentication Sequence](diagrams/exported/sequence-auth.png)

### Participants

| Participant | Role |
|-------------|------|
| **Student (Browser)** | End user interacting with the SvelteKit SPA |
| **Frontend (SvelteKit)** | Client-side application handling routing, forms, and token storage |
| **Backend (DRF)** | Django REST Framework handling authentication endpoints |
| **Database (PostgreSQL)** | Persistent storage for user records |

### Flow Description

#### Registration

1. The student navigates to `/register` and fills in the registration form (username, email, password, first/last name, role).
2. The frontend sends `POST /api/auth/register/` with the form data.
3. The backend validates the input (password ≥ 8 characters, unique username) and creates a new user via `User.objects.create_user()`, which hashes the password.
4. The database inserts the user record and returns it.
5. The backend responds with `201 Created` containing the user profile (id, username, email, role).

#### Login

6. The student navigates to `/login` and enters their credentials.
7. The frontend sends `POST /api/auth/login/` (SimpleJWT's `TokenObtainPairView`).
8. The backend queries the database for the user record and verifies the password hash.
9. On successful verification, the backend generates a JWT access token (15-minute lifetime) and a refresh token (1-day lifetime).
10. The frontend receives the token pair in the `200 OK` response.
11. The frontend stores both tokens in `localStorage` (`token` and `refresh_token` keys).

#### Protected API Request

12. When the student navigates to a protected route (e.g., `/submissions`), the frontend reads the access token from `localStorage`.
13. The frontend includes the token in the `Authorization: Bearer <access>` header with every API request.
14. The backend validates the JWT signature and expiry, then processes the request normally.

#### Token Refresh

15. If an API request returns `401 Unauthorized` (expired access token), the frontend intercepts the error.
16. The frontend sends `POST /api/auth/token/refresh/` with the stored refresh token.
17. The backend validates the refresh token, generates a new access/refresh pair (rotation enabled), and returns them. The frontend updates `localStorage` with the new tokens and retries the original request.

### Implementation References

| Component | Source |
|-----------|--------|
| Registration view | `accounts/views.py` → `RegisterView` (CreateAPIView, AllowAny) |
| Login view | SimpleJWT `TokenObtainPairView` |
| Token refresh | SimpleJWT `TokenRefreshView` |
| User profile | `accounts/views.py` → `MeView` |
| Frontend auth store | `frontend/src/lib/stores/auth.ts` |
| Frontend API client | `frontend/src/lib/api.ts` (Bearer token injection) |
| JWT configuration | `mrgrammar/settings.py` → `SIMPLE_JWT` dict |

---

## 2. Submission & NLP Analysis Flow

**Diagram**: [`diagrams/sequence-submission.drawio`](diagrams/sequence-submission.drawio)

![Submission Sequence](diagrams/exported/sequence-submission.png)

### Participants

| Participant | Role |
|-------------|------|
| **Student (Browser)** | Student creating and analyzing a text submission |
| **Frontend (SvelteKit)** | SPA handling submission forms and error display |
| **SubmissionView (DRF)** | Handles CRUD operations for text submissions |
| **AnalyzeView (DRF)** | Triggers NLP analysis pipeline |
| **ErrorDetectionService** | Orchestrates error detection with pluggable backends |
| **SpacyTextProcessor** | Text cleaning, sentence splitting, POS analysis, and error post-processing (`nlp/spacy_processor.py`) |
| **LanguageTool (REST API)** | Self-hosted grammar checker (`/v2/check`) |
| **SpacyGrammarDetector** | OOV spell detection and noun capitalisation checking via spaCy (`nlp/services.py`) |
| **Database (PostgreSQL)** | Stores submissions and detected errors |

### Flow Description

#### Phase 1: Create Submission

1. The student navigates to `/submissions` and fills in the submission form (title, text content).
2. The frontend sends `POST /api/submissions/` with the classroom ID, title, content, and language. The `student` field is auto-set to `request.user` by the view.
3. The backend inserts a new `TextSubmission` record with `status = SUBMITTED`.
4. The database returns the created record.
5. The frontend receives `201 Created` with the submission data.

#### Phase 2: NLP Analysis

6. The student clicks the "Analyze" button on the submission detail page.
7. The frontend sends `POST /api/nlp/submissions/{id}/analyze/`.
8. The `AnalyzeView` validates ownership (`student == request.user`) and that the submission hasn't already been analyzed (`status == SUBMITTED`). It then updates the status to `ANALYZING`.
9. The view delegates to `ErrorDetectionService.analyze(submission)`.
10. The `ErrorDetectionService` creates a spaCy `Doc` from the original submission text via `SpacyTextProcessor.make_doc()`, then runs its configured backends sequentially:
    - **LanguageToolClient**: sends `POST /v2/check` to the self-hosted LanguageTool instance. Optionally splits text into sentences using `SpacyTextProcessor.split_sentences()` and checks each sentence individually, remapping offsets back to the original text.
    - **SpacyGrammarDetector**: iterates over spaCy tokens to detect out-of-vocabulary (OOV) misspellings and missing noun capitalisation. Skips named entities (PER, LOC, ORG) and uppercase proper nouns. Generates correction suggestions via Levenshtein distance over the model's vector vocabulary.
11. Both backends return lists of raw error dicts (offset, length, category, message, replacement).
12. The `ErrorDetectionService` post-processes each error using `SpacyTextProcessor`:
    - **Category override**: `categorize_error()` uses POS/morphology tags to refine the category (e.g., DET→ARTICLE, ADP→PREPOSITION, VERB/AUX→VERB_TENSE).
    - **Context extraction**: `extract_error_context()` records surrounding POS tags, dependency relations, and named entities as JSON.
    - **POS tag**: `get_pos_tag()` records the spaCy POS tag at the error offset.
13. The view deduplicates errors by character offset range and batch-creates `DetectedError` records (including `spacy_pos_tag` and `error_context` fields) in the database, then updates the submission status to `IN_REVIEW`.
14. The view responds with `200 OK` containing the submission ID, error count, and new status.

#### Phase 3: Fetch & Display Errors

15. The frontend immediately fetches the detected errors via `GET /api/feedback/submissions/{id}/errors/`.
16. The `SubmissionErrorsView` queries all `DetectedError` records for the submission. Pagination is **disabled** on this endpoint to allow the frontend to perform inline text highlighting.
17. The database returns the error records.
18. The frontend receives the full error list, each with `start_offset`, `end_offset`, `error_category`, and `severity`.
19. The frontend renders the submission text with colour-coded inline highlights at the corresponding character offsets, grouped by error category.

### Implementation References

| Component | Source |
|-----------|--------|
| Submission CRUD | `submissions/views.py` → `SubmissionListCreateView` |
| NLP trigger | `nlp/views.py` → `AnalyzeSubmissionView` |
| Error detection | `nlp/services.py` → `ErrorDetectionService`, `LanguageToolClient`, `SpacyGrammarDetector` |
| spaCy processing | `nlp/spacy_processor.py` → `SpacyTextProcessor` |
| Category mapping | `nlp/services.py` → `LanguageToolClient._map_category()`, `SpacyTextProcessor.categorize_error()` |
| Error list | `feedback/views.py` → `SubmissionErrorsView` |
| Frontend submission page | `frontend/src/routes/submissions/[id]/+page.svelte` |
| LanguageTool config | `mrgrammar/settings.py` → `MRGRAMMAR['LANGUAGETOOL_URL']` |

---

## 3. Guided Correction Workflow

**Workflow diagrams**:

- [`diagrams/my_idea_workflow_phase_1.drawio`](diagrams/my_idea_workflow_phase_1.drawio) — Phase 1 analysis and grouped highlights
- [`diagrams/my_idea_workflow_phase_2.drawio`](diagrams/my_idea_workflow_phase_2.drawio) — Phase 2 second try and hint path
- [`diagrams/my_idea_workflow_phase_3.drawio`](diagrams/my_idea_workflow_phase_3.drawio) — Phase 3 third try and answer reveal

> **Note**: [`diagrams/sequence-correction.drawio`](diagrams/sequence-correction.drawio) is a legacy correction sequence artifact and no longer reflects the current phase-led workflow as closely as the three workflow diagrams above.

### Participants

| Participant | Role |
|-------------|------|
| **Student (Browser)** | Student attempting to correct detected errors |
| **Frontend (SvelteKit)** | Renders correction UI with input field, hint display, and solution reveal |
| **FeedbackView (DRF)** | Handles correction attempt and solution request endpoints |
| **CorrectionWorkflowService** | Implements the guided correction business logic |
| **Database (PostgreSQL)** | Stores correction attempts and updates error resolution status |

### Configuration Parameters

The correction workflow is controlled by three parameters defined in `settings.MRGRAMMAR`:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `SIMILARITY_THRESHOLD` | `0.85` | Levenshtein ratio at or above which an attempt is accepted as correct |
| `HINT_THRESHOLD` | `1` | Attempt number at which a hint is revealed on failure |
| `MAX_CORRECTION_ATTEMPTS` | `2` | Attempt number at which the solution is revealed and the error is auto-resolved |

### Flow Description

The workflow now maps to the learner-facing second-try and third-try phases in the updated UI.

#### Phase 2: Second Try

1. The student clicks a highlighted error in the submission text and types a second try (for example `"die"` for an article error where the correct answer is `"das"`).
2. The frontend sends `POST /api/feedback/errors/{id}/attempt/` with `{attempted_text: "die"}`.
3. The `SubmitAttemptView` validates that the error is not already resolved, then delegates to `CorrectionWorkflowService.submit_attempt()`.
4. The service computes the Levenshtein similarity ratio between `"die"` and the correct solution `"das"`: ratio = 0.33, which is **below** the threshold of 0.85 → **incorrect**.
5. Since `attempt_number = 1` and the default configuration reveals hints on the first failed correction attempt, the response includes a hint and unlocks phase 3.
6. The service creates a `CorrectionAttempt` record (`attempt_number=1`, `is_correct=false`, `hint_shown=true`).
7. The response returns a phase-aware payload such as `{attempt_number: 1, display_attempt_number: 2, phase: "phase_2", outcome: "hint", is_correct: false, is_resolved: false, can_request_solution: true, hint: "..."}`.

#### Phase 3: Third Try

1. The student either types a third try or uses the gated reveal action.
2. If the third try is correct, the error is resolved immediately.
3. If the third try is still wrong, the service reveals the hint, the answer, and a short explanation generated by the local Ollama-hosted Gemma model.
4. The final incorrect-attempt response is shaped like `{attempt_number: 2, display_attempt_number: 3, phase: "phase_3", outcome: "solution_revealed", is_correct: false, is_resolved: true, solution: "das", explanation: "..."}`.

#### Correct Answer

1. The student submits `"das"` (the correct answer).
2. The service computes Levenshtein ratio(`"das"`, `"das"`) = 1.0 ≥ 0.85 → **correct**.
3. The service marks the `DetectedError` as resolved (`is_resolved = true`) and creates a `CorrectionAttempt` record (`is_correct=true`).
4. The response returns a phase-aware payload such as `{attempt_number: 1, display_attempt_number: 2, phase: "phase_2", outcome: "correct", is_correct: true, is_resolved: true}`.
5. The frontend removes the error highlight and shows a success indicator.

#### Alternative: Gated Manual Reveal

After phase 2 has been failed once, the student may use the gated reveal action instead of typing the third try:

1. The frontend sends `POST /api/feedback/errors/{id}/solution/`.
2. The `RequestSolutionView` verifies that reveal is unlocked, then retrieves the hint and answer and generates the short explanation.
3. The response returns a phase-3 payload such as `{phase: "phase_3", outcome: "manual_reveal", hint: "...", solution: "das", explanation: "..."}`.

### Correctness Evaluation

The `CorrectionWorkflowService` uses the **Levenshtein similarity ratio** (via the `RapidFuzz` library) to evaluate student attempts. This provides fuzzy matching that tolerates minor typos while still requiring a substantially correct answer. The threshold of 0.85 means the student's attempt must be at least 85% similar to the correct solution to be accepted.

### Implementation References

| Component | Source |
|-----------|--------|
| Attempt submission | `feedback/views.py` → `SubmitAttemptView` |
| Solution reveal | `feedback/views.py` → `RequestSolutionView` |
| Correction logic | `feedback/services.py` → `CorrectionWorkflowService` |
| Levenshtein matching | `feedback/services.py` (uses `rapidfuzz` or `Levenshtein` library) |
| Workflow config | `mrgrammar/settings.py` → `MRGRAMMAR` dict |
| Frontend correction UI | `frontend/src/routes/submissions/[id]/+page.svelte` |
