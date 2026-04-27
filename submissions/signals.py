from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from submissions.models import TextSubmission


@receiver(post_save, sender=TextSubmission)
def invalidate_analytics_cache(sender, instance, **kwargs):
    """Evict stale analytics cache when a submission analysis completes."""
    if instance.status == TextSubmission.Status.IN_REVIEW:
        cache.delete(f'analytics:student:{instance.student_id}:progress')
        if instance.classroom_id:
            cache.delete(f'analytics:classroom:{instance.classroom_id}:patterns')
