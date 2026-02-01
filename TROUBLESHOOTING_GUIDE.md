# Troubleshooting Guide: Memory Integration

## Issues Found in Logs

### ✅ FIXED: ImportError for `get_signal_extractor`

**Error** (Line 825-831):
```
ImportError: cannot import name 'get_signal_extractor' from 'apps.signals.extractors'
```

**Fix**: Added alias `get_signal_extractor = get_extractor` to extractors.py

**Status**: Server will auto-reload with fix

---

### ⚠️ STILL NEEDS FIX: Database Migration

**Issue**: Columns `temperature`, `access_count`, `last_accessed`, `pinned_at` don't exist in DB yet

**Fix**: Run this migration:

```bash
cd backend
./venv/bin/python manage.py migrate signals
```

This will apply `0002_add_memory_tier_fields_sql.py` which uses raw SQL to add the columns.

---

### ⚠️ Streaming Not Working

**Issue** (Line 796):
```
WARNING: Not Acceptable: /api/chat/threads/.../messages/?stream=true
POST .../messages/?stream=true HTTP/1.1" 406
```

**Diagnosis**: Frontend is requesting streaming (`?stream=true`) but backend returns 406 Not Acceptable

**Possible causes**:
1. Streaming endpoint might not support the request format
2. Accept headers might be incorrect
3. The streaming logic might be disabled

**To investigate**: Check `apps/chat/views.py` line ~150-180 for streaming logic

---

### ⚠️ Frontend Polling Too Aggressively

**Issue** (Lines 784, 790, 805, 817, 820...):
```
GET /api/signals/?thread_id=... HTTP/1.1" 200 52
GET /api/signals/?thread_id=... HTTP/1.1" 200 52
GET /api/signals/?thread_id=... HTTP/1.1" 200 52
```

**Diagnosis**: Frontend is polling `/api/signals/` every ~3 seconds, even when nothing changes

**Impact**: 
- Unnecessary load on server
- Inefficient (200 requests/minute!)
- Returns empty results each time (`200 52` = empty JSON)

**Fix**: Update frontend to:
1. Only poll when expecting new signals (after sending message)
2. Use longer intervals (10-30 seconds instead of 3)
3. Stop polling after getting signals
4. Or better: Use WebSocket for real-time updates

---

## Current System State

### ✅ What's Working

- Chat messages are being saved (201 status)
- Assistant responses are being generated (OpenAI API call at line 824)
- Authentication is working (200 status after line 776)
- Signal retrieval endpoints are responding (200 status)
- Sentence transformer model loaded successfully (lines 798-812)

### ❌ What's Not Working

1. **Signal extraction**: Fails due to ImportError (now fixed, needs server restart)
2. **Database columns**: Need migration applied
3. **Streaming**: Not working, responses appearing all at once
4. **Frontend polling**: Too aggressive, needs throttling

---

## Next Steps

### 1. Apply Database Migration

```bash
cd backend
./venv/bin/python manage.py migrate signals
```

Expected output:
```
Running migrations:
  Applying signals.0002_add_memory_tier_fields_sql... OK
```

### 2. Restart Server

The ImportError fix should be auto-reloaded, but if not:
```bash
# Ctrl+C to stop server
python manage.py runserver
```

### 3. Test Signal Extraction

Send a message in the chat. You should see in logs:
```
INFO batch_signals_extracted
  thread_id: ...
  messages_in_batch: 1
  signals_extracted: 3
```

### 4. Fix Streaming (Optional)

If you want token-by-token streaming, investigate the streaming endpoint in `apps/chat/views.py`.

The 406 error suggests the streaming response format might not match what the frontend expects.

### 5. Fix Frontend Polling (Recommended)

Update the frontend to:
- Poll less frequently (every 30s instead of 3s)
- Stop polling when signals are retrieved
- Or use WebSocket for real-time updates

---

## Understanding the Logs

### Successful Chat Flow

```
POST /api/chat/threads/.../messages/ HTTP/1.1" 201 412
  └─ Message saved ✅

HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
  └─ LLM generated response ✅

ERROR batch_signal_extraction_failed (before fix)
  └─ Signal extraction failed ❌ (ImportError)

GET /api/chat/messages/?thread=... HTTP/1.1" 200 5484
  └─ Frontend polling for new messages ✅
```

### Polling Pattern

```
00:14:11 GET /api/signals/?thread_id=... HTTP/1.1" 200 52
00:14:14 GET /api/signals/?thread_id=... HTTP/1.1" 200 52  (+3s)
00:14:17 GET /api/signals/?thread_id=... HTTP/1.1" 200 52  (+3s)
00:14:20 GET /api/signals/?thread_id=... HTTP/1.1" 200 52  (+3s)
```

This is the frontend checking for new signals every 3 seconds. Since no signals exist yet (empty results), it keeps polling.

---

## Quick Health Check

After fixing and restarting:

1. **Check migrations**:
   ```bash
   ./venv/bin/python manage.py showmigrations signals
   ```
   Should show:
   ```
   [X] 0001_initial
   [X] 0002_add_memory_tier_fields_sql
   ```

2. **Send a test message** in chat

3. **Check logs** for:
   ```
   INFO batch_signals_extracted
   ```

4. **Verify columns exist**:
   ```bash
   ./venv/bin/python manage.py dbshell
   \d signals_signal
   # Should show temperature, access_count, last_accessed, pinned_at columns
   ```

---

## Summary

**Immediate action needed**:
1. ✅ ImportError fixed (auto-reload should pick it up)
2. ⏳ Run migration: `./venv/bin/python manage.py migrate signals`
3. 🔍 Investigate streaming if token-by-token responses are important
4. 🔍 Investigate frontend polling if performance is a concern

The core system is working - chat is functional, just needs the DB migration to enable signal extraction!
