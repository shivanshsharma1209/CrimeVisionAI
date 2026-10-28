from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import Config
from backend.models.database import get_db
from backend.models.case import Case
from backend.models.evidence import Evidence
from backend.models.timeline import TimelineEvent, Report
from backend.services.report_service import ReportService
from backend.utils.validators import api_response

reports_router = APIRouter(tags=["reports"])
report_service = ReportService()


@reports_router.post("/api/cases/{case_id}/report")
def generate_report(case_id: int, db: Session = Depends(get_db)):
    """Generate a formal forensic PDF analysis report for the case."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    evidence_items = db.query(Evidence).filter_by(case_id=case_id).all()
    evidence_list = [e.to_dict(include_children=True) for e in evidence_items]
    timeline_events = db.query(TimelineEvent).filter_by(case_id=case_id).all()
    timeline_list = [t.to_dict() for t in timeline_events]
    transcripts_list = []
    for ev in evidence_items:
        for tr in (ev.transcripts or []):
            transcripts_list.append(tr.to_dict())

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clean_num = c.case_number.replace("-", "_")
    output_filename = f"CrimeVision_Report_{clean_num}_{timestamp_str}.pdf"

    try:
        report_meta = report_service.generate_forensic_report(
            case_data=c.to_dict(),
            evidence_list=evidence_list,
            timeline_list=timeline_list,
            transcripts_list=transcripts_list,
            output_filename=output_filename,
        )

        new_report = Report(
            case_id=c.id,
            report_filename=output_filename,
            report_path=report_meta["path"],
            sha256_hash=report_meta["sha256_hash"],
            summary=f"Forensic Analysis Report generated with {len(evidence_list)} evidence files and {len(timeline_list)} timeline events.",
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        return api_response(success=True, data=new_report.to_dict(), status_code=201)

    except Exception as e:
        return api_response(
            success=False,
            error={"code": "REPORT_GEN_FAILED", "message": f"Report generation failed: {str(e)}"},
            status_code=500,
        )


@reports_router.get("/api/reports/{report_id}/download")
def download_report(report_id: int, as_attachment: bool = Query(False), db: Session = Depends(get_db)):
    """Download or view a generated forensic report PDF."""
    rep = db.get(Report, report_id)
    if not rep:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Report #{report_id} not found."},
            status_code=404,
        )

    file_path = (Config.REPORTS_DIR / rep.report_filename).resolve()
    if not file_path.exists():
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": "Report PDF file not found on disk."},
            status_code=404,
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=rep.report_filename if as_attachment else None,
    )


@reports_router.get("/api/cases/{case_id}/reports")
def get_case_reports(case_id: int, db: Session = Depends(get_db)):
    """List all reports generated for this case."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    reports = (
        db.query(Report)
        .filter_by(case_id=case_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return api_response(success=True, data=[r.to_dict() for r in reports])
