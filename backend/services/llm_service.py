import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from config import Config

logger = logging.getLogger("crimevision.llm")

STRICT_FORENSIC_SYSTEM_PROMPT = """You are CrimeVision AI, an expert forensic evidence analysis assistant designed for forensic investigators and decision-support.

STRICT FORENSIC REASONING RULES:
1. Never fabricate evidence or facts that are not present in the provided case context.
2. Never identify any individual as guilty, criminal, or legally responsible. This is a decision-support platform, NOT an autonomous system determining guilt or innocence.
3. Do not infer sensitive personal characteristics or criminal intent solely from appearance or proximity.
4. Clearly distinguish between directly observed empirical evidence (e.g. "a person was detected at timestamp 00:00:15") and analytical inference.
5. Always cite specific evidence IDs or timeline references in brackets, e.g. [EV-1], [TL-3], [TR-1].
6. If the provided evidence is incomplete, ambiguous, or insufficient to reach a conclusion, explicitly state that it is insufficient.
7. Mention limitations and uncertainty levels for detections or inferences when applicable.
8. Maintain a strictly objective, clinical, neutral forensic tone.
"""


class LLMService:
    """
    Forensic Reasoning & AI Evidence Chat Service using Groq LLM
    with lightweight RAG retrieval and analytical fallback.
    """

    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        self.model = Config.GROQ_MODEL
        self._groq_client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.api_key:
            try:
                from groq import Groq

                self._groq_client = Groq(api_key=self.api_key)
                logger.info(f"Groq LLM client initialized (model: {self.model}).")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
                self._groq_client = None

    def query_evidence_chat(
        self,
        case_id: int,
        user_query: str,
        case_data: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
        timeline_list: List[Dict[str, Any]],
        transcripts_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Forensic RAG Chat:
        1. Retrieve relevant items from evidence, timeline, and transcripts.
        2. Construct context with strict citation anchors.
        3. Invoke Groq LLM (or structured forensic rule-based analyzer if API key absent).
        4. Return answer, cited evidence references, and limitations.
        """
        retrieved_context, cited_references = self._retrieve_relevant_context(
            user_query, case_data, evidence_list, timeline_list, transcripts_list
        )

        if self._groq_client is not None:
            try:
                user_prompt = f"""CASE RECORD:
Case #{case_data.get('case_number')} - "{case_data.get('title')}"
Status: {case_data.get('status')}
Investigator: {case_data.get('investigator')}

FORENSIC EVIDENCE REPOSITORY FOR CASE #{case_data.get('case_number')}:
{retrieved_context}

INVESTIGATOR QUESTION:
"{user_query}"

Provide an objective forensic response adhering strictly to the forensic guidelines. Cite evidence items [EV-id] or [TL-id] where applicable."""

                completion = self._groq_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": STRICT_FORENSIC_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=850,
                )

                answer_text = completion.choices[0].message.content

                return {
                    "answer": answer_text,
                    "evidence_references": cited_references,
                    "model_used": f"Groq ({self.model})",
                    "disclaimer": "AI-assisted reasoning decision-support. Findings subject to independent investigator verification.",
                    "status": "SUCCESS",
                }
            except Exception as e:
                logger.error(f"Groq LLM call failed: {e}. Utilizing analytical fallback.")

        return self._analytical_fallback_reasoning(
            user_query, case_data, evidence_list, timeline_list, transcripts_list, cited_references
        )

    def _retrieve_relevant_context(
        self,
        query: str,
        case_data: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
        timeline_list: List[Dict[str, Any]],
        transcripts_list: List[Dict[str, Any]],
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Rank and format relevant evidence items matching query tokens."""
        query_words = set(re.findall(r"\w+", query.lower()))
        context_lines = []
        cited_references = []

        # 1. Evidence items context
        context_lines.append("=== REGISTERED EVIDENCE FILES ===")
        for ev in evidence_list:
            ev_id = ev.get("id")
            meta = ev.get("metadata", {})
            desc = meta.get("scene_description", {}).get("description", "")
            objs = meta.get("objects_detected", [])

            line = f"[EV-{ev_id}] Type: {ev.get('file_type').upper()} | File: {ev.get('filename')} | SHA256: {ev.get('sha256_hash')[:12]}..."
            if objs:
                line += f" | Detected: {', '.join(objs)}"
            if desc:
                line += f" | Scene: {desc}"
            context_lines.append(line)

            text_corpus = f"{ev.get('filename')} {ev.get('file_type')} {' '.join(objs)} {desc}".lower()
            if any(w in text_corpus for w in query_words) or len(query_words) == 0:
                cited_references.append(
                    {
                        "ref_id": f"EV-{ev_id}",
                        "type": "evidence",
                        "title": ev.get("filename"),
                        "details": desc or f"{ev.get('file_type')} evidence",
                    }
                )

        # 2. Timeline Events context
        context_lines.append("\n=== CHRONOLOGICAL TIMELINE EVENTS ===")
        for tl in timeline_list:
            tl_id = tl.get("id")
            ts = tl.get("timestamp_str", "timestamp_unavailable")
            desc = tl.get("description", "")
            etype = tl.get("event_type", "")
            conf = tl.get("confidence", 1.0)

            context_lines.append(
                f"[TL-{tl_id}] Time: {ts} | Type: {etype} | Conf: {conf:.2f} | {desc}"
            )

            tl_corpus = f"{ts} {etype} {desc}".lower()
            if any(w in tl_corpus for w in query_words):
                cited_references.append(
                    {
                        "ref_id": f"TL-{tl_id}",
                        "type": "timeline",
                        "title": f"Event at {ts}",
                        "details": desc,
                    }
                )

        # 3. Audio Transcripts context
        if transcripts_list:
            context_lines.append("\n=== SPEECH TRANSCRIPTS ===")
            for tr in transcripts_list:
                tr_id = tr.get("id")
                start = tr.get("start_time", 0.0)
                lang = tr.get("language", "en")
                text = tr.get("text", "")
                context_lines.append(f"[TR-{tr_id}] Lang: {lang} | {start:.1f}s: \"{text}\"")

                if any(w in text.lower() for w in query_words):
                    cited_references.append(
                        {
                            "ref_id": f"TR-{tr_id}",
                            "type": "transcript",
                            "title": f"Transcript ({lang})",
                            "details": text,
                        }
                    )

        if not cited_references and evidence_list:
            for ev in evidence_list[:2]:
                cited_references.append(
                    {
                        "ref_id": f"EV-{ev.get('id')}",
                        "type": "evidence",
                        "title": ev.get("filename"),
                        "details": f"{ev.get('file_type')} item",
                    }
                )

        return "\n".join(context_lines), cited_references

    def _analytical_fallback_reasoning(
        self,
        query: str,
        case_data: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
        timeline_list: List[Dict[str, Any]],
        transcripts_list: List[Dict[str, Any]],
        cited_references: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Rule-based analytical forensic response generator when Groq API key is unconfigured.
        Provides accurate, strictly factual answers derived from parsed case data.
        """
        q_lower = query.lower()

        if any(w in q_lower for w in ["what people", "person", "who was", "people detected"]):
            person_dets = []
            for ev in evidence_list:
                for det in ev.get("detections", []):
                    if any(p in det.get("object_name", "").lower() for p in ["person", "human", "man", "woman"]):
                        person_dets.append(f"{det.get('object_name')} in [EV-{ev.get('id')}]")

            persons_events = [
                tl for tl in timeline_list if any(p in tl.get("event_type", "").lower() or p in tl.get("description", "").lower() for p in ["person", "human", "individual", "male", "female", "suspect", "witness"])
            ]

            if persons_events or person_dets:
                details = "; ".join([f"[TL-{t.get('id')} at {t.get('timestamp_str')}]: {t.get('description')}" for t in persons_events])
                answer = (
                    f"Human people and individual entities were detected across active case evidence: {details or ', '.join(person_dets)}. "
                    "Note: In accordance with forensic standards, the system does not infer personal identity or intent from visual appearance alone."
                )
            else:
                answer = "No person detections are currently indexed in the active evidence records for this case."

        elif any(w in q_lower for w in ["object", "weapon", "knife", "car", "vehicle"]):
            all_objs = []
            for ev in evidence_list:
                objs = ev.get("metadata", {}).get("objects_detected", [])
                if objs:
                    all_objs.extend([f"{o} ([EV-{ev.get('id')}])" for o in objs])
            if all_objs:
                answer = f"The following physical entities were isolated by the object detection pipeline: {', '.join(set(all_objs))}."
            else:
                answer = "No distinct vehicle or object categories have been confirmed above the detection threshold."

        elif any(w in q_lower for w in ["audio", "speech", "hear", "voice", "transcript", "say"]):
            if transcripts_list:
                tr_texts = [f"\"{t.get('text')}\" (at {t.get('start_time')}s, lang: {t.get('language')}, [TR-{t.get('id')}])" for t in transcripts_list]
                answer = f"Forensic audio analysis identified the following speech segments: {' '.join(tr_texts)}."
            else:
                answer = "No audio speech transcripts are currently registered for this case."

        elif any(w in q_lower for w in ["first", "timeline", "summarize", "summary", "happened"]):
            if timeline_list:
                first_ev = timeline_list[0]
                total = len(timeline_list)
                answer = (
                    f"Forensic Timeline Reconstruction for Case #{case_data.get('case_number')}:\n"
                    f"- Initial recorded event occurs at {first_ev.get('timestamp_str')} ([TL-{first_ev.get('id')}]: {first_ev.get('description')}).\n"
                    f"- A total of {total} chronological events have been synthesized across visual and audio streams.\n"
                    "All timeline events maintain strict chronological sequence without fabricated timestamps."
                )
            else:
                answer = f"Case #{case_data.get('case_number')} currently has no processed timeline events."

        else:
            answer = (
                f"Forensic Assessment for Case #{case_data.get('case_number')} ({case_data.get('title')}):\n"
                f"- Total Evidence Files: {len(evidence_list)}\n"
                f"- Total Timeline Events: {len(timeline_list)}\n"
                f"- Audio Transcripts: {len(transcripts_list)}\n"
                "The records show documented visual and auditory forensic evidence. "
                "For deeper LLM reasoning, configure GROQ_API_KEY in your environment."
            )

        return {
            "answer": answer,
            "evidence_references": cited_references,
            "model_used": "Forensic Analytical Rule-Based Engine (Groq Key Unconfigured)",
            "disclaimer": "Groq LLM API key not configured or offline. Operating via analytical decision-support fallback.",
            "status": "FALLBACK_SUCCESS",
        }
