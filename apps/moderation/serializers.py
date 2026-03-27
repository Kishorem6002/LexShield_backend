from rest_framework import serializers
from common.validators import validate_image_file, validate_video_file, validate_text_length
from .models import ModerationLog

ALLOWED_AUDIO_TYPES = {'audio/wav', 'audio/mpeg', 'audio/flac', 'audio/mp4', 'audio/ogg', 'audio/x-wav'}
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB


class TextModerationSerializer(serializers.Serializer):
    text    = serializers.CharField(max_length=10000)
    context = serializers.DictField(required=False, default=dict)

    def validate_text(self, value):
        validate_text_length(value)
        return value


class ImageModerationSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        validate_image_file(value)
        return value


class VideoModerationSerializer(serializers.Serializer):
    video = serializers.FileField()

    def validate_video(self, value):
        validate_video_file(value)
        return value


class AudioModerationSerializer(serializers.Serializer):
    audio = serializers.FileField()

    def validate_audio(self, value):
        if hasattr(value, 'content_type') and value.content_type not in ALLOWED_AUDIO_TYPES:
            raise serializers.ValidationError(f'Unsupported audio type: {value.content_type}')
        if value.size > MAX_AUDIO_SIZE:
            raise serializers.ValidationError('Audio file exceeds 50MB limit.')
        return value


class MultimodalModerationSerializer(serializers.Serializer):
    text  = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)
    video = serializers.FileField(required=False)
    audio = serializers.FileField(required=False)

    def validate(self, data):
        if not any([data.get('text'), data.get('image'), data.get('video'), data.get('audio')]):
            raise serializers.ValidationError('At least one of text, image, video, or audio is required.')
        return data


class ModerationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ModerationLog
        fields = (
            'id', 'modality', 'status', 'reason',
            'confidence', 'severity', 'severity_score',
            'risk_level', 'risk_score', 'escalated',
            'raw_result', 'created_at'
        )
