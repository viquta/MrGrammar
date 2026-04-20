from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacherOrAdmin
from .models import Classroom, ClassroomMembership
from .serializers import (
    ClassroomSerializer,
    ClassroomMembershipSerializer,
    AddMemberSerializer,
)


class ClassroomListCreateView(generics.ListCreateAPIView):
    serializer_class = ClassroomSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return Classroom.objects.all()
        return Classroom.objects.filter(memberships__user=user)

    def perform_create(self, serializer):
        classroom = serializer.save(created_by=self.request.user)
        ClassroomMembership.objects.create(
            user=self.request.user,
            classroom=classroom,
            role=ClassroomMembership.MemberRole.TEACHER,
        )


class ClassroomDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClassroomSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return Classroom.objects.all()
        return Classroom.objects.filter(memberships__user=user)


class ClassroomMembersView(generics.ListAPIView):
    serializer_class = ClassroomMembershipSerializer

    def get_queryset(self):
        return ClassroomMembership.objects.filter(
            classroom_id=self.kwargs['classroom_id'],
            classroom__memberships__user=self.request.user,
        ).select_related('user')


class AddMemberView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, classroom_id):
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify the requesting user has access to this classroom
        if not request.user.is_admin_user:
            if not ClassroomMembership.objects.filter(
                classroom_id=classroom_id,
                user=request.user,
                role=ClassroomMembership.MemberRole.TEACHER,
            ).exists():
                return Response(
                    {'detail': 'You are not a teacher in this classroom.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        membership, created = ClassroomMembership.objects.get_or_create(
            user_id=serializer.validated_data['user_id'],
            classroom_id=classroom_id,
            defaults={'role': serializer.validated_data['role']},
        )

        if not created:
            return Response(
                {'detail': 'User is already a member of this classroom.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            ClassroomMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )
