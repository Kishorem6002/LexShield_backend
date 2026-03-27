from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin


class UserSettings(TimestampMixin):
    user                    = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings')
    email_notifications     = models.BooleanField(default=True)
    moderation_alerts       = models.BooleanField(default=True)
    content_filter_level    = models.CharField(max_length=20, default='default',
                                               choices=[('strict','Strict'),('default','Default'),('lenient','Lenient')])

    def __str__(self):
        return f'Settings({self.user.username})'
