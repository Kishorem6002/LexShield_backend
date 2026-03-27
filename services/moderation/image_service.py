from services.moderation.ml_adapter import (
    moderate_image,
    postprocess_image_result,
    get_model_manager,
    get_severity,
    assess_risk,
    escalate,
)


def run_image_moderation(file_path: str, file_name: str = 'image') -> dict:
    manager = get_model_manager()
    raw     = moderate_image(file_path, manager, file_name=file_name)
    result  = postprocess_image_result(raw)

    severity = get_severity(result['status'], result['confidence'])
    risk     = assess_risk({'status': result['status'], 'confidence': result['confidence']})

    output = {
        'modality':         'image',
        'file':             result.get('file', file_name),
        'status':           result['status'],
        'reason':           result['reason'],
        'confidence':       result['confidence'],
        'scores':           result.get('scores', {}),
        'top_label':        result.get('top_label'),
        'categories':       result.get('categories', []),
        'violation_reason': result.get('violation_reason'),
        'severity':         severity,
        'risk_level':       risk,
    }

    output = escalate(output)
    return output
