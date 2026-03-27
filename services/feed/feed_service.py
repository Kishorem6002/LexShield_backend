from apps.posts.models import Post
from apps.interactions.models import Follow


def get_feed_for_user(user, limit=20):
    following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    return Post.objects.filter(
        user_id__in=list(following_ids),
        is_published=True,
        moderation_status='APPROVED',
    ).order_by('-created_at')[:limit]
