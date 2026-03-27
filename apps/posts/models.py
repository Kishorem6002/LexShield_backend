from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin, SoftDeleteMixin, ActiveManager
from common.choices import MODERATION_STATUS_CHOICES, MODALITY_CHOICES
from common.constants import MODERATION_STATUS_APPROVED


class Post(TimestampMixin, SoftDeleteMixin):
    user               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    caption            = models.TextField(blank=True)
    media_file         = models.FileField(upload_to='posts/', null=True, blank=True)
    modality           = models.CharField(max_length=20, choices=MODALITY_CHOICES, default='text')
    moderation_status  = models.CharField(max_length=20, choices=MODERATION_STATUS_CHOICES, default=MODERATION_STATUS_APPROVED)
    is_published       = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f'Post({self.id}) by {self.user.username}'
