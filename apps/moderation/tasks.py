from config.celery import app
from services.moderation.orchestrator import moderate
from .models import ModerationLog


@app.task(bind=True, max_retries=3)
def moderate_text_async(self, text: str, user_id: int, context: dict = None):
    try:
        result = moderate('text', text=text, context=context)
        ModerationLog.objects.create(requested_by_id=user_id, **result)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@app.task(bind=True, max_retries=3)
def moderate_image_async(self, file_path: str, file_name: str, user_id: int):
    try:
        result = moderate('image', file_path=file_path, file_name=file_name)
        ModerationLog.objects.create(requested_by_id=user_id, **result)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@app.task(bind=True, max_retries=3)
def moderate_video_async(self, file_path: str, user_id: int):
    try:
        result = moderate('video', file_path=file_path)
        ModerationLog.objects.create(requested_by_id=user_id, **result)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@app.task(bind=True, max_retries=3)
def moderate_audio_async(self, file_path: str, file_name: str, user_id: int):
    try:
        result = moderate('audio', file_path=file_path, file_name=file_name)
        ModerationLog.objects.create(requested_by_id=user_id, **result)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
