from django.core.exceptions import ValidationError

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/bmp'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/avi', 'video/quicktime', 'video/webm', 'video/x-matroska'}

MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_TEXT_LENGTH = 10000

ALLOWED_AUDIO_TYPES = {'audio/wav', 'audio/mpeg', 'audio/flac', 'audio/mp4', 'audio/ogg', 'audio/x-wav'}
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB


def validate_image_file(file):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(f'Unsupported image type: {file.content_type}')
    if file.size > MAX_IMAGE_SIZE:
        raise ValidationError('Image exceeds 10MB limit.')


def validate_video_file(file):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise ValidationError(f'Unsupported video type: {file.content_type}')
    if file.size > MAX_VIDEO_SIZE:
        raise ValidationError('Video exceeds 200MB limit.')


def validate_audio_file(file):
    if hasattr(file, 'content_type') and file.content_type not in ALLOWED_AUDIO_TYPES:
        raise ValidationError(f'Unsupported audio type: {file.content_type}')
    if file.size > MAX_AUDIO_SIZE:
        raise ValidationError('Audio exceeds 50MB limit.')


def validate_text_length(text: str):
    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationError(f'Text exceeds {MAX_TEXT_LENGTH} character limit.')
