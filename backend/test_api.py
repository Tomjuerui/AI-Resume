"""HTTP endpoint tests using FastAPI TestClient.

Validates the full request/response contract for all endpoints.
"""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ── Helpers ──

def create_test_pdf_bytes() -> bytes:
    """Create a minimal PDF with known candidate info."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "简历\n\n"
        "姓名：测试用户\n"
        "电话：13912345678\n"
        "邮箱：test@example.com\n"
        "地址：北京市朝阳区\n\n"
        "技能：Python, Java, Docker\n"
        "工作经历：ABC公司 高级工程师 5年"
    )
    page.insert_text(fitz.Point(50, 50), content, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


VALID_JD = "高级Python开发工程师，要求精通Python、Docker、FastAPI，5年以上经验，本科及以上学历"


# ══════════════════════════════════════════════
#  Health Check
# ══════════════════════════════════════════════

def test_health_check():
    """GET / should return status ok."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "AI-Resume" in data["service"]
    print("  [PASS] Health check")


# ══════════════════════════════════════════════
#  POST /api/v1/upload
# ══════════════════════════════════════════════

def test_upload_valid_pdf():
    """Upload a valid PDF should return extracted text."""
    pdf_bytes = create_test_pdf_bytes()
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["text_length"] > 0
    assert "test@example.com" in data["raw_text"] or "13912345678" in data["raw_text"]
    assert len(data["text_preview"]) > 0
    print("  [PASS] Upload valid PDF")


def test_upload_invalid_extension():
    """Upload non-PDF file should return 400."""
    response = client.post(
        "/api/v1/upload",
        files={"file": ("resume.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == 400
    assert "PDF" in data["message"]
    print("  [PASS] Upload invalid extension")


def test_upload_no_file():
    """POST without file should return 422 (FastAPI validation)."""
    response = client.post("/api/v1/upload")
    assert response.status_code == 422
    print("  [PASS] Upload missing file")


# ══════════════════════════════════════════════
#  POST /api/v1/analyze
# ══════════════════════════════════════════════

def test_analyze_valid_pdf():
    """Analyze a valid PDF with JD should return full analysis."""
    pdf_bytes = create_test_pdf_bytes()
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"jd_text": VALID_JD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"] is not None
    assert "candidate_info" in data["data"]
    assert "overall_score" in data["data"]
    assert "dimensions" in data["data"]
    assert isinstance(data["data"]["overall_score"], int)
    print("  [PASS] Analyze valid PDF + JD")


def test_analyze_invalid_extension():
    """Analyze with non-PDF file should return 400."""
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("resume.txt", io.BytesIO(b"not pdf"), "text/plain")},
        data={"jd_text": VALID_JD},
    )
    assert response.status_code == 400
    data = response.json()
    assert "PDF" in data["message"]
    print("  [PASS] Analyze invalid extension")


def test_analyze_short_jd():
    """Analyze with too-short JD should return 400."""
    pdf_bytes = create_test_pdf_bytes()
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"jd_text": "短"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "过短" in data["message"] or "字符" in data["message"]
    print("  [PASS] Analyze short JD")


def test_analyze_missing_file():
    """POST without file should return 422."""
    response = client.post(
        "/api/v1/analyze",
        data={"jd_text": VALID_JD},
    )
    assert response.status_code == 422
    print("  [PASS] Analyze missing file")


def test_analyze_missing_jd():
    """POST without jd_text should return 422."""
    pdf_bytes = create_test_pdf_bytes()
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 422
    print("  [PASS] Analyze missing JD")


def test_analyze_empty_pdf():
    """Analyze with an empty PDF (no text) should return scanned PDF error."""
    import fitz
    doc = fitz.open()
    doc.new_page()
    empty_pdf = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("empty.pdf", io.BytesIO(empty_pdf), "application/pdf")},
        data={"jd_text": VALID_JD},
    )
    assert response.status_code == 422
    data = response.json()
    assert "扫描件" in data["message"]
    print("  [PASS] Analyze empty/scanned PDF")


def test_analyze_response_schema():
    """Verify the response matches the AnalysisResponse contract."""
    pdf_bytes = create_test_pdf_bytes()
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"jd_text": VALID_JD},
    )
    data = response.json()

    # Top-level envelope
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert isinstance(data["code"], int)

    # Data fields
    d = data["data"]
    assert isinstance(d["candidate_info"], dict)
    assert isinstance(d["overall_score"], int)
    assert isinstance(d["dimensions"], list)
    assert isinstance(d["missing_skills"], list)
    assert isinstance(d["risk_tips"], list)
    assert isinstance(d["raw_json"], dict)

    # Dimensions have required shape
    for dim in d["dimensions"]:
        assert "name" in dim
        assert "score" in dim
        assert "reason" in dim
        assert isinstance(dim["score"], int)
        assert 0 <= dim["score"] <= 100

    print("  [PASS] Analyze response schema")


# ══════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("AI-Resume Analyzer — HTTP Endpoint Tests")
    print("=" * 60 + "\n")

    tests = [
        ("Health Check", test_health_check),
        ("Upload Valid PDF", test_upload_valid_pdf),
        ("Upload Invalid Extension", test_upload_invalid_extension),
        ("Upload Missing File", test_upload_no_file),
        ("Analyze Valid PDF+JD", test_analyze_valid_pdf),
        ("Analyze Invalid Extension", test_analyze_invalid_extension),
        ("Analyze Short JD", test_analyze_short_jd),
        ("Analyze Missing File", test_analyze_missing_file),
        ("Analyze Missing JD", test_analyze_missing_jd),
        ("Analyze Empty/Scanned PDF", test_analyze_empty_pdf),
        ("Analyze Response Schema", test_analyze_response_schema),
    ]

    results = []
    for name, test_fn in tests:
        try:
            test_fn()
            results.append((name, "PASSED"))
        except Exception as e:
            print(f"  [FAIL] {e}")
            import traceback
            traceback.print_exc()
            results.append((name, "FAILED"))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r == "PASSED")
    failed = sum(1 for _, r in results if r == "FAILED")
    for name, result in results:
        print(f"  [{'PASS' if result == 'PASSED' else 'FAIL'}] {name}")
    print(f"\n  Total: {passed} passed, {failed} failed\n")

    sys.exit(0 if failed == 0 else 1)
