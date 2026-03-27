from django.contrib import admin
from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'post', 'moderation_status', 'created_at')
    list_filter   = ('moderation_status',)
    search_fields = ('user__username', 'body')
