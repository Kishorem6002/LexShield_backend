import threading
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from common.utils import success_response, created_response, error_response
from apps.moderation.models import ModerationLog
from .models import Comment
from .serializers import CommentSerializer, CommentCreateSerializer

LOG_FIELDS   = {'modality', 'status', 'reason', 'confidence', 'severity',
                'severity_score', 'risk_level', 'risk_score', 'escalated', 'raw_result'}
SEVERITY_MAP = {'LOW': 25, 'MEDIUM': 50, 'HIGH': 75, 'CRITICAL': 100}
MOD_TIMEOUT  = 25   # seconds — if ML takes longer, approve and save


def _moderate_text_safe(text: str):
    """
    Run text moderation with a hard timeout.
    Returns (result, error_str).
    Never raises — always returns something.
    """
    result_box = [None]
    error_box  = [None]

    def _run():
        try:
            from services.moderation.orchestrator import moderate
            result_box[0] = moderate('text', text=text, context={'source': 'comment'})
        except Exception as e:
            error_box[0] = str(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=MOD_TIMEOUT)

    if t.is_alive():
        # Timed out — approve so comment is not lost
        return None, 'moderation_timeout'

    return result_box[0], error_box[0]


def _save_log(result, user, comment_id):
    try:
        raw_conf = float(result.get('confidence', 0.0))
        log_data = {k: v for k, v in result.items() if k in LOG_FIELDS}
        log_data['confidence'] = round(raw_conf * 100, 2) if raw_conf <= 1.0 else round(raw_conf, 2)
        log_data.setdefault('modality', 'text')
        ModerationLog.objects.create(
            requested_by=user,
            content_type='comment',
            object_id=comment_id,
            **log_data,
        )
    except Exception:
        pass


def _build_rejection(result: dict) -> dict:
    raw_conf       = float(result.get('confidence', 0.0))
    confidence_pct = round(raw_conf * 100, 2) if raw_conf <= 1.0 else round(raw_conf, 2)
    severity       = result.get('severity', 'LOW')
    risk_level     = result.get('risk_level', 'LOW')
    return {
        'status':         result.get('status'),
        'reason':         result.get('reason', 'Content policy violation.'),
        'confidence':     confidence_pct,
        'confidence_pct': f"{confidence_pct}%",
        'severity':       severity,
        'severity_score': SEVERITY_MAP.get(severity, 0),
        'risk_level':     risk_level,
        'risk_score':     SEVERITY_MAP.get(risk_level, 0),
        'keyword_hits':   result.get('keyword_hits', []),
        'escalated':      result.get('escalated', False),
    }


class CommentListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        post_id = request.query_params.get('post_id')
        if not post_id:
            return error_response(message='post_id is required.')
        qs = Comment.objects.filter(post_id=post_id).order_by('created_at')
        return success_response(CommentSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        body = serializer.validated_data.get('body', '').strip()
        if not body:
            return error_response(message='Comment cannot be empty.')

        # ── Moderate with timeout ─────────────────────────────────────────
        mod_result, mod_error = _moderate_text_safe(body)

        # Only BLOCK hard violations — FLAGGED content is saved but marked
        if mod_result:
            mod_status = mod_result.get('status', 'APPROVED')
            if mod_status == 'BLOCKED':
                _save_log(mod_result, request.user, None)
                return error_response(
                    message=f'Comment blocked — {mod_result.get("reason", "Content policy violation.")}',
                    errors={'moderation': _build_rejection(mod_result)},
                    status_code=422,
                )

        # ── Save comment ──────────────────────────────────────────────────
        final_status = 'APPROVED'
        if mod_result:
            final_status = mod_result.get('status', 'APPROVED')
        elif mod_error == 'moderation_timeout':
            final_status = 'APPROVED'   # timeout → approve

        comment = serializer.save(
            user=request.user,
            moderation_status=final_status,
        )

        if mod_result:
            _save_log(mod_result, request.user, comment.id)

        # ── Notify post owner ─────────────────────────────────────────────
        try:
            from services.notifications.notification_service import send_notification
            post = comment.post
            if post.user_id != request.user.id:
                send_notification(
                    post.user_id,
                    f"{request.user.username} commented on your post: \"{comment.body[:60]}\"",
                    {'type': 'comment', 'post_id': post.id, 'comment_id': comment.id}
                )
        except Exception:
            pass

        return created_response(CommentSerializer(comment, context={'request': request}).data)


class CommentDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            raise NotFound('Comment not found.')

    def delete(self, request, pk):
        comment = self.get_object(pk)
        if comment.user != request.user:
            raise PermissionDenied('You can only delete your own comments.')
        comment.soft_delete()
        return success_response(message='Comment deleted.')
