import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.schemas import Coordinate
from beat_arc_agi_3.synthesis import BfsReport, SynthesisHarness


class ClickCandidate(BaseModel):
    """One candidate coordinate for modeled ACTION6 expansion."""

    model_config = ConfigDict(frozen=True)

    x: Coordinate
    y: Coordinate


class RunBfsQuery(BaseModel):
    """Canonical bounded model-space search request."""

    model_config = ConfigDict(frozen=True)

    target: Literal["is_goal", "level_up", "win"] = "is_goal"
    max_depth: int = Field(default=24, ge=0, le=200)
    node_budget: int = Field(default=100_000, ge=1, le=4_000_000)
    click_candidates: tuple[ClickCandidate, ...] = ()
    timeout_seconds: int = Field(default=60, ge=1, le=600)


def execute_run_bfs(
    harness: SynthesisHarness,
    query: RunBfsQuery,
) -> BfsReport:
    return harness.run_bfs(
        target=query.target,
        max_depth=query.max_depth,
        node_budget=query.node_budget,
        click_candidates=tuple(
            (candidate.x, candidate.y)
            for candidate in query.click_candidates
        ),
        timeout_seconds=query.timeout_seconds,
    )


def render_bfs_report(report: BfsReport) -> str:
    summary = (
        f"revision={report.revision[:12]} target={report.target} "
        f"expanded={report.expanded_nodes} "
        f"distinct={report.distinct_states}"
    )
    if report.status == "exhausted":
        return f"BFS EXHAUSTED {summary}; no plan found within the bounds."
    actions = json.dumps(
        [
            action.model_dump(mode="json", exclude_none=True)
            for action in report.actions
        ],
        separators=(",", ":"),
    )
    return (
        f"BFS FOUND {summary} depth={report.depth}; "
        f"commit-ready actions={actions}"
    )
