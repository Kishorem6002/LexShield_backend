from django.contrib import admin
from .models import ModerationLog


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display  = ('id', 'requested_by', 'modality', 'status', 'severity', 'confidence', 'created_at')
    list_filter   = ('status', 'modality', 'severity')
    search_fields = ('requested_by__username', 'reason')
    readonly_fields = ('raw_result',)
