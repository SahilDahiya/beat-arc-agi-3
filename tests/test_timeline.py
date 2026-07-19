import json
from pathlib import Path

import pytest
from arcengine import FrameData, GameState

from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.timeline import (
    JsonlTimeline,
    ModelPredictionRecord,
    TimelineChainError,
    TimelineCorruptionError,
    TimelineNotFoundError,
)


def observation(
    value: int,
    *,
    game_id: str = "test-game",
    state: GameState = GameState.NOT_FINISHED,
    levels_completed: int = 0,
) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id=game_id,
            frame=[[[value]]],
            state=state,
            levels_completed=levels_completed,
            win_levels=2,
            available_actions=[1, 6],
        )
    )


def action(name: str = "ACTION1") -> ArcAction:
    if name == "ACTION6":
        return ArcAction(action="ACTION6", x=4, y=5)
    return ArcAction(action="ACTION1")


def prediction(
    value: int,
    *,
    level_up: bool = False,
    dead: bool = False,
    win: bool = False,
) -> ModelPredictionRecord:
    return ModelPredictionRecord(
        grid=((value,),),
        level_up=level_up,
        dead=dead,
        win=win,
    )


def test_timeline_records_exact_and_mismatched_model_predictions(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))

    exact = timeline.append(
        action=action(),
        after=observation(1),
        model_revision="abc123",
        prediction=prediction(1),
    )
    mismatch = timeline.append(
        action=action(),
        after=observation(3),
        model_revision="abc123",
        prediction=prediction(2),
    )

    assert exact.prediction_status == "exact"
    assert mismatch.prediction_status == "mismatch"
    reopened = JsonlTimeline(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    assert reopened.transitions()[1].model_revision == "abc123"


def test_timeline_records_an_explicitly_unchecked_action(tmp_path: Path) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))

    transition = timeline.append(
        action=action(),
        after=observation(7),
        model_revision="dirty-revision",
        prediction=None,
    )

    assert transition.model_revision == "dirty-revision"
    assert transition.prediction is None
    assert transition.prediction_status == "unchecked"
    assert JsonlTimeline(
        tmp_path / "timeline.jsonl", game_id="test-game"
    ).transitions() == (transition,)


def test_timeline_persists_initial_observation_and_linear_transitions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "timeline.jsonl"
    timeline = JsonlTimeline.create(path, game_id="test-game")
    start = observation(0)
    timeline.initialize(start)

    first = timeline.append(
        action=action(),
        after=observation(1, levels_completed=1),
        model_revision="abc123",
        prediction=prediction(1, level_up=True),
    )
    second = timeline.append(
        action=action("ACTION6"),
        after=observation(2, state=GameState.WIN, levels_completed=1),
        model_revision="abc123",
        prediction=prediction(2, win=True),
    )

    assert first.index == 0
    assert first.before == start
    assert first.level_up is True
    assert first.dead is False
    assert first.win is False
    assert second.index == 1
    assert second.before == first.after
    assert second.win is True
    assert JsonlTimeline(path, game_id="test-game").transitions() == (
        first,
        second,
    )

    persisted = path.read_text(encoding="utf-8").splitlines()
    assert len(persisted) == 3
    assert json.loads(persisted[0])["type"] == "initial_observation"
    assert all("before" not in line for line in persisted)


def test_timeline_open_fails_when_the_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(TimelineNotFoundError, match="does not exist"):
        JsonlTimeline(tmp_path / "missing.jsonl", game_id="test-game")


def test_timeline_requires_initial_observation_before_append(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl", game_id="test-game"
    )

    with pytest.raises(TimelineChainError, match="initial observation"):
        timeline.append(
            action=action(),
            after=observation(1),
            model_revision="abc123",
            prediction=prediction(1),
        )


def test_timeline_rejects_reinitialization_without_writing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "timeline.jsonl"
    timeline = JsonlTimeline.create(path, game_id="test-game")
    timeline.initialize(observation(0))
    original = path.read_bytes()

    with pytest.raises(TimelineChainError, match="already initialized"):
        timeline.initialize(observation(1))

    assert path.read_bytes() == original


def test_timeline_derives_death_from_the_result_observation(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl", game_id="test-game"
    )
    timeline.initialize(observation(0))

    transition = timeline.append(
        action=action(),
        after=observation(1, state=GameState.GAME_OVER),
        model_revision="abc123",
        prediction=prediction(1, dead=True),
    )

    assert transition.dead is True
    assert transition.win is False


def test_timeline_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "timeline.jsonl"
    path.write_text('{"type": "initial_observation"\n', encoding="utf-8")

    with pytest.raises(TimelineCorruptionError, match="line 1"):
        JsonlTimeline(path, game_id="test-game")


def test_timeline_rejects_a_corrupt_persisted_index(tmp_path: Path) -> None:
    path = tmp_path / "timeline.jsonl"
    timeline = JsonlTimeline.create(path, game_id="test-game")
    timeline.initialize(observation(0))
    timeline.append(
        action=action(),
        after=observation(1),
        model_revision="abc123",
        prediction=prediction(1),
    )
    corrupt = {
        "type": "action_result",
        "index": 9,
        "action": action().model_dump(mode="json"),
        "after": observation(2).model_dump(mode="json"),
        "model_revision": "abc123",
        "prediction": prediction(2).model_dump(mode="json"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{json.dumps(corrupt)}\n")

    with pytest.raises(TimelineCorruptionError, match="index 9"):
        JsonlTimeline(path, game_id="test-game")


def test_timeline_rejects_an_observation_from_another_game_without_writing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "timeline.jsonl"
    timeline = JsonlTimeline.create(path, game_id="test-game")

    with pytest.raises(TimelineChainError, match="session game"):
        timeline.initialize(observation(0, game_id="other-game"))

    assert path.read_text(encoding="utf-8") == ""


def test_timeline_append_does_not_reload_persisted_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl", game_id="test-game"
    )
    timeline.initialize(observation(0))
    monkeypatch.setattr(
        timeline,
        "_load",
        lambda: (_ for _ in ()).throw(AssertionError("history was reloaded")),
    )

    transition = timeline.append(
        action=action(),
        after=observation(1),
        model_revision="abc123",
        prediction=prediction(1),
    )

    assert transition.index == 0
