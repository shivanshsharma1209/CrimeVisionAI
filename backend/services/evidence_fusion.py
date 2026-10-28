import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("crimevision.fusion")


class EvidenceFusionEngine:
    """
    Multimodal Forensic Evidence Fusion Engine.
    Combines visual detections, video frame changes, and speech transcripts
    into a chronologically sorted, cross-modal forensic timeline.
    Preserves forensic integrity: never fabricates timestamps.
    """

    def fuse_case_evidence(
        self,
        timeline_events: List[Dict[str, Any]],
        image_evidences: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a unified timeline and cross-modal correlation intelligence.
        Args:
            timeline_events: List of raw timeline event dicts (from DB or active analysis)
            image_evidences: Optional list of static image evidence items without explicit video time
        """
        all_events = list(timeline_events)

        # Separate timestamped events from events where timestamp is unavailable
        timestamped_events = []
        unavailable_events = []

        for ev in all_events:
            ts = ev.get("timestamp")
            if ts is not None and isinstance(ts, (int, float)):
                timestamped_events.append(ev)
            else:
                # Static image evidence or events without timeline offset
                ev_copy = dict(ev)
                ev_copy["timestamp"] = None
                ev_copy["timestamp_str"] = "timestamp_unavailable"
                unavailable_events.append(ev_copy)

        # Sort timestamped events chronologically by timestamp float
        timestamped_events.sort(key=lambda x: (x["timestamp"], x.get("confidence", 0.0)))

        # Perform cross-modal correlation across timestamped events
        correlated_events = self._detect_cross_modal_correlations(timestamped_events)

        # Unified list: chronological events first, followed by static/undated evidence
        unified_timeline = correlated_events + unavailable_events

        # Summary statistics
        stats = self._calculate_timeline_statistics(unified_timeline)

        return {
            "timeline": unified_timeline,
            "total_events": len(unified_timeline),
            "timestamped_count": len(correlated_events),
            "undated_count": len(unavailable_events),
            "statistics": stats,
        }

    def _detect_cross_modal_correlations(
        self, events: List[Dict[str, Any]], time_window: float = 4.0
    ) -> List[Dict[str, Any]]:
        """
        Analyze concurrent audio and visual events occurring within a close time window.
        E.g., Person detected in video + Speech recorded at the same time window.
        """
        enhanced_events = []
        for i, ev in enumerate(events):
            item = dict(ev)
            correlations = []
            ev_time = ev.get("timestamp", 0.0)
            ev_source = ev.get("source", "")

            # Check neighbors within time_window
            for j, other in enumerate(events):
                if i == j:
                    continue
                other_time = other.get("timestamp", 0.0)
                other_source = other.get("source", "")

                if abs(ev_time - other_time) <= time_window and ev_source != other_source:
                    correlations.append(
                        {
                            "related_event_id": other.get("id"),
                            "related_type": other.get("event_type"),
                            "related_source": other_source,
                            "delta_seconds": round(abs(ev_time - other_time), 2),
                            "note": f"Cross-modal alignment: {ev_source} event coincides with {other_source} activity ({other.get('event_type')}).",
                        }
                    )

            if correlations:
                meta = item.get("metadata", {})
                if not isinstance(meta, dict):
                    meta = {}
                meta["cross_modal_correlations"] = correlations
                item["metadata"] = meta
                item["is_multimodal_correlated"] = True
            else:
                item["is_multimodal_correlated"] = False

            enhanced_events.append(item)

        return enhanced_events

    def _calculate_timeline_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate high-level counts and event distribution."""
        sources = {}
        event_types = {}
        avg_confidence = 0.0

        for ev in events:
            src = ev.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

            etype = ev.get("event_type", "generic")
            event_types[etype] = event_types.get(etype, 0) + 1

            conf = ev.get("confidence") or 0.0
            avg_confidence += conf

        if events:
            avg_confidence = round(avg_confidence / len(events), 3)

        return {
            "source_distribution": sources,
            "event_type_distribution": event_types,
            "average_confidence": avg_confidence,
        }
