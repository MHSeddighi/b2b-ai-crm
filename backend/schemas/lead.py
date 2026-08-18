"""Example module: a CRM Lead schema with validation and scoring.

This file demonstrates the conventions used in this project:

* one module per concern, living in the layer it belongs to (``schemas``);
* type hints everywhere (Python 3.12 syntax);
* stdlib-only code — no external dependencies yet;
* a runnable ``__main__`` demo so the module can be sanity-checked with
  ``python -m backend.schemas.lead`` (or any other runnable path).

A ``Lead`` is a raw sales prospect captured from some source (web form,
import, API). Scoring turns the raw fields into a 0-100 priority number so
the CRM can sort the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class LeadSource(str, Enum):
    """Where the lead came from. Enum values are the stable wire values."""

    WEB_FORM = "web_form"
    IMPORT = "import"
    API = "api"
    MANUAL = "manual"


class LeadStatus(str, Enum):
    """Lifecycle state of a lead in the pipeline."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"


def _validate_email(email: str) -> str:
    """Very small email sanity check (a real project would use a library)."""
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError(f"invalid email: {email!r}")
    return email.strip().lower()


@dataclass(slots=True)
class Lead:
    """A sales lead with basic validation.

    Example:
        >>> lead = Lead(
        ...     email="bob@acme.com",
        ...     company="Acme Inc",
        ...     budget=50000,
        ...     source=LeadSource.WEB_FORM,
        ... )
        >>> lead.score()
        90
    """

    email: str
    company: str
    source: LeadSource = LeadSource.MANUAL
    status: LeadStatus = LeadStatus.NEW
    budget: float | None = None          # expected deal size in USD
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Run validation right after construction."""
        self.email = _validate_email(self.email)
        self.company = self.company.strip()
        if not self.company:
            raise ValueError("company must not be empty")
        if self.budget is not None and self.budget < 0:
            raise ValueError("budget must be >= 0")

    def score(self) -> int:
        """Return a 0-100 priority score.

        Simple heuristic — real logic would live in a scoring service
        (``backend/services``) and probably use the ML models in ``ml/``.
        """
        points = 10  # every lead starts with a baseline

        # A stated budget is a strong signal of intent.
        if self.budget is not None:
            points += min(50, int(self.budget // 1000))  # up to 50 pts

        # Web-form leads are typically warmer than cold imports.
        if self.source is LeadSource.WEB_FORM:
            points += 20
        elif self.source is LeadSource.API:
            points += 10

        # A company name means a real business, not a placeholder signup.
        if len(self.company) >= 3:
            points += 10

        return min(100, points)

    def is_contactable(self) -> bool:
        """A lead is contactable when it is not lost and has a valid email."""
        return self.status is not LeadStatus.LOST and "@" in self.email


def demo() -> None:
    """Small runnable demo so the module can be checked by hand."""
    leads = [
        Lead(email="bob@acme.com", company="Acme Inc", budget=50_000, source=LeadSource.WEB_FORM),
        Lead(email="carol@globex.org", company="Globex", budget=5_000, source=LeadSource.IMPORT),
        Lead(email="dave@initech.com", company="Initech", source=LeadSource.API),
    ]
    for lead in leads:
        print(
            f"{lead.company:<10} {lead.source.value:<9} "
            f"score={lead.score():>3} contactable={lead.is_contactable()}"
        )


if __name__ == "__main__":  # pragma: no cover
    demo()
