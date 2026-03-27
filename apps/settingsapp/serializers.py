from rest_framework import serializers
from .models import UserSettings


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserSettings
        fields = ('email_notifications', 'moderation_alerts', 'content_filter_level')
