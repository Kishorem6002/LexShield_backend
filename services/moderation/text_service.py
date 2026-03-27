from services.moderation.ml_adapter import (
    moderate_text,
    postprocess_text_result,
    get_severity,
    assess_risk,
    escalate,
)


def run_text_moderation(text: str, context: dict = None) -> dict:
    raw    = moderate_text(text)
    result = postprocess_text_result(raw, text)

    confidence_pct = round(result['confidence'] * 100, 2)
    severity       = get_severity(result['status'], confidence_pct)
    risk           = assess_risk({'status': result['status'], 'confidence': confidence_pct})

    output = {
        'modality':     'text',
        'status':       result['status'],
        'reason':       result['reason'],
        'confidence':   result['confidence'],
        'label':        result.get('label'),
        'categories':   result.get('categories', []),
        'keyword_hits': result.get('keyword_hits', []),
        'severity':     severity,
        'risk_level':   risk,
        'context':      context or {},
    }

    output = escalate(output)
    return output
