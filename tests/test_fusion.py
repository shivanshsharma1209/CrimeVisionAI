from backend.services.evidence_fusion import EvidenceFusionEngine


def test_timeline_chronological_sorting():
    engine = EvidenceFusionEngine()

    raw_events = [
        {"id": 1, "timestamp": 15.2, "timestamp_str": "00:00:15", "source": "video", "event_type": "scene_change", "confidence": 0.88},
        {"id": 2, "timestamp": 4.1, "timestamp_str": "00:00:04", "source": "video", "event_type": "person_detected", "confidence": 0.94},
        {"id": 3, "timestamp": None, "timestamp_str": "timestamp_unavailable", "source": "image", "event_type": "object_detected", "confidence": 0.82},
        {"id": 4, "timestamp": 4.5, "timestamp_str": "00:00:04", "source": "audio", "event_type": "speech_event", "confidence": 0.92},
    ]

    result = engine.fuse_case_evidence(raw_events)

    assert result["total_events"] == 4
    assert result["timestamped_count"] == 3
    assert result["undated_count"] == 1

    timeline = result["timeline"]
    # Check that first event is 4.1s
    assert timeline[0]["timestamp"] == 4.1
    # Check that second event is 4.5s
    assert timeline[1]["timestamp"] == 4.5
    # Check that third event is 15.2s
    assert timeline[2]["timestamp"] == 15.2
    # Undated event is placed at the end with timestamp None
    assert timeline[3]["timestamp"] is None
    assert timeline[3]["timestamp_str"] == "timestamp_unavailable"


def test_cross_modal_correlation():
    engine = EvidenceFusionEngine()

    # Audio event at 5.0s, video event at 5.5s (delta 0.5s <= 4.0s window)
    events = [
        {"id": 10, "timestamp": 5.0, "timestamp_str": "00:00:05", "source": "video", "event_type": "person_detected", "confidence": 0.90},
        {"id": 20, "timestamp": 5.5, "timestamp_str": "00:00:05", "source": "audio", "event_type": "speech_event", "confidence": 0.95},
    ]

    result = engine.fuse_case_evidence(events)
    timeline = result["timeline"]

    assert timeline[0]["is_multimodal_correlated"] is True
    assert timeline[1]["is_multimodal_correlated"] is True
    corrs = timeline[0]["metadata"]["cross_modal_correlations"]
    assert len(corrs) == 1
    assert corrs[0]["related_event_id"] == 20
