import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def run_acceptance_tests():
    print("=" * 60)
    print("CRIMEVISION AI - END-TO-END ACCEPTANCE TEST SUITE")
    print("=" * 60)

    # 1. Health & Status
    res = requests.get(f"{BASE_URL}/api/system/status")
    assert res.status_code == 200, f"System status failed: {res.text}"
    status_data = res.json()["data"]
    print(f"[OK] System Status: Platform: {status_data['platform']} | Device: {status_data['device']}")
    print(f"     Detector: {status_data['models']['object_detector']}")

    # 2. Main Dashboard Stats
    res = requests.get(f"{BASE_URL}/api/dashboard/stats")
    assert res.status_code == 200
    print(f"[OK] Dashboard Stats: {res.json()['data']['total_cases']} cases, {res.json()['data']['total_evidence']} evidence items")

    # 3. Seed Demo Case
    res = requests.post(f"{BASE_URL}/api/demo/seed")
    assert res.status_code in [200, 201]
    case_data = res.json()["data"]
    case_id = case_data["id"]
    print(f"[OK] Demo Case Ingested: Case #{case_data['case_number']} ({case_data['title']}) [ID: {case_id}]")

    # 4. Evidence Inspection
    res = requests.get(f"{BASE_URL}/api/cases/{case_id}/evidence")
    assert res.status_code == 200
    evidence_items = res.json()["data"]
    print(f"[OK] Case Evidence Count: {len(evidence_items)} items")
    for ev in evidence_items:
        print(f"     - [EV-{ev['id']}] {ev['filename']} ({ev['file_type'].upper()}) | SHA256: {ev['sha256_hash'][:16]}... | Status: {ev['analysis_status']}")

    # 5. Timeline Synthesis (EvidenceFusionEngine)
    res = requests.get(f"{BASE_URL}/api/cases/{case_id}/timeline")
    assert res.status_code == 200
    tl_data = res.json()["data"]
    print(f"[OK] Unified Timeline: {tl_data['total_events']} events synthesized ({tl_data['timestamped_count']} timestamped, {tl_data['undated_count']} undated)")
    for ev in tl_data["timeline"][:4]:
        print(f"     * [{ev['timestamp_str']}] ({ev['source'].upper()}) {ev['description'][:65]}...")

    # 6. AI Evidence Chat (RAG)
    chat_queries = [
        "What people were detected in this incident?",
        "Summarize the chronological sequence of events.",
        "What speech was recorded by acoustic sensors?",
    ]
    for q in chat_queries:
        res = requests.post(
            f"{BASE_URL}/api/cases/{case_id}/chat",
            json={"message": q},
        )
        assert res.status_code == 200
        chat_resp = res.json()["data"]
        refs = [r["ref_id"] for r in chat_resp.get("evidence_references", [])]
        print(f"\n[OK] Chat Query: \"{q}\"")
        print(f"     AI Response: {chat_resp['message'][:120]}...")
        print(f"     Cited References: {refs}")
        print(f"     Model: {chat_resp.get('model_used')}")

    # 7. PDF Report Generation
    res = requests.post(f"{BASE_URL}/api/cases/{case_id}/report")
    assert res.status_code in [200, 201]
    report_data = res.json()["data"]
    print(f"\n[OK] Forensic PDF Report Generated: {report_data['report_filename']}")
    print(f"     Document SHA-256: {report_data['sha256_hash']}")

    # 8. Report Download Verification
    res = requests.get(f"{BASE_URL}/api/reports/{report_data['id']}/download")
    assert res.status_code == 200
    assert len(res.content) > 1000
    assert res.content[:4] == b"%PDF"
    print(f"[OK] Report PDF verified: {len(res.content)} bytes, valid PDF header.")

    # 9. Frontend HTML Route
    res = requests.get(f"{BASE_URL}/")
    assert res.status_code == 200
    assert "CrimeVision AI" in res.text
    assert "scene3d-container" in res.text
    print(f"[OK] Web Frontend UI successfully rendered at {BASE_URL}/")

    print("\n" + "=" * 60)
    print("ALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_acceptance_tests()
