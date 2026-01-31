"""
Pydantic schemas for AI-powered services

These schemas define the structure of LLM outputs across the platform.
Using Pydantic ensures type safety and automatic validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class SpanLocation(BaseModel):
    """Character span within source text"""
    start: int = Field(ge=0, description="Start character position")
    end: int = Field(ge=0, description="End character position")


class SignalExtraction(BaseModel):
    """A single epistemic signal extracted from a message"""
    type: str = Field(
        description=(
            "Signal type. Must be one of: "
            "Assumption, Question, Constraint, Goal, DecisionIntent, Claim, EvidenceMention"
        )
    )
    text: str = Field(
        description="The normalized, standalone statement of the signal",
        min_length=1
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0-1.0)",
        default=0.8
    )
    span: Optional[SpanLocation] = Field(
        default=None,
        description="Character position in original message"
    )


class SignalExtractionResult(BaseModel):
    """Collection of signals extracted from a message"""
    signals: List[SignalExtraction] = Field(
        default_factory=list,
        description="All signals found in the message"
    )


class TitleGeneration(BaseModel):
    """Auto-generated title for a conversation or case"""
    title: str = Field(
        max_length=100,
        description="A concise, 3-7 word title"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.9,
        description="Confidence in this title"
    )


class SummaryGeneration(BaseModel):
    """Summary of a conversation or document"""
    summary: str = Field(
        description="Clear, concise summary"
    )
    key_points: List[str] = Field(
        default_factory=list,
        description="Main points extracted"
    )
