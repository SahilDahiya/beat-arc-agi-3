from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.grid_analysis import render_grid_change_summary
from beat_arc_agi_3.synthesis import BacktestReport, SynthesisHarness


class RunBacktestQuery(BaseModel):
    """Canonical finite-replay request for the installed world model."""

    model_config = ConfigDict(frozen=True)

    max_details: int = Field(default=1, ge=0, le=100)


def execute_run_backtest(
    harness: SynthesisHarness,
    query: RunBacktestQuery,
) -> str:
    return render_backtest_report(
        harness.run_backtest(max_details=query.max_details)
    )


def render_backtest_report(report: BacktestReport) -> str:
    revision = report.revision[:12]
    if report.status == "green":
        return (
            f"BACKTEST GREEN revision={revision}; "
            f"exact={report.exact_transitions}/"
            f"{report.timeline_transitions}. The current revision is "
            "historically consistent and may be committed or searched."
        )

    mismatch = report.mismatch
    assert mismatch is not None
    lines = [
        f"BACKTEST MISMATCH revision={revision}; "
        f"exact={report.exact_transitions}/"
        f"{report.timeline_transitions}",
        f"earliest transition={mismatch.transition_index} "
        f"action={mismatch.action.action} "
        f"differing_cells={mismatch.differing_cells}",
        "predicted flags=" + mismatch.predicted_flags.model_dump_json(),
        "actual flags=" + mismatch.actual_flags.model_dump_json(),
        "prediction-vs-actual structure: "
        + render_grid_change_summary(mismatch.difference_summary),
        "observed before-vs-after structure: "
        + render_grid_change_summary(mismatch.actual_transition_summary),
    ]
    if mismatch.differences:
        lines.append("first cell differences:")
        lines.extend(
            f"  ({item.row},{item.column}) predicted={item.predicted} "
            f"actual={item.actual}"
            for item in mismatch.differences
        )
    return "\n".join(lines)
