from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DetectedError
from .serializers import (
    DetectedErrorSerializer,
    DetectedErrorDetailSerializer,
    RequestSolutionSerializer,
    SubmitAttemptSerializer,
)
from .services import CorrectionWorkflowService


class SubmissionErrorsView(generics.ListAPIView):
    serializer_class = DetectedErrorSerializer
    pagination_class = None  # Always return all errors — needed for highlight rendering

    def get_queryset(self):
        return DetectedError.objects.filter(
            submission_id=self.kwargs['submission_id'],
            submission__student=self.request.user,
        ).prefetch_related('attempts')


class ErrorDetailView(generics.RetrieveAPIView):
    serializer_class = DetectedErrorDetailSerializer

    def get_queryset(self):
        return DetectedError.objects.filter(submission__student=self.request.user)


def _get_owned_error(pk, user):
    try:
        return DetectedError.objects.get(pk=pk, submission__student=user)
    except DetectedError.DoesNotExist:
        return None


class SubmitAttemptView(APIView):
    def post(self, request, pk):
        error = _get_owned_error(pk, request.user)
        if error is None:
            return Response(
                {'detail': 'Error not found.'}, status=status.HTTP_404_NOT_FOUND,
            )

        if error.is_resolved:
            return Response(
                {'detail': 'This error has already been resolved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmitAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CorrectionWorkflowService()
        result = service.submit_attempt(
            error=error,
            student=request.user,
            attempted_text=serializer.validated_data['attempted_text'],
        )

        return Response(result, status=status.HTTP_200_OK)


class RequestSolutionView(APIView):
    def post(self, request, pk):
        error = _get_owned_error(pk, request.user)
        if error is None:
            return Response(
                {'detail': 'Error not found.'}, status=status.HTTP_404_NOT_FOUND,
            )

        service = CorrectionWorkflowService()
        if error.is_resolved:
            return Response(
                {'detail': 'This error has already been resolved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not service.can_request_solution(error):
            return Response(
                {'detail': 'Solution reveal is not available yet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RequestSolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = service.request_solution(
            error,
            attempted_text=serializer.validated_data.get('attempted_text', ''),
        )

        return Response(result, status=status.HTTP_200_OK)
