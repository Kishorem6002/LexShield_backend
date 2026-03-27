from rest_framework import serializers
from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    author   = serializers.CharField(source='user.username', read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model  = Comment
        fields = ('id', 'author', 'post', 'body', 'moderation_status', 'is_owner', 'created_at')
        read_only_fields = ('moderation_status',)

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id
        return False


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Comment
        fields = ('post', 'body')
