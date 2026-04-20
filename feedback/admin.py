from django.contrib import admin

from .models import DetectedError, CorrectionAttempt


class AttemptInline(admin.TabularInline):
    model = CorrectionAttempt
    extra = 0
    readonly_fields = ['created_at']


@admin.register(DetectedError)
class DetectedErrorAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'submission', 'error_category', 'severity',
        'original_text', 'is_resolved',
    ]
    list_filter = ['error_category', 'severity', 'is_resolved']
    inlines = [AttemptInline]


@admin.register(CorrectionAttempt)
class CorrectionAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'error', 'student', 'attempt_number',
        'is_correct', 'hint_shown', 'solution_shown',
    ]
    list_filter = ['is_correct', 'hint_shown', 'solution_shown']
