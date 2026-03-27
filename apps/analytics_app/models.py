from django.db import models
from common.mixins import TimestampMixin
from common.choices import MODERATION_STATUS_CHOICES, MODALITY_CHOICES


class ModerationStat(TimestampMixin):
    date          = models.DateField(auto_now_add=True)
    modality      = models.CharField(max_length=20, choices=MODALITY_CHOICES)
    status        = models.CharField(max_length=20, choices=MODERATION_STATUS_CHOICES)
    count         = models.PositiveIntegerField(default=0)
    avg_confidence = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('date', 'modality', 'status')
        ordering = ['-date']

    def __str__(self):
        return f'{self.date} | {self.modality} | {self.status} | {self.count}'
