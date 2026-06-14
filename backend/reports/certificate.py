# backend/reports/certificate.py
"""Render the board-ready Safety Certificate as a PDF (PDF Phase 4)."""
from __future__ import annotations

import io


def render_certificate_pdf(cert: dict) -> bytes:
    """Render a signed Safety Certificate dict to PDF bytes.

    Uses reportlab when available; falls back to a minimal valid PDF so the
    endpoint never hard-fails in a stripped-down deployment.
    """
    try:
        return _reportlab_pdf(cert)
    except Exception:
        return _fallback_pdf(cert)


def _reportlab_pdf(cert: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 30 * mm

    c.setFont("Helvetica-Bold", 20)
    c.drawString(25 * mm, y, "Talamanda AI — Safety Certificate")
    y -= 12 * mm
    c.setFont("Helvetica", 11)

    lines = [
        f"Tenant: {cert.get('tenant')}",
        f"Issued: {cert.get('issued_at')}",
        f"Trust Score: {cert.get('trust_score')}  ({cert.get('band')})",
        f"Adversary pass rate: {cert.get('adversary_pass_rate')}",
        f"Frameworks: {', '.join(cert.get('frameworks', []))}",
        f"Evidence ledger valid: {cert.get('ledger_valid')}",
        "",
        cert.get("statement", ""),
        "",
        f"Digest (SHA-256): {cert.get('digest', '')[:48]}...",
        "Signature: RSA-2048 (PKCS#1 v1.5)",
    ]
    for line in lines:
        for chunk in _wrap(line, 90):
            c.drawString(25 * mm, y, chunk)
            y -= 7 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(25 * mm, 15 * mm,
                 "Independent AI governance attestation — issued by the Talamanda Notary agent.")
    c.showPage()
    c.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    if len(text) <= width:
        return [text]
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out or [""]


def _fallback_pdf(cert: dict) -> bytes:
    text = (
        f"Talamanda Safety Certificate\\n"
        f"Tenant: {cert.get('tenant')}  Score: {cert.get('trust_score')} "
        f"({cert.get('band')})"
    )
    content = f"BT /F1 14 Tf 60 760 Td ({text}) Tj ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = "%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n{obj}\nendobj\n"
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n"
    pdf += (
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF"
    )
    return pdf.encode("latin-1")
