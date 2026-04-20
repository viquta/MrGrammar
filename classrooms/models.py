from django.conf import settings
from django.db import models


class Classroom(models.Model):
    name = models.CharField(max_length=200)
    language = models.CharField(max_length=10, default='de')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_classrooms',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ClassroomMembership(models.Model):
    class MemberRole(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='classroom_memberships',
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=10, choices=MemberRole.choices)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'classroom']
        ordering = ['classroom', 'role', 'user']

    def __str__(self):
        return f'{self.user} in {self.classroom} ({self.role})'
