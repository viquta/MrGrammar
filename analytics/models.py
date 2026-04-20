from django.conf import settings
from django.db import models


class LearnerErrorSummary(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='error_summaries',
    )
    submission = models.ForeignKey(
        'submissions.TextSubmission',
        on_delete=models.CASCADE,
        related_name='error_summaries',
    )
    error_category = models.CharField(max_length=20)
    total_errors = models.PositiveIntegerField(default=0)
    first_attempt_successes = models.PositiveIntegerField(default=0)
    avg_hints_used = models.FloatField(default=0.0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'submission', 'error_category']
        ordering = ['-submission__submitted_at', 'error_category']

    def __str__(self):
        return f'{self.student} – {self.error_category} ({self.submission})'
