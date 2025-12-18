from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence

from .state_store import is_step_completed, mark_step_completed

logger = logging.getLogger(__name__)


class Step(Protocol):
    """A single idempotent step."""

    step_id: str

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class PipelineResult:
    state: Dict[str, Any]
    ran_steps: List[str]
    skipped_steps: List[str]


def run_pipeline(
    *,
    state: Dict[str, Any],
    steps: Sequence[Step],
    start_at: Optional[str] = None,
    stop_after: Optional[str] = None,
    force: bool = False,
) -> PipelineResult:
    """Run steps in order with resume/idempotency semantics."""

    ran: List[str] = []
    skipped: List[str] = []

    started = start_at is None

    for step in steps:
        if not started:
            if step.step_id == start_at:
                started = True
            else:
                continue

        state.setdefault("execution", {})["current_step"] = step.step_id

        if (not force) and is_step_completed(state, step.step_id):
            logger.info("Skipping step %s (already completed)", step.step_id)
            skipped.append(step.step_id)
        else:
            logger.info("Running step %s", step.step_id)
            state = step.run(state)
            mark_step_completed(state, step.step_id)
            ran.append(step.step_id)

        if stop_after is not None and step.step_id == stop_after:
            logger.info("Stopping after %s", stop_after)
            break

    state.setdefault("execution", {})["current_step"] = None
    return PipelineResult(state=state, ran_steps=ran, skipped_steps=skipped)
