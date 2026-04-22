from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/classrooms/', include('classrooms.urls')),
    path('api/submissions/', include('submissions.urls')),
    path('api/feedback/', include('feedback.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/nlp/', include('nlp.urls')),
]
