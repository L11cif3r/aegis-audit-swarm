# backend/gateway/auth_router.py
"""Authentication API.

Sessions use a short-lived access token (JWT) plus a rotating, DB-backed refresh
token. Also covers account recovery: email verification, password change, and
password reset.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from config import settings
from gateway import (
    account_tokens,
    email as email_sender,
    loginguard,
    provider_store,
    refresh as refresh_store,
    tokens,
    users as users_store,
)
from gateway.auth import Principal, authenticate, issue_token
from gateway.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def _validate_password_strength(pw: str) -> str:
    if len(pw) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters.")
    if not any(c.isalpha() for c in pw) or not any(c.isdigit() for c in pw):
        raise ValueError("Password must contain both letters and numbers.")
    return pw


class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshBody(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class LogoutBody(BaseModel):
    refresh_token: str | None = None


class ChangePasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ForgotBody(BaseModel):
    email: EmailStr


class ResetBody(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=1, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class VerifyBody(BaseModel):
    token: str = Field(min_length=1, max_length=512)


async def _session(user: dict) -> dict:
    access = issue_token(
        subject=user["id"], tenant=user["tenant"],
        roles=(user.get("role") or "admin",),
    )
    refresh = await refresh_store.issue(user["id"], user["tenant"])
    return {
        "token": access,
        "refresh_token": refresh,
        "user": users_store.public_view(user),
    }


async def _send_verification(user: dict) -> None:
    raw = await account_tokens.create(user["id"], account_tokens.PURPOSE_VERIFY, ttl_minutes=1440)
    link = f"{settings.app_base_url.rstrip('/')}/verify-email?token={raw}"
    await email_sender.send_verification(user["email"], link)


@router.post("/signup")
async def signup(body: SignupBody, request: Request):
    await enforce_rate_limit(request)
    if await users_store.get_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    user = await users_store.create_user(body.email, body.password, body.display_name)
    # Seed the new tenant's provider catalog so the Gateway tab is usable.
    await provider_store.ensure_seeded(user["tenant"])
    await _send_verification(user)
    return await _session(user)


@router.post("/login")
async def login(body: LoginBody, request: Request):
    await enforce_rate_limit(request)
    await loginguard.check_locked(body.email)
    user = await users_store.get_by_email(body.email)
    # Generic error — do not reveal whether the email exists.
    if not user or not users_store.verify_password(body.password, user["password_hash"]):
        await loginguard.record_failure(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if settings.require_email_verification and not user.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before signing in.",
        )
    await loginguard.reset(body.email)
    return await _session(user)


@router.post("/refresh")
async def refresh(body: RefreshBody, request: Request):
    await enforce_rate_limit(request)
    rotated = await refresh_store.rotate(body.refresh_token)
    if not rotated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    user = await users_store.get_by_id(rotated["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")
    access = issue_token(
        subject=user["id"], tenant=user["tenant"],
        roles=(user.get("role") or "admin",),
    )
    return {
        "token": access,
        "refresh_token": rotated["refresh"],
        "user": users_store.public_view(user),
    }


@router.get("/me")
async def me(principal: Principal = Depends(authenticate)):
    user = await users_store.get_by_id(principal.subject)
    if not user:
        # API-key / dev principals without a user row.
        return {"id": principal.subject, "tenant": principal.tenant,
                "email": None, "role": principal.roles[0] if principal.roles else "admin"}
    return users_store.public_view(user)


@router.post("/logout")
async def logout(body: LogoutBody, principal: Principal = Depends(authenticate)):
    # Revoke the presented access JWT and the refresh token (if supplied).
    if principal.scheme == "jwt" and principal.jti:
        await tokens.revoke(principal.jti, principal.tenant, principal.exp)
    if body.refresh_token:
        await refresh_store.revoke(body.refresh_token)
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: ChangePasswordBody, principal: Principal = Depends(authenticate)):
    user = await users_store.get_by_id(principal.subject)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No user account.")
    if not users_store.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")
    await users_store.set_password(user["id"], body.new_password)
    # Invalidate every other session: revoke all refresh tokens + this access jti.
    await refresh_store.revoke_all_for_user(user["id"])
    if principal.jti:
        await tokens.revoke(principal.jti, principal.tenant, principal.exp)
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(body: ForgotBody, request: Request):
    await enforce_rate_limit(request)
    user = await users_store.get_by_email(body.email)
    # Always return the same response — never reveal whether the email exists.
    if user:
        raw = await account_tokens.create(user["id"], account_tokens.PURPOSE_RESET, ttl_minutes=60)
        link = f"{settings.app_base_url.rstrip('/')}/reset-password?token={raw}"
        await email_sender.send_password_reset(user["email"], link)
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetBody, request: Request):
    await enforce_rate_limit(request)
    user_id = await account_tokens.consume(body.token, account_tokens.PURPOSE_RESET)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")
    await users_store.set_password(user_id, body.new_password)
    await refresh_store.revoke_all_for_user(user_id)
    return {"ok": True}


@router.post("/verify-email")
async def verify_email(body: VerifyBody):
    user_id = await account_tokens.consume(body.token, account_tokens.PURPOSE_VERIFY)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token.")
    await users_store.mark_email_verified(user_id)
    return {"ok": True}


@router.post("/resend-verification")
async def resend_verification(principal: Principal = Depends(authenticate)):
    user = await users_store.get_by_id(principal.subject)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No user account.")
    if user.get("email_verified"):
        return {"ok": True, "message": "Already verified."}
    await _send_verification(user)
    return {"ok": True}


@router.post("/api-key/rotate")
async def rotate_api_key(principal: Principal = Depends(authenticate)):
    user = await users_store.get_by_id(principal.subject)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No user account for this principal.")
    key = await users_store.rotate_api_key(user["id"])
    return {"ingress_api_key": key}
