# PydanticAI Migration Guide

## Overview

We've migrated from manual OpenAI API calls with JSON parsing to **PydanticAI** for all "one-off" LLM services. This provides:

- ✅ **Type Safety**: Pydantic schemas ensure LLM outputs match expected structure
- ✅ **Automatic Validation**: Invalid outputs trigger retries automatically
- ✅ **Zero Boilerplate**: No more manual JSON parsing or markdown stripping
- ✅ **Better DX**: Cleaner code, easier to add new AI features

## What Changed

### 1. New Dependencies

Added to `requirements/base.txt`:
```
pydantic-ai==0.0.18
logfire>=0.1.0
```

### 2. New Files Created

#### `apps/common/ai_schemas.py`
Central location for all AI data contracts:
- `SignalExtraction`: Individual signal schema
- `SignalExtractionResult`: Collection of signals
- `TitleGeneration`: Auto-generated titles
- `SummaryGeneration`: Conversation summaries

#### `apps/common/ai_services.py`
General-purpose AI utilities:
- `generate_chat_title()`: Auto-generate chat thread titles
- `generate_case_title()`: Auto-generate case titles
- `summarize_conversation()`: Summarize chat threads

### 3. Refactored Files

#### `apps/signals/extractors.py`
**Before**: 277 lines with manual JSON parsing, validation, error handling

**After**: ~180 lines with PydanticAI handling all parsing/validation

Key changes:
- `SignalExtractor.extract_from_message()` is now `async`
- Removed `_call_llm()` and `_validate_signal()` methods
- Added `_is_valid_signal_type()` for Django model validation
- Uses `SignalExtractionResult` schema for type safety

#### `tasks/workflows.py`
- `assistant_response_workflow()` is now async
- Uses Django async ORM (`aget`, `asave`, `acount`)
- Properly awaits `extractor.extract_from_message()`

## How to Use

### Installing Dependencies

```bash
# In Docker
docker-compose exec backend pip install -r requirements/base.txt

# Or rebuild
docker-compose down
docker-compose build
docker-compose up -d
```

### Setting Up Environment

PydanticAI needs your OpenAI API key. Add to `.env`:
```
OPENAI_API_KEY=sk-...
```

### Adding New AI Services

The pattern is now extremely simple:

```python
from pydantic_ai import Agent
from pydantic import BaseModel

# 1. Define your schema
class MyOutput(BaseModel):
    result: str
    confidence: float

# 2. Create an agent
my_agent = Agent(
    'openai:gpt-4o-mini',
    result_type=MyOutput,
    system_prompt="You are a helpful assistant."
)

# 3. Use it
async def my_service(input_text: str):
    result = await my_agent.run(input_text)
    return result.data.result
```

## Migration Benefits

### Before (Manual OpenAI)
```python
def _call_llm(self, prompt: str):
    response = openai.ChatCompletion.create(...)
    content = response.choices[0].message.content.strip()
    
    # Manual markdown stripping
    if content.startswith('```'):
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]
        content = content.strip()
    
    # Manual JSON parsing
    extracted = json.loads(content)
    
    # Manual validation
    validated = []
    for item in extracted:
        if self._validate_signal(item):
            validated.append(item)
    
    return validated
```

### After (PydanticAI)
```python
async def extract_signals(self, prompt: str):
    result = await self._extraction_agent.run(prompt)
    return result.data.signals  # Already validated!
```

## Next Steps

### 1. Add More One-Off Services

Now that the pattern is established, add:
- Auto-suggest inquiry titles
- Generate case summaries
- Classify message intent
- Extract key decisions from chat

### 2. Integrate Google ADK for Agents

PydanticAI handles "one-off" tasks. For multi-step agentic workflows (Research, Debates, Critiques), use **Google ADK** as planned.

### 3. Add Observability with Logfire

PydanticAI integrates with Logfire for tracing LLM calls:

```python
import logfire

logfire.configure()

# Automatically logs all PydanticAI calls
```

## Testing the Migration

### Test Signal Extraction
```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.chat.models import Message
from apps.signals.extractors import get_extractor
import asyncio

# Get a message
msg = Message.objects.first()

# Test extraction
extractor = get_extractor()
signals = asyncio.run(extractor.extract_from_message(msg, sequence_index=0))

print(f"Extracted {len(signals)} signals")
for signal in signals:
    print(f"- {signal.type}: {signal.text}")
```

### Test Title Generation
```python
from apps.common.ai_services import generate_chat_title
import asyncio

messages = ["I need to decide between Postgres and MongoDB", "Let me help you evaluate the options"]
title = asyncio.run(generate_chat_title(messages))
print(f"Generated title: {title}")
```

## Troubleshooting

### "pydantic_ai module not found"
```bash
docker-compose exec backend pip install pydantic-ai logfire
# Or rebuild: docker-compose build
```

### "Agent run() missing required argument"
Make sure you're using `await` with async functions:
```python
# Wrong
signals = extractor.extract_from_message(msg)

# Correct
signals = await extractor.extract_from_message(msg)
```

### "This model does not support structured outputs"
Some models don't support function calling. Use `gpt-4o-mini` or `gpt-4o`:
```python
Agent('openai:gpt-4o-mini', ...)  # ✅ Supported
Agent('openai:gpt-3.5-turbo', ...) # ⚠️ Limited support
```

## Architecture Notes

### Two-Framework Strategy

**PydanticAI** (One-off services):
- Signal extraction
- Title generation
- Summarization
- Classification
- Any single LLM call with structured output

**Google ADK** (Agentic workflows - coming soon):
- Research generation
- Multi-perspective debates
- Critique generation
- Complex multi-step reasoning

This separation keeps the codebase clean and uses the right tool for each job.

## Resources

- [PydanticAI Docs](https://ai.pydantic.dev/)
- [Google ADK Docs](https://google.github.io/adk-docs/)
- [Logfire Integration](https://ai.pydantic.dev/logfire/)
