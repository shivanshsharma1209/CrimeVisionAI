import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.models.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id = Column(
        Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=True, index=True
    )
    timestamp = Column(Float, nullable=True)  # in seconds, None if timestamp unavailable
    timestamp_str = Column(String(50), default="timestamp_unavailable")
    event_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    source = Column(String(50), default="unknown")  # image, video, audio, fusion
    metadata_json = Column(Text, default="{}")

    # Relationships
    case = relationship("Case", back_populates="timeline_events")
    evidence = relationship("Evidence", back_populates="timeline_events")

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}

    def set_metadata(self, data):
        self.metadata_json = json.dumps(data)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "evidence_id": self.evidence_id,
            "timestamp": self.timestamp,
            "timestamp_str": self.timestamp_str,
            "event_type": self.event_type,
            "description": self.description,
            "confidence": round(self.confidence, 4) if self.confidence else None,
            "source": self.source,
            "metadata": self.get_metadata(),
        }


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(30), nullable=False)  # user, assistant, system
    message = Column(Text, nullable=False)
    evidence_context = Column(Text, default="[]")  # List of referenced evidence or timeline IDs
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="chat_messages")

    def get_context(self):
        try:
            return json.loads(self.evidence_context or "[]")
        except Exception:
            return []

    def set_context(self, context_list):
        self.evidence_context = json.dumps(context_list)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "role": self.role,
            "message": self.message,
            "evidence_context": self.get_context(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_filename = Column(String(255), nullable=False)
    report_path = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    summary = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="reports")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "report_filename": self.report_filename,
            "report_path": self.report_path,
            "sha256_hash": self.sha256_hash,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
