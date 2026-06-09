"""Workspace, TeamMember, CompanyProfile, Capability schemas."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel


_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,78}[a-z0-9])?$")


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = None
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.lower().strip()
        if not _SLUG_RE.match(v):
            raise ValueError(
                "slug must be 1-80 chars, lowercase alphanumeric, hyphens allowed (not at ends)"
            )
        return v


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    settings_json: dict | None = None


class WorkspaceResponse(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    owner_user_id: uuid.UUID
    settings_json: dict
    created_at: datetime
    updated_at: datetime


class TeamMemberInvite(BaseModel):
    email: EmailStr
    role: Literal["admin", "member", "viewer"] = "member"


class TeamMemberUpdate(BaseModel):
    role: Literal["owner", "admin", "member", "viewer"]


class TeamMemberResponse(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str
    user_email: str
    user_full_name: str
    joined_at: datetime | None
    created_at: datetime


class CompanyProfileUpdate(BaseModel):
    legal_name: str | None = None
    duns: str | None = None
    uei: str | None = None
    cage_code: str | None = None
    primary_naics: str | None = None
    size_standard: str | None = None
    certifications: list[str] | None = None
    overview: str | None = None
    differentiators: str | None = None
    past_performance_summary: str | None = None


class CompanyProfileResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    legal_name: str | None
    duns: str | None
    uei: str | None
    cage_code: str | None
    primary_naics: str | None
    size_standard: str | None
    certifications: list[str] | None
    overview: str | None
    differentiators: str | None
    past_performance_summary: str | None


class CapabilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = None
    maturity: Literal["emerging", "developing", "mature", "market-leading"] | None = None
    description: str | None = None
    keywords: list[str] | None = None
    evidence_links: list[str] | None = None


class CapabilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = None
    maturity: Literal["emerging", "developing", "mature", "market-leading"] | None = None
    description: str | None = None
    keywords: list[str] | None = None
    evidence_links: list[str] | None = None


class CapabilityResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    category: str | None
    maturity: str | None
    description: str | None
    keywords: list[str] | None
    evidence_links: list[str] | None
