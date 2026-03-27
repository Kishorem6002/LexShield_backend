from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin
from common.choices import MODERATION_STATUS_CHOICES, SEVERITY_CHOICES, CONTENT_TYPE_CHOICES
from common.constants import MODERATION_STATUS_APPROVED

MODALITY_CHOICES = [
    ('text',       'Text'),
    ('image',      'Image'),
    ('video',      'Video'),
    ('audio',      'Audio'),
    ('multimodal', 'Multimodal'),
]


class ModerationLog(TimestampMixin):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='moderation_requests'
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, null=True, blank=True)
    object_id    = models.PositiveIntegerField(null=True, blank=True)
    modality     = models.CharField(max_length=20, choices=MODALITY_CHOICES)
    status       = models.CharField(max_length=20, choices=MODERATION_STATUS_CHOICES, default=MODERATION_STATUS_APPROVED)
    reason       = models.TextField(blank=True)
    confidence   = models.FloatField(default=0.0)
    severity       = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='LOW')
    severity_score = models.PositiveSmallIntegerField(default=0)   # 0-100 numeric
    risk_level     = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='LOW')
    risk_score     = models.PositiveSmallIntegerField(default=0)   # 0-100 numeric
    escalated      = models.BooleanField(default=False)
    raw_result   = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'ModerationLog({self.id}) [{self.modality}] {self.status}'
