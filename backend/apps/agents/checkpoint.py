"""
Checkpointing & Resume — serialize research loop state to the event store.

After each phase boundary (plan, evaluate, compact), the loop emits a
checkpoint event. If the loop crashes, the latest checkpoint can be loaded
and the loop resumed from where it left off.

Round-trip is through to_dict() / from_dict() — reuses existing dataclass
serialization on ScoredFinding, SearchResult, and ResearchConfig.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchCheckpoint:
    """Serializable snapshot of the research loop's state at a phase boundary."""

    correlation_id: str
    question: str
    iteration: int
    phase: str  # "plan", "evaluate", "compact", "contrary", "synthesize"
    total_sources_found: int
    search_rounds: int
    timestamp: str = ""

    # Serialized state (dicts, not objects — survives JSON round-trip)
    plan_dict: dict = field(default_factory=dict)
    findings_dicts: list[dict] = field(default_factory=list)
    config_dict: dict = field(default_factory=dict)
    prompt_extension: str = ""
    context_dict: dict = field(default_factory=dict)

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "question": self.question,
            "iteration": self.iteration,
            "phase": self.phase,
            "total_sources_found": self.total_sources_found,
            "search_rounds": self.search_rounds,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
            "plan_dict": self.plan_dict,
            "findings_dicts": self.findings_dicts,
            "config_dict": self.config_dict,
            "prompt_extension": self.prompt_extension,
            "context_dict": self.context_dict,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResearchCheckpoint:
        return cls(
            correlation_id=data.get("correlation_id", ""),
            question=data.get("question", ""),
            iteration=data.get("iteration", 0),
            phase=data.get("phase", ""),
            total_sources_found=data.get("total_sources_found", 0),
            search_rounds=data.get("search_rounds", 0),
            timestamp=data.get("timestamp", ""),
            plan_dict=data.get("plan_dict", {}),
            findings_dicts=data.get("findings_dicts", []),
            config_dict=data.get("config_dict", {}),
            prompt_extension=data.get("prompt_extension", ""),
            context_dict=data.get("context_dict", {}),
        )


# ─── Persistence via Event Store ──────────────────────────────────────────


def save_checkpoint(checkpoint: ResearchCheckpoint) -> None:
    """Append an AGENT_CHECKPOINT event to the event store."""
    try:
        from apps.events.services import EventService
        from apps.events.models import ActorType

        EventService.append(
            event_type="AgentCheckpoint",
            payload=checkpoint.to_dict(),
            actor_type=ActorType.SYSTEM,
            correlation_id=checkpoint.correlation_id,
        )
        logger.info(
            "checkpoint_saved",
            extra={
                "correlation_id": checkpoint.correlation_id,
                "phase": checkpoint.phase,
                "iteration": checkpoint.iteration,
                "findings": len(checkpoint.findings_dicts),
            },
        )
    except Exception as e:
        # Checkpoint save is best-effort — never crash the loop
        logger.exception(
            "checkpoint_save_failed",
            extra={"correlation_id": checkpoint.correlation_id, "error": str(e)},
        )


def load_latest_checkpoint(correlation_id: str) -> Optional[ResearchCheckpoint]:
    """
    Load the most recent checkpoint for a correlation_id.

    Returns None if no checkpoint exists.
    """
    try:
        from apps.events.models import Event

        event = (
            Event.objects.filter(
                correlation_id=correlation_id,
                type="AgentCheckpoint",
            )
            .order_by("-timestamp")
            .first()
        )

        if not event:
            return None

        return ResearchCheckpoint.from_dict(event.payload)

    except Exception as e:
        logger.exception(
            "checkpoint_load_failed",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        return None
