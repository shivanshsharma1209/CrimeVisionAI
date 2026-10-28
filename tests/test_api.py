import io
import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app import app
from backend.models.database import engine, Base, SessionLocal
from backend.models.case import Case


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_case_crud_api(client):
    # 1. Create Case
    res = client.post(
        "/api/cases",
        json={
            "title": "Perimeter Gate Breach",
            "investigator": "Det. Vance",
            "status": "Open",
            "description": "Unauthorized access test case.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    case_id = data["data"]["id"]
    assert "CV-" in data["data"]["case_number"]

    # 2. Get Case Detail
    res_get = client.get(f"/api/cases/{case_id}")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["title"] == "Perimeter Gate Breach"

    # 3. Update Case
    res_put = client.put(
        f"/api/cases/{case_id}",
        json={"status": "Under Analysis"},
    )
    assert res_put.status_code == 200
    assert res_put.json()["data"]["status"] == "Under Analysis"


def test_evidence_upload_validation(client):
    # Create a parent case first
    res_case = client.post(
        "/api/cases",
        json={"title": "Upload Test Case", "investigator": "Agent Carter"},
    )
    case_id = res_case.json()["data"]["id"]

    # Reject disallowed file format (e.g. .exe or .py)
    fake_file = ("payload.exe", io.BytesIO(b"malicious script"), "application/octet-stream")
    res_invalid = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": fake_file},
    )
    assert res_invalid.status_code == 400
    assert res_invalid.json()["success"] is False
    assert res_invalid.json()["error"]["code"] == "INVALID_FILE_TYPE"

    # Accept valid image file
    valid_file = ("test_image.jpg", io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"), "image/jpeg")
    res_valid = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": valid_file},
    )
    assert res_valid.status_code == 201
    assert res_valid.json()["success"] is True
    assert res_valid.json()["data"]["filename"] == "test_image.jpg"
    assert len(res_valid.json()["data"]["sha256_hash"]) == 64


def test_demo_seed_and_chat_fallback(client):
    # 1. Seed demo case
    res_seed = client.post("/api/demo/seed")
    assert res_seed.status_code in (200, 201)
    demo_data = res_seed.json()["data"]
    demo_id = demo_data["id"]

    # 2. Chat with unconfigured Groq key (must not crash, must return analytical response)
    res_chat = client.post(
        f"/api/cases/{demo_id}/chat",
        json={"message": "What people were detected?"},
    )
    assert res_chat.status_code == 200
    chat_resp = res_chat.json()
    assert chat_resp["success"] is True
    msg = chat_resp["data"]["message"].lower()
    assert any(w in msg for w in ["people", "human", "individual", "person", "suspect"])
    assert len(chat_resp["data"]["evidence_references"]) > 0

    # 3. Report generation for demo case
    res_report = client.post(f"/api/cases/{demo_id}/report")
    assert res_report.status_code in (200, 201)
    report_data = res_report.json()["data"]
    assert report_data["report_filename"].endswith(".pdf")
    assert len(report_data["sha256_hash"]) == 64
