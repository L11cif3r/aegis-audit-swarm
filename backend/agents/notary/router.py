# backend/agents/notary/router.py
"""Notary API: evidence ledger, Trust Score, and Safety Certificate."""
from __future__ import annotations

from fastapi import APIRouter, Response

from . import ledger, service, signing

router = APIRouter(prefix="/notary", tags=["notary"])


@router.get("/ledger")
async def get_ledger(limit: int = 200):
    return await ledger.all_records(limit)


@router.get("/verify")
async def verify():
    return await ledger.verify_chain()


@router.get("/public-key")
async def public_key():
    return {"public_key_pem": signing.public_key_pem()}


@router.get("/trust-score")
async def trust_score():
    return await service.trust_score()


@router.get("/certificate")
async def certificate(tenant: str = "default"):
    return await service.safety_certificate(tenant)


@router.get("/certificate.pdf")
async def certificate_pdf(tenant: str = "default"):
    cert = await service.safety_certificate(tenant)
    from reports.certificate import render_certificate_pdf

    pdf_bytes = render_certificate_pdf(cert)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="safety_certificate_{tenant}.pdf"'},
    )


@router.get("/audit-package")
async def audit_package(tenant: str = "default"):
    from reports.audit_package import build_audit_package

    return await build_audit_package(tenant)


@router.get("/audit-package.pdf")
async def audit_package_pdf(tenant: str = "default"):
    from reports.audit_package import build_audit_package, render_audit_package_pdf

    pkg = await build_audit_package(tenant)
    pdf_bytes = render_audit_package_pdf(pkg)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="audit_package_{tenant}.pdf"'},
    )
