import os
import wave
import struct
import math
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import cv2
import numpy as np

from config import Config
from backend.models.database import db
from backend.models.case import Case
from backend.models.evidence import Evidence, Detection, Transcript
from backend.models.timeline import TimelineEvent
from backend.utils.hashing import calculate_sha256
from backend.services.audio_analysis import AUDIO_TRANSLATIONS, DEFAULT_CRIME_TIMELINE

logger = logging.getLogger("crimevision.demo")


class DemoService:
    """
    Demo Mode Service:
    Provides one-click generation of 'CV-DEMO-001 Multimodal Crime Scene & Witness Reconstruction'.
    Seeds the exact Office Crime Scene Image, Audio Witness Statement with Multilingual Translations,
    and Surveillance Video footage.
    """

    def __init__(self):
        self.demo_dir = Config.DEMO_DIR
        self.originals_dir = Config.ORIGINALS_DIR
        self.processed_dir = Config.PROCESSED_DIR

    def seed_demo_case(self) -> Dict[str, Any]:
        """Create or reset the demo case CV-DEMO-001 with sample multimodal evidence."""
        # Check if demo case already exists
        demo_case = Case.query.filter_by(case_number="CV-DEMO-001").first()
        if demo_case:
            logger.info("Demo case CV-DEMO-001 already exists. Returning existing case.")
            return demo_case.to_dict()

        # 1. Create Case Record
        demo_case = Case(
            case_number="CV-DEMO-001",
            title="Office Incident & Jewelry Robbery Reconstruction [DEMO DATA]",
            description=(
                "[DEMO DATA - MULTIMODAL FORENSIC RECONSTRUCTION]\n"
                "Investigation into downtown commercial incident and witness acoustic statement. "
                "Multimodal integration of crime scene imagery, CCTV footage, and multilingual audio testimony."
            ),
            investigator="Lead Investigator (Forensic Team)",
            status="Under Analysis",
        )
        db.session.add(demo_case)
        db.session.commit()

        # 2. Ingest Office Crime Scene Image
        image_orig_name, image_path = self._get_or_create_crime_scene_image()
        img_hash = calculate_sha256(image_path)
        img_size = image_path.stat().st_size

        img_evidence = Evidence(
            case_id=demo_case.id,
            filename="crime-scene-investigation.jpg",
            stored_filename=image_orig_name,
            file_type="image",
            mime_type="image/jpeg",
            file_size=img_size,
            sha256_hash=img_hash,
            analysis_status="COMPLETED",
        )

        img_meta = {
            "is_demo_data": True,
            "summary_type": "Crime Scene",
            "brief_description": "A male individual is observed lying on the floor, surrounded by a knife and restrained with tape.",
            "visual_summary": "A man laying on the floor with a knife and tape around him",
            "metrics": {
                "objects": 9,
                "persons": 1,
                "weapons": 1,
                "location": "office",
            },
            "actions_detected": "lying down",
            "evidence_facts": ["laptop", "diningtable", "chair", "Human", "sofa", "cup"],
            "scenarios": [
                {
                    "id": 1,
                    "title": "Scenario 1",
                    "text": (
                        "The man was attacked by an unknown assailant while working late in the office, "
                        "and the perpetrator used the knife to inflict fatal wounds before fleeing the scene."
                    ),
                },
                {
                    "id": 2,
                    "title": "Scenario 2",
                    "text": (
                        "The individual, feeling overwhelmed by stress, attempted to harm himself with the knife "
                        "but was unable to complete the act and lies there, awaiting help, with the tape possibly being "
                        "used in a misguided attempt to treat the wound."
                    ),
                },
                {
                    "id": 3,
                    "title": "Scenario 3",
                    "text": "The person staged a crime scene to mislead investigators.",
                },
            ],
            "scene_classification": {
                "primary_category": "office",
                "confidence": 0.92,
                "model_used": "CLIP (ViT-B/32)",
            },
            "scene_description": {
                "description": "A male individual is observed lying on the floor, surrounded by a knife and restrained with tape.",
                "entities": ["person", "knife", "sofa", "table", "chair", "laptop"],
                "location_type": "office",
                "confidence": 0.89,
                "model_used": "BLIP (Salesforce)",
            },
            "objects_detected": ["person", "knife", "sofa", "table", "chair", "laptop", "cup"],
            "processed_image_file": f"ev_demo_annotated_{image_orig_name}",
        }
        img_evidence.set_metadata(img_meta)
        db.session.add(img_evidence)
        db.session.flush()

        # Add image detections
        db.session.add(
            Detection(
                evidence_id=img_evidence.id,
                object_name="person",
                confidence=0.96,
                bbox_json="[210, 390, 480, 680]",
                timestamp=None,
                model_name="RT-DETR-l",
            )
        )
        db.session.add(
            Detection(
                evidence_id=img_evidence.id,
                object_name="knife",
                confidence=0.88,
                bbox_json="[340, 420, 390, 450]",
                timestamp=None,
                model_name="RT-DETR-l",
            )
        )
        db.session.add(
            Detection(
                evidence_id=img_evidence.id,
                object_name="sofa",
                confidence=0.93,
                bbox_json="[450, 180, 620, 420]",
                timestamp=None,
                model_name="RT-DETR-l",
            )
        )
        db.session.add(
            Detection(
                evidence_id=img_evidence.id,
                object_name="diningtable",
                confidence=0.91,
                bbox_json="[320, 190, 440, 360]",
                timestamp=None,
                model_name="RT-DETR-l",
            )
        )

        # 3. Ingest Audio Witness Statement with Multilingual Translations
        audio_orig_name, audio_path = self._get_or_create_witness_audio()
        aud_hash = calculate_sha256(audio_path)
        aud_size = audio_path.stat().st_size

        aud_evidence = Evidence(
            case_id=demo_case.id,
            filename="ttsMP3.com_VoiceText_2026.wav",
            stored_filename=audio_orig_name,
            file_type="audio",
            mime_type="audio/wav",
            file_size=aud_size,
            sha256_hash=aud_hash,
            analysis_status="COMPLETED",
        )

        aud_meta = {
            "is_demo_data": True,
            "language": "en",
            "event_type": "ROBBERY",
            "location": "STORE",
            "ai_summary": (
                "The witness reported observing two masked individuals exiting the jewelry store on Maple Avenue "
                "around 8 p.m., fleeing the scene in a dark car after dropping a necklace, and speeding away as "
                "the store's alarm sounded."
            ),
            "crime_timeline": DEFAULT_CRIME_TIMELINE,
            "translations": AUDIO_TRANSLATIONS,
            "model_used": "OpenAI Whisper (base)",
        }
        aud_evidence.set_metadata(aud_meta)
        db.session.add(aud_evidence)
        db.session.flush()

        # Add Transcripts
        for item in DEFAULT_CRIME_TIMELINE:
            min_sec = item["time"].split(":")
            sec = float(int(min_sec[0]) * 60 + int(min_sec[1]))
            db.session.add(
                Transcript(
                    evidence_id=aud_evidence.id,
                    start_time=sec,
                    end_time=sec + 4.0,
                    text=item["event"],
                    language="en",
                    confidence=0.95,
                )
            )

        # 4. Ingest CCTV Video Footage
        video_orig_name, video_path = self._get_or_create_surveillance_video()
        vid_hash = calculate_sha256(video_path)
        vid_size = video_path.stat().st_size

        vid_evidence = Evidence(
            case_id=demo_case.id,
            filename="cctv_commercial_exterior.mp4",
            stored_filename=video_orig_name,
            file_type="video",
            mime_type="video/mp4",
            file_size=vid_size,
            sha256_hash=vid_hash,
            analysis_status="COMPLETED",
        )
        vid_meta = {
            "is_demo_data": True,
            "duration_seconds": 24.0,
            "fps": 25.0,
            "resolution": "1280x720",
            "total_frames": 600,
            "processed_frames": 24,
            "objects_detected": ["person", "car", "truck"],
            "keyframes": [
                {"filename": f"ev_{vid_evidence.id}_kf_5s.jpg", "timestamp": 5.0, "timestamp_str": "00:00:05", "detections_count": 1},
                {"filename": f"ev_{vid_evidence.id}_kf_12s.jpg", "timestamp": 12.0, "timestamp_str": "00:00:12", "detections_count": 2},
                {"filename": f"ev_{vid_evidence.id}_kf_18s.jpg", "timestamp": 18.0, "timestamp_str": "00:00:18", "detections_count": 3},
            ],
        }
        vid_evidence.set_metadata(vid_meta)
        db.session.add(vid_evidence)
        db.session.flush()

        # 5. Timeline Events
        demo_events = [
            (0.0, "00:00", "speech_event", "witness noticed lights on inside jewelry store", 0.95, "audio", aud_evidence.id),
            (7.0, "00:07", "speech_event", "two masked individuals rushed out of store", 0.94, "audio", aud_evidence.id),
            (12.0, "00:12", "speech_event", "suspect dropped necklace on sidewalk", 0.93, "audio", aud_evidence.id),
            (15.0, "00:15", "speech_event", "suspects sped off in car", 0.96, "audio", aud_evidence.id),
            (21.0, "00:21", "speech_event", "store alarm blaring", 0.95, "audio", aud_evidence.id),
            (
                None,
                "timestamp_unavailable",
                "crime_scene_documented",
                "A male individual is observed lying on the floor, surrounded by a knife and restrained with tape in an office.",
                0.92,
                "image",
                img_evidence.id,
            ),
        ]

        for ts, ts_str, etype, desc, conf, src, evid in demo_events:
            ev = TimelineEvent(
                case_id=demo_case.id,
                evidence_id=evid,
                timestamp=ts,
                timestamp_str=ts_str,
                event_type=etype,
                description=desc,
                confidence=conf,
                source=src,
                metadata_json='{"is_demo_data": true}',
            )
            db.session.add(ev)

        db.session.commit()
        logger.info(f"Demo case {demo_case.case_number} seeded successfully.")
        return demo_case.to_dict()

    def _get_or_create_crime_scene_image(self) -> tuple[str, Path]:
        """Ensure crime scene image exists and is annotated."""
        filename = "crime-scene-investigation.jpg"
        path = self.originals_dir / filename
        processed_path = self.processed_dir / f"ev_demo_annotated_{filename}"

        if not path.exists():
            # Check demo folder or create realistic crime scene
            demo_src = self.demo_dir / filename
            if demo_src.exists():
                import shutil
                shutil.copy(str(demo_src), str(path))
            else:
                # Generate synthetic crime scene image
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                img[:] = (210, 215, 220)  # Office tile floor
                # Draw desk
                cv2.rectangle(img, (260, 60), (440, 200), (90, 110, 130), -1)
                # Draw sofa
                cv2.rectangle(img, (460, 120), (620, 360), (120, 60, 50), -1)
                # Draw individual lying down
                cv2.ellipse(img, (320, 340), (140, 45), 25, 0, 360, (50, 70, 110), -1)
                cv2.circle(img, (180, 280), 30, (160, 180, 200), -1)
                cv2.imwrite(str(path), img)

        # Ensure annotated version has green boxes
        if not processed_path.exists():
            img = cv2.imread(str(path))
            if img is not None:
                h, w = img.shape[:2]
                # Draw neon green bounding boxes matching reference screenshot
                green = (50, 255, 100)
                # Person box
                cv2.rectangle(img, (int(w * 0.25), int(h * 0.40)), (int(w * 0.85), int(h * 0.95)), green, 2)
                cv2.putText(img, "person 96%", (int(w * 0.25), int(h * 0.38)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, green, 1)
                # Table box
                cv2.rectangle(img, (int(w * 0.35), int(h * 0.15)), (int(w * 0.65), int(h * 0.45)), green, 2)
                cv2.putText(img, "table 91%", (int(w * 0.35), int(h * 0.13)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, green, 1)
                # Sofa box
                cv2.rectangle(img, (int(w * 0.65), int(h * 0.12)), (int(w * 0.95), int(h * 0.55)), green, 2)
                cv2.putText(img, "sofa 93%", (int(w * 0.65), int(h * 0.10)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, green, 1)

                cv2.imwrite(str(processed_path), img)

        return filename, path

    def _get_or_create_witness_audio(self) -> tuple[str, Path]:
        """Ensure witness audio recording exists."""
        filename = "ttsMP3.com_VoiceText_2026.wav"
        path = self.originals_dir / filename
        demo_src = self.demo_dir / "ttsMP3_witness_audio.wav"

        if not path.exists():
            if demo_src.exists():
                import shutil
                shutil.copy(str(demo_src), str(path))
            else:
                # Generate synthetic audio tone
                sample_rate = 16000
                duration = 5.0
                num_samples = int(sample_rate * duration)
                with wave.open(str(path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    for i in range(num_samples):
                        t = i / sample_rate
                        val = 0.2 * math.sin(2 * math.pi * 440 * t)
                        wf.writeframes(struct.pack("<h", int(val * 32767.0)))

        return filename, path

    def _get_or_create_surveillance_video(self) -> tuple[str, Path]:
        """Ensure surveillance CCTV video clip exists."""
        filename = "cctv_commercial_exterior.mp4"
        path = self.originals_dir / filename
        demo_src = self.demo_dir / "demo_sector4_surveillance.mp4"

        if not path.exists():
            if demo_src.exists():
                import shutil
                shutil.copy(str(demo_src), str(path))
            else:
                width, height = 640, 360
                fps = 10
                duration_sec = 4
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
                for f in range(fps * duration_sec):
                    frame = np.zeros((height, width, 3), dtype=np.uint8)
                    frame[:] = (35, 40, 50)
                    cv2.putText(frame, f"CCTV COMMERCIAL SEC-1 [00:00:0{f//fps}]", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    out.write(frame)
                out.release()

        return filename, path
