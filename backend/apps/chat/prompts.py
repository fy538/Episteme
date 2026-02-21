"""
Prompts for chat assistant responses.
"""


def get_assistant_response_prompt(
    user_message: str,
    conversation_context: str = "",
    project_summary_context: str = "",
    companion_context: str = "",
) -> str:
    """
    Build the prompt for generating assistant responses.

    Args:
        user_message: The user's latest message
        conversation_context: Formatted previous conversation
        project_summary_context: Optional project summary for grounding
        companion_context: Optional companion state summary (the clarifying loop)

    Returns:
        Complete prompt for assistant response
    """
    context_section = ""
    if conversation_context:
        context_section = f"""Previous conversation:
{conversation_context}

"""

    summary_section = ""
    if project_summary_context:
        summary_section = f"""Project knowledge context (use to ground your responses):
{project_summary_context}

"""

    companion_section = ""
    if companion_context:
        companion_section = f"""CONVERSATION STATE (tracked by companion):
{companion_context}

IMPORTANT: Use this state to guide your response:
- Do NOT suggest or explain things that have been ELIMINATED
- Do NOT ask about things that are already ESTABLISHED
- Address OPEN QUESTIONS when relevant
- Stay focused on the current exploration direction

"""

    prompt = f"""{context_section}{summary_section}{companion_section}User's latest message:
{user_message}

You are a thoughtful assistant helping the user think through complex decisions and investigations.

Your role:
- Ask clarifying questions to surface assumptions
- Help the user articulate constraints and goals
- Challenge weak reasoning (gently)
- Suggest alternative perspectives
- Point out potential risks or blind spots
- When relevant, reference insights from the project's knowledge graph and summary

Respond in a conversational, helpful tone. Keep responses concise (2-4 paragraphs max).

Do not:
- Make decisions for the user
- Be overly prescriptive
- Ignore context from previous messages
- Give generic advice

Response:"""

    return prompt


def format_summary_for_chat(sections: dict) -> str:
    """
    Format a ProjectSummary's sections dict into compact text for the chat prompt.

    Keeps it concise (~200-400 tokens) to avoid overwhelming the context window.
    Strips citation markers since the chat LLM doesn't have access to node data.
    """
    import re

    parts = []

    overview = sections.get('overview', '')
    if overview:
        # Strip [nodeId:...] citation markers
        clean = re.sub(r'\[nodeId:[a-f0-9-]+\]', '', overview).strip()
        parts.append(f"Overview: {clean}")

    findings = sections.get('key_findings', [])
    if findings:
        themes = []
        for f in findings[:5]:  # Cap at 5 themes
            label = f.get('theme_label', '')
            narrative = f.get('narrative', '')
            clean = re.sub(r'\[nodeId:[a-f0-9-]+\]', '', narrative).strip()
            if label and clean:
                themes.append(f"- {label}: {clean[:150]}")
        if themes:
            parts.append("Key themes:\n" + "\n".join(themes))

    attention = sections.get('attention_needed', '')
    if attention:
        clean = re.sub(r'\[nodeId:[a-f0-9-]+\]', '', attention).strip()
        parts.append(f"Attention needed: {clean[:200]}")

    return "\n\n".join(parts)
