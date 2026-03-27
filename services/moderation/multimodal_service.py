from services.moderation.ml_adapter import build_final_decision, escalate, get_severity, assess_risk
from services.moderation.text_service  import run_text_moderation
from services.moderation.image_service import run_image_moderation
from services.moderation.video_service import run_video_moderation
from services.moderation.audio_service import run_audio_moderation


def run_multimodal_moderation(
    text: str = None,
    image_path: str = None,
    video_path: str = None,
    audio_path: str = None,
) -> dict:
    results = []

    if text:
        results.append(run_text_moderation(text))
    if image_path:
        results.append(run_image_moderation(image_path))
    if video_path:
        results.append(run_video_moderation(video_path))
    if audio_path:
        results.append(run_audio_moderation(audio_path))

    if not results:
        return {
            'modality': 'multimodal',
            'status':   'APPROVED',
            'reason':   'No content provided.',
            'confidence': 0.0,
            'severity': 'LOW',
            'risk_level': 'LOW',
            'escalated': False,
        }

    # build_final_decision: fuse_results → cross_modal_validator → consistency_checker
    final = build_final_decision(results)
    final['modality'] = 'multimodal'

    confidence = float(final.get('confidence', 0.0))
    final['severity']   = get_severity(final['status'], confidence)
    final['risk_level'] = assess_risk({'status': final['status'], 'confidence': confidence})
    final = escalate(final)

    return final
