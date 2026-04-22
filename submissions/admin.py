from django.contrib import admin

from .models import TextSubmission


@admin.register(TextSubmission)
class TextSubmissionAdmin(admin.ModelAdmin):
    list_display = ['title', 'student', 'classroom', 'status', 'submitted_at']
    list_filter = ['status', 'language', 'classroom']
    search_fields = ['title', 'content']
