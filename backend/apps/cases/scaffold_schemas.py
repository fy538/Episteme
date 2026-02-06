"""
Pydantic schemas for case scaffolding LLM extraction.

These schemas define the structured output the LLM produces when
analyzing a scaffolding chat transcript to create a case.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class UncertaintyItem(BaseModel):
    """A key uncertainty / question to investigate."""
    title: str = Field(description="Short title for the inquiry (question form)")
    description: str = Field(default="", description="Optional elaboration")
    why_important: str = Field(default="", description="Why this matters for the decision")


class ConstraintItem(BaseModel):
    """A constraint on the decision."""
    type: str = Field(description="Category: timeline, budget, regulatory, technical, etc.")
    description: str = Field(description="The constraint description")


class StakeholderItem(BaseModel):
    """A stakeholder in the decision."""
    name: str = Field(description="Stakeholder name or role")
    interest: str = Field(description="What they care about")
    influence: Literal['low', 'medium', 'high'] = Field(default='medium')


class ScaffoldExtraction(BaseModel):
    """
    Structured extraction from a scaffolding chat transcript.

    The LLM analyzes the conversation and extracts the decision structure.
    """
    decision_question: str = Field(
        description="The core decision question in clear, specific terms"
    )
    key_uncertainties: list[UncertaintyItem] = Field(
        default_factory=list,
        description="2-5 key uncertainties that need investigation (become inquiries)"
    )
    initial_position: Optional[str] = Field(
        default=None,
        description="The user's current position or thesis, if stated"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions detected in the conversation"
    )
    constraints: list[ConstraintItem] = Field(
        default_factory=list,
        description="Constraints on the decision"
    )
    stakeholders: list[StakeholderItem] = Field(
        default_factory=list,
        description="Key stakeholders mentioned"
    )
    suggested_research: list[str] = Field(
        default_factory=list,
        description="Topics that would benefit from research"
    )
    stakes_level: Literal['low', 'medium', 'high'] = Field(
        default='medium',
        description="How high-stakes is this decision"
    )
    background_summary: str = Field(
        default="",
        description="Brief summary of the decision context"
    )
