"""
Demo: Using PydanticAI services in Episteme

This file shows examples of how to use the new AI services.
Run from Django shell: python manage.py shell < examples/ai_services_demo.py
"""
import logging
import asyncio
from apps.common.ai_services import (
    generate_chat_title,
    generate_case_title,
    summarize_conversation
)

logger = logging.getLogger(__name__)

async def demo_title_generation():
    """Example: Auto-generate chat titles"""
    logger.info("demo_chat_title_generation_start")
    
    messages = [
        "I'm trying to decide between using Postgres or MongoDB for our event store",
        "What are your main concerns?",
        "Performance and consistency. We'll have high write volume",
        "Let me help you evaluate both options..."
    ]
    
    title = await generate_chat_title(messages)
    logger.info("demo_chat_title_generation_result", extra={"title": title})


async def demo_case_title():
    """Example: Auto-generate case titles"""
    logger.info("demo_case_title_generation_start")
    
    position = "We should migrate from MongoDB to PostgreSQL for the event store"
    context = "Current MongoDB setup has consistency issues under high load"
    
    title = await generate_case_title(position, context)
    logger.info("demo_case_title_generation_result", extra={"title": title})


async def demo_summarization():
    """Example: Summarize conversations"""
    logger.info("demo_conversation_summarization_start")
    
    messages = [
        "I'm evaluating database options for our new event-sourced system",
        "What kind of events will you be storing?",
        "User actions, system events, and signal extractions. Probably 10k writes/second peak",
        "That's substantial. Have you considered using Postgres with partitioning?",
        "Not yet, but I'm worried about consistency if we use eventual consistency",
        "Postgres gives you ACID guarantees, which might be important for your use case"
    ]
    
    result = await summarize_conversation(messages, focus="technical decisions")
    
    logger.info("demo_summarization_summary", extra={"summary": result["summary"]})
    logger.info("demo_summarization_key_points")
    for i, point in enumerate(result['key_points'], 1):
        logger.info("demo_summarization_key_point", extra={"index": i, "point": point})


async def demo_signal_extraction():
    """Example: Extract signals from a message"""
    logger.info("demo_signal_extraction_start")
    
    # This would normally use a real Message object
    # Here we're just showing the concept
    from apps.signals.extractors import get_extractor
    
    logger.info("demo_signal_extraction_info", extra={"detail": "Signal extraction handled via PydanticAI"})
    logger.info("demo_signal_extraction_info", extra={"detail": "See apps/signals/extractors.py for implementation"})
    logger.info("demo_signal_extraction_info", extra={"detail": "Extractor is async and type-safe"})
    logger.info(
        "demo_signal_extraction_info",
        extra={"detail": "signals = await extractor.extract_from_message(message)"},
    )


async def main():
    """Run all demos"""
    logger.info("demo_start")
    
    await demo_title_generation()
    await demo_case_title()
    await demo_summarization()
    await demo_signal_extraction()
    
    logger.info("demo_complete")


if __name__ == "__main__":
    # Run the demos
    asyncio.run(main())
