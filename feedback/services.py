from django.conf import settings
from Levenshtein import ratio as levenshtein_ratio

from .explanations import ExplanationGenerationService
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
        self.explanations = ExplanationGenerationService()

    def submit_attempt(self, error: DetectedError, student, attempted_text: str) -> dict:
        attempt_number = error.attempts.count() + 1
        if attempt_number > self.max_attempts:
            return {
                'attempt_number': error.attempts.count(),
                'display_attempt_number': error.attempts.count() + 1,
                'phase': self._phase_for_attempt(error.attempts.count()),
                'outcome': 'locked',
                'is_correct': False,
                'is_resolved': error.is_resolved,
                'can_request_solution': False,
            }

        is_correct = self._check_correctness(attempted_text, error.correct_solution)

        show_hint = (
            not is_correct and attempt_number >= self.hint_threshold and attempt_number < self.max_attempts
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
        elif show_solution:
            error.is_resolved = True
        if is_correct or show_solution:
            error.save(update_fields=['is_resolved'])

        result = {
            'attempt_number': attempt_number,
            'display_attempt_number': attempt_number + 1,
            'phase': self._phase_for_attempt(attempt_number),
            'outcome': self._outcome_for_attempt(is_correct, show_hint, show_solution),
            'is_correct': is_correct,
            'is_resolved': error.is_resolved,
            'can_request_solution': self.can_request_solution(error),
        }

        if show_hint and not show_solution:
            result['hint'] = error.hint_text

        if show_solution:
            result['hint'] = error.hint_text
            result['solution'] = error.correct_solution
            result['explanation'] = self.explanations.generate(error, attempted_text)
            result['can_request_solution'] = False

        return result

    def request_solution(self, error: DetectedError, attempted_text: str = '') -> dict:
        return {
            'attempt_number': error.attempts.count(),
            'display_attempt_number': error.attempts.count() + 1,
            'phase': 'phase_3',
            'outcome': 'manual_reveal',
            'is_correct': False,
            'is_resolved': True,
            'can_request_solution': False,
            'hint': error.hint_text,
            'solution': error.correct_solution,
            'explanation': self.explanations.generate(error, attempted_text),
        }

    def can_request_solution(self, error: DetectedError) -> bool:
        return not error.is_resolved and error.attempts.count() >= max(1, self.hint_threshold)

    def _phase_for_attempt(self, attempt_number: int) -> str:
        return 'phase_2' if attempt_number <= 1 else 'phase_3'

    def _outcome_for_attempt(self, is_correct: bool, show_hint: bool, show_solution: bool) -> str:
        if is_correct:
            return 'correct'
        if show_solution:
            return 'solution_revealed'
        if show_hint:
            return 'hint'
        return 'retry'

    def _check_correctness(self, attempted: str, correct: str) -> bool:
        attempted_norm = attempted.strip().lower()
        correct_norm = correct.strip().lower()

        if attempted_norm == correct_norm:
            return True

        return levenshtein_ratio(attempted_norm, correct_norm) >= self.SIMILARITY_THRESHOLD
