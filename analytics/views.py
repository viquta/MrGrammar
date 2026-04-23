from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacherOrAdmin
from classrooms.models import ClassroomMembership
from .services import AnalyticsService


class StudentProgressView(APIView):
    def get(self, request, student_id):
        # Students can only view their own progress
        if request.user.is_student and request.user.id != student_id:
            return Response(
                {'detail': 'You can only view your own progress.'},
                status=403,
            )
        if request.user.is_teacher and not ClassroomMembership.objects.filter(
            user=request.user,
            role=ClassroomMembership.MemberRole.TEACHER,
            classroom__memberships__user_id=student_id,
            classroom__memberships__role=ClassroomMembership.MemberRole.STUDENT,
        ).exists():
            return Response(
                {'detail': 'You do not have access to this student.'},
                status=403,
            )
        data = AnalyticsService.get_student_progress(student_id)
        return Response(data)


class ClassroomPatternsView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, classroom_id):
        if request.user.is_teacher and not ClassroomMembership.objects.filter(
            classroom_id=classroom_id,
            user=request.user,
            role=ClassroomMembership.MemberRole.TEACHER,
        ).exists():
            return Response(
                {'detail': 'You are not a teacher in this classroom.'},
                status=403,
            )
        data = AnalyticsService.get_classroom_patterns(classroom_id)
        return Response(data)
