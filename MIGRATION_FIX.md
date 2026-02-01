# Migration Fix Instructions

## The Problem

The `signals_signal` table exists in your database but Django has no migration record of it. This happened because it was created with `--run-syncdb` or outside of migrations.

## The Solution

Run these commands in order:

### Step 1: Fake the initial migration

```bash
cd backend
./venv/bin/python manage.py migrate signals --fake-initial
```

This tells Django: "The Signal table already exists, just record it in migration history"

### Step 2: Create the new fields migration

```bash
./venv/bin/python manage.py makemigrations signals -n add_memory_tier_fields
```

This creates a migration to add the new fields (temperature, access_count, last_accessed, pinned_at)

### Step 3: Apply the new migration

```bash
./venv/bin/python manage.py migrate signals
```

This actually adds the new columns to the existing table

## Verify

```bash
./venv/bin/python manage.py showmigrations signals
```

You should see:
```
signals
 [X] 0001_initial
 [X] 0002_add_memory_tier_fields
```

## Then Start the Server

```bash
python manage.py runserver
```

All migrations should be applied!
