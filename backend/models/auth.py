"""
models/auth.py — Pydantic schemas for authentication endpoints.

Used by routes/auth.py for request validation and response serialization.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Full name")
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")


class GoogleCallbackRequest(BaseModel):
    code: str = Field(..., description="Google OAuth authorization code")


class UserOut(BaseModel):
    id: str = ""
    email: str = ""
    name: Optional[str] = None
    blueprints_generated: int = 0
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str = ""
    user: UserOut = UserOut()
