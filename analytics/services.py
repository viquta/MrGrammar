from django.db.models import Count, Avg, Q

from feedback.models import DetectedError, CorrectionAttempt
from submissions.models import TextSubmission
from .models import LearnerErrorSummary


class AnalyticsService:
    """Computes and caches learner analytics (FR-5, FR-6, FR-7)."""

    @staticmethod
    def compute_summary_for_submission(submission: TextSubmission):
        errors = submission.errors.all()
        categories = errors.values_list('error_category', flat=True).distinct()

        summaries = []
        for category in categories:
            cat_errors = errors.filter(error_category=category)
            total = cat_errors.count()

            first_attempt_ok = 0
            total_hints = 0
            for error in cat_errors:
                first_attempt = error.attempts.filter(attempt_number=1).first()
                if first_attempt and first_attempt.is_correct:
                    first_attempt_ok += 1
                total_hints += error.attempts.filter(hint_shown=True).count()

            avg_hints = total_hints / total if total > 0 else 0.0

            summary, _ = LearnerErrorSummary.objects.update_or_create(
                student=submission.student,
                submission=submission,
                error_category=category,
                defaults={
                    'total_errors': total,
                    'first_attempt_successes': first_attempt_ok,
                    'avg_hints_used': avg_hints,
                },
            )
            summaries.append(summary)

        return summaries

    @staticmethod
    def get_student_progress(student_id: int) -> list[dict]:
        return list(
            LearnerErrorSummary.objects.filter(student_id=student_id)
            .values('error_category', 'submission__submitted_at')
            .annotate(
                errors=Count('total_errors'),
            )
            .order_by('submission__submitted_at')
        )

    @staticmethod
    def get_classroom_patterns(classroom_id: int) -> list[dict]:
        return list(
            DetectedError.objects.filter(submission__classroom_id=classroom_id)
            .values('error_category')
            .annotate(
                count=Count('id'),
                resolved_count=Count('id', filter=Q(is_resolved=True)),
            )
            .order_by('-count')
        )
