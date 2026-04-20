from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from submissions.models import TextSubmission
from .services import ErrorDetectionService


class AnalyzeSubmissionView(APIView):
    def post(self, request, submission_id):
        try:
            submission = TextSubmission.objects.get(
                pk=submission_id, student=request.user,
            )
        except TextSubmission.DoesNotExist:
            return Response(
                {'detail': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if submission.errors.exists():
            return Response(
                {'detail': 'This submission has already been analyzed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission.status = TextSubmission.Status.ANALYZING
        submission.save(update_fields=['status'])

        service = ErrorDetectionService()
        errors = service.analyze(submission)

        submission.status = TextSubmission.Status.IN_REVIEW
        submission.save(update_fields=['status'])

        return Response(
            {
                'submission_id': submission.id,
                'errors_found': len(errors),
                'status': submission.status,
            },
            status=status.HTTP_200_OK,
        )
