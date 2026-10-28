from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from backend.models.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    investigator = Column(String(120), nullable=False)
    status = Column(String(50), default="Open")  # Open, Under Analysis, Review, Closed
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    evidence_items = relationship(
        "Evidence", back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    timeline_events = relationship(
        "TimelineEvent", back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    reports = relationship(
        "Report", back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self):
        evidence_count = len(self.evidence_items) if self.evidence_items else 0
        timeline_count = len(self.timeline_events) if self.timeline_events else 0
        return {
            "id": self.id,
            "case_number": self.case_number,
            "title": self.title,
            "description": self.description,
            "investigator": self.investigator,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "evidence_count": evidence_count,
            "timeline_event_count": timeline_count,
        }
