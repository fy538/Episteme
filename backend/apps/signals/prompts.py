"""
Prompts for signal extraction

Keeping prompts separate from service logic for easy iteration and versioning.
"""


def get_signal_extraction_prompt(user_message: str, conversation_context: str = "") -> str:
    """
    Build the prompt for extracting signals from a user message
    
    Args:
        user_message: The latest user message to extract from
        conversation_context: Formatted previous conversation (optional)
    
    Returns:
        Complete prompt string for LLM
    """
    
    context_section = ""
    if conversation_context:
        context_section = f"""Previous conversation context (for interpretation only):
{conversation_context}

"""
    
    prompt = f"""You are extracting structured epistemic signals from a serious technical conversation.

{context_section}Latest user message (EXTRACT FROM HERE):
USER: {user_message}

Extract the following signal types from the USER's message ONLY:

1. ASSUMPTION - What the user takes as true without proof
   Examples:
   - "I assume users will accept eventual consistency"
   - "Customers probably won't notice the delay"
   - Implicit: "We need caching" → assumes "Performance is currently insufficient"

2. QUESTION - Open uncertainties the user has
   Examples:
   - "What's our current p99 latency?"
   - "Not sure if MongoDB supports this"
   - "How do other teams handle this?"

3. CONSTRAINT - Hard boundaries or requirements
   Examples:
   - "Must ship by end of Q2"
   - "Budget is under $50k"
   - "Has to support 10k concurrent users"
   - "Can't add new dependencies"

4. GOAL - Desired outcomes or targets
   Examples:
   - "Reduce latency to under 100ms"
   - "Increase conversion by 10%"
   - "Make the system more reliable"

5. DECISION_INTENT - Need to make a choice
   Examples:
   - "Should we use Postgres or MongoDB?"
   - "Deciding between microservices and monolith"
   - "Not sure which approach to take"

6. CLAIM - Factual assertions (verifiable or falsifiable)
   Examples:
   - "Postgres is faster for writes"
   - "Our current p99 is 500ms"
   - "Redis supports pub/sub"

7. EVIDENCE_MENTION - References to data, docs, or sources
   Examples:
   - "According to the dashboard, we're at 500ms"
   - "The docs say it supports X"
   - "Based on last quarter's metrics"

EXTRACTION GUIDELINES:

1. Extract ONLY from the latest user message (not from AI responses)
2. Use conversation context to interpret ambiguous statements
3. Normalize to clear, standalone statements
4. Include confidence (0.0-1.0):
   - 0.9-1.0: Explicit, clear statement
   - 0.7-0.9: Implied but clear from context
   - 0.5-0.7: Somewhat ambiguous, requires inference
5. Provide character span in the original message (start, end positions)
6. Skip:
   - Social pleasantries ("thanks", "hello")
   - Meta-commentary ("let me think about this")
   - Pure acknowledgments ("ok", "yes" without content)

OUTPUT FORMAT:

Return a JSON array of extracted signals:

[
  {{
    "type": "Assumption",
    "text": "Event store writes are append-only",
    "confidence": 0.85,
    "span": {{"start": 20, "end": 65}}
  }},
  {{
    "type": "Constraint",
    "text": "Must ship by end of Q2",
    "confidence": 0.95,
    "span": {{"start": 100, "end": 125}}
  }}
]

Return ONLY the JSON array, no other text or markdown formatting."""

    return prompt


def get_assistant_response_prompt(user_message: str, conversation_context: str = "") -> str:
    """
    Build the prompt for generating assistant responses
    
    This is separate from extraction - assistant helps the user think,
    extraction happens in the background.
    
    Args:
        user_message: The user's latest message
        conversation_context: Formatted previous conversation
    
    Returns:
        Complete prompt for assistant response
    """
    
    context_section = ""
    if conversation_context:
        context_section = f"""Previous conversation:
{conversation_context}

"""
    
    prompt = f"""{context_section}User's latest message:
{user_message}

You are a thoughtful assistant helping the user think through complex decisions and investigations.

Your role:
- Ask clarifying questions to surface assumptions
- Help the user articulate constraints and goals
- Challenge weak reasoning (gently)
- Suggest alternative perspectives
- Point out potential risks or blind spots

Respond in a conversational, helpful tone. Keep responses concise (2-4 paragraphs max).

Do not:
- Make decisions for the user
- Be overly prescriptive
- Ignore context from previous messages
- Give generic advice

Response:"""
    
    return prompt


def get_evidence_extraction_prompt(chunk_text: str, document_title: str = "") -> str:
    """
    Extract evidence (facts, metrics, claims) from document chunks.
    
    This is LIGHTER than signal extraction:
    - Focused on factual statements only
    - No epistemic content (assumptions, questions)
    - Used for user-uploaded documents (not AI-generated)
    
    Args:
        chunk_text: Text chunk to extract from
        document_title: Document title for context
    
    Returns:
        Prompt for evidence extraction
    """
    
    context = ""
    if document_title:
        context = f"Document: {document_title}\n\n"
    
    prompt = f"""{context}Extract factual evidence from this text segment.

TEXT:
{chunk_text}

Extract ONLY these types of evidence:

1. METRIC - Specific numbers or measurements
   Examples:
   - "System handles 50,000 requests per second"
   - "P99 latency is 150ms"
   - "Budget is $100,000"

2. BENCHMARK - Performance comparisons or test results
   Examples:
   - "PostgreSQL 2x faster than MongoDB for writes"
   - "Redis achieved 99.99% uptime in production"
   - "Load test showed 10k concurrent users"

3. FACT - Verifiable technical statements
   Examples:
   - "PostgreSQL supports JSONB indexing"
   - "The system uses eventual consistency"
   - "Data is replicated across 3 regions"

4. CLAIM - Assertions that could be verified
   Examples:
   - "This is the fastest key-value store"
   - "Most users prefer lower latency over consistency"
   - "Industry standard is 99.9% uptime"

5. QUOTE - Important direct quotes (for attribution)
   Examples:
   - "According to the CTO: 'We prioritize availability over consistency'"
   - "The paper states: 'Performance degrades at 100k users'"

EXTRACTION RULES:

- Extract standalone statements (readable without surrounding context)
- Include specific numbers when present (exact metrics)
- Skip subjective opinions or recommendations
- Skip background/introductory text
- Skip procedural/how-to content
- Confidence based on specificity:
  - Metrics with numbers: 0.9-1.0
  - Benchmarks with data: 0.8-0.9
  - General claims: 0.6-0.8

OUTPUT FORMAT:

Return JSON array of evidence items:

[
  {{
    "type": "metric",
    "text": "System handles 50,000 requests per second",
    "confidence": 0.95
  }},
  {{
    "type": "benchmark",
    "text": "PostgreSQL 2x faster than MongoDB for write operations",
    "confidence": 0.85
  }}
]

Return ONLY the JSON array, no other text."""

    return prompt


# Version tracking (for prompt experimentation)
PROMPT_VERSION = {
    'signal_extraction': 'v1.0',
    'assistant_response': 'v1.0',
    'evidence_extraction': 'v1.0',  # Phase 2.2
}
