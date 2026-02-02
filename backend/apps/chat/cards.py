"""
Card schema definitions for rich message types
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class CardAction(BaseModel):
    """Action button on a card"""
    id: str
    label: str
    action_type: str  # e.g., 'create_inquiry', 'add_to_brief', 'validate_assumption'
    payload: dict = Field(default_factory=dict)
    variant: Literal['primary', 'secondary', 'danger'] = 'secondary'
    

class SignalExtractionCard(BaseModel):
    """Card displaying extracted signals with actions"""
    type: Literal['card_signal_extraction'] = 'card_signal_extraction'
    heading: str = "Signals Detected"
    description: Optional[str] = None
    
    signals: List[dict]  # Signal objects grouped by type
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)
    

class CaseSuggestionCard(BaseModel):
    """Card suggesting relevant cases"""
    type: Literal['card_case_suggestion'] = 'card_case_suggestion'
    heading: str = "Relevant Cases"
    description: Optional[str] = None
    
    cases: List[dict]  # Case objects with relevance scores
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)


class StructurePreviewCard(BaseModel):
    """Card suggesting case structure"""
    type: Literal['card_structure_preview'] = 'card_structure_preview'
    heading: str = "Case Structure Detected"
    description: Optional[str] = None
    
    suggested_title: str
    confidence: float
    structure_type: str  # e.g., 'appeal', 'motion', 'brief'
    key_elements: List[dict]  # Detected elements (assumptions, questions, etc.)
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)


class AssumptionValidatorCard(BaseModel):
    """Card for validating assumptions"""
    type: Literal['card_assumption_validator'] = 'card_assumption_validator'
    heading: str = "Assumption Validation"
    description: Optional[str] = None
    
    assumptions: List[dict]  # Assumption objects with validation status
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)


class ResearchStatusCard(BaseModel):
    """Card showing real-time research agent progress"""
    type: Literal['card_research_status'] = 'card_research_status'
    heading: str = "Research in Progress"
    description: Optional[str] = None
    
    agent_type: str  # 'research', 'critique', 'brief'
    status: Literal['running', 'completed', 'failed']
    progress_steps: List[dict]  # Steps with status
    results_preview: Optional[str] = None
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)


class ActionPromptCard(BaseModel):
    """Card prompting user to take action"""
    type: Literal['card_action_prompt'] = 'card_action_prompt'
    heading: str
    description: str
    
    prompt_type: str  # e.g., 'organize_questions', 'validate_assumptions', 'create_case'
    priority: Literal['high', 'medium', 'low'] = 'medium'
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)


class EvidenceMapCard(BaseModel):
    """Card showing visual evidence map"""
    type: Literal['card_evidence_map'] = 'card_evidence_map'
    heading: str = "Evidence Map"
    description: Optional[str] = None
    
    nodes: List[dict]  # Graph nodes (claims, evidence)
    edges: List[dict]  # Connections between nodes
    actions: List[CardAction]
    metadata: dict = Field(default_factory=dict)
