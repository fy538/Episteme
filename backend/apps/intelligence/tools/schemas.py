"""
Tool Schema Definitions — maps to existing service methods.

Each tool definition includes:
- JSON Schema for parameters (matching service method signatures)
- Permission level (AUTO_EXECUTE vs CONFIRM_REQUIRED)
- Required context (case_id, project_id, etc.)
- Reference to the service method it dispatches to

Initial tool set:
  create_inquiry      — InquiryService.create_inquiry()
  resolve_inquiry     — InquiryService.resolve_inquiry()
  update_case_stage   — PlanService.update_stage()
  update_assumption   — PlanService.update_assumption_status()
  update_criterion    — PlanService.update_criterion_status()
  record_decision     — ResolutionService.create_resolution()
  add_outcome_note    — DecisionService.add_outcome_note()
  create_case         — CaseService.create_case()
  add_evidence_node   — GraphService.create_node(type='evidence')
"""

from .registry import ToolRegistry, ToolDefinition, ToolPermission


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

CREATE_INQUIRY = ToolDefinition(
    name="create_inquiry",
    description=(
        "Create a new inquiry (investigation thread) for a case. "
        "Use when a specific question needs focused investigation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The inquiry question or title (e.g. 'What are the cost implications of Option B?')",
            },
            "description": {
                "type": "string",
                "description": "Optional longer description of what to investigate",
            },
        },
        "required": ["title"],
    },
    permission=ToolPermission.AUTO_EXECUTE,
    required_context=["case_id"],
    service_method="apps.inquiries.services.InquiryService.create_inquiry",
    display_name="Create Inquiry",
)


RESOLVE_INQUIRY = ToolDefinition(
    name="resolve_inquiry",
    description=(
        "Resolve an open inquiry with a conclusion. "
        "Use when enough evidence has been gathered to answer the inquiry question."
    ),
    parameters={
        "type": "object",
        "properties": {
            "inquiry_id": {
                "type": "string",
                "description": "UUID of the inquiry to resolve",
            },
            "conclusion": {
                "type": "string",
                "description": "The conclusion reached from the investigation",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in the conclusion (0.0 to 1.0)",
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
        "required": ["inquiry_id", "conclusion"],
    },
    permission=ToolPermission.CONFIRM_REQUIRED,
    required_context=["case_id"],
    service_method="apps.inquiries.services.InquiryService.resolve_inquiry",
    display_name="Resolve Inquiry",
)


UPDATE_CASE_STAGE = ToolDefinition(
    name="update_case_stage",
    description=(
        "Update the investigation stage of the current case. "
        "Stages: exploring, focusing, synthesizing, ready, deciding."
    ),
    parameters={
        "type": "object",
        "properties": {
            "new_stage": {
                "type": "string",
                "description": "The new stage",
                "enum": ["exploring", "focusing", "synthesizing", "ready", "deciding"],
            },
            "rationale": {
                "type": "string",
                "description": "Brief explanation for the stage change",
            },
        },
        "required": ["new_stage", "rationale"],
    },
    permission=ToolPermission.AUTO_EXECUTE,
    required_context=["case_id"],
    service_method="apps.cases.plan_service.PlanService.update_stage",
    display_name="Update Stage",
)


UPDATE_ASSUMPTION = ToolDefinition(
    name="update_assumption_status",
    description=(
        "Update the status of a case assumption based on new evidence. "
        "Statuses: untested, testing, validated, invalidated."
    ),
    parameters={
        "type": "object",
        "properties": {
            "assumption_id": {
                "type": "string",
                "description": "UUID of the assumption to update",
            },
            "new_status": {
                "type": "string",
                "description": "The new assumption status",
                "enum": ["untested", "testing", "validated", "invalidated"],
            },
            "evidence_summary": {
                "type": "string",
                "description": "Brief summary of evidence supporting this status change",
            },
        },
        "required": ["assumption_id", "new_status"],
    },
    permission=ToolPermission.AUTO_EXECUTE,
    required_context=["case_id"],
    service_method="apps.cases.plan_service.PlanService.update_assumption_status",
    display_name="Update Assumption",
)


UPDATE_CRITERION = ToolDefinition(
    name="update_criterion_status",
    description=(
        "Mark a decision criterion as met or unmet based on evidence."
    ),
    parameters={
        "type": "object",
        "properties": {
            "criterion_id": {
                "type": "string",
                "description": "UUID of the criterion to update",
            },
            "is_met": {
                "type": "boolean",
                "description": "Whether the criterion is now met",
            },
        },
        "required": ["criterion_id", "is_met"],
    },
    permission=ToolPermission.AUTO_EXECUTE,
    required_context=["case_id"],
    service_method="apps.cases.plan_service.PlanService.update_criterion_status",
    display_name="Update Criterion",
)


RECORD_DECISION = ToolDefinition(
    name="record_decision",
    description=(
        "Resolve a case. This auto-generates all resolution fields from case "
        "state and transitions the case to DECIDED status. Use when the user "
        "indicates they've reached a resolution or wants to close the case."
    ),
    parameters={
        "type": "object",
        "properties": {
            "resolution_type": {
                "type": "string",
                "enum": ["resolved", "closed"],
                "description": (
                    "'resolved' — user has landed on an answer, "
                    "'closed' — closing without resolution (paused, moot, needs reframing, etc.)"
                ),
            },
        },
        "required": ["resolution_type"],
    },
    permission=ToolPermission.CONFIRM_REQUIRED,
    required_context=["case_id"],
    service_method="apps.cases.resolution_service.ResolutionService.create_resolution",
    display_name="Resolve Case",
)


ADD_OUTCOME_NOTE = ToolDefinition(
    name="add_outcome_note",
    description=(
        "Add an outcome note to an existing decision. Use during outcome "
        "review to track how the decision played out."
    ),
    parameters={
        "type": "object",
        "properties": {
            "note": {
                "type": "string",
                "description": "Observation about how the decision turned out",
            },
            "sentiment": {
                "type": "string",
                "description": "Overall sentiment of the outcome",
                "enum": ["positive", "negative", "neutral", "mixed"],
            },
        },
        "required": ["note"],
    },
    permission=ToolPermission.CONFIRM_REQUIRED,
    required_context=["case_id"],
    service_method="apps.cases.decision_service.DecisionService.add_outcome_note",
    display_name="Add Outcome Note",
)


CREATE_CASE = ToolDefinition(
    name="create_case",
    description=(
        "Create a new decision investigation case. Use when the conversation "
        "reveals a significant decision that warrants structured tracking."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Case title describing the decision",
            },
            "position": {
                "type": "string",
                "description": "Initial position or hypothesis about the decision",
            },
            "decision_question": {
                "type": "string",
                "description": "The core question being decided",
            },
            "stakes": {
                "type": "string",
                "description": "Stakes level for this decision",
                "enum": ["low", "medium", "high", "critical"],
            },
        },
        "required": ["title"],
    },
    permission=ToolPermission.CONFIRM_REQUIRED,
    required_context=["project_id"],
    service_method="apps.cases.services.CaseService.create_case",
    display_name="Create Case",
)


ADD_EVIDENCE_NODE = ToolDefinition(
    name="add_evidence_node",
    description=(
        "Add an evidence node to the knowledge graph. Use when the conversation "
        "surfaces a concrete data point, finding, or observation that should "
        "be formally tracked."
    ),
    parameters={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The evidence content (a specific fact or finding)",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in this evidence (0.0 to 1.0)",
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
        "required": ["content"],
    },
    permission=ToolPermission.AUTO_EXECUTE,
    required_context=["project_id"],
    service_method="apps.graph.services.GraphService.create_node",
    display_name="Add Evidence",
)


# ---------------------------------------------------------------------------
# All tool definitions for registration
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    CREATE_INQUIRY,
    RESOLVE_INQUIRY,
    UPDATE_CASE_STAGE,
    UPDATE_ASSUMPTION,
    UPDATE_CRITERION,
    RECORD_DECISION,
    ADD_OUTCOME_NOTE,
    CREATE_CASE,
    ADD_EVIDENCE_NODE,
]


def register_all_tools():
    """Register all tool definitions with the ToolRegistry."""
    for tool in TOOL_SCHEMAS:
        ToolRegistry.register(tool)
