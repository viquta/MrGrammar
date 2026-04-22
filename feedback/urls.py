from django.urls import path

from . import views

urlpatterns = [
    path(
        'submissions/<int:submission_id>/errors/',
        views.SubmissionErrorsView.as_view(),
        name='submission-errors',
    ),
    path('errors/<int:pk>/', views.ErrorDetailView.as_view(), name='error-detail'),
    path(
        'errors/<int:pk>/attempt/',
        views.SubmitAttemptView.as_view(),
        name='submit-attempt',
    ),
    path(
        'errors/<int:pk>/solution/',
        views.RequestSolutionView.as_view(),
        name='request-solution',
    ),
]
