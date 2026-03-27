from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg
from django.utils import timezone
from common.utils import success_response
from apps.moderation.models import ModerationLog
from apps.posts.models import Post
from apps.interactions.models import Like, Follow
from apps.comments.models import Comment
from apps.notifications.models import Notification


def _fmt(dt):
    if dt is None:
        return ''
    local_dt = timezone.localtime(dt)
    return local_dt.strftime('%d %b %Y, %I:%M %p')


class UserAnalyticsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user

        # ── Post stats ────────────────────────────────────────────────────
        # Use all_objects (plain Manager) to bypass ActiveManager
        # APPROVED and FLAGGED posts are saved to DB
        # BLOCKED posts are NEVER saved — count from ModerationLog
        saved_posts    = Post.all_objects.filter(user=user, is_deleted=False)
        approved_posts = saved_posts.filter(moderation_status='APPROVED').count()
        flagged_posts  = saved_posts.filter(moderation_status='FLAGGED').count()

        # All moderation logs for this user
        mod_logs = ModerationLog.objects.filter(requested_by=user)

        # Blocked = rejected before saving (object_id=None in log)
        blocked_posts = mod_logs.filter(status='BLOCKED').count()

        # Total = saved + blocked attempts
        total_posts = approved_posts + flagged_posts + blocked_posts

        # ── Interaction stats ─────────────────────────────────────────────
        total_likes_received    = Like.objects.filter(post__user=user).count()
        total_comments_received = Comment.all_objects.filter(
            post__user=user, is_deleted=False
        ).count()
        total_following = Follow.objects.filter(follower=user).count()
        total_followers = Follow.objects.filter(following=user).count()

        # ── Moderation breakdown ──────────────────────────────────────────
        total_moderated = mod_logs.count()

        moderation_by_modality = list(
            mod_logs.values('modality', 'status')
            .annotate(count=Count('id'), avg_confidence=Avg('confidence'))
            .order_by('modality', 'status')
        )

        severity_breakdown = list(
            mod_logs.values('severity')
            .annotate(count=Count('id'))
            .order_by('severity')
        )

        # ── Safety score ──────────────────────────────────────────────────
        if total_moderated > 0:
            safe_count   = mod_logs.filter(status='APPROVED').count()
            safety_score = round((safe_count / total_moderated) * 100, 1)
        else:
            safety_score = 100.0

        # ── Recent activity — ALL mod logs (blocked + flagged + approved) ─
        recent_activity = []
        for log in mod_logs.order_by('-created_at')[:20]:
            recent_activity.append({
                'type':       'moderation',
                'modality':   log.modality,
                'status':     log.status,
                'detail':     log.reason[:100] if log.reason else 'Content analyzed',
                'confidence': round(float(log.confidence), 1) if log.confidence else None,
                'severity':   log.severity,
                'escalated':  log.escalated,
                'created_at': _fmt(log.created_at),
            })

        # ── Notifications ─────────────────────────────────────────────────
        unread_notifications = Notification.objects.filter(
            recipient=user, is_read=False
        ).count()

        recent_notifications = []
        for n in Notification.objects.filter(recipient=user).order_by('-created_at')[:5]:
            recent_notifications.append({
                'verb':       n.verb,
                'is_read':    n.is_read,
                'created_at': _fmt(n.created_at),
            })

        return success_response({
            'posts': {
                'total':    total_posts,
                'approved': approved_posts,
                'flagged':  flagged_posts,
                'blocked':  blocked_posts,
            },
            'interactions': {
                'likes_received':    total_likes_received,
                'comments_received': total_comments_received,
                'following':         total_following,
                'followers':         total_followers,
            },
            'moderation': {
                'total_moderated':    total_moderated,
                'safety_score':       safety_score,
                'by_modality':        moderation_by_modality,
                'severity_breakdown': severity_breakdown,
            },
            'recent_activity':      recent_activity,
            'recent_notifications': recent_notifications,
            'notifications': {
                'unread': unread_notifications,
            },
        })
