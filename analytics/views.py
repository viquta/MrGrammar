from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacherOrAdmin
from .services import AnalyticsService


class StudentProgressView(APIView):
    def get(self, request, student_id):
        # Students can only view their own progress
        if request.user.is_student and request.user.id != student_id:
            return Response(
                {'detail': 'You can only view your own progress.'},
                status=403,
            )
        data = AnalyticsService.get_student_progress(student_id)
        return Response(data)


class ClassroomPatternsView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, classroom_id):
        data = AnalyticsService.get_classroom_patterns(classroom_id)
        return Response(data)
