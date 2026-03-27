from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    reported_by = serializers.CharField(source='reported_by.username', read_only=True)

    class Meta:
        model  = Report
        fields = ('id', 'reported_by', 'content_type', 'object_id', 'reason', 'status', 'created_at')
        read_only_fields = ('status',)
