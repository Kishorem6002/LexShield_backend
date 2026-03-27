from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin


class Profile(TimestampMixin):
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio        = models.TextField(blank=True)
    avatar     = models.ImageField(upload_to='avatars/', null=True, blank=True)
    website    = models.URLField(blank=True)
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return f'Profile({self.user.username})'
