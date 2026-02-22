"""Pydantic state models for DiscoverySummary, ScopingOutput, ConversationState."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DiscoverySummary(BaseModel):
    """Structured output from Discovery phase."""

    target_user: Optional[str] = None
    core_problem: Optional[str] = None
    current_alternatives: list[str] = Field(default_factory=list)
    why_now: Optional[str] = None
    feature_wishlist: list[str] = Field(default_factory=list)
    success_metric: Optional[str] = None
    revenue_model: Optional[str] = None
    constraints: Optional[str] = None


class Feature(BaseModel):
    """Single MVP feature with priority and optional RICE scoring."""

    name: str
    description: str
    priority: Literal["P0", "P1", "P2"]
    rice_reach: Optional[int] = None
    rice_impact: Optional[float] = None
    rice_confidence: Optional[float] = None
    rice_effort: Optional[float] = None
    rice_score: Optional[float] = None
    phase: int = 1


class CutFeature(BaseModel):
    """Feature that was cut with rationale."""

    name: str
    reason_cut: str


class ComparableProduct(BaseModel):
    """Reference product from web search."""

    name: str
    url: Optional[str] = None
    relevance: str


class ImplementationPhase(BaseModel):
    """One phase of the implementation plan (e.g. Core MVP, Essential Additions)."""

    phase_number: int
    name: str
    goal: str
    estimated_weeks: str
    features: list[str] = Field(default_factory=list)


class ScopingOutput(BaseModel):
    """Structured output from Scoping phase."""

    mvp_features: list[Feature] = Field(default_factory=list)
    cut_features: list[CutFeature] = Field(default_factory=list)
    comparable_products: list[ComparableProduct] = Field(default_factory=list)
    core_user_flow: Optional[str] = None
    scope_rationale: Optional[str] = None
    key_screens: list[str] = Field(default_factory=list)
    implementation_phases: list[ImplementationPhase] = Field(default_factory=list)


class ConversationState(BaseModel):
    """Full conversation state across phases."""

    phase: Literal["discovery", "scoping", "spec", "done"] = "discovery"
    messages: list[dict] = Field(default_factory=list)
    discovery_summary: DiscoverySummary = Field(default_factory=DiscoverySummary)
    discovery_summary_shown: bool = False
    scoping_output: Optional[ScopingOutput] = None
    negotiation_rounds: int = 0
    max_negotiation_rounds: int = 3
    spec_markdown: Optional[str] = None
    scope_agreed: bool = False
    awaiting_scope_agreement: bool = False
