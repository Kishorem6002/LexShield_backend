from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin


class Notification(TimestampMixin):
    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    verb       = models.CharField(max_length=100)
    is_read    = models.BooleanField(default=False)
    data       = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Notification({self.id}) -> {self.recipient.username}'
