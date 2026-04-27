from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.db import connections
from django.core.cache import cache
from django.views.decorators.http import require_GET


@require_GET
def health_check(_request):
    checks = {
        'database': 'ok',
        'cache': 'ok',
    }
    status_code = 200

    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        checks['database'] = 'error'
        status_code = 503

    try:
        cache.set('healthcheck:ping', 'pong', 5)
        if cache.get('healthcheck:ping') != 'pong':
            raise RuntimeError('cache mismatch')
    except Exception:
        checks['cache'] = 'error'
        status_code = 503

    overall = 'ok' if status_code == 200 else 'degraded'
    return JsonResponse({'status': overall, 'checks': checks}, status=status_code)

urlpatterns = [
    path('healthz/', health_check),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/classrooms/', include('classrooms.urls')),
    path('api/submissions/', include('submissions.urls')),
    path('api/feedback/', include('feedback.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/nlp/', include('nlp.urls')),
]
