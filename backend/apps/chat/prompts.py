"""
Prompts for chat assistant responses.
"""


def get_assistant_response_prompt(user_message: str, conversation_context: str = "") -> str:
    """
    Build the prompt for generating assistant responses.

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
