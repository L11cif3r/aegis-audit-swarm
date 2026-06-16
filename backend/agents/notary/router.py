# backend/agents/notary/router.py
"""Notary API: evidence ledger, Trust Score, and Safety Certificate."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from gateway.auth import Principal, authenticate
from . import ledger, service, signing

router = APIRouter(prefix="/notary", tags=["notary"])


@router.get("/ledger")
async def get_ledger(limit: int = 200, principal: Principal = Depends(authenticate)):
    return await ledger.all_records(principal.tenant, limit)


@router.get("/verify")
async def verify(principal: Principal = Depends(authenticate)):
    return await ledger.verify_chain(principal.tenant)


@router.get("/public-key")
async def public_key():
    return {"public_key_pem": signing.public_key_pem()}


@router.get("/trust-score")
async def trust_score(principal: Principal = Depends(authenticate)):
    return await service.trust_score(principal.tenant)


@router.get("/certificate")
async def certificate(principal: Principal = Depends(authenticate)):
    return await service.safety_certificate(principal.tenant)


@router.get("/certificate.pdf")
async def certificate_pdf(principal: Principal = Depends(authenticate)):
    cert = await service.safety_certificate(principal.tenant)
    from reports.certificate import render_certificate_pdf

    pdf_bytes = render_certificate_pdf(cert)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="safety_certificate_{principal.tenant}.pdf"'},
    )


@router.get("/audit-package")
async def audit_package(principal: Principal = Depends(authenticate)):
    from reports.audit_package import build_audit_package

    return await build_audit_package(principal.tenant)


@router.get("/audit-package.pdf")
async def audit_package_pdf(principal: Principal = Depends(authenticate)):
    from reports.audit_package import build_audit_package, render_audit_package_pdf

    pkg = await build_audit_package(principal.tenant)
    pdf_bytes = render_audit_package_pdf(pkg)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="audit_package_{principal.tenant}.pdf"'},
    )
