import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import Config
from backend.models.database import get_db
from backend.models.case import Case
from backend.models.evidence import Evidence
from backend.utils.file_security import (
    is_allowed_file,
    classify_media_type,
    detect_mime_type,
    generate_secure_storage_name,
)
from backend.utils.hashing import calculate_sha256
from backend.utils.validators import api_response

evidence_router = APIRouter(tags=["evidence"])


@evidence_router.get("/api/cases/{case_id}/evidence")
def get_case_evidence(case_id: int, db: Session = Depends(get_db)):
    """Retrieve all evidence registered under a case."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    evidence_items = (
        db.query(Evidence)
        .filter_by(case_id=case_id)
        .order_by(Evidence.upload_timestamp.desc())
        .all()
    )
    return api_response(success=True, data=[e.to_dict(include_children=True) for e in evidence_items])


@evidence_router.post("/api/cases/{case_id}/evidence")
async def upload_evidence(case_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Ingest new evidence file for a case.
    Preserves forensic chain of custody:
    - Stores file in storage/originals/ untouched
    - Computes SHA-256 hash
    - Classifies media type (image, video, audio)
    - Enqueues for multimodal analysis
    """
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    if not file or not file.filename:
        return api_response(
            success=False,
            error={"code": "EMPTY_FILENAME", "message": "No file selected."},
            status_code=400,
        )

    original_filename = file.filename
    if not is_allowed_file(original_filename):
        return api_response(
            success=False,
            error={
                "code": "INVALID_FILE_TYPE",
                "message": f"Unsupported media format. Allowed: {Config.ALLOWED_EXTENSIONS}",
            },
            status_code=400,
        )

    stored_filename = generate_secure_storage_name(original_filename)
    target_path = Config.ORIGINALS_DIR / stored_filename

    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)

    sha256 = calculate_sha256(target_path)
    file_size = target_path.stat().st_size
    file_type = classify_media_type(original_filename)
    mime_type = detect_mime_type(target_path, original_filename)

    new_evidence = Evidence(
        case_id=case_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        sha256_hash=sha256,
        analysis_status="QUEUED",
    )
    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)

    return api_response(
        success=True,
        data=new_evidence.to_dict(),
        status_code=201,
    )


@evidence_router.get("/api/evidence/{evidence_id}")
def get_evidence_detail(evidence_id: int, db: Session = Depends(get_db)):
    """Get complete forensic intelligence record for an evidence item."""
    ev = db.get(Evidence, evidence_id)
    if not ev:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Evidence #{evidence_id} not found."},
            status_code=404,
        )
    return api_response(success=True, data=ev.to_dict(include_children=True))


@evidence_router.delete("/api/evidence/{evidence_id}")
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Delete an evidence item and its associated files."""
    ev = db.get(Evidence, evidence_id)
    if not ev:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Evidence #{evidence_id} not found."},
            status_code=404,
        )

    orig_path = Config.ORIGINALS_DIR / ev.stored_filename
    if orig_path.exists():
        try:
            os.remove(orig_path)
        except Exception:
            pass

    db.delete(ev)
    db.commit()

    return api_response(
        success=True, data={"message": f"Evidence #{evidence_id} successfully deleted."}
    )


@evidence_router.get("/storage/originals/{filename:path}")
def serve_original(filename: str):
    """Serve untouched original evidence file securely."""
    file_path = (Config.ORIGINALS_DIR / filename).resolve()
    if not file_path.exists() or not str(file_path).startswith(str(Config.ORIGINALS_DIR.resolve())):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@evidence_router.get("/storage/processed/{filename:path}")
def serve_processed(filename: str):
    """Serve processed forensic derivatives (annotated images, keyframes)."""
    file_path = (Config.PROCESSED_DIR / filename).resolve()
    if not file_path.exists() or not str(file_path).startswith(str(Config.PROCESSED_DIR.resolve())):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
