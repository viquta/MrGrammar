from django.conf import settings
from Levenshtein import ratio as levenshtein_ratio

from .models import DetectedError, CorrectionAttempt


class CorrectionWorkflowService:
    """
    Manages the guided correction workflow (FR-4):
    1. Student attempts a correction
    2. If correct → mark resolved
    3. If incorrect and below hint threshold → "try again"
    4. If incorrect and at/above hint threshold → show hint
    5. If incorrect and at/above max attempts → reveal solution
    """

    SIMILARITY_THRESHOLD = 0.85

    def __init__(self):
        config = settings.MRGRAMMAR
        self.max_attempts = config['MAX_CORRECTION_ATTEMPTS']
        self.hint_threshold = config['HINT_THRESHOLD']

    def submit_attempt(self, error: DetectedError, student, attempted_text: str) -> dict:
        attempt_number = error.attempts.count() + 1

        is_correct = self._check_correctness(attempted_text, error.correct_solution)

        show_hint = (
            not is_correct and attempt_number >= self.hint_threshold
        )
        show_solution = (
            not is_correct and attempt_number >= self.max_attempts
        )

        attempt = CorrectionAttempt.objects.create(
            error=error,
            student=student,
            attempt_number=attempt_number,
            attempted_text=attempted_text,
            is_correct=is_correct,
            hint_shown=show_hint,
            solution_shown=show_solution,
        )

        if is_correct:
            error.is_resolved = True
            error.save(update_fields=['is_resolved'])

        result = {
            'attempt_number': attempt_number,
            'is_correct': is_correct,
            'is_resolved': error.is_resolved,
        }

        if show_hint and not show_solution:
            result['hint'] = error.hint_text

        if show_solution:
            result['hint'] = error.hint_text
            result['solution'] = error.correct_solution

        return result

    def request_solution(self, error: DetectedError) -> dict:
        return {
            'hint': error.hint_text,
            'solution': error.correct_solution,
        }

    def _check_correctness(self, attempted: str, correct: str) -> bool:
        attempted_norm = attempted.strip().lower()
        correct_norm = correct.strip().lower()

        if attempted_norm == correct_norm:
            return True

        return levenshtein_ratio(attempted_norm, correct_norm) >= self.SIMILARITY_THRESHOLD
