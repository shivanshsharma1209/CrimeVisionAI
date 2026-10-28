import torch
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import Config
from backend.models.database import get_db
from backend.models.case import Case
from backend.models.evidence import Evidence, Detection, Transcript
from backend.models.timeline import TimelineEvent
from backend.services.demo_service import DemoService
from backend.services.object_detection import ObjectDetectionService
from backend.utils.validators import api_response

system_router = APIRouter(tags=["system"])
demo_service = DemoService()


@system_router.post("/api/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Endpoint to seed the demo case CV-DEMO-001 with sample multimodal assets."""
    try:
        case_data = demo_service.seed_demo_case()
        return api_response(success=True, data=case_data, status_code=201)
    except Exception as e:
        return api_response(
            success=False,
            error={"code": "DEMO_SEED_ERROR", "message": f"Failed to seed demo case: {str(e)}"},
            status_code=500,
        )


@system_router.get("/api/system/status")
def system_status():
    """Retrieve runtime device, AI models status, and storage configuration."""
    detector = ObjectDetectionService()
    det_status = detector.get_service_status()

    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU (Standard Host)"

    groq_configured = bool(Config.GROQ_API_KEY and len(Config.GROQ_API_KEY.strip()) > 5)

    status_data = {
        "platform": "CrimeVision AI v2.4 (Production Multimodal)",
        "device": device_name,
        "cuda_available": cuda_available,
        "models": {
            "object_detector": det_status.get("model_name"),
            "detector_fallback_active": det_status.get("is_fallback"),
            "clip_model": Config.CLIP_MODEL_NAME,
            "blip_model": Config.BLIP_MODEL_NAME,
            "whisper_model": Config.WHISPER_MODEL_NAME,
            "groq_model": Config.GROQ_MODEL,
            "groq_configured": groq_configured,
        },
        "disclosures": {
            "weapon_detection": det_status.get("weapon_disclosure"),
            "decision_support": (
                "CrimeVision AI is an investigator decision-support and analytical tool. "
                "It does not autonomously determine guilt, identity, or legal liability."
            ),
        },
        "limits": {
            "max_upload_mb": Config.MAX_CONTENT_LENGTH / (1024 * 1024),
            "video_sample_fps": Config.VIDEO_SAMPLE_FPS,
        },
        "demo_mode_enabled": Config.ENABLE_DEMO_MODE,
    }

    return api_response(success=True, data=status_data)


@system_router.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """Aggregate statistics for the main forensic overview dashboard."""
    total_cases = db.query(Case).count()
    total_evidence = db.query(Evidence).count()
    images_count = db.query(Evidence).filter_by(file_type="image").count()
    videos_count = db.query(Evidence).filter_by(file_type="video").count()
    audio_count = db.query(Evidence).filter_by(file_type="audio").count()
    total_detections = db.query(Detection).count()
    total_events = db.query(TimelineEvent).count()
    total_transcripts = db.query(Transcript).count()

    # Status distribution
    status_counts = {
        "Open": db.query(Case).filter_by(status="Open").count(),
        "Under Analysis": db.query(Case).filter_by(status="Under Analysis").count(),
        "Review": db.query(Case).filter_by(status="Review").count(),
        "Closed": db.query(Case).filter_by(status="Closed").count(),
    }

    recent_cases = db.query(Case).order_by(Case.created_at.desc()).limit(5).all()

    return api_response(
        success=True,
        data={
            "total_cases": total_cases,
            "total_evidence": total_evidence,
            "images_count": images_count,
            "videos_count": videos_count,
            "audio_count": audio_count,
            "total_detections": total_detections,
            "total_events": total_events,
            "total_transcripts": total_transcripts,
            "case_statuses": status_counts,
            "recent_cases": [c.to_dict() for c in recent_cases],
        },
    )
