"""
schema.py — Pydantic v2 models for the Composio product research pipeline.

Each AppResearch instance captures everything needed to judge an app's
buildability inside the Composio ecosystem. Validation rules are enforced
via model_validator so that bad data surfaces at parse time, not at
analysis time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Evidence entry — typed dict-like sub-model
# ---------------------------------------------------------------------------

class EvidenceEntry(BaseModel):
    """A single piece of evidence that supports a claim about the app."""

    claim: str
    url: str
    source_tier: Literal[1, 2, 3, 4, 5]
    """
    Tier guide:
      1 = Official developer docs / changelog
      2 = Official blog / press release
      3 = Reputable third-party (e.g. G2, PH, TechCrunch)
      4 = Community / GitHub discussion
      5 = Inferred / LLM knowledge, no live URL
    """


# ---------------------------------------------------------------------------
# Core research result model
# ---------------------------------------------------------------------------

class AppResearch(BaseModel):
    # ── Identity ──────────────────────────────────────────────────────────
    app_name: str
    category: str  # one of the 10 assignment categories
    description: str  # one line, no marketing language

    # ── Auth ──────────────────────────────────────────────────────────────
    auth_methods: list[str]          # e.g. ["OAuth 2.0", "API key"]
    credential_acquisition: str      # HOW a dev actually gets creds — 1-2 sentences

    # ── Access ────────────────────────────────────────────────────────────
    self_serve_status: Literal[
        "Self-serve",
        "Self-serve with restrictions",
        "Trial",
        "Paid plan required",
        "Admin approval",
        "Partner approval",
        "Contact sales",
        "Enterprise only",
        "Unknown",
    ]

    # ── API surface ───────────────────────────────────────────────────────
    api_type: list[str]              # e.g. ["REST"], ["GraphQL"], ["REST", "GraphQL"], ["None found"]
    api_breadth: Literal["Narrow", "Moderate", "Broad", "Very broad", "Unknown"]
    api_documentation_url: str | None

    # ── MCP ───────────────────────────────────────────────────────────────
    mcp_available: Literal["Yes", "No evidence found", "Unknown"]
    mcp_official: Literal["Official", "Third-party", "Community", "N/A", "Unknown"]
    mcp_url: str | None

    # ── Verdict ───────────────────────────────────────────────────────────
    buildability_verdict: Literal["Easy", "Possible", "Difficult", "Blocked", "Unknown"]
    primary_blocker: str | None      # null only if verdict is "Easy"

    # ── Evidence & confidence ─────────────────────────────────────────────
    evidence: list[EvidenceEntry]
    confidence: Literal["High", "Medium", "Low"]
    human_review_required: bool
    human_review_notes: str | None

    # -----------------------------------------------------------------------
    # Field-level validators
    # -----------------------------------------------------------------------

    @field_validator("auth_methods", "api_type", mode="before")
    @classmethod
    def non_empty_list(cls, v: list) -> list:
        """Both list fields must have at least one entry."""
        if not v:
            raise ValueError("List must contain at least one entry.")
        return v

    @field_validator("evidence", mode="before")
    @classmethod
    def coerce_evidence_entries(cls, v: list) -> list:
        """
        Accept raw dicts (from JSON) or EvidenceEntry objects transparently.
        Pydantic v2 handles this automatically; this validator is a no-op
        kept here as an explicit hook for future custom coercion.
        """
        return v

    # -----------------------------------------------------------------------
    # Cross-field validation rules
    # -----------------------------------------------------------------------

    @model_validator(mode="after")
    def enforce_review_rules(self) -> "AppResearch":
        notes: list[str] = []

        # ── Rule 1: Low confidence always requires human review ───────────
        if self.confidence == "Low" and not self.human_review_required:
            self.human_review_required = True
            notes.append("Auto-flagged: confidence is Low.")

        # ── Rule 2: primary_blocker must be set unless verdict is Easy ────
        if self.buildability_verdict != "Easy" and self.primary_blocker is None:
            notes.append(
                f"primary_blocker is null but verdict is '{self.buildability_verdict}'."
            )
            self.human_review_required = True

        # ── Rule 3: MCP claimed but no URL ────────────────────────────────
        if self.mcp_available == "Yes" and self.mcp_url is None:
            notes.append("mcp_available is 'Yes' but mcp_url is null — verify MCP endpoint.")
            self.human_review_required = True

        # ── Rule 4: Easy verdict contradicts restrictive access ───────────
        _restrictive = {"Enterprise only", "Contact sales", "Partner approval"}
        if (
            self.buildability_verdict == "Easy"
            and self.self_serve_status in _restrictive
        ):
            notes.append(
                f"Verdict is 'Easy' but self_serve_status is '{self.self_serve_status}' "
                f"— likely mislabelled."
            )
            self.human_review_required = True

        # ── Rule 5: Non-Unknown / non-negative fields need supporting evidence ──
        # Fields that explicitly state absence of info are exempt from coverage.
        _NEGATIVE_SENTINELS = {
            "unknown",
            "no evidence found",
            "none found",
            "n/a",
        }
        _claimed_fields = {
            "auth_methods": self.auth_methods,
            "self_serve_status": self.self_serve_status,
            "api_type": self.api_type,
            "mcp_available": self.mcp_available,
            "buildability_verdict": self.buildability_verdict,
        }
        evidence_claims_lower = {e.claim.lower() for e in self.evidence}

        for field_name, value in _claimed_fields.items():
            # Normalise to a flat string and a list of individual tokens.
            if isinstance(value, list):
                val_str   = ", ".join(value)
                val_items = [v.lower() for v in value]
            else:
                val_str   = str(value)
                val_items = [val_str.lower()]

            # Skip fields that declare they have no positive information.
            if val_str.lower() in _NEGATIVE_SENTINELS:
                continue
            if all(v in _NEGATIVE_SENTINELS for v in val_items):
                continue

            # Evidence is considered covering if ANY evidence claim mentions:
            #   • the field name (e.g. "api_type"), OR
            #   • any individual list item (e.g. "rest" from ["REST", "GraphQL"]), OR
            #   • the first meaningful word of the value (handles "Easy → easy").
            first_word = val_items[0].split()[0] if val_items[0].split() else ""
            covered = any(
                field_name in c
                or any(item in c for item in val_items)
                or (first_word and first_word in c)
                for c in evidence_claims_lower
            )
            if not covered:
                notes.append(
                    f"No evidence entry covers field '{field_name}' (value: {val_str!r})."
                )
                self.human_review_required = True

        # ── Merge notes ───────────────────────────────────────────────────
        if notes:
            existing = self.human_review_notes or ""
            separator = "\n" if existing else ""
            self.human_review_notes = existing + separator + "\n".join(notes)

        return self

    # -----------------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------------

    def is_composio_ready(self) -> bool:
        """True when the app is Easy/Possible and does NOT require human review."""
        return (
            self.buildability_verdict in {"Easy", "Possible"}
            and not self.human_review_required
        )

    def evidence_urls(self) -> list[str]:
        """Flat list of all evidence URLs for quick link-checking."""
        return [e.url for e in self.evidence]
