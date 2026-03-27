from common.constants import MODERATION_STATUS_APPROVED, MODERATION_STATUS_FLAGGED, MODERATION_STATUS_BLOCKED

# Numeric severity map — 0 to 100 scale
SEVERITY_SCORE_MAP = {
    'LOW':      25,
    'MEDIUM':   50,
    'HIGH':     75,
    'CRITICAL': 100,
}


def map_to_db(result: dict) -> dict:
    """Map ML service result to ModerationLog model fields."""
    raw_confidence = float(result.get('confidence', 0.0))

    # Normalize confidence to 0–100
    confidence_pct = round(raw_confidence * 100, 2) if raw_confidence <= 1.0 else round(raw_confidence, 2)

    severity   = result.get('severity', 'LOW')
    risk_level = result.get('risk_level', 'LOW')

    return {
        'modality':        result.get('modality', 'text'),
        'status':          result.get('status', MODERATION_STATUS_APPROVED),
        'reason':          result.get('reason', ''),
        'confidence':      confidence_pct,                          # 0–100
        'severity':        severity,                                # label
        'severity_score':  SEVERITY_SCORE_MAP.get(severity, 0),    # 0–100 numeric
        'risk_level':      risk_level,                              # label
        'risk_score':      SEVERITY_SCORE_MAP.get(risk_level, 0),  # 0–100 numeric
        'escalated':       result.get('escalated', False),
        'raw_result':      result,
    }


def should_block(result: dict) -> bool:
    return result.get('status') == MODERATION_STATUS_BLOCKED


def should_flag(result: dict) -> bool:
    return result.get('status') == MODERATION_STATUS_FLAGGED


def should_escalate(result: dict) -> bool:
    return result.get('escalated', False)


def is_safe(result: dict) -> bool:
    """Returns True only if content is APPROVED — safe to publish."""
    return result.get('status') == MODERATION_STATUS_APPROVED
