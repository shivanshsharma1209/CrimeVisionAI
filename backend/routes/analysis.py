import json
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import Config
from backend.models.database import get_db
from backend.models.case import Case
from backend.models.evidence import Evidence, Detection, Transcript
from backend.models.timeline import TimelineEvent
from backend.services.image_analysis import ImageAnalysisService
from backend.services.video_analysis import VideoAnalysisService
from backend.services.audio_analysis import AudioAnalysisService
from backend.services.evidence_fusion import EvidenceFusionEngine
from backend.utils.validators import api_response

logger = logging.getLogger("crimevision.analysis_route")
analysis_router = APIRouter(tags=["analysis"])

image_service = ImageAnalysisService()
video_service = VideoAnalysisService()
audio_service = AudioAnalysisService()
fusion_engine = EvidenceFusionEngine()


def _do_analyze_evidence(evidence_id: int, db: Session):
    ev = db.get(Evidence, evidence_id)
    if not ev:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Evidence #{evidence_id} not found."},
            status_code=404,
        )

    file_path = Config.ORIGINALS_DIR / ev.stored_filename
    if not file_path.exists():
        return api_response(
            success=False,
            error={"code": "FILE_NOT_FOUND", "message": "Original evidence file missing from storage."},
            status_code=500,
        )

    ev.analysis_status = "PROCESSING"
    db.commit()

    try:
        if ev.file_type == "image":
            result = image_service.analyze_image(
                image_path=file_path,
                processed_dir=Config.PROCESSED_DIR,
                evidence_id=ev.id,
            )
            ev.set_metadata(result["metadata"])

            db.query(Detection).filter_by(evidence_id=ev.id).delete()
            for d in result["detections"]:
                det = Detection(
                    evidence_id=ev.id,
                    object_name=d["object"],
                    confidence=d["confidence"],
                    bbox_json=json.dumps(d.get("bbox", [])),
                    timestamp=None,
                    model_name=d.get("model_used", "RT-DETR"),
                )
                db.add(det)

            db.query(TimelineEvent).filter_by(evidence_id=ev.id).delete()
            desc = result["scene_description"].get(
                "description", f"Visual evidence ({ev.filename}) analyzed."
            )
            tl_event = TimelineEvent(
                case_id=ev.case_id,
                evidence_id=ev.id,
                timestamp=None,
                timestamp_str="timestamp_unavailable",
                event_type="visual_evidence_analyzed",
                description=desc,
                confidence=result["scene_description"].get("confidence", 0.85),
                source="image",
                metadata_json=json.dumps(result["metadata"]),
            )
            db.add(tl_event)

        elif ev.file_type == "video":
            result = video_service.analyze_video(
                video_path=file_path,
                processed_dir=Config.PROCESSED_DIR,
                evidence_id=ev.id,
            )
            ev.set_metadata(result["metadata"])

            db.query(Detection).filter_by(evidence_id=ev.id).delete()
            db.query(TimelineEvent).filter_by(evidence_id=ev.id).delete()

            for d in result["detections"]:
                det = Detection(
                    evidence_id=ev.id,
                    object_name=d["object"],
                    confidence=d["confidence"],
                    bbox_json=json.dumps(d.get("bbox", [])),
                    timestamp=d.get("timestamp"),
                    model_name=d.get("model_used", "RT-DETR"),
                )
                db.add(det)

            for evt in result["events"]:
                tl_event = TimelineEvent(
                    case_id=ev.case_id,
                    evidence_id=ev.id,
                    timestamp=evt["timestamp"],
                    timestamp_str=evt["timestamp_str"],
                    event_type=evt["event_type"],
                    description=evt["description"],
                    confidence=evt["confidence"],
                    source="video",
                    metadata_json=json.dumps(evt.get("metadata", {})),
                )
                db.add(tl_event)

        elif ev.file_type == "audio":
            result = audio_service.analyze_audio(
                audio_path=file_path,
                evidence_id=ev.id,
            )
            ev.set_metadata(result["metadata"])

            db.query(Transcript).filter_by(evidence_id=ev.id).delete()
            db.query(TimelineEvent).filter_by(evidence_id=ev.id).delete()

            for seg in result["segments"]:
                tr = Transcript(
                    evidence_id=ev.id,
                    start_time=seg["start"],
                    end_time=seg["end"],
                    text=seg["text"],
                    language=seg.get("language", "en"),
                    confidence=seg.get("confidence", 0.90),
                )
                db.add(tr)

            for evt in result["events"]:
                tl_event = TimelineEvent(
                    case_id=ev.case_id,
                    evidence_id=ev.id,
                    timestamp=evt["timestamp"],
                    timestamp_str=evt["timestamp_str"],
                    event_type=evt["event_type"],
                    description=evt["description"],
                    confidence=evt["confidence"],
                    source="audio",
                    metadata_json=json.dumps(evt.get("metadata", {})),
                )
                db.add(tl_event)

        ev.analysis_status = "COMPLETED"
        if ev.case:
            ev.case.status = "Under Analysis"
        db.commit()
        db.refresh(ev)

        return api_response(success=True, data=ev.to_dict(include_children=True))

    except Exception as e:
        logger.error(f"Analysis failed for evidence {evidence_id}: {e}", exc_info=True)
        ev.analysis_status = "FAILED"
        db.commit()
        return api_response(
            success=False,
            error={"code": "ANALYSIS_FAILED", "message": f"Analysis failed: {str(e)}"},
            status_code=500,
        )


@analysis_router.post("/api/evidence/{evidence_id}/analyze")
def analyze_evidence_item(evidence_id: int, db: Session = Depends(get_db)):
    """Execute multimodal AI analysis on a specific evidence item."""
    return _do_analyze_evidence(evidence_id, db)


@analysis_router.post("/api/cases/{case_id}/analyze-all")
def analyze_all_case_evidence(case_id: int, db: Session = Depends(get_db)):
    """Batch-analyze all QUEUED or FAILED evidence items in the case."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    pending_items = (
        db.query(Evidence)
        .filter(
            Evidence.case_id == case_id,
            Evidence.analysis_status.in_(["QUEUED", "FAILED"]),
        )
        .all()
    )

    processed_count = 0
    errors = []

    for ev in pending_items:
        try:
            resp = _do_analyze_evidence(ev.id, db)
            if resp.status_code == 200:
                processed_count += 1
            else:
                errors.append({"evidence_id": ev.id, "error": f"Status {resp.status_code}"})
        except Exception as e:
            errors.append({"evidence_id": ev.id, "error": str(e)})

    return api_response(
        success=True,
        data={
            "processed_count": processed_count,
            "errors": errors,
            "remaining_pending": len(pending_items) - processed_count,
        },
    )


@analysis_router.get("/api/cases/{case_id}/timeline")
def get_case_timeline(case_id: int, db: Session = Depends(get_db)):
    """
    Retrieve unified chronological forensic timeline synthesized
    by the EvidenceFusionEngine.
    """
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    events = (
        db.query(TimelineEvent)
        .filter_by(case_id=case_id)
        .all()
    )
    raw_events = [ev.to_dict() for ev in events]
    fusion_output = fusion_engine.fuse_case_evidence(raw_events)

    return api_response(success=True, data=fusion_output)
