from django.contrib import admin

from .models import LearnerErrorSummary


@admin.register(LearnerErrorSummary)
class LearnerErrorSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'submission', 'error_category',
        'total_errors', 'first_attempt_successes', 'avg_hints_used',
    ]
    list_filter = ['error_category']
