from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.case import Case
from backend.utils.validators import CaseCreateSchema, CaseUpdateSchema, api_response

cases_router = APIRouter(prefix="/api/cases", tags=["cases"])


@cases_router.get("")
@cases_router.get("/")
def get_cases(db: Session = Depends(get_db)):
    """Retrieve all forensic cases with summary counts."""
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    return api_response(success=True, data=[c.to_dict() for c in cases])


@cases_router.post("")
@cases_router.post("/")
async def create_case(request: Request, db: Session = Depends(get_db)):
    """Create a new forensic case."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    try:
        validated = CaseCreateSchema(**data)
    except Exception as e:
        return api_response(
            success=False,
            error={"code": "VALIDATION_ERROR", "message": str(e)},
            status_code=400,
        )

    year = datetime.now(timezone.utc).year
    count = db.query(Case).count() + 1
    case_number = f"CV-{year}-{count:03d}"

    new_case = Case(
        case_number=case_number,
        title=validated.title.strip(),
        description=validated.description.strip() if validated.description else "",
        investigator=validated.investigator.strip(),
        status=validated.status,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return api_response(success=True, data=new_case.to_dict(), status_code=201)


@cases_router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a single case."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    case_dict = c.to_dict()
    images_count = sum(1 for e in (c.evidence_items or []) if e.file_type == "image")
    videos_count = sum(1 for e in (c.evidence_items or []) if e.file_type == "video")
    audio_count = sum(1 for e in (c.evidence_items or []) if e.file_type == "audio")
    case_dict["breakdown"] = {
        "images": images_count,
        "videos": videos_count,
        "audio": audio_count,
    }
    return api_response(success=True, data=case_dict)


@cases_router.put("/{case_id}")
async def update_case(case_id: int, request: Request, db: Session = Depends(get_db)):
    """Update case metadata or status."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    try:
        data = await request.json()
    except Exception:
        data = {}
    try:
        validated = CaseUpdateSchema(**data)
    except Exception as e:
        return api_response(
            success=False,
            error={"code": "VALIDATION_ERROR", "message": str(e)},
            status_code=400,
        )

    if validated.title is not None:
        c.title = validated.title.strip()
    if validated.description is not None:
        c.description = validated.description.strip()
    if validated.investigator is not None:
        c.investigator = validated.investigator.strip()
    if validated.status is not None:
        c.status = validated.status

    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)

    return api_response(success=True, data=c.to_dict())


@cases_router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """Delete case and all attached evidence."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    db.delete(c)
    db.commit()
    return api_response(
        success=True, data={"message": f"Case #{case_id} successfully deleted."}
    )
