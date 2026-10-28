import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import Config

logger = logging.getLogger("crimevision.object_detection")

# Known weapon-like classes in standard COCO datasets
COCO_WEAPON_CANDIDATES = {"knife", "scissors", "baseball bat"}


class ObjectDetectionService:
    """
    Forensic Object Detection Service using RT-DETR / Ultralytics adapters
    with graceful fallback for offline or constrained environments.
    """

    _instance = None
    _model = None
    _model_name = None
    _is_fallback = False
    _custom_weapon_model = None

    def __init__(self):
        self.model_path = Config.RT_DETR_MODEL_PATH
        self.custom_weapon_path = Config.CUSTOM_WEAPON_MODEL_PATH
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
        self._initialize_model()

    def _initialize_model(self):
        """Lazy load or initialize RT-DETR or fallback model."""
        if ObjectDetectionService._model is not None:
            return

        # Attempt to load custom weapon model if path provided
        if self.custom_weapon_path and os.path.exists(self.custom_weapon_path):
            try:
                from ultralytics import YOLO
                ObjectDetectionService._custom_weapon_model = YOLO(self.custom_weapon_path)
                logger.info(f"Loaded custom weapon detection model from {self.custom_weapon_path}")
            except Exception as e:
                logger.warning(f"Failed to load custom weapon model: {e}")

        # Attempt to load RT-DETR
        try:
            from ultralytics import RTDETR
            logger.info(f"Attempting to load RT-DETR model ({self.model_path})...")
            # RTDETR('rtdetr-l.pt')
            model = RTDETR(self.model_path)
            ObjectDetectionService._model = model
            ObjectDetectionService._model_name = f"RT-DETR ({Path(self.model_path).name})"
            ObjectDetectionService._is_fallback = False
            logger.info("RT-DETR model loaded successfully.")
            return
        except Exception as e_rtdetr:
            logger.warning(f"Could not load RT-DETR ({e_rtdetr}). Attempting YOLOv8 fallback...")

        # Fallback to YOLOv8n if RT-DETR unavailable
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            ObjectDetectionService._model = model
            ObjectDetectionService._model_name = "YOLOv8n (RT-DETR Fallback)"
            ObjectDetectionService._is_fallback = False
            logger.info("YOLOv8n model loaded successfully as fallback detector.")
            return
        except Exception as e_yolo:
            logger.warning(f"Could not load YOLOv8n ({e_yolo}). Engaging Computer Vision Heuristic Fallback.")

        # If both fail (e.g., completely offline with no cached weights)
        ObjectDetectionService._model = "CV_HEURISTIC_DETECTOR"
        ObjectDetectionService._model_name = "Forensic CV HOG/Blob Detector (Offline Fallback)"
        ObjectDetectionService._is_fallback = True

    def get_service_status(self) -> Dict[str, Any]:
        """Expose current model configuration and forensic disclosures."""
        return {
            "model_name": ObjectDetectionService._model_name or "Uninitialized",
            "is_fallback": ObjectDetectionService._is_fallback,
            "custom_weapon_model_loaded": ObjectDetectionService._custom_weapon_model is not None,
            "weapon_disclosure": (
                "Generic COCO pretrained models detect knife and scissors. "
                "Firearms/specialized weapon detection requires a dedicated trained checkpoint."
            ),
            "confidence_threshold": self.confidence_threshold,
        }

    def detect(
        self,
        image_input: Union[str, Path, np.ndarray],
        timestamp: Optional[float] = None,
        conf_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run object detection on an image path or OpenCV BGR numpy array.
        Returns a list of structured detection objects.
        """
        threshold = conf_threshold or self.confidence_threshold
        detections: List[Dict[str, Any]] = []

        if ObjectDetectionService._model is None:
            self._initialize_model()

        # Handle real Ultralytics RT-DETR or YOLO model
        if not ObjectDetectionService._is_fallback and hasattr(ObjectDetectionService._model, "predict"):
            try:
                results = ObjectDetectionService._model.predict(
                    source=image_input,
                    conf=threshold,
                    verbose=False,
                )
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = r.names.get(cls_id, f"object_{cls_id}")
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                        bbox = [int(round(coord)) for coord in xyxy]

                        # Check if weapon candidate
                        is_weapon_candidate = cls_name.lower() in COCO_WEAPON_CANDIDATES

                        detections.append(
                            {
                                "type": "visual_detection",
                                "object": cls_name,
                                "confidence": round(conf, 4),
                                "bbox": bbox,
                                "timestamp": timestamp,
                                "is_weapon_candidate": is_weapon_candidate,
                                "model_used": ObjectDetectionService._model_name,
                            }
                        )
                return detections
            except Exception as e:
                logger.error(f"Inference error with primary detector: {e}. Falling back to CV detector.")

        # Fallback: OpenCV HOG Person Detector & Heuristics
        return self._cv_heuristic_detect(image_input, timestamp, threshold)

    def _cv_heuristic_detect(
        self,
        image_input: Union[str, Path, np.ndarray],
        timestamp: Optional[float] = None,
        conf_threshold: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """
        Lightweight fallback detector using OpenCV HOG person detector and basic contour analysis.
        Ensures the application operates cleanly in offline or resource-restricted environments.
        """
        detections: List[Dict[str, Any]] = []
        try:
            if isinstance(image_input, (str, Path)):
                img = cv2.imread(str(image_input))
            else:
                img = image_input

            if img is None:
                return detections

            h, w = img.shape[:2]

            # Use OpenCV HOG person detector
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            rects, weights = hog.detectMultiScale(
                img, winStride=(8, 8), padding=(16, 16), scale=1.05
            )

            for (x, y, rw, rh), weight in zip(rects, weights):
                conf = float(min(0.92, max(0.40, weight * 0.3 + 0.4)))
                if conf >= conf_threshold:
                    detections.append(
                        {
                            "type": "visual_detection",
                            "object": "person",
                            "confidence": round(conf, 4),
                            "bbox": [int(x), int(y), int(x + rw), int(y + rh)],
                            "timestamp": timestamp,
                            "is_weapon_candidate": False,
                            "model_used": "OpenCV HOG Person Detector (Fallback)",
                        }
                    )

            # Basic motion/object blob detection if no persons found
            if not detections:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edged = cv2.Canny(blurred, 50, 150)
                contours, _ = cv2.findContours(
                    edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                for c in contours:
                    if cv2.contourArea(c) > (w * h * 0.05):  # Large significant contour
                        bx, by, bw, bh = cv2.boundingRect(c)
                        detections.append(
                            {
                                "type": "visual_detection",
                                "object": "object",
                                "confidence": 0.55,
                                "bbox": [int(bx), int(by), int(bx + bw), int(by + bh)],
                                "timestamp": timestamp,
                                "is_weapon_candidate": False,
                                "model_used": "OpenCV Salient Object (Fallback)",
                            }
                        )
                        break
        except Exception as e:
            logger.error(f"Fallback detection error: {e}")

        return detections

    def draw_detections(
        self,
        image_path: Union[str, Path],
        detections: List[Dict[str, Any]],
        output_path: Union[str, Path],
    ) -> bool:
        """
        Draw forensic-style bounding boxes, class labels, confidence scores,
        and forensic verification watermark on the output image.
        """
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return False

            h, w = img.shape[:2]

            for det in detections:
                bbox = det.get("bbox", [])
                if len(bbox) != 4:
                    continue
                x1, y1, x2, y2 = bbox
                # Clamp coordinates to image boundaries
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)

                obj_name = det.get("object", "object").upper()
                conf = det.get("confidence", 0.0)
                is_weapon = det.get("is_weapon_candidate", False)

                # Color scheme:
                # Weapon candidate: Neon Amber/Red (0, 100, 255) in BGR
                # Person: Neon Cyan (255, 200, 0)
                # Vehicle/other: Emerald Green (50, 205, 50)
                if is_weapon:
                    box_color = (0, 80, 255)  # Red/Orange in BGR
                elif "person" in obj_name.lower():
                    box_color = (255, 200, 0)  # Cyan in BGR
                elif any(v in obj_name.lower() for v in ["car", "truck", "vehicle", "bus", "motorcycle"]):
                    box_color = (50, 220, 100)  # Emerald in BGR
                else:
                    box_color = (220, 160, 50)  # Blue/Teal in BGR

                # Draw bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)

                # Draw label badge
                label = f"{obj_name} {int(conf * 100)}%"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

                # Badge background
                badge_y1 = max(0, y1 - text_h - 8)
                badge_y2 = y1
                badge_x2 = min(w, x1 + text_w + 10)
                cv2.rectangle(img, (x1, badge_y1), (badge_x2, badge_y2), box_color, -1)

                # Text inside badge (black text for high contrast on neon badge)
                cv2.putText(
                    img,
                    label,
                    (x1 + 4, y1 - 4),
                    font,
                    font_scale,
                    (10, 10, 10),
                    thickness,
                    cv2.LINE_AA,
                )

            # Forensic Watermark banner at the bottom
            banner_h = 24
            cv2.rectangle(img, (0, h - banner_h), (w, h), (15, 20, 30), -1)
            watermark_text = f"CRIMEVISION AI FORENSIC ANALYSIS | DETECTIONS: {len(detections)} | DECISION-SUPPORT ONLY"
            cv2.putText(
                img,
                watermark_text,
                (10, h - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (180, 190, 200),
                1,
                cv2.LINE_AA,
            )

            # Ensure parent directory exists and write image
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), img)
            return True
        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            return False
