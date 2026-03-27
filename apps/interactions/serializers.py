from rest_framework import serializers
from .models import Like, Follow


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Like
        fields = ('id', 'post', 'created_at')


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Follow
        fields = ('id', 'following', 'created_at')
