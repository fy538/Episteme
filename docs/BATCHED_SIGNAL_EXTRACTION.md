# Batched Signal Extraction

**Cost Optimization Strategy**: Combine Strategy 1 (Selective Extraction) + Strategy 2 (Batched Extraction)

## Overview

Instead of extracting signals from every single message, we:
1. **Accumulate** messages until a threshold is met
2. **Extract** from the batch in a single LLM call
3. **Reset** counters and start accumulating again

This reduces extraction costs by **60-70%** while maintaining quality.

## How It Works

### Threshold-Based Triggering

Extraction is triggered when **either** condition is met:

```python
chars_since_extraction >= 500  # Character threshold
OR
turns_since_extraction >= 5     # Turn threshold
```

**Why two thresholds?**
- **Character threshold**: Ensures we extract from long, detailed messages
- **Turn threshold**: Ensures we extract regularly even from short back-and-forth

### Accumulation Flow

```
User Message 1 (100 chars)
  └─ Accumulate: chars=100, turns=1
  └─ Threshold NOT met (continue accumulating)

User Message 2 (150 chars)
  └─ Accumulate: chars=250, turns=2
  └─ Threshold NOT met (continue accumulating)

User Message 3 (200 chars)
  └─ Accumulate: chars=450, turns=3
  └─ Threshold NOT met (continue accumulating)

User Message 4 (100 chars)
  └─ Accumulate: chars=550, turns=4
  └─ Threshold MET! (chars >= 500)
  
  EXTRACT SIGNALS FROM ALL 4 MESSAGES IN ONE BATCH
  └─ Single LLM call processes all messages
  └─ Extract 15 signals total
  └─ Reset: chars=0, turns=0

User Message 5 (80 chars)
  └─ Accumulate: chars=80, turns=1
  └─ Start new batch cycle...
```

## Implementation Details

### ChatThread Model

New fields for tracking accumulation:

```python
class ChatThread(models.Model):
    # ...existing fields...
    
    # Batching tracking
    last_extraction_at = DateTimeField(null=True)
    chars_since_extraction = IntegerField(default=0)
    turns_since_extraction = IntegerField(default=0)
```

### Workflow Integration

**File**: `backend/tasks/workflows.py`

```python
# In assistant_response_workflow()

# 1. Accumulate message stats
thread.accumulate_for_extraction(len(user_message.content))

# 2. Check if threshold met
if should_trigger_batch_extraction(thread, char_threshold=500, turn_threshold=5):
    # 3. Get all unprocessed messages
    unprocessed_messages = get_unprocessed_messages(thread)
    
    # 4. Extract from batch in single LLM call
    signals_extracted = extract_signals_from_batch(
        thread=thread,
        messages=unprocessed_messages
    )
    
    # 5. Counters automatically reset after extraction
```

### Batch Extraction Logic

**File**: `backend/apps/signals/batch_extraction.py`

```python
async def extract_signals_from_batch_async(thread, messages):
    """Extract from multiple messages in one LLM call"""
    
    # Single LLM call for all messages
    signals_by_message = await extractor.extract_from_messages_batch(
        messages=messages,
        thread=thread
    )
    
    # Save all signals
    for message_id, signals in signals_by_message.items():
        for signal in signals:
            # Create event + save signal
            ...
    
    # Reset counters
    thread.reset_extraction_counters()
```

## Cost Analysis

### Before (Per-Message Extraction)

```
Scenario: 10 messages in a conversation
- LLM calls: 10 (one per message)
- Total cost: 10 × $0.00027 = $0.0027
- Latency: 10 × 1.5s = 15s total
```

### After (Batched Extraction)

```
Scenario: 10 messages in a conversation
- Accumulate: Messages 1-4 (not extracted)
- Trigger: Message 5 hits threshold
- Extract: Batch 1 (messages 1-5) in ONE call
- Accumulate: Messages 6-9 (not extracted)
- Trigger: Message 10 hits threshold
- Extract: Batch 2 (messages 6-10) in ONE call

- LLM calls: 2 (batches of 5)
- Total cost: 2 × $0.00040 = $0.0008
- Savings: 70% reduction
- Latency: 2 × 2s = 4s total (amortized)
```

## Tuning Thresholds

You can adjust thresholds based on your use case:

### Conservative (More Frequent Extraction)

```python
should_trigger_batch_extraction(
    thread,
    char_threshold=300,  # Lower threshold
    turn_threshold=3     # Fewer turns
)
```

**Use when:**
- High-stakes cases where you want signals quickly
- Users expect real-time memory
- Cost is less of a concern

### Aggressive (More Cost Savings)

```python
should_trigger_batch_extraction(
    thread,
    char_threshold=1000,  # Higher threshold
    turn_threshold=10     # More turns
)
```

**Use when:**
- Maximizing cost savings
- Batch processing is acceptable
- Users don't need immediate signal extraction

### Default (Balanced)

```python
should_trigger_batch_extraction(
    thread,
    char_threshold=500,   # ~2-3 paragraphs
    turn_threshold=5      # ~5 exchanges
)
```

**Best for:**
- Most conversations
- Balance between cost and responsiveness
- Typical chat interactions

## Edge Cases Handled

### 1. First Message in Thread

```python
# No previous extraction
thread.last_extraction_at = None

# Message 1: 600 chars
thread.accumulate_for_extraction(600)
# chars=600, turns=1
# Threshold MET (chars >= 500)
# Extract immediately from first message
```

### 2. Very Short Messages

```python
# Messages: "ok", "sure", "thanks", "got it", "yes"
# Total: ~20 chars, 5 turns

# Threshold MET (turns >= 5)
# Batch extraction triggered
# LLM likely extracts ZERO signals (all trivial)
# Still better than 5 separate LLM calls!
```

### 3. One Long Message

```python
# Message 1: 2000 chars (detailed explanation)
# chars=2000, turns=1
# Threshold MET (chars >= 500)
# Extract from single message
```

### 4. Abandoned Threads

```python
# Messages 1-2 accumulated but never hit threshold
# No extraction = no cost
# If user never comes back, counters just sit there
# Clean up in periodic maintenance task (future)
```

## Configuration

### Environment Variables

```bash
# Optional: Override defaults in .env
SIGNAL_EXTRACTION_CHAR_THRESHOLD=500
SIGNAL_EXTRACTION_TURN_THRESHOLD=5
```

### Per-Thread Override

```python
# For high-priority threads, extract more frequently
if thread.case and thread.case.stakes == 'high':
    char_threshold = 300
    turn_threshold = 3
else:
    char_threshold = 500
    turn_threshold = 5
```

## Monitoring

### Logs to Watch

```python
# When threshold met and extraction triggered
logger.info("batch_signals_extracted", extra={
    "thread_id": str(thread.id),
    "messages_in_batch": 5,
    "signals_extracted": 12
})

# When threshold not yet met (debug level)
logger.debug("batch_threshold_not_met", extra={
    "thread_id": str(thread.id),
    "chars_accumulated": 350,
    "turns_accumulated": 3
})
```

### Metrics to Track

- **Batch size distribution**: How many messages per batch?
- **Signals per batch**: Are we extracting enough?
- **Cost savings**: Compare to per-message baseline
- **Threshold hit rate**: chars vs turns (which triggers more?)

## Database Migration

```bash
cd backend
./venv/bin/python manage.py migrate chat
```

Migration: `apps/chat/migrations/0003_add_extraction_batching.py`

## Testing

### Manual Test

```python
# Start a conversation
thread = ChatThread.objects.create(user=user)

# Send short messages
for i in range(4):
    msg = Message.objects.create(
        thread=thread,
        role=MessageRole.USER,
        content=f"Short message {i}"
    )
    thread.accumulate_for_extraction(len(msg.content))

print(thread.chars_since_extraction)  # ~60 chars
print(thread.turns_since_extraction)  # 4 turns

# Send 5th message (hits turn threshold)
msg5 = Message.objects.create(
    thread=thread,
    role=MessageRole.USER,
    content="Fifth message"
)
thread.accumulate_for_extraction(len(msg5.content))

# Threshold met!
print(thread.should_extract_signals())  # True

# Extract
signals = extract_signals_from_batch(thread, get_unprocessed_messages(thread))

# Counters reset
print(thread.chars_since_extraction)  # 0
print(thread.turns_since_extraction)  # 0
```

## Benefits Summary

✅ **60-70% cost reduction** (fewer LLM calls)
✅ **Better quality** (more context per call)
✅ **Lower latency** (amortized, async)
✅ **Simpler logic** (no per-message filtering)
✅ **Auto-tuning** (adjust thresholds as needed)

## Future Enhancements

### Priority-Based Batching

```python
# Extract immediately for high-priority messages
if is_high_priority(user_message):
    extract_now()
else:
    accumulate_and_batch()
```

### Adaptive Thresholds

```python
# Learn optimal thresholds per user/thread
thread.optimal_char_threshold = calculate_based_on_history()
```

### Smart Batch Sizing

```python
# Limit batch size to avoid huge LLM calls
if len(unprocessed_messages) > 10:
    # Extract in sub-batches of 5
    for batch in chunk(unprocessed_messages, size=5):
        extract_signals_from_batch(thread, batch)
```

## FAQ

**Q: What if I want immediate extraction for important messages?**

A: You can force extraction by checking message content:

```python
if 'critical' in user_message.content.lower():
    # Force immediate extraction
    extract_signals_from_batch(thread, [user_message])
    thread.reset_extraction_counters()
```

**Q: Do I still get real-time signal retrieval in chat?**

A: Yes! Retrieval pulls from existing signals. Extraction delay doesn't affect retrieval - you just get signals from the previous batch.

**Q: What happens to signals extracted in a batch?**

A: They're saved individually with event sourcing, just like before. The only difference is they're extracted together.

**Q: Can I disable batching and go back to per-message?**

A: Yes, set thresholds to 0:

```python
should_trigger_batch_extraction(thread, char_threshold=0, turn_threshold=1)
# Triggers on every message
```

## Files Modified

- `backend/apps/chat/models.py`: Added batching fields
- `backend/apps/signals/batch_extraction.py`: Batch extraction logic (NEW)
- `backend/apps/signals/prompts.py`: Added batch extraction prompt
- `backend/tasks/workflows.py`: Updated to use batching
- `backend/apps/chat/migrations/0003_add_extraction_batching.py`: Migration (NEW)
