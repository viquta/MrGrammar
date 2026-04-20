from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from classrooms.models import ClassroomMembership
from .models import DetectedError
from .serializers import (
    DetectedErrorSerializer,
    DetectedErrorDetailSerializer,
    SubmitAttemptSerializer,
)
from .services import CorrectionWorkflowService


class SubmissionErrorsView(generics.ListAPIView):
    serializer_class = DetectedErrorSerializer
    pagination_class = None  # Always return all errors — needed for highlight rendering

    def get_queryset(self):
        return DetectedError.objects.filter(
            submission_id=self.kwargs['submission_id'],
        ).prefetch_related('attempts')


class ErrorDetailView(generics.RetrieveAPIView):
    serializer_class = DetectedErrorDetailSerializer
    queryset = DetectedError.objects.all()


class SubmitAttemptView(APIView):
    def post(self, request, pk):
        try:
            error = DetectedError.objects.get(pk=pk)
        except DetectedError.DoesNotExist:
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
        try:
            error = DetectedError.objects.get(pk=pk)
        except DetectedError.DoesNotExist:
            return Response(
                {'detail': 'Error not found.'}, status=status.HTTP_404_NOT_FOUND,
            )

        service = CorrectionWorkflowService()
        result = service.request_solution(error)

        error.is_resolved = True
        error.save(update_fields=['is_resolved'])

        return Response(result, status=status.HTTP_200_OK)
