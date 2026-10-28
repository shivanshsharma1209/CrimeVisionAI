import logging
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from PIL import Image

from config import Config

logger = logging.getLogger("crimevision.blip")


class BLIPService:
    """
    Forensic scene description & captioning service using Salesforce BLIP
    with structured entity extraction and forensic neutrality safeguards.
    """

    _model = None
    _processor = None
    _is_fallback = False
    _initialized = False

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or Config.BLIP_MODEL_NAME
        self._initialize()

    def _initialize(self):
        if BLIPService._initialized:
            return

        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration

            logger.info(f"Loading BLIP captioning model ({self.model_name})...")
            BLIPService._processor = BlipProcessor.from_pretrained(self.model_name)
            BLIPService._model = BlipForConditionalGeneration.from_pretrained(self.model_name)
            BLIPService._model.eval()
            BLIPService._is_fallback = False
            BLIPService._initialized = True
            logger.info("BLIP model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"BLIP model could not be loaded ({e}). Using forensic descriptive heuristic."
            )
            BLIPService._is_fallback = True
            BLIPService._initialized = True

    def describe(
        self,
        image_input: Union[str, Path, Image.Image],
        detected_objects: Optional[List[str]] = None,
        scene_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate neutral forensic description and convert into structured evidence.
        Never infers guilt, criminal intent, or identity.
        """
        objects = [o.lower() for o in (detected_objects or [])]
        unique_entities = sorted(list(set(objects))) if objects else []

        # Try real BLIP model
        if not BLIPService._is_fallback and BLIPService._model and BLIPService._processor:
            try:
                import torch

                if isinstance(image_input, (str, Path)):
                    raw_image = Image.open(str(image_input)).convert("RGB")
                else:
                    raw_image = image_input

                # Conditional forensic caption prompt
                inputs = BLIPService._processor(raw_image, return_tensors="pt")
                with torch.no_grad():
                    out = BLIPService._model.generate(**inputs, max_new_tokens=40)
                    caption = BLIPService._processor.decode(out[0], skip_special_tokens=True).strip()

                if caption:
                    # Sanitize caption to maintain neutral forensic language
                    sanitized_caption = self._enforce_forensic_neutrality(caption)
                    return {
                        "description": sanitized_caption,
                        "entities": unique_entities or self._extract_entities_from_text(caption),
                        "location_type": scene_category or "unspecified",
                        "confidence": 0.84,
                        "model_used": "BLIP (Salesforce)",
                    }
            except Exception as e:
                logger.error(f"BLIP generation failed: {e}. Using structured synthesis.")

        # Structured synthesis fallback using detected objects and scene
        return self._synthesize_neutral_description(unique_entities, scene_category)

    def _synthesize_neutral_description(
        self, entities: List[str], scene_category: Optional[str]
    ) -> Dict[str, Any]:
        """Synthesize neutral forensic description from observed entities and scene classification."""
        loc = scene_category or "indoor/outdoor setting"

        if not entities:
            desc = f"Visual evidence shows a scene located in a {loc} with no distinct human or vehicular entities isolated at primary confidence threshold."
            conf = 0.60
        elif "person" in entities and any(v in entities for v in ["car", "truck", "motorcycle", "vehicle"]):
            desc = f"Observed footage indicates presence of human individual(s) in proximity to vehicular entities within a {loc}."
            conf = 0.82
        elif "person" in entities:
            desc = f"Observed scene captures person(s) present within a {loc}."
            conf = 0.85
        elif any(v in entities for v in ["car", "truck", "motorcycle", "vehicle"]):
            desc = f"Observed scene records vehicle(s) stationed or active in a {loc}."
            conf = 0.80
        else:
            items_str = ", ".join(entities[:4])
            desc = f"Visual recording shows {items_str} present within a {loc}."
            conf = 0.75

        return {
            "description": desc,
            "entities": entities,
            "location_type": loc,
            "confidence": conf,
            "model_used": "Forensic Scene Synthesizer (Structured Fallback)",
        }

    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract recognizable forensic object keywords from text."""
        keywords = ["person", "man", "woman", "car", "vehicle", "truck", "backpack", "phone", "knife", "door", "window"]
        found = []
        lower = text.lower()
        for kw in keywords:
            if kw in lower:
                found.append("person" if kw in ["man", "woman"] else kw)
        return list(set(found))

    def _enforce_forensic_neutrality(self, text: str) -> str:
        """Strip judgmental or biased phrasing from auto-generated captions."""
        forbidden_replacements = {
            "criminal": "individual",
            "suspect": "individual",
            "thief": "individual",
            "attacker": "individual",
            "victim": "individual",
            "stole": "interacted with",
            "fleeing": "moving away",
            "suspicious": "observed",
        }
        words = text.split()
        sanitized = []
        for w in words:
            clean = w.lower().strip(".,:;!?'\"")
            if clean in forbidden_replacements:
                sanitized.append(forbidden_replacements[clean])
            else:
                sanitized.append(w)
        return " ".join(sanitized)
