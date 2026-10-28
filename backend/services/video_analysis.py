import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np

from config import Config
from backend.services.object_detection import ObjectDetectionService

logger = logging.getLogger("crimevision.video_analysis")


def format_seconds_to_timestamp(seconds: float) -> str:
    """Format float seconds into standard HH:MM:SS format."""
    total_sec = max(0, int(round(seconds)))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    sec = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{sec:02d}"


class VideoAnalysisService:
    """
    Forensic Video Analysis Engine:
    - Metadata extraction (FPS, duration, resolution)
    - Intelligent frame sampling
    - RT-DETR object detection across keyframes
    - Forensic video event extraction and change detection
    """

    def __init__(self):
        self.detector = ObjectDetectionService()
        self.sample_fps = Config.VIDEO_SAMPLE_FPS

    def analyze_video(
        self,
        video_path: Path,
        processed_dir: Path,
        evidence_id: int,
    ) -> Dict[str, Any]:
        """
        Process video evidence:
        - Extract video technical metadata
        - Sample keyframes at configured rate (or scene changes)
        - Run RT-DETR on sampled frames
        - Generate timestamped forensic events
        - Save annotated keyframes to processed_dir
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Determine frame skip interval based on target sampling FPS
        # e.g., if video is 30 FPS and sample_fps is 1, sample every 30 frames
        sample_step = max(1, int(round(fps / max(0.1, self.sample_fps))))

        all_detections: List[Dict[str, Any]] = []
        video_events: List[Dict[str, Any]] = []
        sampled_keyframe_files: List[Dict[str, Any]] = []

        prev_gray_frame = None
        prev_detected_objects = set()

        current_frame_idx = 0
        processed_frames_count = 0

        logger.info(
            f"Analyzing video: {video_path.name} ({duration:.1f}s, {width}x{height}, {fps:.1f} FPS, step={sample_step})"
        )

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if current_frame_idx % sample_step == 0:
                processed_frames_count += 1
                curr_time_sec = current_frame_idx / fps
                timestamp_str = format_seconds_to_timestamp(curr_time_sec)

                # Check for scene change via frame differencing
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                is_scene_change = False
                if prev_gray_frame is not None:
                    diff = cv2.absdiff(prev_gray_frame, gray)
                    diff_mean = np.mean(diff)
                    if diff_mean > 35.0:  # Significant visual difference
                        is_scene_change = True
                        video_events.append(
                            {
                                "timestamp": round(curr_time_sec, 2),
                                "timestamp_str": timestamp_str,
                                "event_type": "scene_change",
                                "description": f"Significant visual transition detected at {timestamp_str}.",
                                "confidence": 0.88,
                                "source": "video",
                                "metadata": {"diff_mean": round(float(diff_mean), 2)},
                            }
                        )
                prev_gray_frame = gray

                # Run object detection on keyframe
                frame_dets = self.detector.detect(frame, timestamp=round(curr_time_sec, 2))
                current_objects = set()
                persons_count = 0
                vehicles_count = 0

                for d in frame_dets:
                    all_detections.append(d)
                    obj_name = d["object"].lower()
                    current_objects.add(obj_name)
                    if "person" in obj_name:
                        persons_count += 1
                    elif any(v in obj_name for v in ["car", "truck", "bus", "motorcycle", "vehicle"]):
                        vehicles_count += 1

                # Generate high-value forensic events based on detections
                # 1. Person detected event (when first appearing or isolated)
                if persons_count > 0 and "person" not in prev_detected_objects:
                    video_events.append(
                        {
                            "timestamp": round(curr_time_sec, 2),
                            "timestamp_str": timestamp_str,
                            "event_type": "person_detected",
                            "description": f"Individual observed entering camera frame at {timestamp_str}.",
                            "confidence": 0.92,
                            "source": "video",
                            "metadata": {"count": persons_count},
                        }
                    )

                # 2. Multiple people event
                if persons_count >= 2:
                    video_events.append(
                        {
                            "timestamp": round(curr_time_sec, 2),
                            "timestamp_str": timestamp_str,
                            "event_type": "multiple_people",
                            "description": f"Multiple individuals ({persons_count}) observed simultaneously in view.",
                            "confidence": 0.90,
                            "source": "video",
                            "metadata": {"count": persons_count},
                        }
                    )

                # 3. Vehicle detected event
                if vehicles_count > 0 and not any(v in prev_detected_objects for v in ["car", "truck", "vehicle"]):
                    video_events.append(
                        {
                            "timestamp": round(curr_time_sec, 2),
                            "timestamp_str": timestamp_str,
                            "event_type": "vehicle_detected",
                            "description": f"Vehicular entity observed in frame at {timestamp_str}.",
                            "confidence": 0.89,
                            "source": "video",
                            "metadata": {"count": vehicles_count},
                        }
                    )

                # 4. Weapon candidate detection
                for d in frame_dets:
                    if d.get("is_weapon_candidate"):
                        video_events.append(
                            {
                                "timestamp": round(curr_time_sec, 2),
                                "timestamp_str": timestamp_str,
                                "event_type": "weapon_candidate",
                                "description": f"Potential weapon-like object ({d['object']}) detected (confidence: {int(d['confidence']*100)}%). Verification required.",
                                "confidence": d["confidence"],
                                "source": "video",
                                "metadata": {"candidate_object": d["object"], "bbox": d["bbox"]},
                            }
                        )

                # Save annotated keyframe snapshot if events occurred or at regular intervals
                if frame_dets or is_scene_change or len(sampled_keyframe_files) == 0:
                    kf_filename = f"ev_{evidence_id}_kf_{int(curr_time_sec)}s.jpg"
                    kf_path = processed_dir / kf_filename
                    self.detector.draw_detections(frame, frame_dets, kf_path)
                    sampled_keyframe_files.append(
                        {
                            "filename": kf_filename,
                            "timestamp": round(curr_time_sec, 2),
                            "timestamp_str": timestamp_str,
                            "detections_count": len(frame_dets),
                        }
                    )

                prev_detected_objects = current_objects

            current_frame_idx += 1

        cap.release()

        # If no specific events were detected, record a neutral baseline event
        if not video_events:
            video_events.append(
                {
                    "timestamp": 0.0,
                    "timestamp_str": "00:00:00",
                    "event_type": "video_reviewed",
                    "description": f"Video footage analyzed across {duration:.1f}s. No high-confidence anomalies flagged.",
                    "confidence": 0.95,
                    "source": "video",
                    "metadata": {},
                }
            )

        metadata = {
            "duration_seconds": round(duration, 2),
            "fps": round(fps, 2),
            "resolution": f"{width}x{height}",
            "width": width,
            "height": height,
            "total_frames": frame_count,
            "processed_frames": processed_frames_count,
            "sampling_rate_fps": self.sample_fps,
            "keyframes": sampled_keyframe_files,
            "detections_count": len(all_detections),
            "events_count": len(video_events),
        }

        return {
            "metadata": metadata,
            "detections": all_detections,
            "events": video_events,
            "keyframes": sampled_keyframe_files,
        }
