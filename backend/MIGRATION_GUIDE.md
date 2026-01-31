# Migration Guide: Signals to Inquiries

## Quick Start

**1. Review the changes:**
- Read `INQUIRIES_IMPLEMENTATION.md` for full details
- Key change: Signals no longer have status (suggested/confirmed/rejected)
- New: Inquiries system for elevated signals

**2. Create migrations:**
```bash
cd backend
python manage.py makemigrations signals
python manage.py makemigrations inquiries
```

**3. Review migration files:**
The migrations will:
- Remove `status` field from Signal model
- Remove `RejectedSignalFingerprint` table (if exists)
- Add `dismissed_at` timestamp to Signal
- Add `inquiry` FK to Signal
- Create new `Inquiry` table

**4. Run migrations:**
```bash
python manage.py migrate signals
python manage.py migrate inquiries
```

**5. Update any existing code:**
- Remove references to `signal.status`
- Replace `signal.confirm()` / `signal.reject()` calls with `signal.dismiss()`
- Use new inquiry endpoints

## Breaking Changes

### Removed from Signal Model
- `status` field
- `SignalStatus` choices
- `RejectedSignalFingerprint` model

### Removed API Endpoints
- `POST /api/signals/{id}/confirm/`
- `POST /api/signals/{id}/reject/`

### New API Endpoints
- `POST /api/signals/{id}/dismiss/`
- `POST /api/signals/{id}/undismiss/`
- `POST /api/signals/{id}/promote_to_inquiry/`
- `GET /api/signals/promotion_suggestions/?case_id=uuid`
- All inquiry CRUD endpoints: `/api/inquiries/`

## Testing After Migration

**1. Test signal extraction still works:**
```bash
# Existing chat functionality should work unchanged
# Signals should be created without status field
```

**2. Test dismissing signals:**
```bash
curl -X POST http://localhost:8000/api/signals/{signal-id}/dismiss/
# Signal should have dismissed_at timestamp
```

**3. Test promotion to inquiry:**
```bash
curl -X POST http://localhost:8000/api/signals/{signal-id}/promote_to_inquiry/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Test inquiry"}'
# Should create inquiry and link signal
```

**4. Run tests:**
```bash
python manage.py test apps.inquiries
python manage.py test apps.signals
```

## Rollback Plan

If you need to rollback:

**1. Revert code changes:**
```bash
git checkout main  # or your previous branch
```

**2. Rollback migrations:**
```bash
python manage.py migrate signals <previous_migration_name>
python manage.py migrate inquiries zero  # Remove all inquiry migrations
```

**3. Remove inquiries app:**
```bash
# Remove from INSTALLED_APPS in settings
rm -rf apps/inquiries
```

## Data Migration Notes

**Existing signals:**
- All existing signals will remain unchanged
- No `status` field means they'll be treated as "active" based on timestamp/confidence
- No data loss

**If you had rejected signals:**
- These will no longer be marked as rejected
- Consider running a one-time script to mark them as dismissed instead
- Or just leave them - they'll age out naturally

## Next Steps After Migration

**1. Frontend Integration:**
- Update signal display to show `dismissed_at` instead of `status`
- Add "Promote to Inquiry" button
- Build inquiry detail view
- Show promotion suggestions

**2. Test Auto-Promotion:**
- Create signals that repeat 3+ times
- Check promotion suggestions endpoint
- Verify similar signals link to same inquiry

**3. Monitor:**
- Check inquiry creation rate
- Verify promotion thresholds work well
- Adjust as needed

## Support

If you encounter issues:
1. Check `INQUIRIES_IMPLEMENTATION.md` for detailed docs
2. Review migration files for unexpected changes
3. Check Django admin for data integrity
4. Run tests to verify behavior

---

**Ready to migrate?**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
```
