# AI Services Quick Reference

Quick copy-paste examples for using Episteme's AI services.

## Signal Extraction

Extract epistemic signals (assumptions, questions, constraints, etc.) from messages.

```python
from apps.signals.extractors import get_extractor
from apps.chat.models import Message

# Get the extractor
extractor = get_extractor()

# Extract signals from a message
message = Message.objects.get(id=message_id)
signals = await extractor.extract_from_message(
    message=message,
    context_messages=previous_messages[-5:],  # Last 5 for context
    sequence_index=position_in_thread
)

# Save signals
for signal in signals:
    signal.event_id = event.id  # Link to event
    signal.case = case  # Link to case if applicable
    await signal.asave()
```

**Signal Types**:
- `Assumption`: What user takes as true without proof
- `Question`: Open uncertainties
- `Constraint`: Hard boundaries or requirements
- `Goal`: Desired outcomes
- `DecisionIntent`: Need to make a choice
- `Claim`: Factual assertions
- `EvidenceMention`: References to data/docs/sources

## Title Generation

### Chat Thread Titles

```python
from apps.common.ai_services import generate_chat_title

messages = thread.messages.values_list('content', flat=True)
title = await generate_chat_title(list(messages))

thread.title = title
await thread.asave()
```

### Case Titles

```python
from apps.common.ai_services import generate_case_title

title = await generate_case_title(
    position="We should migrate from MongoDB to Postgres",
    context="Current system has consistency issues"
)

case.title = title
await case.asave()
```

## Summarization

```python
from apps.common.ai_services import summarize_conversation

messages = thread.messages.values_list('content', flat=True)
result = await summarize_conversation(
    list(messages),
    focus="technical decisions"  # Optional focus area
)

print(result['summary'])
# "The conversation focused on database selection..."

print(result['key_points'])
# ["Evaluated Postgres vs MongoDB", "Concerns about consistency", ...]
```

## Adding Custom AI Services

### 1. Define Schema

```python
# In apps/common/ai_schemas.py
from pydantic import BaseModel, Field

class MyServiceOutput(BaseModel):
    result: str = Field(description="The main result")
    confidence: float = Field(ge=0, le=1)
```

### 2. Create Agent

```python
# In apps/common/ai_services.py
from pydantic_ai import Agent
from .ai_schemas import MyServiceOutput

my_agent = Agent(
    'openai:gpt-4o-mini',
    result_type=MyServiceOutput,
    system_prompt="You are a helpful assistant who..."
)
```

### 3. Create Service Function

```python
async def my_service(input_text: str) -> str:
    """
    Do something useful with LLM
    
    Args:
        input_text: User input
        
    Returns:
        Processed result
    """
    try:
        result = await my_agent.run(input_text)
        return result.data.result
    except Exception as e:
        print(f"Service failed: {e}")
        return "Fallback result"
```

### 4. Use It

```python
from apps.common.ai_services import my_service

result = await my_service("Some input")
```

## Common Patterns

### Check Before Extraction

```python
extractor = get_extractor()

if extractor.should_extract(message):
    signals = await extractor.extract_from_message(message)
```

### Error Handling

```python
try:
    title = await generate_chat_title(messages)
except Exception as e:
    title = "Untitled Conversation"
    print(f"Title generation failed: {e}")
```

### Batch Processing

```python
# Process multiple messages
for message in messages:
    if extractor.should_extract(message):
        signals = await extractor.extract_from_message(message)
        # Save signals...
```

## Environment Setup

Ensure these environment variables are set in `.env`:

```bash
OPENAI_API_KEY=sk-...
```

## Model Selection

**Fast & Cheap** (default):
- `openai:gpt-4o-mini`: $0.15/1M input tokens

**High Quality**:
- `openai:gpt-4o`: $5/1M input tokens
- `anthropic:claude-3.5-sonnet`: Best reasoning

**Local** (no API key needed):
- `ollama:llama3`: Free, runs locally

To change model:
```python
Agent('openai:gpt-4o', ...)  # High quality
Agent('anthropic:claude-3.5-sonnet', ...)  # Best reasoning
Agent('ollama:llama3', ...)  # Local/free
```

## Async in Django Views

### In Async Views

```python
from django.http import JsonResponse
from asgiref.sync import async_to_sync

async def my_view(request):
    title = await generate_chat_title(messages)
    return JsonResponse({'title': title})
```

### In Sync Views (Convert)

```python
from asgiref.sync import async_to_sync

def my_sync_view(request):
    title = async_to_sync(generate_chat_title)(messages)
    return JsonResponse({'title': title})
```

### In Celery Tasks

```python
@shared_task
async def my_task():
    title = await generate_chat_title(messages)
    return title
```

## Debugging

### Enable Logfire Tracing

```python
import logfire

logfire.configure()

# All PydanticAI calls will be traced automatically
```

### Print Agent Responses

```python
result = await my_agent.run(prompt)
print(f"Raw result: {result.data}")
print(f"All fields: {result.data.model_dump()}")
```

### Test in Shell

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.common.ai_services import generate_chat_title
import asyncio

messages = ["First message", "Second message"]
title = asyncio.run(generate_chat_title(messages))
print(f"Title: {title}")
```

## Performance Tips

### Batching

Avoid calling LLM services in tight loops. Batch when possible:

```python
# ❌ Bad - N API calls
for msg in messages:
    title = await generate_chat_title([msg])

# ✅ Good - 1 API call
title = await generate_chat_title(messages)
```

### Caching

Cache LLM results when inputs don't change:

```python
from django.core.cache import cache

cache_key = f"title:{thread.id}"
title = cache.get(cache_key)

if not title:
    title = await generate_chat_title(messages)
    cache.set(cache_key, title, timeout=3600)  # 1 hour
```

### Async Concurrency

Run multiple LLM calls in parallel:

```python
import asyncio

# ❌ Sequential - slow
title1 = await generate_chat_title(messages1)
title2 = await generate_chat_title(messages2)

# ✅ Parallel - fast
title1, title2 = await asyncio.gather(
    generate_chat_title(messages1),
    generate_chat_title(messages2)
)
```

## Resources

- [PydanticAI Docs](https://ai.pydantic.dev/)
- [Migration Guide](./PYDANTIC_AI_MIGRATION.md)
- [Demo Examples](./examples/ai_services_demo.py)
