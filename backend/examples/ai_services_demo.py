"""
Demo: Using PydanticAI services in Episteme

This file shows examples of how to use the new AI services.
Run from Django shell: python manage.py shell < examples/ai_services_demo.py
"""
import asyncio
from apps.common.ai_services import (
    generate_chat_title,
    generate_case_title,
    summarize_conversation
)


async def demo_title_generation():
    """Example: Auto-generate chat titles"""
    print("\n=== Chat Title Generation ===")
    
    messages = [
        "I'm trying to decide between using Postgres or MongoDB for our event store",
        "What are your main concerns?",
        "Performance and consistency. We'll have high write volume",
        "Let me help you evaluate both options..."
    ]
    
    title = await generate_chat_title(messages)
    print(f"Generated title: '{title}'")


async def demo_case_title():
    """Example: Auto-generate case titles"""
    print("\n=== Case Title Generation ===")
    
    position = "We should migrate from MongoDB to PostgreSQL for the event store"
    context = "Current MongoDB setup has consistency issues under high load"
    
    title = await generate_case_title(position, context)
    print(f"Generated title: '{title}'")


async def demo_summarization():
    """Example: Summarize conversations"""
    print("\n=== Conversation Summarization ===")
    
    messages = [
        "I'm evaluating database options for our new event-sourced system",
        "What kind of events will you be storing?",
        "User actions, system events, and signal extractions. Probably 10k writes/second peak",
        "That's substantial. Have you considered using Postgres with partitioning?",
        "Not yet, but I'm worried about consistency if we use eventual consistency",
        "Postgres gives you ACID guarantees, which might be important for your use case"
    ]
    
    result = await summarize_conversation(messages, focus="technical decisions")
    
    print(f"\nSummary:\n{result['summary']}\n")
    print("Key Points:")
    for i, point in enumerate(result['key_points'], 1):
        print(f"{i}. {point}")


async def demo_signal_extraction():
    """Example: Extract signals from a message"""
    print("\n=== Signal Extraction ===")
    
    # This would normally use a real Message object
    # Here we're just showing the concept
    from apps.signals.extractors import get_extractor
    
    print("Signal extraction is now handled via PydanticAI")
    print("See apps/signals/extractors.py for implementation")
    print("\nExtractor is async and type-safe:")
    print("  signals = await extractor.extract_from_message(message)")


async def main():
    """Run all demos"""
    print("=" * 60)
    print("PydanticAI Services Demo")
    print("=" * 60)
    
    await demo_title_generation()
    await demo_case_title()
    await demo_summarization()
    await demo_signal_extraction()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the demos
    asyncio.run(main())
