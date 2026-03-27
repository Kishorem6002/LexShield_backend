from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'modality', 'moderation_status', 'is_published', 'created_at')
    list_filter   = ('moderation_status', 'modality')
    search_fields = ('user__username', 'caption')
