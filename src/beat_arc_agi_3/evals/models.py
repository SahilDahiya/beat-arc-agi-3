from pydantic import BaseModel, ConfigDict, Field


class StageEvalInput(BaseModel):
    """One persisted Session and the observable progress target to score."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    target_levels_completed: int = Field(ge=1)


class StageEvidenceExpectation(BaseModel):
    """Exact deterministic facts expected from one persisted Session."""

    model_config = ConfigDict(frozen=True)

    target_reached: bool
    initial_levels_completed: int = Field(ge=0)
    final_levels_completed: int = Field(ge=0)
    target_transition_index: int | None = Field(default=None, ge=0)
    actions_to_target: int | None = Field(default=None, ge=1)
    turns_to_target: int | None = Field(default=None, ge=1)
    prediction_exact: int = Field(ge=0)
    prediction_mismatch: int = Field(ge=0)
    prediction_unchecked: int = Field(ge=0)
    tool_counts: dict[str, int]
    target_action_event_found: bool
    target_snapshot_found: bool
    target_snapshot_path: str | None = None
    failure_before_target: bool
    post_target_run_failure: str | None = None


class StageEvalMetadata(BaseModel):
    """Versioned provenance and expected evidence for one regression case."""

    model_config = ConfigDict(frozen=True)

    provenance: str = Field(min_length=1)
    expected: StageEvidenceExpectation


class StageEvalOutcome(BaseModel):
    """Stage-scoped facts extracted from one validated Session."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    game_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    target_levels_completed: int = Field(ge=1)
    target_reached: bool
    initial_levels_completed: int = Field(ge=0)
    final_levels_completed: int = Field(ge=0)
    target_transition_index: int | None = Field(default=None, ge=0)
    actions_to_target: int | None = Field(default=None, ge=1)
    turns_to_target: int | None = Field(default=None, ge=1)
    duration_to_target_seconds: float | None = Field(default=None, ge=0)
    prediction_exact: int = Field(ge=0)
    prediction_mismatch: int = Field(ge=0)
    prediction_unchecked: int = Field(ge=0)
    tool_counts: dict[str, int]
    target_action_event_found: bool
    target_snapshot_found: bool
    target_snapshot_path: str | None = None
    failure_before_target: bool
    post_target_run_failure: str | None = None

    @property
    def stage_evidence_complete(self) -> bool:
        return (
            self.target_reached
            and self.target_action_event_found
            and self.target_snapshot_found
        )

    @property
    def prediction_accuracy(self) -> float | None:
        checked = self.prediction_exact + self.prediction_mismatch
        if checked == 0:
            return None
        return self.prediction_exact / checked
