from django.conf import settings
from django.db import models


class TextSubmission(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        ANALYZING = 'analyzing', 'Analyzing'
        IN_REVIEW = 'in_review', 'In Review'
        COMPLETED = 'completed', 'Completed'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    classroom = models.ForeignKey(
        'classrooms.Classroom',
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    title = models.CharField(max_length=300)
    content = models.TextField()
    language = models.CharField(max_length=10, default='de')
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    analysis_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Celery task ID for async analysis',
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.title} by {self.student}'
