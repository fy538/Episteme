# Getting Started with AI Services

**5-minute setup to start using PydanticAI in Episteme**

## Step 1: Install Dependencies (2 minutes)

```bash
# Option A: Rebuild containers (recommended)
docker-compose down
docker-compose build
docker-compose up -d

# Option B: Install directly
docker-compose exec backend pip install pydantic-ai logfire
```

## Step 2: Add Your API Key (1 minute)

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

Get your key: https://platform.openai.com/api-keys

## Step 3: Test It Works (2 minutes)

```bash
docker-compose exec backend python manage.py shell
```

```python
# Test 1: Title Generation
from apps.common.ai_services import generate_chat_title
import asyncio

messages = ["Should we use Postgres or MongoDB?", "Let me help you decide"]
title = asyncio.run(generate_chat_title(messages))
print(f"✅ Title: {title}")

# Test 2: Signal Extraction
from apps.chat.models import Message
from apps.signals.extractors import get_extractor

message = Message.objects.first()
if message:
    extractor = get_extractor()
    signals = asyncio.run(extractor.extract_from_message(message, sequence_index=0))
    print(f"✅ Extracted {len(signals)} signals")
else:
    print("No messages yet - create one first!")
```

## Step 4: Start Using in Your Code

### Auto-Title Chat Threads

```python
from apps.common.ai_services import generate_chat_title

async def create_thread_with_auto_title(user, messages):
    thread = ChatThread.objects.create(user=user)
    
    # Auto-generate title
    title = await generate_chat_title([m.content for m in messages])
    thread.title = title
    await thread.asave()
    
    return thread
```

### Extract Signals from Messages

```python
from apps.signals.extractors import get_extractor

async def process_user_message(message):
    extractor = get_extractor()
    
    if extractor.should_extract(message):
        signals = await extractor.extract_from_message(
            message=message,
            sequence_index=0
        )
        
        # Save signals
        for signal in signals:
            await signal.asave()
        
        return signals
    return []
```

## That's It!

You're now using PydanticAI for type-safe, validated LLM outputs.

### Next Steps

- **More examples**: See `backend/AI_SERVICES_QUICK_REFERENCE.md`
- **Add features**: See `backend/PYDANTIC_AI_MIGRATION.md`
- **Run demo**: `python examples/ai_services_demo.py`

### Common Tasks

**Add a new AI service:**
1. Define schema in `apps/common/ai_schemas.py`
2. Create agent in `apps/common/ai_services.py`
3. Use it: `result = await my_agent.run(prompt)`

**Change model:**
```python
# Fast & cheap
Agent('openai:gpt-4o-mini', ...)

# High quality
Agent('openai:gpt-4o', ...)

# Best reasoning
Agent('anthropic:claude-3.5-sonnet', ...)
```

**Debug LLM calls:**
```python
import logfire
logfire.configure()  # Traces all PydanticAI calls
```

## Troubleshooting

**"pydantic_ai not found"**: Run `docker-compose build`

**"No API key"**: Add `OPENAI_API_KEY` to `.env`

**"This model doesn't support..."**: Use `gpt-4o-mini` or `gpt-4o`

---

**You're ready to build! 🚀**

See full documentation: `backend/PYDANTIC_AI_MIGRATION.md`
