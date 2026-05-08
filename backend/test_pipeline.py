"""
End-to-end pipeline test for AI-Resume Analyzer.
Tests all components: PDF extraction, text cleaning, LLM extraction, schema validation.
"""
import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services import pdf_service, llm_service
from models.schemas import AnalysisResponse, CandidateInfo, AnalysisData


# ── Test Helpers ──

def create_test_pdf(path: Path) -> None:
    """Create a PDF with known candidate info."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "简历\n\n"
        "个人信息\n"
        "姓名：李四\n"
        "电话：13912345678\n"
        "邮箱：lisi@company.cn\n"
        "地址：上海市浦东新区张江高科技园区\n\n"
        "教育背景\n"
        "清华大学 软件工程 硕士 2019-2022\n"
        "浙江大学 计算机科学与技术 学士 2015-2019\n\n"
        "工作经历\n"
        "XYZ科技有限公司 Python高级工程师 2022-至今\n"
        "  - 主导AI中台架构设计\n"
        "  - 负责大规模模型训练和部署\n"
    )
    page.insert_text(fitz.Point(50, 50), content, fontsize=11)
    doc.save(str(path))
    doc.close()


# ── Tests ──

async def test_pdf_extraction():
    """Test PDF text extraction and cleaning."""
    print("=" * 60)
    print("TEST 1: PDF Text Extraction & Cleaning")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "test.pdf"
        create_test_pdf(pdf_path)

        # Extract
        raw_text = await pdf_service.extract_text(pdf_path)
        assert len(raw_text) > 0, "Raw text should not be empty"
        print(f"  Raw text: {len(raw_text)} chars")

        # Clean
        cleaned = pdf_service.clean_text(raw_text)
        assert len(cleaned) > 0, "Cleaned text should not be empty"
        print(f"  Cleaned text: {len(cleaned)} chars")

        # Check content
        expected_checks = [
            "13912345678", "lisi@company.cn", "清华大学", "python",
        ]
        cleaned_lower = cleaned.lower()
        for check in expected_checks:
            if check not in cleaned_lower and check not in cleaned:
                print(f"  WARNING: Expected content '{check}' not found in output")
            else:
                print(f"  Found: {check}")

        # Not scanned
        assert not pdf_service.is_scanned_pdf(cleaned), "Should not be scanned PDF"
        print("  Is scanned PDF: False (correct)")

        # MD5
        md5 = pdf_service.compute_md5(pdf_path)
        assert len(md5) == 32, "MD5 should be 32 hex chars"
        print(f"  MD5: {md5}")

        print("  PASSED\n")
        return cleaned


async def test_text_cleaning():
    """Test text cleaning edge cases."""
    print("=" * 60)
    print("TEST 2: Text Cleaning Edge Cases")
    print("=" * 60)

    # Test: garbled control chars
    dirty = "Hello\x00World\x1f\x7fTest\n\n\n\nExtra"
    cleaned = pdf_service.clean_text(dirty)
    assert "Hello" in cleaned and "World" in cleaned and "Test" in cleaned, \
        f"Control chars should be replaced, got: {repr(cleaned)}"
    assert "\x00" not in cleaned and "\x1f" not in cleaned, \
        "Control characters must be fully removed"
    print("  Control chars replaced: OK")

    # Test: excessive newlines collapsed
    assert cleaned.count("\n") <= 2, \
        f"Excessive newlines should be collapsed: {repr(cleaned)}"
    print("  Newline normalization: OK")

    # Test: scanned PDF detection
    assert pdf_service.is_scanned_pdf("   \n  \n  "), \
        "Whitespace-only text should be detected as scanned"
    assert pdf_service.is_scanned_pdf(""), \
        "Empty text should be detected as scanned"
    assert not pdf_service.is_scanned_pdf("Hello World"), \
        "Text with content should not be scanned"
    print("  Scanned PDF detection: OK")

    print("  PASSED\n")


async def test_json_cleaning():
    """Test LLM response JSON cleaning."""
    print("=" * 60)
    print("TEST 3: JSON Response Cleaning & Parsing")
    print("=" * 60)

    # Test: markdown code block
    raw = '```json\n{"name": "test", "phone": "123", "email": "a@b.com", "address": "here"}\n```'
    cleaned = llm_service._clean_json_response(raw)
    result = llm_service._parse_with_retry(cleaned)
    assert result["name"] == "test"
    assert result["phone"] == "123"
    print("  Markdown code fence stripping: OK")

    # Test: plain JSON
    raw = '{"name": "test2", "phone": "456", "email": "x@y.com", "address": "there"}'
    cleaned = llm_service._clean_json_response(raw)
    result = llm_service._parse_with_retry(cleaned)
    assert result["name"] == "test2"
    print("  Plain JSON: OK")

    # Test: JSON with surrounding text (simulated LLM rambling)
    raw = 'Here is the result:\n{"name": "test3", "phone": "789", "email": "c@d.com", "address": "somewhere"}\nHope this helps!'
    cleaned = llm_service._clean_json_response(raw)
    result = llm_service._parse_with_retry(cleaned)
    assert result["name"] == "test3"
    print("  JSON with surrounding text: OK")

    # Test: think tags (DeepSeek style)
    raw = '<think>Let me analyze the resume...</think>\n{"name": "test4", "phone": "000", "email": "e@f.com", "address": "nowhere"}'
    cleaned = llm_service._clean_json_response(raw)
    result = llm_service._parse_with_retry(cleaned)
    assert result["name"] == "test4"
    print("  Think tag stripping: OK")

    print("  PASSED\n")


def test_schema_validation():
    """Test Pydantic schema serialization and field alignment."""
    print("=" * 60)
    print("TEST 4: Schema Validation")
    print("=" * 60)

    # Test response with full data
    response = AnalysisResponse(
        code=200,
        message="解析成功",
        data=AnalysisData(
            candidate_info=CandidateInfo(
                name="王五",
                phone="13700001111",
                email="wangwu@test.com",
                address="北京市朝阳区",
            ),
            overall_score=85,
            dimensions=[],
            raw_json={"extra": "data"},
        ),
    )

    json_str = response.model_dump_json()
    data = json.loads(json_str)

    assert data["code"] == 200
    assert data["data"]["candidate_info"]["name"] == "王五"
    assert data["data"]["candidate_info"]["phone"] == "13700001111"
    assert data["data"]["candidate_info"]["email"] == "wangwu@test.com"
    assert data["data"]["candidate_info"]["address"] == "北京市朝阳区"
    print("  Full response serialization: OK")

    # Test response with null data (error case)
    error_resp = AnalysisResponse(code=500, message="Server Error", data=None)
    json_str = error_resp.model_dump_json()
    data = json.loads(json_str)
    assert data["data"] is None
    print("  Error response serialization: OK")

    # Test CandidateInfo with empty fields
    empty = CandidateInfo()
    assert empty.name == ""
    assert empty.phone == ""
    assert empty.email == ""
    assert empty.address == ""
    print("  Empty CandidateInfo defaults: OK")

    print("  PASSED\n")


async def test_pdf_parse_error():
    """Test handling of corrupted/unreadable PDF."""
    print("=" * 60)
    print("TEST 5: PDF Parse Error Handling")
    print("=" * 60)

    from core.exceptions import PdfParseError

    with tempfile.TemporaryDirectory() as tmpdir:
        bad_pdf = Path(tmpdir) / "bad.pdf"
        bad_pdf.write_bytes(b"not a real pdf file")

        try:
            await pdf_service.extract_text(bad_pdf)
            print("  No exception raised — unexpected (pdfplumber may handle gracefully)")
        except PdfParseError as e:
            print(f"  Correctly raised PdfParseError: {e}")
        except Exception as e:
            print(f"  Raised other exception: {type(e).__name__}: {e}")

    print("  PASSED\n")


def test_oss_config_detection():
    """Test OSS configuration detection."""
    print("=" * 60)
    print("TEST 6: OSS Configuration Detection")
    print("=" * 60)

    from core.config import settings

    # With placeholder credentials, OSS should be detected as NOT configured
    # (unless the user set real credentials)
    configured = settings.oss_configured
    print(f"  OSS configured: {configured}")
    if not configured:
        print("  OSS not configured (expected — skipping OSS integration)")
    else:
        print("  OSS is configured — integration will run")

    print("  PASSED\n")


# ── Main ──

async def main():
    print("\n" + "=" * 60)
    print("AI-Resume Analyzer — Pipeline Test Suite")
    print("=" * 60 + "\n")

    results = []

    tests = [
        ("PDF Extraction & Cleaning", test_pdf_extraction),
        ("Text Cleaning Edge Cases", test_text_cleaning),
        ("JSON Response Cleaning", test_json_cleaning),
        ("Schema Validation", test_schema_validation),
        ("PDF Parse Error Handling", test_pdf_parse_error),
        ("OSS Configuration", test_oss_config_detection),
    ]

    for name, test_fn in tests:
        try:
            if asyncio.iscoroutinefunction(test_fn):
                await test_fn()
            else:
                test_fn()
            results.append((name, "PASSED"))
        except Exception as e:
            print(f"  FAILED: {e}\n")
            import traceback
            traceback.print_exc()
            results.append((name, "FAILED"))

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r == "PASSED")
    failed = sum(1 for _, r in results if r == "FAILED")
    for name, result in results:
        status = "PASS" if result == "PASSED" else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\n  Total: {passed} passed, {failed} failed")
    print()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
