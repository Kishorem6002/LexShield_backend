from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from common.utils import success_response, created_response, error_response
from .models import Like, Follow


def _notify(recipient_id, actor_username, verb, data=None):
    try:
        from services.notifications.notification_service import send_notification
        if recipient_id:
            send_notification(recipient_id, f"{actor_username} {verb}", data or {})
    except Exception:
        pass


class LikeToggleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, post_id):
        like, created = Like.objects.get_or_create(user=request.user, post_id=post_id)
        count = Like.objects.filter(post_id=post_id).count()

        if not created:
            like.delete()
            count = Like.objects.filter(post_id=post_id).count()
            return success_response({'liked': False, 'like_count': count}, message='Unliked.')

        # Notify post owner (not self)
        try:
            post = like.post
            if post.user_id != request.user.id:
                _notify(
                    post.user_id,
                    request.user.username,
                    'liked your post.',
                    {'type': 'like', 'post_id': post_id}
                )
        except Exception:
            pass

        return created_response({'liked': True, 'like_count': count}, message='Liked.')


class LikeStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, post_id):
        liked = Like.objects.filter(user=request.user, post_id=post_id).exists()
        count = Like.objects.filter(post_id=post_id).count()
        return success_response({'liked': liked, 'like_count': count})


class FollowToggleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, user_id):
        if request.user.id == user_id:
            return error_response(message='Cannot follow yourself.')

        follow, created = Follow.objects.get_or_create(
            follower=request.user, following_id=user_id
        )
        if not created:
            follow.delete()
            return success_response({'following': False}, message='Unfollowed.')

        # Notify the followed user
        _notify(
            user_id,
            request.user.username,
            'started following you.',
            {'type': 'follow', 'follower_id': request.user.id}
        )
        return created_response({'following': True}, message='Followed.')
