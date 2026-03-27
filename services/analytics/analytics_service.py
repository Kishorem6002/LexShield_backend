from django.db.models import Count, Avg
from apps.moderation.models import ModerationLog


def get_moderation_summary():
    return ModerationLog.objects.values('modality', 'status').annotate(
        count=Count('id'),
        avg_confidence=Avg('confidence'),
    ).order_by('modality', 'status')


def get_flagged_rate() -> float:
    total   = ModerationLog.objects.count()
    flagged = ModerationLog.objects.filter(status__in=['FLAGGED', 'BLOCKED']).count()
    return round((flagged / total) * 100, 2) if total else 0.0
