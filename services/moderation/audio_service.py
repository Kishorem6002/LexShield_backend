from services.moderation.ml_adapter import (
    moderate_audio,
    postprocess_audio_result,
    get_severity,
    assess_risk,
    escalate,
)


def run_audio_moderation(file_path: str, file_name: str = 'audio') -> dict:
    raw    = moderate_audio(file_path)
    result = postprocess_audio_result(raw)

    confidence_pct = round(result['confidence'] * 100, 2)
    severity       = get_severity(result['status'], confidence_pct)
    risk           = assess_risk({'status': result['status'], 'confidence': confidence_pct})

    output = {
        'modality':        'audio',
        'file':            file_name,
        'status':          result['status'],
        'reason':          result['reason'],
        'confidence':      result['confidence'],
        'transcript':      result.get('transcript', ''),
        'audio_events':    result.get('audio_events', {}),
        'text_moderation': result.get('text_moderation', {}),
        'severity':        severity,
        'risk_level':      risk,
    }

    output = escalate(output)
    return output
