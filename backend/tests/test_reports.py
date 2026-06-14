from reports.certificate import render_certificate_pdf
from reports.audit_package import render_audit_package_pdf


def _cert():
    return {
        "tenant": "acme", "issued_at": "2026-01-01T00:00:00Z",
        "trust_score": 88.5, "band": "CERTIFIED", "adversary_pass_rate": 0.9,
        "frameworks": ["NIST_AI_RMF", "ISO_27001"], "ledger_valid": True,
        "statement": "attestation", "digest": "ab" * 32,
    }


def test_certificate_pdf_is_valid_pdf():
    pdf = render_certificate_pdf(_cert())
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 500


def test_audit_package_pdf_is_valid_pdf():
    pkg = {
        "tenant": "acme",
        "trust": {"trust_score": 90, "band": "CERTIFIED",
                  "components": {"adversarial_pass_rate": 0.9},
                  "ledger": {"valid": True}},
        "coverage": {"by_framework": {"NIST_AI_RMF": 5}, "total_controls": 15},
        "adversary": {"total_tests": 10, "passed": 8, "partial": 1,
                      "failed": 1, "pass_rate": 0.8},
    }
    pdf = render_audit_package_pdf(pkg)
    assert pdf[:5] == b"%PDF-"
