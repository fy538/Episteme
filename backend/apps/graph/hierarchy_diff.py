"""
Hierarchy diff computation — compare two hierarchy versions to detect
what changed: new themes, merged themes, expanded topics, new documents.

Used by Plan 6 (Document-Aware Hierarchy Refresh + Change Detection) to
give users visibility into how their knowledge base evolves as new
documents are added.
"""
import logging
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from typing import List, Set

logger = logging.getLogger(__name__)


@dataclass
class HierarchyDiff:
    """Summary of changes between two hierarchy versions."""

    # Theme-level changes
    new_themes: List[dict] = field(default_factory=list)
    removed_themes: List[dict] = field(default_factory=list)
    merged_themes: List[dict] = field(default_factory=list)
    expanded_themes: List[dict] = field(default_factory=list)

    # Document-level changes
    new_documents: List[dict] = field(default_factory=list)
    removed_documents: List[dict] = field(default_factory=list)

    # Summary stats
    chunks_added: int = 0
    chunks_removed: int = 0
    themes_before: int = 0
    themes_after: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_themes or self.removed_themes or self.merged_themes
            or self.expanded_themes or self.new_documents or self.removed_documents
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def summary_text(self) -> str:
        """Human-readable summary for the project dashboard."""
        parts = []
        if self.new_themes:
            labels = [t['label'] for t in self.new_themes[:3]]
            parts.append(f"{len(self.new_themes)} new theme(s): {', '.join(labels)}")
        if self.merged_themes:
            parts.append(f"{len(self.merged_themes)} theme(s) merged")
        if self.expanded_themes:
            labels = [t['label'] for t in self.expanded_themes[:3]]
            parts.append(f"{len(self.expanded_themes)} theme(s) expanded: {', '.join(labels)}")
        if self.new_documents:
            titles = [d['document_title'] for d in self.new_documents[:3]]
            parts.append(f"{len(self.new_documents)} new document(s): {', '.join(titles)}")
        if self.removed_documents:
            parts.append(f"{len(self.removed_documents)} document(s) removed")
        if not parts:
            return "No significant changes"
        return "; ".join(parts)


def compute_hierarchy_diff(old_hierarchy, new_hierarchy) -> HierarchyDiff:
    """Compare two ClusterHierarchy instances and return a diff.

    Uses theme/topic label similarity (fuzzy matching) to detect
    renames, merges, and expansions rather than relying on cluster IDs
    (which change every rebuild).

    Args:
        old_hierarchy: Previous ClusterHierarchy instance (or None for first build).
        new_hierarchy: Newly built ClusterHierarchy instance.

    Returns:
        HierarchyDiff with all detected changes.
    """
    diff = HierarchyDiff()

    old_tree = (old_hierarchy.tree if old_hierarchy else {}) or {}
    new_tree = (new_hierarchy.tree if new_hierarchy else {}) or {}
    old_meta = (old_hierarchy.metadata if old_hierarchy else {}) or {}
    new_meta = (new_hierarchy.metadata if new_hierarchy else {}) or {}

    # --- Document diff ---
    old_docs_list = old_meta.get('document_manifest', [])
    new_docs_list = new_meta.get('document_manifest', [])
    old_docs = {d['document_id'] for d in old_docs_list}
    new_docs = {d['document_id'] for d in new_docs_list}

    diff.new_documents = [d for d in new_docs_list if d['document_id'] not in old_docs]
    diff.removed_documents = [d for d in old_docs_list if d['document_id'] not in new_docs]

    # --- Chunk counts ---
    old_chunks = old_meta.get('total_chunks', 0)
    new_chunks = new_meta.get('total_chunks', 0)
    diff.chunks_added = max(0, new_chunks - old_chunks)
    diff.chunks_removed = max(0, old_chunks - new_chunks)

    # --- Theme diff (Level 2 nodes = root's direct children) ---
    old_themes = old_tree.get('children', [])
    new_themes = new_tree.get('children', [])
    diff.themes_before = len(old_themes)
    diff.themes_after = len(new_themes)

    # Match themes by label similarity using global best-first assignment.
    # Compute all pairwise scores, then greedily assign the highest-scoring
    # pair first. This prevents a low-scoring early match from "stealing"
    # a partner that a later theme would match much better.
    matched_old: Set[int] = set()
    matched_new: Set[int] = set()

    scored_pairs = []
    for i, new_theme in enumerate(new_themes):
        for j, old_theme in enumerate(old_themes):
            score = _label_similarity(
                new_theme.get('label', ''),
                old_theme.get('label', ''),
            )
            if score >= 0.5:
                scored_pairs.append((score, i, j))

    # Sort by score descending — assign best matches first
    scored_pairs.sort(key=lambda x: x[0], reverse=True)

    for score, i, j in scored_pairs:
        if i in matched_new or j in matched_old:
            continue
        matched_old.add(j)
        matched_new.add(i)

        new_theme = new_themes[i]
        old_theme = old_themes[j]
        old_count = old_theme.get('chunk_count', 0)
        new_count = new_theme.get('chunk_count', 0)
        chunk_growth = new_count - old_count
        # Theme is "expanded" if it grew by ≥30% of its original size
        if chunk_growth > 0 and old_count > 0 and chunk_growth >= old_count * 0.3:
            diff.expanded_themes.append({
                'label': new_theme.get('label', ''),
                'old_chunk_count': old_count,
                'new_chunk_count': new_count,
                'growth': chunk_growth,
            })

    # Unmatched new themes = genuinely new
    for i, theme in enumerate(new_themes):
        if i not in matched_new:
            diff.new_themes.append({
                'label': theme.get('label', ''),
                'summary': theme.get('summary', ''),
                'chunk_count': theme.get('chunk_count', 0),
            })

    # Unmatched old themes — check if they were merged into new themes
    for j, old_theme in enumerate(old_themes):
        if j not in matched_old:
            # Check if old theme's chunks appear in any new theme (merge detection)
            old_chunk_set = set(old_theme.get('chunk_ids', []))
            merged_into = None

            if old_chunk_set:
                for new_theme in new_themes:
                    new_chunk_set = set(new_theme.get('chunk_ids', []))
                    overlap = len(old_chunk_set & new_chunk_set)
                    if overlap >= len(old_chunk_set) * 0.5:
                        merged_into = new_theme.get('label', '')
                        break

            if merged_into:
                diff.merged_themes.append({
                    'old_label': old_theme.get('label', ''),
                    'merged_into': merged_into,
                })
            else:
                diff.removed_themes.append({
                    'label': old_theme.get('label', ''),
                    'chunk_count': old_theme.get('chunk_count', 0),
                })

    return diff


def _label_similarity(a: str, b: str) -> float:
    """Fuzzy label similarity using SequenceMatcher.

    Returns a ratio between 0.0 and 1.0. A threshold of 0.5 is used
    in compute_hierarchy_diff to consider two labels as "the same theme".
    """
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
