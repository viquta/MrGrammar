from django.conf import settings
from django.db import models


class DetectedError(models.Model):
    class Category(models.TextChoices):
        GRAMMAR = 'grammar', 'Grammar'
        SPELLING = 'spelling', 'Spelling'
        ARTICLE = 'article', 'Article'
        PREPOSITION = 'preposition', 'Preposition'
        VERB_TENSE = 'verb_tense', 'Verb Tense'
        PUNCTUATION = 'punctuation', 'Punctuation'
        OTHER = 'other', 'Other'

    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    submission = models.ForeignKey(
        'submissions.TextSubmission',
        on_delete=models.CASCADE,
        related_name='errors',
    )
    error_category = models.CharField(max_length=20, choices=Category.choices)
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM,
    )
    start_offset = models.PositiveIntegerField()
    end_offset = models.PositiveIntegerField()
    original_text = models.TextField()
    hint_text = models.TextField(blank=True)
    correct_solution = models.TextField()
    languagetool_rule_id = models.CharField(max_length=100, blank=True)
    spacy_pos_tag = models.CharField(max_length=20, blank=True)
    error_context = models.JSONField(default=dict, blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_offset']

    def __str__(self):
        return f'[{self.error_category}] "{self.original_text}" in submission {self.submission_id}'


class CorrectionAttempt(models.Model):
    error = models.ForeignKey(
        DetectedError,
        on_delete=models.CASCADE,
        related_name='attempts',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='correction_attempts',
    )
    attempt_number = models.PositiveSmallIntegerField()
    attempted_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    hint_shown = models.BooleanField(default=False)
    solution_shown = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['error', 'attempt_number']
        unique_together = ['error', 'attempt_number']

    def __str__(self):
        status = 'correct' if self.is_correct else 'incorrect'
        return f'Attempt {self.attempt_number} ({status}) for error {self.error_id}'
