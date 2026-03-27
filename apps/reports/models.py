from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin
from common.choices import REPORT_STATUS_CHOICES, CONTENT_TYPE_CHOICES


class Report(TimestampMixin):
    reported_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_filed')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    object_id    = models.PositiveIntegerField()
    reason       = models.TextField()
    status       = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='PENDING')
    reviewed_by  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports_reviewed')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report({self.id}) on {self.content_type}:{self.object_id}'
