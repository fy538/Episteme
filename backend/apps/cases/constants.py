"""
Shared constants for the cases app.

Centralizes thresholds and limits that were previously hardcoded
across plan_service.py and brief_grounding.py.
"""

# ── Evidence Linker ──────────────────────────────────────────────────────

# Minimum chars of claim text to use for fuzzy matching
EVIDENCE_MATCH_PREFIX_LEN = 50

# Maximum evidence records to link per claim (prevents over-linking)
EVIDENCE_MATCH_LIMIT = 5

# Maximum chars of claim text to consider for evidence matching
EVIDENCE_CLAIM_TEXT_LIMIT = 100

# Minimum cosine similarity for embedding-based evidence matching
EVIDENCE_EMBEDDING_SIMILARITY_THRESHOLD = 0.75


# ── Evidence Extraction ──────────────────────────────────────────────────

# Minimum relevance score for a research finding to become an Evidence record
EVIDENCE_RELEVANCE_THRESHOLD = 0.6

# Maximum length for evidence text
EVIDENCE_TEXT_MAX_LEN = 2000


# ── Assumption Cascade ───────────────────────────────────────────────────

# Maximum depth for assumption → plan → grounding cascade
MAX_CASCADE_DEPTH = 3
