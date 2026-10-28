from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.case import Case
from backend.models.evidence import Evidence
from backend.models.timeline import TimelineEvent, ChatMessage
from backend.services.llm_service import LLMService
from backend.utils.validators import ChatQuerySchema, api_response

chat_router = APIRouter(tags=["chat"])
llm_service = LLMService()


@chat_router.post("/api/cases/{case_id}/chat")
async def post_case_chat(case_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Forensic Investigator AI Evidence Chat.
    Uses RAG retrieval over case evidence repository and Groq LLM reasoning.
    Enforces strict forensic neutrality rules.
    """
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
        validated = ChatQuerySchema(**data)
    except Exception as e:
        return api_response(
            success=False,
            error={"code": "VALIDATION_ERROR", "message": str(e)},
            status_code=400,
        )

    user_query = validated.message.strip()

    # Save user message to DB
    user_msg = ChatMessage(case_id=case_id, role="user", message=user_query)
    db.add(user_msg)
    db.commit()

    # Load case evidence context for RAG
    evidence_items = db.query(Evidence).filter_by(case_id=case_id).all()
    evidence_list = [e.to_dict(include_children=True) for e in evidence_items]
    timeline_events = db.query(TimelineEvent).filter_by(case_id=case_id).all()
    timeline_list = [t.to_dict() for t in timeline_events]
    transcripts_list = []
    for ev in evidence_items:
        for tr in (ev.transcripts or []):
            transcripts_list.append(tr.to_dict())

    # Query LLM service
    response_data = llm_service.query_evidence_chat(
        case_id=case_id,
        user_query=user_query,
        case_data=c.to_dict(),
        evidence_list=evidence_list,
        timeline_list=timeline_list,
        transcripts_list=transcripts_list,
    )

    # Save assistant message to DB
    assistant_msg = ChatMessage(
        case_id=case_id,
        role="assistant",
        message=response_data.get("answer", ""),
    )
    assistant_msg.set_context(response_data.get("evidence_references", []))
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return api_response(
        success=True,
        data={
            "id": assistant_msg.id,
            "role": "assistant",
            "message": response_data.get("answer"),
            "evidence_references": response_data.get("evidence_references", []),
            "model_used": response_data.get("model_used"),
            "disclaimer": response_data.get("disclaimer"),
            "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
        },
    )


@chat_router.get("/api/cases/{case_id}/chat/history")
def get_chat_history(case_id: int, db: Session = Depends(get_db)):
    """Retrieve all historical chat messages for a case."""
    c = db.get(Case, case_id)
    if not c:
        return api_response(
            success=False,
            error={"code": "NOT_FOUND", "message": f"Case #{case_id} not found."},
            status_code=404,
        )

    messages = (
        db.query(ChatMessage)
        .filter_by(case_id=case_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return api_response(success=True, data=[m.to_dict() for m in messages])
