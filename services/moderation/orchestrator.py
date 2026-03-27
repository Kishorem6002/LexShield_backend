from services.moderation.text_service       import run_text_moderation
from services.moderation.image_service      import run_image_moderation
from services.moderation.video_service      import run_video_moderation
from services.moderation.audio_service      import run_audio_moderation
from services.moderation.multimodal_service import run_multimodal_moderation
from services.moderation.decision_mapper    import map_to_db


def moderate(modality: str, **kwargs) -> dict:
    """
    Single entry point for all moderation.

    modality: 'text' | 'image' | 'video' | 'audio' | 'multimodal'

    kwargs:
        text        — str  (text, multimodal)
        file_path   — str  (image, video, audio)
        file_name   — str  (image, audio — display name)
        image_path  — str  (multimodal)
        video_path  — str  (multimodal)
        audio_path  — str  (multimodal)
        context     — dict (text)
    """
    if modality == 'text':
        result = run_text_moderation(kwargs['text'], kwargs.get('context'))

    elif modality == 'image':
        result = run_image_moderation(kwargs['file_path'], kwargs.get('file_name', 'image'))

    elif modality == 'video':
        result = run_video_moderation(kwargs['file_path'])

    elif modality == 'audio':
        result = run_audio_moderation(kwargs['file_path'], kwargs.get('file_name', 'audio'))

    elif modality == 'multimodal':
        result = run_multimodal_moderation(
            text=kwargs.get('text'),
            image_path=kwargs.get('image_path'),
            video_path=kwargs.get('video_path'),
            audio_path=kwargs.get('audio_path'),
        )
    else:
        raise ValueError(f'Unsupported modality: {modality}')

    return map_to_db(result)
