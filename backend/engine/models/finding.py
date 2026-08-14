"""
Normalized finding data model for issues from axe-core, Lighthouse, or custom sources.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid
from pydantic import BaseModel, Field


class Source(str, Enum):
    AXE = "axe"
    LIGHTHOUSE = "lighthouse"
    CUSTOM = "custom"


class Category(str, Enum):
    ACCESSIBILITY = "accessibility"
    SEO = "seo"
    PERFORMANCE = "performance"


class Severity(str, Enum):
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"f_{uuid.uuid4().hex[:8]}")
    source: Source = Field(default=Source.AXE)
    category: Category = Field(default=Category.ACCESSIBILITY)
    rule_id: str = Field(default="wcag-rule")
    title: str = Field(default="Accessibility Violation")
    description: str = Field(default="Remediation target")
    severity: Severity = Field(default=Severity.SERIOUS)
    selectors: List[str] = Field(default_factory=list)
    html_snippets: List[str] = Field(default_factory=list)
    help_url: Optional[str] = None
    manual_review_required: bool = False
    dom_path: Optional[str] = None
    parent_context: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    page_url: Optional[str] = None
    screenshot_ref: Optional[str] = None

    class Config:
        populate_by_name = True

