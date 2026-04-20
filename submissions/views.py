from rest_framework import generics

from classrooms.models import ClassroomMembership
from .models import TextSubmission
from .serializers import TextSubmissionSerializer, TextSubmissionListSerializer


class SubmissionListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TextSubmissionListSerializer
        return TextSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_student:
            return TextSubmission.objects.filter(student=user).select_related('student')
        if user.is_teacher:
            classroom_ids = ClassroomMembership.objects.filter(
                user=user, role=ClassroomMembership.MemberRole.TEACHER,
            ).values_list('classroom_id', flat=True)
            return TextSubmission.objects.filter(
                classroom_id__in=classroom_ids,
            ).select_related('student')
        return TextSubmission.objects.all().select_related('student')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class SubmissionDetailView(generics.RetrieveAPIView):
    serializer_class = TextSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_student:
            return TextSubmission.objects.filter(student=user)
        if user.is_teacher:
            classroom_ids = ClassroomMembership.objects.filter(
                user=user, role=ClassroomMembership.MemberRole.TEACHER,
            ).values_list('classroom_id', flat=True)
            return TextSubmission.objects.filter(classroom_id__in=classroom_ids)
        return TextSubmission.objects.all()
