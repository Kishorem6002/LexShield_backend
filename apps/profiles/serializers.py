from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    username        = serializers.CharField(source='user.username', read_only=True)
    email           = serializers.CharField(source='user.email',    read_only=True)
    user_id         = serializers.IntegerField(source='user.id',    read_only=True)
    follower_count  = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    post_count      = serializers.SerializerMethodField()

    class Meta:
        model  = Profile
        fields = (
            'id', 'user_id', 'username', 'email', 'bio', 'avatar', 'website',
            'is_private', 'follower_count', 'following_count', 'post_count',
            'created_at',
        )

    def get_follower_count(self, obj):
        return obj.user.followers.count()

    def get_following_count(self, obj):
        return obj.user.following.count()

    def get_post_count(self, obj):
        return obj.user.posts.filter(is_deleted=False).count()
