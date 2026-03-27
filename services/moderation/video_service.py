import os
import cv2
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from PIL import Image

from services.moderation.ml_adapter import (
    get_model_manager,
    moderate_image,
    postprocess_image_result,
    get_severity,
    assess_risk,
    escalate,
)

# ── Performance settings ──────────────────────────────────────────────────────
MAX_FRAMES         = 30
FRAME_STEP_OVERRIDE = 15
EARLY_EXIT_BLOCKED = 3
MAX_AUDIO_SECONDS  = 60
RESIZE_W           = 224
RESIZE_H           = 224
# ─────────────────────────────────────────────────────────────────────────────


def _extract_frames_fast(video_path: str, tmp_dir: str) -> tuple:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps          = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration     = round(total_frames / fps, 2) if fps > 0 else 0.0

    frame_index = 0
    saved       = 0
    frame_paths = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break                          # ← FIX: was missing, caused infinite loop
        if frame_index % FRAME_STEP_OVERRIDE == 0 and saved < MAX_FRAMES:
            path = os.path.join(tmp_dir, f"frame_{frame_index:05d}.jpg")
            cv2.imwrite(path, frame)
            frame_paths.append(path)
            saved += 1
            if saved >= MAX_FRAMES:
                break
        frame_index += 1

    cap.release()

    return frame_paths, {
        'fps':              fps,
        'total_frames':     total_frames,
        'frames_extracted': saved,
        'frame_step':       FRAME_STEP_OVERRIDE,
        'duration_seconds': duration,
    }


def _moderate_frames_fast(frame_paths: list, fps: float, manager) -> dict:
    violated   = []
    all_results = []
    blocked = flagged = approved = 0
    max_nsfw   = 0.0
    early_exit = False

    for frame_path in frame_paths:
        frame_name  = Path(frame_path).stem
        try:
            frame_index = int(frame_name.split('_')[-1])
        except (ValueError, IndexError):
            frame_index = 0
        timestamp = round(frame_index / max(fps, 1.0), 4)

        try:
            bgr = cv2.imread(frame_path)
            if bgr is None:
                continue
            rgb    = cv2.cvtColor(cv2.resize(bgr, (RESIZE_W, RESIZE_H)), cv2.COLOR_BGR2RGB)
            result = moderate_image(Image.fromarray(rgb), manager, file_name=frame_name)
            result = postprocess_image_result(result)
            result['frame_index'] = frame_index
            result['timestamp']   = timestamp

            nsfw_val = result.get('scores', {}).get('nsfw', 0.0)
            max_nsfw = max(max_nsfw, float(nsfw_val))

            if result['status'] == 'BLOCKED':
                blocked += 1
                violated.append(result)
                if blocked >= EARLY_EXIT_BLOCKED:
                    early_exit = True
                    break
            elif result['status'] == 'FLAGGED':
                flagged += 1
                violated.append(result)
            else:
                approved += 1

            all_results.append(result)

        except Exception as e:
            blocked += 1
            violated.append({
                'file': frame_name, 'frame_index': frame_index,
                'timestamp': timestamp, 'status': 'BLOCKED',
                'reason': f'Frame inference error: {e}',
                'confidence': 0.0, 'scores': {'nsfw': 0.0},
            })

    return {
        'violated_frames': violated,
        'early_exit':      early_exit,
        'summary': {
            'total_frames_checked': len(all_results),
            'blocked':              blocked,
            'flagged':              flagged,
            'approved':             approved,
            'max_nsfw_score':       round(max_nsfw, 2),
        }
    }


def _extract_audio_fast(video_path: str, tmp_dir: str) -> Optional[str]:
    try:
        import subprocess
        out_path = os.path.join(tmp_dir, 'audio.wav')
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-t', str(MAX_AUDIO_SECONDS),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            out_path,
            '-loglevel', 'error'
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
        return None
    except Exception:
        return None


def run_video_moderation(file_path: str) -> dict:
    manager = get_model_manager()
    tmp_dir = tempfile.mkdtemp(prefix='civility_video_')

    try:
        # ── Step 1: Extract frames ────────────────────────────────────────
        try:
            frame_paths, metadata = _extract_frames_fast(file_path, tmp_dir)
        except Exception as e:
            return {
                'modality': 'video', 'status': 'BLOCKED',
                'reason': f'Video could not be opened: {e}',
                'confidence': 0.0, 'severity': 'HIGH', 'risk_level': 'HIGH',
                'escalated': False, 'summary': {}, 'metadata': {},
            }

        if not frame_paths:
            return {
                'modality': 'video', 'status': 'FLAGGED',
                'reason': 'No frames could be extracted from video.',
                'confidence': 0.0, 'severity': 'MEDIUM', 'risk_level': 'MEDIUM',
                'escalated': False, 'summary': {}, 'metadata': metadata,
            }

        # ── Step 2: Moderate frames ───────────────────────────────────────
        frame_data    = _moderate_frames_fast(frame_paths, metadata['fps'], manager)
        frame_summary = frame_data['summary']

        if frame_summary['blocked'] >= 1:
            visual_status = 'BLOCKED'
            visual_reason = f"Unsafe visual content in {frame_summary['blocked']} frame(s)"
        elif frame_summary['flagged'] >= 1:
            visual_status = 'FLAGGED'
            visual_reason = f"Suspicious content in {frame_summary['flagged']} frame(s)"
        else:
            visual_status = 'APPROVED'
            visual_reason = 'No unsafe visual content detected'

        # ── Step 3: Audio moderation ──────────────────────────────────────
        audio_status = 'APPROVED'
        audio_reason = 'No audio track or audio skipped'
        audio_result = None

        audio_path = _extract_audio_fast(file_path, tmp_dir)
        if audio_path:
            try:
                from services.moderation.audio_service import run_audio_moderation
                audio_result = run_audio_moderation(audio_path, 'video_audio')
                audio_status = audio_result['status']
                audio_reason = audio_result['reason']
            except Exception as e:
                audio_reason = f'Audio moderation error: {e}'

        # ── Step 4: Final decision ────────────────────────────────────────
        _RANK = {'APPROVED': 0, 'FLAGGED': 1, 'BLOCKED': 2}
        final_status = visual_status \
            if _RANK.get(visual_status, 0) >= _RANK.get(audio_status, 0) \
            else audio_status
        inconsistent = _RANK.get(visual_status, 0) != _RANK.get(audio_status, 0)

        if final_status == 'BLOCKED':
            if visual_status == 'BLOCKED' and audio_status == 'BLOCKED':
                final_reason = 'BLOCKED — unsafe visual frames and audio detected'
            elif visual_status == 'BLOCKED':
                final_reason = f'BLOCKED — {visual_reason}'
            else:
                final_reason = f'BLOCKED — {audio_reason}'
        elif final_status == 'FLAGGED':
            final_reason = 'FLAGGED — cross-modal inconsistency detected' \
                if inconsistent else f'FLAGGED — {visual_reason or audio_reason}'
        else:
            final_reason = 'APPROVED — visual and audio passed moderation'

        confidence = float(frame_summary.get('max_nsfw_score', 0.0))
        severity   = get_severity(final_status, confidence)
        risk       = assess_risk({'status': final_status, 'confidence': confidence})

        # ── Collect categories from violated frames ───────────────────────
        all_categories = []
        for fr in frame_data['violated_frames'][:5]:
            all_categories.extend(fr.get('categories', []))
        # deduplicate preserving order
        seen = set()
        categories = [c for c in all_categories if not (c in seen or seen.add(c))]
        # fallback if frames had no categories but video is blocked/flagged
        if not categories and final_status in ('BLOCKED', 'FLAGGED'):
            nsfw = frame_summary.get('max_nsfw_score', 0.0)
            if nsfw >= 78:
                categories = ['Explicit / NSFW Content']
            elif nsfw >= 22:
                categories = ['Potentially Explicit Content']
            else:
                categories = ['Unsafe Visual Content']

        output = {
            'modality':   'video',
            'file':       Path(file_path).name,
            'status':     final_status,
            'reason':     final_reason,
            'confidence': confidence,
            'severity':   severity,
            'risk_level': risk,
            'categories': categories,
            'cross_modal_inconsistency': inconsistent,
            'early_exit': frame_data.get('early_exit', False),
            'visual_moderation': {
                'status':          visual_status,
                'reason':          visual_reason,
                'summary':         frame_summary,
                'violated_frames': frame_data['violated_frames'][:5],
            },
            'audio_moderation': {
                'status':       audio_status,
                'reason':       audio_reason,
                'transcript':   audio_result.get('transcript', '') if audio_result else '',
                'audio_events': audio_result.get('audio_events', {}) if audio_result else {},
            },
            'summary': {
                'total_frames_checked': frame_summary['total_frames_checked'],
                'frames_blocked':       frame_summary['blocked'],
                'frames_flagged':       frame_summary['flagged'],
                'frames_approved':      frame_summary['approved'],
                'max_nsfw_score':       frame_summary['max_nsfw_score'],
                'audio_status':         audio_status,
                'visual_status':        visual_status,
                'final_status':         final_status,
            },
            'metadata': metadata,
        }

        output = escalate(output)
        return output

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
