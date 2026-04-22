from django.urls import path

from . import views

urlpatterns = [
    path(
        'submissions/<int:submission_id>/analyze/',
        views.AnalyzeSubmissionView.as_view(),
        name='analyze-submission',
    ),
]
