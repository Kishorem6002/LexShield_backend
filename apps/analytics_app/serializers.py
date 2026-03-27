from rest_framework import serializers
from .models import ModerationStat


class ModerationStatSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ModerationStat
        fields = ('id', 'date', 'modality', 'status', 'count', 'avg_confidence')
