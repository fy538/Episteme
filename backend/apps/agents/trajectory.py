"""
Trajectory Capture — structured decision recording for prompt improvement.

Captures what the research loop *decided* at each step, not just timing.
One AGENT_TRAJECTORY event per workflow (not per step), stored as a single
JSON blob in the event store. Optionally pushed to Langfuse as a trace.

Opt-in: pass ``trajectory_recorder=TrajectoryRecorder()`` to ResearchLoop.
When ``None`` (default), zero overhead.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Maximum characters to store for any single prompt/output in a trajectory event
MAX_PROMPT_CHARS = 2000


@dataclass
class TrajectoryEvent:
    """A single decision point in the research loop."""

    step_name: str  # e.g. "plan", "search", "extract", "evaluate", "completeness", "synthesize"
    input_summary: str = ""
    output_summary: str = ""
    decision_rationale: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Truncate long fields for storage
        d["input_summary"] = d["input_summary"][:MAX_PROMPT_CHARS]
        d["output_summary"] = d["output_summary"][:MAX_PROMPT_CHARS]
        d["decision_rationale"] = d["decision_rationale"][:MAX_PROMPT_CHARS]
        return d


class TrajectoryRecorder:
    """
    Records structured decision trajectories during a research loop run.

    Usage:
        recorder = TrajectoryRecorder(correlation_id="abc-123")
        recorder.record(TrajectoryEvent(step_name="plan", ...))
        # After loop completes:
        recorder.save_to_events()
    """

    def __init__(
        self,
        correlation_id: str = "",
        max_prompt_chars: int = MAX_PROMPT_CHARS,
    ):
        self.correlation_id = correlation_id
        self.max_prompt_chars = max_prompt_chars
        self._events: list[TrajectoryEvent] = []
        self._start_time = time.time()

    def record(self, event: TrajectoryEvent) -> None:
        """Append a trajectory event."""
        if not event.timestamp:
            event.timestamp = datetime.now(timezone.utc).isoformat()
        self._events.append(event)

    def record_step(
        self,
        step_name: str,
        input_summary: str = "",
        output_summary: str = "",
        decision_rationale: str = "",
        metrics: dict[str, Any] | None = None,
        duration_ms: int = 0,
    ) -> None:
        """Convenience: record a step without constructing TrajectoryEvent manually."""
        self.record(TrajectoryEvent(
            step_name=step_name,
            input_summary=input_summary[:self.max_prompt_chars],
            output_summary=output_summary[:self.max_prompt_chars],
            decision_rationale=decision_rationale[:self.max_prompt_chars],
            metrics=metrics or {},
            duration_ms=duration_ms,
        ))

    def finalize(self) -> dict[str, Any]:
        """
        Build the full trajectory dict for storage.

        Returns a single JSON-serializable dict containing all events
        and summary metadata.
        """
        elapsed_ms = int((time.time() - self._start_time) * 1000)
        return {
            "correlation_id": self.correlation_id,
            "total_steps": len(self._events),
            "total_duration_ms": elapsed_ms,
            "events": [e.to_dict() for e in self._events],
            "finalized_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_to_events(self, case_id: str | None = None) -> None:
        """
        Persist the trajectory as a single AGENT_TRAJECTORY event.

        One event per workflow — keeps the event store clean.
        """
        try:
            from apps.events.services import EventService
            from apps.events.models import ActorType

            payload = self.finalize()

            EventService.append(
                event_type="AGENT_TRAJECTORY",
                payload=payload,
                actor_type=ActorType.SYSTEM,
                correlation_id=self.correlation_id,
                case_id=case_id,
            )
            logger.info(
                "trajectory_saved",
                extra={
                    "correlation_id": self.correlation_id,
                    "steps": len(self._events),
                },
            )
        except Exception as e:
            # Trajectory save is best-effort
            logger.exception(
                "trajectory_save_failed",
                extra={"correlation_id": self.correlation_id, "error": str(e)},
            )

    def push_to_langfuse(self, trace_id: str) -> None:
        """
        Optionally push trajectory data to Langfuse as a generation.

        Best-effort — silently fails if Langfuse is not configured.
        """
        try:
            import os

            if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
                return

            from langfuse import Langfuse

            lf = Langfuse()
            payload = self.finalize()

            lf.generation(
                trace_id=trace_id,
                name="research_trajectory",
                input={"total_steps": payload["total_steps"]},
                output=payload,
                metadata={
                    "correlation_id": self.correlation_id,
                    "total_duration_ms": payload["total_duration_ms"],
                },
            )
        except ImportError:
            pass
        except Exception:
            pass  # Langfuse push is best-effort

    @property
    def events(self) -> list[TrajectoryEvent]:
        """Read-only access to recorded events."""
        return list(self._events)
