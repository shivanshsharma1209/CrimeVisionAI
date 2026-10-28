import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from backend.models.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # image, video, audio
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    upload_timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    analysis_status = Column(
        String(50), default="QUEUED", nullable=False
    )  # QUEUED, PROCESSING, COMPLETED, FAILED
    metadata_json = Column(Text, default="{}")

    # Relationships
    case = relationship("Case", back_populates="evidence_items")
    detections = relationship(
        "Detection", back_populates="evidence", cascade="all, delete-orphan", lazy="selectin"
    )
    transcripts = relationship(
        "Transcript", back_populates="evidence", cascade="all, delete-orphan", lazy="selectin"
    )
    timeline_events = relationship(
        "TimelineEvent", back_populates="evidence", cascade="all, delete-orphan", lazy="selectin"
    )

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}

    def set_metadata(self, data):
        self.metadata_json = json.dumps(data)

    def to_dict(self, include_children=False):
        meta = self.get_metadata()
        dets = self.detections or []
        trans = self.transcripts or []
        data = {
            "id": self.id,
            "case_id": self.case_id,
            "filename": self.filename,
            "stored_filename": self.stored_filename,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "sha256_hash": self.sha256_hash,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "analysis_status": self.analysis_status,
            "metadata": meta,
            "detections_count": len(dets),
            "transcripts_count": len(trans),
        }
        if include_children:
            data["detections"] = [d.to_dict() for d in dets]
            data["transcripts"] = [t.to_dict() for t in trans]
        return data


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_id = Column(
        Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_name = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    bbox_json = Column(Text, default="[]")  # [x1, y1, x2, y2]
    timestamp = Column(Float, nullable=True)  # seconds in video, or null for image
    model_name = Column(String(100), default="RT-DETR")

    evidence = relationship("Evidence", back_populates="detections")

    def get_bbox(self):
        try:
            return json.loads(self.bbox_json or "[]")
        except Exception:
            return []

    def set_bbox(self, bbox_list):
        self.bbox_json = json.dumps(bbox_list)

    def to_dict(self):
        return {
            "id": self.id,
            "evidence_id": self.evidence_id,
            "object_name": self.object_name,
            "confidence": round(self.confidence, 4),
            "bbox": self.get_bbox(),
            "timestamp": self.timestamp,
            "model_name": self.model_name,
        }


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_id = Column(
        Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    language = Column(String(20), default="en")
    confidence = Column(Float, default=1.0)

    evidence = relationship("Evidence", back_populates="transcripts")

    def to_dict(self):
        return {
            "id": self.id,
            "evidence_id": self.evidence_id,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "text": self.text,
            "language": self.language,
            "confidence": round(self.confidence, 4),
        }
