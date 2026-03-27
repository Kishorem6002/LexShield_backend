"""
Adapter layer: bridges Django to ml_engine.
Models are loaded ONCE at import time (Django startup) so the first
request is never slow.
"""
import sys
from pathlib import Path

_civility_root  = str(Path(__file__).resolve().parent.parent.parent.parent)
_ml_engine_root = str(Path(__file__).resolve().parent.parent.parent.parent / 'ml_engine')

for _path in (_civility_root, _ml_engine_root):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from ml_engine.app.models.manager.model_manager import ModelManager

from ml_engine.app.pipelines.text_pipeline.text_moderator     import moderate_text
from ml_engine.app.pipelines.text_pipeline.text_postprocessor import postprocess_text_result

from ml_engine.app.pipelines.image_pipeline.image_moderator     import moderate_image
from ml_engine.app.pipelines.image_pipeline.image_postprocessor import postprocess_image_result

from ml_engine.app.pipelines.video_pipeline.video_postprocessor import postprocess_video_result

from ml_engine.app.pipelines.audio_pipeline.audio_moderator     import moderate_audio
from ml_engine.app.pipelines.audio_pipeline.audio_postprocessor import postprocess_audio_result

from ml_engine.app.pipelines.multimodal_pipeline.final_decision_builder import build_final_decision

from ml_engine.app.decision.severity_engine   import get_severity
from ml_engine.app.decision.risk_engine       import assess_risk
from ml_engine.app.decision.escalation_engine import escalate

from ml_engine.app.contracts.moderation_labels import MODERATION_LABELS, VIOLATION_TYPES

# ── Singleton ModelManager — loaded ONCE, reused for every request ───────────
_model_manager: ModelManager = None


def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
