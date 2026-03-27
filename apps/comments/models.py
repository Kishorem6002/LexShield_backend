from django.db import models
from django.conf import settings
from common.mixins import TimestampMixin, SoftDeleteMixin, ActiveManager
from common.choices import MODERATION_STATUS_CHOICES
from common.constants import MODERATION_STATUS_APPROVED


class Comment(TimestampMixin, SoftDeleteMixin):
    user              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    post              = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='comments')
    body              = models.TextField()
    moderation_status = models.CharField(max_length=20, choices=MODERATION_STATUS_CHOICES, default=MODERATION_STATUS_APPROVED)

    objects     = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f'Comment({self.id}) by {self.user.username}'
