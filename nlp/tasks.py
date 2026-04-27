import logging
from celery import shared_task
from django.db import transaction

from submissions.models import TextSubmission
from analytics.services import AnalyticsService
from .services import ErrorDetectionService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def analyze_submission_async(self, submission_id):
    """
    Async task to analyze a submission text and detect errors.
    
    This runs all three detectors (LanguageTool, Spacy, Advanced German)
    and bulk inserts DetectedError records.
    
    Args:
        submission_id: ID of the TextSubmission to analyze
        
    Returns:
        dict with submission_id and errors_found count
    """
    try:
        submission = TextSubmission.objects.get(id=submission_id)
    except TextSubmission.DoesNotExist:
        logger.error(f'Submission {submission_id} not found')
        return {'error': 'Submission not found', 'submission_id': submission_id}

    try:
        # Set status to ANALYZING if not already
        if submission.status != TextSubmission.Status.ANALYZING:
            submission.status = TextSubmission.Status.ANALYZING
            submission.save(update_fields=['status'])

        # Run error detection service
        service = ErrorDetectionService()
        errors = service.analyze(submission)

        # Update submission status to IN_REVIEW (analysis complete) after successful analysis
        with transaction.atomic():
            submission.status = TextSubmission.Status.IN_REVIEW
            submission.save(update_fields=['status', 'updated_at'])

            # Compute analytics summary
            AnalyticsService.compute_summary_for_submission(submission)

        logger.info(
            f'Successfully analyzed submission {submission_id}. Found {len(errors)} errors.'
        )
        return {
            'submission_id': submission_id,
            'errors_found': len(errors),
            'status': submission.status,
        }

    except Exception as exc:
        logger.exception(
            f'Error analyzing submission {submission_id}: {exc}'
        )
        
        # Mark submission as failed
        submission.status = TextSubmission.Status.SUBMITTED
        submission.save(update_fields=['status'])

        # Retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            logger.error(
                f'Max retries exceeded for submission {submission_id}'
            )
            return {
                'error': 'Analysis failed after max retries',
                'submission_id': submission_id,
            }
