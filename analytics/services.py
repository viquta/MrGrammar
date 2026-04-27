from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Prefetch, Q, Sum

from classrooms.models import Classroom
from feedback.models import DetectedError, CorrectionAttempt
from submissions.models import TextSubmission
from .models import LearnerErrorSummary


User = get_user_model()


class AnalyticsService:
    """Computes and caches learner analytics (FR-5, FR-6, FR-7)."""

    @staticmethod
    def compute_summary_for_submission(submission: TextSubmission):
        # Single aggregated query per submission — no per-error DB round-trips
        error_stats = (
            DetectedError.objects
            .filter(submission=submission)
            .values('error_category')
            .annotate(
                total=Count('id'),
                first_ok=Count(
                    'attempts__id',
                    filter=Q(attempts__attempt_number=1, attempts__is_correct=True),
                ),
                hints_used=Count(
                    'attempts__id',
                    filter=Q(attempts__hint_shown=True),
                ),
            )
        )

        summaries = []
        for stat in error_stats:
            category = stat['error_category']
            total = stat['total']
            avg_hints = stat['hints_used'] / total if total > 0 else 0.0

            summary, _ = LearnerErrorSummary.objects.update_or_create(
                student=submission.student,
                submission=submission,
                error_category=category,
                defaults={
                    'total_errors': total,
                    'first_attempt_successes': stat['first_ok'],
                    'avg_hints_used': avg_hints,
                },
            )
            summaries.append(summary)

        return summaries

    @staticmethod
    def get_student_progress(student_id: int) -> dict:
        student = User.objects.get(pk=student_id)
        submissions = list(
            TextSubmission.objects.filter(student_id=student_id)
            .prefetch_related(
                Prefetch(
                    'errors',
                    queryset=DetectedError.objects.prefetch_related('attempts').order_by('start_offset'),
                ),
                'error_summaries',
            )
            .order_by('submitted_at')
        )

        category_rollups: dict[str, dict] = {}
        submission_rows = []
        total_errors = 0
        resolved_errors = 0
        total_first_attempt_successes = 0
        total_hint_shown_errors = 0
        total_manual_reveals = 0
        total_solution_reveals = 0
        total_attempts = 0

        for submission in submissions:
            errors = list(submission.errors.all())
            error_summaries = {
                summary.error_category: summary
                for summary in submission.error_summaries.all()
            }

            submission_total_errors = len(errors)
            submission_resolved_errors = 0
            submission_first_attempt_successes = 0
            submission_hint_shown_errors = 0
            submission_manual_reveals = 0
            submission_solution_reveals = 0
            submission_attempts = 0
            submission_categories = []

            for error in errors:
                attempts = list(error.attempts.all())
                attempt_count = len(attempts)
                hint_shown = any(attempt.hint_shown for attempt in attempts)
                first_attempt_success = bool(attempts and attempts[0].is_correct)

                submission_attempts += attempt_count
                if error.is_resolved:
                    submission_resolved_errors += 1
                if first_attempt_success:
                    submission_first_attempt_successes += 1
                if hint_shown:
                    submission_hint_shown_errors += 1
                if error.resolution_method == DetectedError.ResolutionMethod.MANUAL_REVEAL:
                    submission_manual_reveals += 1
                if error.resolution_method == DetectedError.ResolutionMethod.SOLUTION_REVEALED:
                    submission_solution_reveals += 1

            for category, summary in error_summaries.items():
                category_errors = [error for error in errors if error.error_category == category]
                category_resolved = sum(1 for error in category_errors if error.is_resolved)
                category_manual_reveals = sum(
                    1
                    for error in category_errors
                    if error.resolution_method == DetectedError.ResolutionMethod.MANUAL_REVEAL
                )
                category_hint_shown = sum(
                    1
                    for error in category_errors
                    if any(attempt.hint_shown for attempt in error.attempts.all())
                )
                # Use len() on prefetched attempts to avoid COUNT query per error
                category_attempts = sum(
                    len(list(error.attempts.all())) for error in category_errors
                )

                submission_categories.append({
                    'error_category': category,
                    'total_errors': summary.total_errors,
                    'resolved_errors': category_resolved,
                    'first_attempt_successes': summary.first_attempt_successes,
                    'avg_hints_used': round(summary.avg_hints_used, 2),
                    'hint_shown_errors': category_hint_shown,
                    'manual_reveal_count': category_manual_reveals,
                    'attempt_count': category_attempts,
                })

                rollup = category_rollups.setdefault(
                    category,
                    {
                        'error_category': category,
                        'total_errors': 0,
                        'resolved_errors': 0,
                        'first_attempt_successes': 0,
                        'hint_shown_errors': 0,
                        'manual_reveal_count': 0,
                        'attempt_count': 0,
                        'timeline': [],
                    },
                )
                rollup['total_errors'] += summary.total_errors
                rollup['resolved_errors'] += category_resolved
                rollup['first_attempt_successes'] += summary.first_attempt_successes
                rollup['hint_shown_errors'] += category_hint_shown
                rollup['manual_reveal_count'] += category_manual_reveals
                rollup['attempt_count'] += category_attempts
                rollup['timeline'].append({
                    'submission_id': submission.id,
                    'submission_title': submission.title,
                    'submitted_at': submission.submitted_at,
                    'total_errors': summary.total_errors,
                    'resolved_errors': category_resolved,
                    'first_attempt_successes': summary.first_attempt_successes,
                    'avg_hints_used': round(summary.avg_hints_used, 2),
                    'hint_shown_errors': category_hint_shown,
                    'manual_reveal_count': category_manual_reveals,
                })

            total_errors += submission_total_errors
            resolved_errors += submission_resolved_errors
            total_first_attempt_successes += submission_first_attempt_successes
            total_hint_shown_errors += submission_hint_shown_errors
            total_manual_reveals += submission_manual_reveals
            total_solution_reveals += submission_solution_reveals
            total_attempts += submission_attempts

            submission_rows.append({
                'submission_id': submission.id,
                'title': submission.title,
                'status': submission.status,
                'submitted_at': submission.submitted_at,
                'total_errors': submission_total_errors,
                'resolved_errors': submission_resolved_errors,
                'first_attempt_successes': submission_first_attempt_successes,
                'hint_shown_errors': submission_hint_shown_errors,
                'manual_reveal_count': submission_manual_reveals,
                'solution_reveal_count': submission_solution_reveals,
                'attempt_count': submission_attempts,
                'categories': sorted(
                    submission_categories,
                    key=lambda item: (-item['total_errors'], item['error_category']),
                ),
            })

        category_breakdown = []
        for rollup in category_rollups.values():
            total_category_errors = rollup['total_errors'] or 1
            category_breakdown.append({
                'error_category': rollup['error_category'],
                'total_errors': rollup['total_errors'],
                'resolved_errors': rollup['resolved_errors'],
                'first_attempt_successes': rollup['first_attempt_successes'],
                'first_attempt_success_rate': round(rollup['first_attempt_successes'] / total_category_errors, 2),
                'avg_hints_used': round(rollup['hint_shown_errors'] / total_category_errors, 2),
                'hint_shown_errors': rollup['hint_shown_errors'],
                'manual_reveal_count': rollup['manual_reveal_count'],
                'avg_attempts_per_error': round(rollup['attempt_count'] / total_category_errors, 2),
                'timeline': rollup['timeline'],
            })

        category_breakdown.sort(key=lambda item: (-item['total_errors'], item['error_category']))
        overall_total_errors = total_errors or 1

        return {
            'student': {
                'id': student.id,
                'username': student.username,
                'full_name': student.get_full_name(),
            },
            'overview': {
                'submission_count': len(submissions),
                'total_errors': total_errors,
                'resolved_errors': resolved_errors,
                'resolution_rate': round(resolved_errors / overall_total_errors, 2),
                'first_attempt_successes': total_first_attempt_successes,
                'first_attempt_success_rate': round(total_first_attempt_successes / overall_total_errors, 2),
                'hint_shown_errors': total_hint_shown_errors,
                'hint_usage_rate': round(total_hint_shown_errors / overall_total_errors, 2),
                'manual_reveal_count': total_manual_reveals,
                'solution_reveal_count': total_solution_reveals,
                'avg_attempts_per_error': round(total_attempts / overall_total_errors, 2),
                'last_submission_at': submissions[-1].submitted_at if submissions else None,
            },
            'submissions': submission_rows,
            'category_breakdown': category_breakdown,
        }

    @staticmethod
    def get_classroom_patterns(classroom_id: int) -> dict:
        classroom = Classroom.objects.get(pk=classroom_id)
        classroom_submissions = list(
            TextSubmission.objects.filter(classroom_id=classroom_id)
            .select_related('student', 'classroom')
            .prefetch_related(
                Prefetch(
                    'errors',
                    queryset=DetectedError.objects.prefetch_related('attempts').order_by('start_offset'),
                ),
                'error_summaries',
            )
            .order_by('submitted_at')
        )

        student_memberships = list(
            User.objects.filter(
                classroom_memberships__classroom_id=classroom_id,
                classroom_memberships__role='student',
            )
            .distinct()
            .order_by('last_name', 'first_name', 'username')
        )

        errors = [error for submission in classroom_submissions for error in submission.errors.all()]
        total_errors = len(errors)
        resolved_errors = sum(1 for error in errors if error.is_resolved)
        first_attempt_successes = sum(
            1
            for error in errors
            if (atts := list(error.attempts.all())) and atts[0].is_correct
        )
        hint_shown_errors = sum(
            1
            for error in errors
            if any(attempt.hint_shown for attempt in error.attempts.all())
        )
        manual_reveals = sum(
            1
            for error in errors
            if error.resolution_method == DetectedError.ResolutionMethod.MANUAL_REVEAL
        )
        solution_reveals = sum(
            1
            for error in errors
            if error.resolution_method == DetectedError.ResolutionMethod.SOLUTION_REVEALED
        )
        # Use len() on prefetched attempts to avoid COUNT query per error
        total_attempts = sum(len(list(error.attempts.all())) for error in errors)

        category_rollups: dict[str, dict] = {}
        timeline_rows = []
        student_rollups: dict[int, dict] = {}

        for student in student_memberships:
            student_rollups[student.id] = {
                'student_id': student.id,
                'username': student.username,
                'full_name': student.get_full_name(),
                'submission_count': 0,
                'total_errors': 0,
                'resolved_errors': 0,
                'first_attempt_successes': 0,
                'hint_shown_errors': 0,
                'manual_reveal_count': 0,
                'attempt_count': 0,
                'last_submission_at': None,
                'top_error_category': None,
                '_category_counter': defaultdict(int),
            }

        for submission in classroom_submissions:
            submission_errors = list(submission.errors.all())
            submission_summaries = {
                summary.error_category: summary
                for summary in submission.error_summaries.all()
            }
            submission_resolved = sum(1 for error in submission_errors if error.is_resolved)
            submission_first_attempt_successes = sum(
                1
                for error in submission_errors
                if (atts := list(error.attempts.all())) and atts[0].is_correct
            )
            submission_hint_shown = sum(
                1
                for error in submission_errors
                if any(attempt.hint_shown for attempt in error.attempts.all())
            )
            submission_manual_reveals = sum(
                1
                for error in submission_errors
                if error.resolution_method == DetectedError.ResolutionMethod.MANUAL_REVEAL
            )

            timeline_rows.append({
                'submission_id': submission.id,
                'submission_title': submission.title,
                'submitted_at': submission.submitted_at,
                'student_id': submission.student_id,
                'student_name': submission.student.get_full_name(),
                'total_errors': len(submission_errors),
                'resolved_errors': submission_resolved,
                'first_attempt_successes': submission_first_attempt_successes,
                'hint_shown_errors': submission_hint_shown,
                'manual_reveal_count': submission_manual_reveals,
            })

            student_rollup = student_rollups[submission.student_id]
            student_rollup['submission_count'] += 1
            student_rollup['total_errors'] += len(submission_errors)
            student_rollup['resolved_errors'] += submission_resolved
            student_rollup['first_attempt_successes'] += submission_first_attempt_successes
            student_rollup['hint_shown_errors'] += submission_hint_shown
            student_rollup['manual_reveal_count'] += submission_manual_reveals
            student_rollup['attempt_count'] += sum(
                len(list(error.attempts.all())) for error in submission_errors
            )
            student_rollup['last_submission_at'] = submission.submitted_at

            for category, summary in submission_summaries.items():
                category_errors = [error for error in submission_errors if error.error_category == category]
                category_resolved = sum(1 for error in category_errors if error.is_resolved)
                category_hint_shown = sum(
                    1
                    for error in category_errors
                    if any(attempt.hint_shown for attempt in error.attempts.all())
                )
                category_manual_reveals = sum(
                    1
                    for error in category_errors
                    if error.resolution_method == DetectedError.ResolutionMethod.MANUAL_REVEAL
                )
                # Use len() on prefetched attempts to avoid COUNT query per error
                category_attempts = sum(
                    len(list(error.attempts.all())) for error in category_errors
                )

                rollup = category_rollups.setdefault(
                    category,
                    {
                        'error_category': category,
                        'total_errors': 0,
                        'resolved_errors': 0,
                        'first_attempt_successes': 0,
                        'hint_shown_errors': 0,
                        'manual_reveal_count': 0,
                        'attempt_count': 0,
                        'timeline': [],
                    },
                )
                rollup['total_errors'] += summary.total_errors
                rollup['resolved_errors'] += category_resolved
                rollup['first_attempt_successes'] += summary.first_attempt_successes
                rollup['hint_shown_errors'] += category_hint_shown
                rollup['manual_reveal_count'] += category_manual_reveals
                rollup['attempt_count'] += category_attempts
                rollup['timeline'].append({
                    'submission_id': submission.id,
                    'submission_title': submission.title,
                    'submitted_at': submission.submitted_at,
                    'student_id': submission.student_id,
                    'student_name': submission.student.get_full_name(),
                    'total_errors': summary.total_errors,
                    'resolved_errors': category_resolved,
                    'first_attempt_successes': summary.first_attempt_successes,
                    'hint_shown_errors': category_hint_shown,
                    'manual_reveal_count': category_manual_reveals,
                })

                student_rollup['_category_counter'][category] += summary.total_errors

        category_breakdown = []
        for rollup in category_rollups.values():
            total_category_errors = rollup['total_errors'] or 1
            category_breakdown.append({
                'error_category': rollup['error_category'],
                'total_errors': rollup['total_errors'],
                'resolved_errors': rollup['resolved_errors'],
                'resolution_rate': round(rollup['resolved_errors'] / total_category_errors, 2),
                'first_attempt_successes': rollup['first_attempt_successes'],
                'first_attempt_success_rate': round(rollup['first_attempt_successes'] / total_category_errors, 2),
                'hint_shown_errors': rollup['hint_shown_errors'],
                'hint_usage_rate': round(rollup['hint_shown_errors'] / total_category_errors, 2),
                'manual_reveal_count': rollup['manual_reveal_count'],
                'avg_attempts_per_error': round(rollup['attempt_count'] / total_category_errors, 2),
                'timeline': rollup['timeline'],
            })
        category_breakdown.sort(key=lambda item: (-item['total_errors'], item['error_category']))

        student_rows = []
        for rollup in student_rollups.values():
            total_student_errors = rollup['total_errors'] or 1
            top_category = None
            if rollup['_category_counter']:
                top_category = max(
                    rollup['_category_counter'].items(),
                    key=lambda item: (item[1], item[0]),
                )[0]

            student_rows.append({
                'student_id': rollup['student_id'],
                'username': rollup['username'],
                'full_name': rollup['full_name'],
                'submission_count': rollup['submission_count'],
                'total_errors': rollup['total_errors'],
                'resolved_errors': rollup['resolved_errors'],
                'resolution_rate': round(rollup['resolved_errors'] / total_student_errors, 2),
                'first_attempt_successes': rollup['first_attempt_successes'],
                'first_attempt_success_rate': round(rollup['first_attempt_successes'] / total_student_errors, 2),
                'hint_shown_errors': rollup['hint_shown_errors'],
                'hint_usage_rate': round(rollup['hint_shown_errors'] / total_student_errors, 2),
                'manual_reveal_count': rollup['manual_reveal_count'],
                'avg_attempts_per_error': round(rollup['attempt_count'] / total_student_errors, 2),
                'top_error_category': top_category,
                'last_submission_at': rollup['last_submission_at'],
            })
        student_rows.sort(key=lambda item: (-item['total_errors'], item['full_name'] or item['username']))

        overall_total_errors = total_errors or 1
        return {
            'classroom': {
                'id': classroom_id,
                'name': classroom.name,
                'language': classroom.language,
            },
            'overview': {
                'student_count': len(student_memberships),
                'submission_count': len(classroom_submissions),
                'total_errors': total_errors,
                'resolved_errors': resolved_errors,
                'resolution_rate': round(resolved_errors / overall_total_errors, 2),
                'first_attempt_successes': first_attempt_successes,
                'first_attempt_success_rate': round(first_attempt_successes / overall_total_errors, 2),
                'hint_shown_errors': hint_shown_errors,
                'hint_usage_rate': round(hint_shown_errors / overall_total_errors, 2),
                'manual_reveal_count': manual_reveals,
                'solution_reveal_count': solution_reveals,
                'avg_attempts_per_error': round(total_attempts / overall_total_errors, 2),
            },
            'timeline': timeline_rows,
            'category_breakdown': category_breakdown,
            'students': student_rows,
        }
