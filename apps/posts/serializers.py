from rest_framework import serializers
from .models import Post


class PostSerializer(serializers.ModelSerializer):
    author      = serializers.CharField(source='user.username', read_only=True)
    author_id   = serializers.IntegerField(source='user.id', read_only=True)
    like_count  = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_owner    = serializers.SerializerMethodField()

    class Meta:
        model  = Post
        fields = (
            'id', 'author', 'author_id', 'caption', 'media_file',
            'modality', 'moderation_status', 'is_published',
            'like_count', 'comment_count', 'is_owner', 'created_at',
        )
        read_only_fields = ('moderation_status',)

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id
        return False


class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Post
        fields = ('caption', 'media_file', 'modality')


class PostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Post
        fields = ('caption', 'is_published')
