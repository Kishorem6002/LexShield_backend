import os
import hashlib
import tempfile
import traceback
from functools import lru_cache
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from common.utils import success_response, error_response
from common.permissions import IsAdminOrModerator
from common.pagination import StandardPagination
from .models import ModerationLog
from .serializers import (
    TextModerationSerializer,
    ImageModerationSerializer,
    VideoModerationSerializer,
    AudioModerationSerializer,
    MultimodalModerationSerializer,
    ModerationLogSerializer,
)

LOG_FIELDS = {
    'modality', 'status', 'reason', 'confidence',
    'severity', 'severity_score', 'risk_level', 'risk_score',
    'escalated', 'raw_result',
}
SEVERITY_SCORE_MAP = {'LOW': 25, 'MEDIUM': 50, 'HIGH': 75, 'CRITICAL': 100}

# ── In-process result cache (LRU, max 512 entries) ────────────────────────────
# Key: sha256 of content. Avoids re-running ML on identical inputs.
_text_cache  = {}   # hash -> result dict
_image_cache = {}   # hash -> result dict
_MAX_CACHE   = 512


def _cache_get(store, key):
    return store.get(key)


def _cache_set(store, key, value):
    if len(store) >= _MAX_CACHE:
        # evict oldest
        oldest = next(iter(store))
        del store[oldest]
    store[key] = value


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _normalize_result(result: dict) -> dict:
    r = dict(result)
    raw_conf = float(r.get('confidence', 0.0))
    r['confidence']     = round(raw_conf * 100, 2) if raw_conf <= 1.0 else round(raw_conf, 2)
    r['confidence_pct'] = f"{r['confidence']}%"
    r['severity_score'] = SEVERITY_SCORE_MAP.get(r.get('severity', 'LOW'), 0)
    r['risk_score']     = SEVERITY_SCORE_MAP.get(r.get('risk_level', 'LOW'), 0)
    return r


def _save_temp(file) -> str:
    suffix = os.path.splitext(file.name)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in file.chunks():
            tmp.write(chunk)
        return tmp.name


def _log(result: dict, user, content_type=None, object_id=None):
    try:
        log_data = {k: v for k, v in result.items() if k in LOG_FIELDS}
        if 'confidence' in log_data:
            c = float(log_data['confidence'])
            log_data['confidence'] = round(c * 100, 2) if c <= 1.0 else round(c, 2)
        log_data.setdefault('modality', 'text')
        ModerationLog.objects.create(
            requested_by=user,
            content_type=content_type,
            object_id=object_id,
            **log_data,
        )
    except Exception:
        pass


def _run_with_timeout(fn, timeout_sec, fallback):
    """Run fn() in a thread; return fallback if it exceeds timeout_sec."""
    import threading
    result_box = [None]
    exc_box    = [None]

    def _run():
        try:
            result_box[0] = fn()
        except Exception as e:
            exc_box[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)

    if t.is_alive():
        return fallback, TimeoutError(f'Moderation timed out after {timeout_sec}s')
    if exc_box[0]:
        return None, exc_box[0]
    return result_box[0], None


# ── Views ─────────────────────────────────────────────────────────────────────
class TextModerationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = TextModerationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        text = serializer.validated_data['text']
        key  = _hash_text(text)

        # Cache hit — return instantly
        cached = _cache_get(_text_cache, key)
        if cached:
            _log(cached, request.user)
            return success_response({**_normalize_result(cached), 'cached': True})

        try:
            from services.moderation.orchestrator import moderate
            result, err = _run_with_timeout(
                lambda: moderate('text', text=text,
                                 context=serializer.validated_data.get('context')),
                timeout_sec=30,
                fallback={'modality': 'text', 'status': 'APPROVED',
                          'reason': 'Moderation timeout — approved by default',
                          'confidence': 0.0, 'severity': 'LOW',
                          'risk_level': 'LOW', 'escalated': False},
            )
            if err and result is None:
                raise err
            _cache_set(_text_cache, key, result)
            _log(result, request.user)
            return success_response(_normalize_result(result))
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e), 'trace': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ImageModerationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ImageModerationSerializer(data=request.FILES)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        file     = serializer.validated_data['image']
        tmp_path = _save_temp(file)
        try:
            key    = _hash_file(tmp_path)
            cached = _cache_get(_image_cache, key)
            if cached:
                _log(cached, request.user)
                return success_response({**_normalize_result(cached), 'cached': True})

            from services.moderation.orchestrator import moderate
            result, err = _run_with_timeout(
                lambda: moderate('image', file_path=tmp_path, file_name=file.name),
                timeout_sec=30,
                fallback={'modality': 'image', 'status': 'APPROVED',
                          'reason': 'Moderation timeout — approved by default',
                          'confidence': 0.0, 'severity': 'LOW',
                          'risk_level': 'LOW', 'escalated': False},
            )
            if err and result is None:
                raise err
            _cache_set(_image_cache, key, result)
            _log(result, request.user)
            return success_response(_normalize_result(result))
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e), 'trace': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class VideoModerationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = VideoModerationSerializer(data=request.FILES)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        file     = serializer.validated_data['video']
        tmp_path = _save_temp(file)
        try:
            from services.moderation.orchestrator import moderate
            # Video timeout: 120s max
            result, err = _run_with_timeout(
                lambda: moderate('video', file_path=tmp_path),
                timeout_sec=120,
                fallback={'modality': 'video', 'status': 'FLAGGED',
                          'reason': 'Video moderation timed out — flagged for manual review',
                          'confidence': 0.0, 'severity': 'MEDIUM',
                          'risk_level': 'MEDIUM', 'escalated': False},
            )
            if err and result is None:
                raise err
            _log(result, request.user)
            return success_response(_normalize_result(result))
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e), 'trace': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class AudioModerationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = AudioModerationSerializer(data=request.FILES)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        file     = serializer.validated_data['audio']
        tmp_path = _save_temp(file)
        try:
            from services.moderation.orchestrator import moderate
            result, err = _run_with_timeout(
                lambda: moderate('audio', file_path=tmp_path, file_name=file.name),
                timeout_sec=60,
                fallback={'modality': 'audio', 'status': 'APPROVED',
                          'reason': 'Audio moderation timeout — approved by default',
                          'confidence': 0.0, 'severity': 'LOW',
                          'risk_level': 'LOW', 'escalated': False},
            )
            if err and result is None:
                raise err
            _log(result, request.user)
            return success_response(_normalize_result(result))
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e), 'trace': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class MultimodalModerationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = MultimodalModerationSerializer(data={**request.data, **request.FILES})
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        data      = serializer.validated_data
        tmp_image = tmp_video = tmp_audio = None
        try:
            if data.get('image'):
                tmp_image = _save_temp(data['image'])
            if data.get('video'):
                tmp_video = _save_temp(data['video'])
            if data.get('audio'):
                tmp_audio = _save_temp(data['audio'])

            from services.moderation.orchestrator import moderate
            result, err = _run_with_timeout(
                lambda: moderate('multimodal', text=data.get('text'),
                                 image_path=tmp_image, video_path=tmp_video,
                                 audio_path=tmp_audio),
                timeout_sec=120,
                fallback={'modality': 'multimodal', 'status': 'FLAGGED',
                          'reason': 'Multimodal moderation timed out',
                          'confidence': 0.0, 'severity': 'MEDIUM',
                          'risk_level': 'MEDIUM', 'escalated': False},
            )
            if err and result is None:
                raise err
            _log(result, request.user)
            return success_response(_normalize_result(result))
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e), 'trace': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            for p in (tmp_image, tmp_video, tmp_audio):
                if p and os.path.exists(p):
                    os.unlink(p)


class ModerationLogListView(APIView):
    permission_classes = (IsAdminOrModerator,)

    def get(self, request):
        logs      = ModerationLog.objects.all()
        paginator = StandardPagination()
        page      = paginator.paginate_queryset(logs, request)
        return paginator.get_paginated_response(ModerationLogSerializer(page, many=True).data)
