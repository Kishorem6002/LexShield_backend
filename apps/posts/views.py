import os
import tempfile
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from common.utils import success_response, created_response, error_response
from common.pagination import StandardPagination
from apps.moderation.models import ModerationLog
from .models import Post
from .serializers import PostSerializer, PostCreateSerializer, PostUpdateSerializer

LOG_FIELDS = {'modality', 'status', 'reason', 'confidence', 'severity', 'severity_score',
              'risk_level', 'risk_score', 'escalated', 'raw_result'}

SEVERITY_MAP = {'LOW': 25, 'MEDIUM': 50, 'HIGH': 75, 'CRITICAL': 100}


def _build_moderation_response(result: dict) -> dict:
    if not result:
        return None
    raw_conf       = float(result.get('confidence', 0.0))
    confidence_pct = round(raw_conf * 100, 2) if raw_conf <= 1.0 else round(raw_conf, 2)
    severity       = result.get('severity', 'LOW')
    risk_level     = result.get('risk_level', 'LOW')
    return {
        'status':         result.get('status'),
        'reason':         result.get('reason', ''),
        'confidence':     confidence_pct,
        'confidence_pct': f"{confidence_pct}%",
        'severity':       severity,
        'severity_score': SEVERITY_MAP.get(severity, 0),
        'risk_level':     risk_level,
        'risk_score':     SEVERITY_MAP.get(risk_level, 0),
        'escalated':      result.get('escalated', False),
        'label':          result.get('label'),
        'keyword_hits':   result.get('keyword_hits', []),
        'modality':       result.get('modality'),
    }


def _save_log(result, user, post_id, content_type='post'):
    try:
        log_data = {k: v for k, v in result.items() if k in LOG_FIELDS}
        raw_conf = float(log_data.get('confidence', 0.0))
        log_data['confidence'] = round(raw_conf * 100, 2) if raw_conf <= 1.0 else round(raw_conf, 2)
        log_data.setdefault('modality', 'text')
        ModerationLog.objects.create(
            requested_by=user,
            content_type=content_type,
            object_id=post_id,
            **log_data,
        )
    except Exception:
        pass


def _moderate_all(modality, caption, tmp_path, file_name):
    """
    Moderate ALL content provided:
    - Text post:  moderate caption
    - Image post: moderate image + caption (both must pass)
    - Video post: moderate video + caption (both must pass)
    Returns (final_result, error_str)
    """
    from services.moderation.orchestrator import moderate

    results = []
    errors  = []

    # Always moderate caption if provided
    if caption and caption.strip():
        try:
            text_result = moderate('text', text=caption, context={'source': 'post'})
            text_result['_source'] = 'caption'
            results.append(text_result)
        except Exception as e:
            errors.append(f'Caption moderation error: {e}')

    # Moderate media file if provided
    if tmp_path:
        try:
            if modality == 'image':
                media_result = moderate('image', file_path=tmp_path, file_name=file_name or 'image')
            elif modality == 'video':
                media_result = moderate('video', file_path=tmp_path)
            else:
                media_result = None

            if media_result:
                media_result['_source'] = modality
                results.append(media_result)
        except Exception as e:
            # For video — if moderation fails, flag it for safety
            if modality == 'video':
                results.append({
                    'status':   'FLAGGED',
                    'reason':   f'Video moderation could not complete: {e}',
                    'confidence': 0.0,
                    'severity': 'MEDIUM',
                    'risk_level': 'MEDIUM',
                    'escalated': False,
                    'modality': 'video',
                    '_source':  'video',
                })
            else:
                errors.append(f'Media moderation error: {e}')

    if not results:
        return None, '; '.join(errors) if errors else None

    # Worst-case wins — BLOCKED > FLAGGED > APPROVED
    rank = {'APPROVED': 0, 'FLAGGED': 1, 'BLOCKED': 2}
    worst = max(results, key=lambda r: rank.get(r.get('status', 'APPROVED'), 0))

    # Build combined reason if multiple sources
    if len(results) > 1:
        reasons = []
        for r in results:
            src    = r.get('_source', 'content')
            status = r.get('status', 'APPROVED')
            reason = r.get('reason', '')
            if status != 'APPROVED':
                reasons.append(f"[{src.upper()}] {reason}")
        if reasons:
            worst = dict(worst)
            worst['reason'] = ' | '.join(reasons)

    return worst, None


class PostListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        posts = Post.objects.filter(
            is_published=True,
            is_deleted=False,
        ).order_by('-created_at')
        paginator = StandardPagination()
        page = paginator.paginate_queryset(posts, request)
        return paginator.get_paginated_response(
            PostSerializer(page, many=True, context={'request': request}).data
        )

    def post(self, request):
        serializer = PostCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        validated  = serializer.validated_data
        modality   = validated.get('modality', 'text')
        caption    = validated.get('caption', '')
        media_file = validated.get('media_file')

        # Require at least caption or media
        if not caption.strip() and not media_file:
            return error_response(message='Post must have a caption or media file.')

        # ── Step 1: Write media to temp file ──────────────────────────────
        tmp_path  = None
        file_name = None
        if media_file:
            suffix    = os.path.splitext(media_file.name)[-1]
            file_name = media_file.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in media_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            media_file.seek(0)  # reset so Django can save it

        # ── Step 2: Moderate ALL content before saving ────────────────────
        mod_result = None
        try:
            mod_result, mod_error = _moderate_all(modality, caption, tmp_path, file_name)
        except Exception as e:
            mod_result, mod_error = None, str(e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # ── Step 3: Reject FLAGGED or BLOCKED — but LOG it first ─────────
        if mod_result:
            status = mod_result.get('status', 'APPROVED')
            if status in ('BLOCKED', 'FLAGGED'):
                # Save log even for rejected content so analytics shows it
                _save_log(mod_result, request.user, None)
                return error_response(
                    message=f'Your post was {status.lower()} by our content moderation system.',
                    errors={'moderation': _build_moderation_response(mod_result)},
                    status_code=422,
                )

        # ── Step 4: Save post ─────────────────────────────────────────────
        post = serializer.save(
            user=request.user,
            moderation_status=mod_result.get('status', 'APPROVED') if mod_result else 'APPROVED',
        )

        # ── Step 5: Log moderation result ────────────────────────────────
        if mod_result:
            _save_log(mod_result, request.user, post.id)

        data = PostSerializer(post, context={'request': request}).data
        data['moderation_result'] = _build_moderation_response(mod_result)
        return created_response(data, message='Post published successfully.')


class PostDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            raise NotFound('Post not found.')

    def get(self, request, pk):
        post = self.get_object(pk)
        return success_response(PostSerializer(post, context={'request': request}).data)

    def patch(self, request, pk):
        post = self.get_object(pk)
        if post.user != request.user:
            raise PermissionDenied('You can only edit your own posts.')
        serializer = PostUpdateSerializer(post, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)
        if 'caption' in request.data and request.data['caption']:
            try:
                from services.moderation.orchestrator import moderate
                mod_result = moderate('text', text=request.data['caption'], context={'source': 'post'})
                if mod_result and mod_result.get('status') in ('BLOCKED', 'FLAGGED'):
                    return error_response(
                        message=f"Caption {mod_result.get('status').lower()} — {mod_result.get('reason')}",
                        errors={'moderation': _build_moderation_response(mod_result)},
                        status_code=422,
                    )
            except Exception:
                pass
        post = serializer.save()
        return success_response(PostSerializer(post, context={'request': request}).data)

    def delete(self, request, pk):
        post = self.get_object(pk)
        if post.user != request.user:
            raise PermissionDenied('You can only delete your own posts.')
        post.soft_delete()
        return success_response(message='Post deleted.')


class MyPostsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        posts = Post.objects.filter(
            user=request.user,
            is_deleted=False,
        ).order_by('-created_at')
        paginator = StandardPagination()
        page = paginator.paginate_queryset(posts, request)
        return paginator.get_paginated_response(
            PostSerializer(page, many=True, context={'request': request}).data
        )


class UserPostsView(APIView):
    """GET /api/posts/user/<username>/ — public posts of any user."""
    permission_classes = (IsAuthenticated,)

    def get(self, request, username):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return error_response(message=f'User "{username}" not found.', status_code=404)

        posts = Post.objects.filter(
            user=user,
            is_published=True,
        ).order_by('-created_at')

        paginator = StandardPagination()
        page = paginator.paginate_queryset(posts, request)
        return paginator.get_paginated_response(
            PostSerializer(page, many=True, context={'request': request}).data
        )
