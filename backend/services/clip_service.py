import logging
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from PIL import Image
import numpy as np

from config import Config

logger = logging.getLogger("crimevision.clip")

DEFAULT_CATEGORIES = [
    "street",
    "room",
    "office",
    "warehouse",
    "vehicle area",
    "outdoor area",
    "residential area",
    "commercial area",
    "unknown",
]


class CLIPService:
    """
    Visual-Semantic Analysis using OpenAI CLIP (via Hugging Face Transformers)
    with scene classification, similarity scoring, and fallback heuristics.
    """

    _model = None
    _processor = None
    _is_fallback = False
    _initialized = False

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or Config.CLIP_MODEL_NAME
        self.categories = DEFAULT_CATEGORIES
        self._initialize()

    def _initialize(self):
        if CLIPService._initialized:
            return

        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel

            logger.info(f"Loading CLIP model ({self.model_name})...")
            CLIPService._model = CLIPModel.from_pretrained(self.model_name)
            CLIPService._processor = CLIPProcessor.from_pretrained(self.model_name)
            CLIPService._model.eval()
            CLIPService._is_fallback = False
            CLIPService._initialized = True
            logger.info("CLIP model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"CLIP model could not be loaded ({e}). Using semantic heuristic fallback."
            )
            CLIPService._is_fallback = True
            CLIPService._initialized = True

    def classify_scene(
        self,
        image_input: Union[str, Path, Image.Image],
        custom_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Classify scene into categories with normalized confidence/similarity scores.
        Does NOT state conclusions as absolute facts.
        """
        categories = custom_categories or self.categories
        if "unknown" not in categories:
            categories.append("unknown")

        try:
            if isinstance(image_input, (str, Path)):
                img = Image.open(str(image_input)).convert("RGB")
            else:
                img = image_input

            # Run actual CLIP model if loaded
            if (
                not CLIPService._is_fallback
                and CLIPService._model is not None
                and CLIPService._processor is not None
            ):
                import torch

                prompts = [f"a photograph of a forensic scene in a {cat}" for cat in categories]
                inputs = CLIPService._processor(
                    text=prompts, images=img, return_tensors="pt", padding=True
                )
                with torch.no_grad():
                    outputs = CLIPService._model(**inputs)
                    logits_per_image = outputs.logits_per_image
                    probs = logits_per_image.softmax(dim=1).squeeze().tolist()

                if not isinstance(probs, list):
                    probs = [probs]

                scores = []
                for cat, prob in zip(categories, probs):
                    scores.append({"category": cat, "confidence": round(float(prob), 4)})
                scores.sort(key=lambda x: x["confidence"], reverse=True)

                top_cat = scores[0]["category"] if scores else "unknown"
                top_conf = scores[0]["confidence"] if scores else 0.0

                return {
                    "primary_category": top_cat,
                    "confidence": top_conf,
                    "all_scores": scores,
                    "model_used": "CLIP (ViT-B/32)",
                    "disclaimer": "Scores represent visual-semantic similarity, not verified factual classification.",
                }
        except Exception as e:
            logger.error(f"CLIP inference error: {e}")

        # Graceful fallback heuristic
        return self._heuristic_scene_classification(image_input, categories)

    def _heuristic_scene_classification(
        self, image_input: Union[str, Path, Image.Image], categories: List[str]
    ) -> Dict[str, Any]:
        """
        Lightweight visual heuristic analyzing brightness, color distribution,
        and aspect ratios for offline or fallback operation.
        """
        try:
            if isinstance(image_input, (str, Path)):
                img = Image.open(str(image_input)).convert("RGB")
            else:
                img = image_input

            stat_np = np.array(img.resize((64, 64)))
            avg_color = stat_np.mean(axis=(0, 1))  # R, G, B
            brightness = avg_color.mean()

            # Simple heuristic distribution
            scores = []
            if brightness > 150:
                top_cat = "outdoor area" if avg_color[2] > avg_color[0] else "office"
            elif brightness > 90:
                top_cat = "warehouse" if avg_color[0] > avg_color[2] else "street"
            else:
                top_cat = "room"

            for cat in categories:
                if cat == top_cat:
                    conf = 0.65
                elif cat == "unknown":
                    conf = 0.15
                else:
                    conf = round(0.20 / (len(categories) - 1), 3)
                scores.append({"category": cat, "confidence": conf})

            scores.sort(key=lambda x: x["confidence"], reverse=True)
            return {
                "primary_category": top_cat,
                "confidence": 0.65,
                "all_scores": scores,
                "model_used": "Visual-Semantic Heuristic (Fallback)",
                "disclaimer": "Scores represent visual-semantic similarity, not verified factual classification.",
            }
        except Exception:
            return {
                "primary_category": "unknown",
                "confidence": 0.50,
                "all_scores": [{"category": cat, "confidence": 1.0 / len(categories)} for cat in categories],
                "model_used": "Default Heuristic (Fallback)",
                "disclaimer": "Scene classification unavailable.",
            }
