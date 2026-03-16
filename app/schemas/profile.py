"""Profile schemas — API Contract Section 4.2.

Defines request/response models for profile CRUD, cloning, and completeness.
"""

import typing
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class _SalaryValidator:
    @model_validator(mode="after")
    def salary_range_check(self) -> typing.Self:
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("salary_min must be <= salary_max")
        return self


class _URLValidator:
    @field_validator("linkedin_url", "github_url", "portfolio_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://"):
            raise ValueError("URL must start with https://")
        return v


class ProfileCreate(_SalaryValidator, _URLValidator, BaseModel):
    """Create a new profile. Required: name, target_role."""

    name: str = Field(..., max_length=255)
    target_role: str = Field(..., max_length=255)
    target_seniority: str | None = None
    target_employment_types: list[str] | None = None
    target_locations: list[str] | None = None
    negative_locations: list[str] | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    years_of_experience: float | None = Field(default=None, ge=0)
    current_title: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    social_urls: dict | None = None
    work_authorization: dict | None = None
    languages: list | None = None
    work_preferences: dict | None = None
    notice_period: str | None = None
    availability_date: str | None = None
    writing_tones: dict | None = None
    custom_fields: dict | None = None
    ai_instructions: str | None = None
    bio_snippet: str | None = None
    scoring_weights: dict | None = None
    automation_config: dict | None = None
    discovery_config: dict | None = None
    dream_companies: list[str] | None = None
    blacklist: list[str] | None = None


class ProfileUpdate(_SalaryValidator, _URLValidator, BaseModel):
    """Update an existing profile. All fields optional."""

    name: str | None = None
    target_role: str | None = None
    target_seniority: str | None = None
    target_employment_types: list[str] | None = None
    target_locations: list[str] | None = None
    negative_locations: list[str] | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    years_of_experience: float | None = Field(default=None, ge=0)
    current_title: str | None = None
    is_active: bool | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    social_urls: dict | None = None
    work_authorization: dict | None = None
    languages: list | None = None
    work_preferences: dict | None = None
    notice_period: str | None = None
    availability_date: str | None = None
    writing_tones: dict | None = None
    custom_fields: dict | None = None
    ai_instructions: str | None = None
    bio_snippet: str | None = None
    scoring_weights: dict | None = None
    automation_config: dict | None = None
    discovery_config: dict | None = None
    dream_companies: list[str] | None = None
    blacklist: list[str] | None = None


class ProfileResponse(BaseModel):
    """Full profile representation returned by API."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    target_role: str
    target_seniority: str | None = None
    target_employment_types: list = []
    target_locations: list = []
    negative_locations: list = []
    years_of_experience: float | None = None
    current_title: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    is_active: bool = True
    completeness_pct: int = 0
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    social_urls: dict = {}
    work_authorization: dict = {}
    languages: list = []
    work_preferences: dict = {}
    notice_period: str | None = None
    availability_date: str | None = None
    writing_tones: dict = {}
    custom_fields: dict = {}
    ai_instructions: str | None = None
    bio_snippet: str | None = None
    scoring_weights: dict = {}
    automation_config: dict = {}
    discovery_config: dict = {}
    dream_companies: list = []
    blacklist: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileCompleteness(BaseModel):
    """Profile completeness check result."""

    pct: int
    missing_items: list[str]


class CloneRequest(BaseModel):
    """Request body for POST /profiles/:id/clone."""

    name: str
    data_types: list[str] = Field(default_factory=list)
