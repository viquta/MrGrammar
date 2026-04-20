from django.urls import path

from . import views

urlpatterns = [
    path(
        'student/<int:student_id>/progress/',
        views.StudentProgressView.as_view(),
        name='student-progress',
    ),
    path(
        'classroom/<int:classroom_id>/patterns/',
        views.ClassroomPatternsView.as_view(),
        name='classroom-patterns',
    ),
]
