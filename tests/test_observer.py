import asyncio
from pathlib import Path

import httpx
from arcengine import FrameData, GameState

from beat_arc_agi_3.events import (
    ActionCompletedEvent,
    ActionStartedEvent,
    PredictionMismatchEvent,
    TurnStartedEvent,
)
from beat_arc_agi_3.observer import (
    build_session_view,
    render_grid_svg,
    render_sse_update,
)
from beat_arc_agi_3.observer_web import create_observer_app
from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.session import Session


def observation(
    grid: list[list[int]],
    *,
    levels_completed: int = 0,
) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[grid],
            state=GameState.NOT_FINISHED,
            levels_completed=levels_completed,
            win_levels=3,
            available_actions=[1, 2, 3, 4],
        )
    )


def observed_session(tmp_path: Path) -> Session:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="20260720T010203.000000Z-observer-test",
        game_id="test-game",
        model="test:model",
    )
    before = observation([[5, 5], [5, 5]])
    after = observation([[5, 8], [5, 5]])
    session.timeline.initialize(before)
    session.events.append(
        turn=1,
        event=TurnStartedEvent(
            summary="Turn 1 started",
            state=before.state,
            levels_completed=0,
            available_actions=before.legal_action_names,
        ),
    )
    action = ArcAction(action="ACTION1")
    session.events.append(
        turn=1,
        event=ActionStartedEvent(
            summary="Executing action 1",
            action_number=1,
            transition_index=0,
            action=action,
            model_revision="revision-1",
            prediction_mode="unchecked",
        ),
    )
    transition = session.timeline.append(
        action=action,
        after=after,
        model_revision="revision-1",
        prediction=None,
    )
    session.events.append(
        turn=1,
        event=ActionCompletedEvent(
            summary="Action 1 completed",
            action_number=1,
            transition_index=0,
            action=action,
            model_revision="revision-1",
            prediction_status="unchecked",
            state=after.state,
            levels_completed=0,
            level_up=False,
            dead=False,
            win=False,
        ),
    )
    session.events.append(
        turn=1,
        event=PredictionMismatchEvent(
            summary="Observed an informative counterexample",
            transition_index=transition.index,
            revision="revision-1",
        ),
    )
    return session


def test_session_view_projects_typed_discovery_and_transition_state(
    tmp_path: Path,
) -> None:
    session = observed_session(tmp_path)

    view = build_session_view(session)

    assert view.session_id == session.metadata.session_id
    assert view.status == "running"
    assert view.current_position == 1
    assert view.transition_count == 1
    assert view.current_observation.grid == ((5, 8), (5, 5))
    assert view.events[-1].phase == "learn"
    assert view.events[-1].tone == "warning"
    assert view.events[-1].seq == session.events.entries()[-1].seq


def test_grid_svg_uses_the_official_palette_and_crisp_cells() -> None:
    svg = render_grid_svg(((0, 8), (14, 15)))

    assert 'viewBox="0 0 2 2"' in svg
    assert 'shape-rendering="crispEdges"' in svg
    assert "#FFFFFF" in svg
    assert "#F93C31" in svg
    assert "#4FCC30" in svg
    assert "#A356D6" in svg


def test_sse_update_is_resumable_by_event_sequence() -> None:
    assert render_sse_update(42) == (
        "id: 42\n"
        "event: session-update\n"
        "data: 42\n\n"
    )


def test_observer_routes_render_session_workspace_and_svg(tmp_path: Path) -> None:
    session = observed_session(tmp_path)
    app = create_observer_app(sessions_root=tmp_path)

    async def request(path: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://observer.test",
        ) as client:
            return await client.get(path)

    index = asyncio.run(request("/"))
    page = asyncio.run(request(f"/sessions/{session.metadata.session_id}"))
    workspace = asyncio.run(
        request(
            f"/sessions/{session.metadata.session_id}/workspace?position=0"
        )
    )
    frame = asyncio.run(
        request(f"/sessions/{session.metadata.session_id}/frames/1.svg")
    )

    assert index.status_code == 200
    assert session.metadata.session_id in index.text
    assert page.status_code == 200
    assert "ARC Discovery" in page.text
    assert 'hx-ext="sse"' in page.text
    assert (
        f'sse-connect="/sessions/{session.metadata.session_id}/events"'
        in page.text
    )
    assert workspace.status_code == 200
    assert "Initial observation" in workspace.text
    assert frame.status_code == 200
    assert frame.headers["content-type"].startswith("image/svg+xml")
    assert 'viewBox="0 0 2 2"' in frame.text


def test_observer_has_no_mutating_http_routes(tmp_path: Path) -> None:
    session = observed_session(tmp_path)
    app = create_observer_app(sessions_root=tmp_path)

    async def post() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://observer.test",
        ) as client:
            return await client.post(
                f"/sessions/{session.metadata.session_id}"
            )

    response = asyncio.run(post())

    assert response.status_code == 405
