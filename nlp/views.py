import logging

from celery.result import AsyncResult
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from submissions.models import TextSubmission
from .tasks import analyze_submission_async


logger = logging.getLogger(__name__)


class AnalyzeSubmissionView(APIView):
    """
    API endpoint to trigger async analysis of a submission.
    
    If submission already has errors (completed), returns 200 with error count.
    If analysis is pending, returns 202 (Accepted) with task ID for polling.
    If new submission, queues async task and returns 202 (Accepted).
    """

    def post(self, request, submission_id):
        """
        POST /api/nlp/submissions/{submission_id}/analyze/
        
        Returns:
            - 200: Analysis already complete, includes error count
            - 202: Analysis queued/in-progress, includes task_id and polling URL
            - 404: Submission not found
            - 400: Already analyzed or invalid state
        """
        try:
            submission = TextSubmission.objects.get(
                pk=submission_id, student=request.user,
            )
        except TextSubmission.DoesNotExist:
            return Response(
                {'detail': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # If already completed with errors, return 200 with cached result
        if submission.status == TextSubmission.Status.IN_REVIEW:
            errors_count = submission.errors.count()
            return Response(
                {
                    'submission_id': submission.id,
                    'status': submission.status,
                    'errors_found': errors_count,
                    'message': 'Analysis already complete.',
                },
                status=status.HTTP_200_OK,
            )

        # If already analyzing, return 202 with existing task ID
        if submission.status == TextSubmission.Status.ANALYZING:
            if submission.analysis_task_id:
                return Response(
                    {
                        'submission_id': submission.id,
                        'task_id': submission.analysis_task_id,
                        'status': submission.status,
                        'message': 'Analysis already in progress.',
                        'status_url': f'/api/nlp/submissions/{submission.id}/status/',
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

        # Queue new analysis task
        submission.status = TextSubmission.Status.ANALYZING
        submission.save(update_fields=['status'])

        try:
            # Queue async task
            task = analyze_submission_async.delay(submission_id)
            
            # Store task ID on submission for tracking
            submission.analysis_task_id = task.id
            submission.save(update_fields=['analysis_task_id'])

            logger.info(f'Queued analysis for submission {submission_id}, task_id={task.id}')

            return Response(
                {
                    'submission_id': submission.id,
                    'task_id': task.id,
                    'status': submission.status,
                    'message': 'Analysis queued.',
                    'status_url': f'/api/nlp/submissions/{submission.id}/status/',
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as exc:
            logger.exception(f'Failed to queue analysis for submission {submission_id}: {exc}')
            submission.status = TextSubmission.Status.SUBMITTED
            submission.save(update_fields=['status'])
            return Response(
                {'detail': 'Failed to queue analysis. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AnalysisStatusView(APIView):
    """
    API endpoint to poll analysis status.
    
    Client polls this endpoint to check if analysis is complete and get results.
    """

    def get(self, request, submission_id):
        """
        GET /api/nlp/submissions/{submission_id}/status/
        
        Returns:
            {
                'submission_id': int,
                'status': str (submitted|analyzing|completed),
                'errors_found': int or null,
                'task_id': str or null,
                'is_complete': bool,
            }
        """
        try:
            submission = TextSubmission.objects.get(
                pk=submission_id, student=request.user,
            )
        except TextSubmission.DoesNotExist:
            return Response(
                {'detail': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = {
            'submission_id': submission.id,
            'status': submission.status,
            'task_id': submission.analysis_task_id,
            'is_complete': submission.status == TextSubmission.Status.IN_REVIEW,
            'errors_found': None,
        }

        # If analysis complete, include error count
        if submission.status == TextSubmission.Status.IN_REVIEW:
            response_data['errors_found'] = submission.errors.count()
            return Response(response_data, status=status.HTTP_200_OK)

        # If analyzing with a task ID, check task status
        if submission.analysis_task_id:
            try:
                task_result = AsyncResult(submission.analysis_task_id)
                response_data['task_state'] = task_result.state
                
                # If task failed, return error
                if task_result.state == 'FAILURE':
                    logger.error(
                        f'Analysis task failed for submission {submission_id}: {task_result.info}'
                    )
                    response_data['error'] = 'Analysis task failed'
                    submission.status = TextSubmission.Status.SUBMITTED
                    submission.save(update_fields=['status'])
                    return Response(response_data, status=status.HTTP_200_OK)

            except Exception as exc:
                logger.warning(f'Could not check task status: {exc}')

        return Response(response_data, status=status.HTTP_200_OK)
