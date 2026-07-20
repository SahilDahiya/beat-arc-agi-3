import asyncio
from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import uvicorn

from beat_arc_agi_3.observer import (
    build_session_view,
    build_transition_view,
    render_grid_svg,
    render_sse_update,
)
from beat_arc_agi_3.session import Session, SessionError


PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATE_ROOT = PACKAGE_ROOT / "observer_templates"
STATIC_ROOT = PACKAGE_ROOT / "observer_static"
templates = Jinja2Templates(directory=TEMPLATE_ROOT)


def _open_session(request: Request) -> Session:
    session_id = request.path_params["session_id"]
    try:
        return Session.open(
            sessions_root=request.app.state.sessions_root,
            session_id=session_id,
        )
    except (SessionError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _session_directories(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        raise RuntimeError(f"sessions root does not exist: {root}")
    return tuple(
        sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
    )


async def index(request: Request) -> Response:
    default_session_id = request.app.state.default_session_id
    if default_session_id is not None:
        return RedirectResponse(f"/sessions/{default_session_id}")
    sessions = tuple(
        build_session_view(
            Session.open(
                sessions_root=request.app.state.sessions_root,
                session_id=path.name,
            ),
            event_limit=1,
        )
        for path in _session_directories(request.app.state.sessions_root)
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {"sessions": sessions},
    )


def _artifact_context(session: Session) -> dict[str, str | None]:
    notes = session.workspace.read_text("notes.md")
    model_path = session.path / "world_model_v5.py"
    world_model = (
        model_path.read_text(encoding="utf-8") if model_path.is_file() else None
    )
    return {"notes": notes, "world_model": world_model}


async def session_page(request: Request) -> Response:
    session = _open_session(request)
    view = build_session_view(session)
    transition = build_transition_view(session)
    return templates.TemplateResponse(
        request,
        "session.html",
        {
            "session": view,
            "session_id": view.session_id,
            "selected": transition,
            **_artifact_context(session),
        },
    )


async def status_fragment(request: Request) -> Response:
    session = _open_session(request)
    return templates.TemplateResponse(
        request,
        "fragments/status.html",
        {"session": build_session_view(session, event_limit=1)},
    )


async def workspace_fragment(request: Request) -> Response:
    session = _open_session(request)
    raw_position = request.query_params.get("position")
    try:
        position = int(raw_position) if raw_position is not None else None
        selected = build_transition_view(session, position=position)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "fragments/workspace.html",
        {"session_id": session.metadata.session_id, "selected": selected},
    )


async def events_fragment(request: Request) -> Response:
    session = _open_session(request)
    return templates.TemplateResponse(
        request,
        "fragments/events.html",
        {"session": build_session_view(session)},
    )


async def artifacts_fragment(request: Request) -> Response:
    session = _open_session(request)
    return templates.TemplateResponse(
        request,
        "fragments/artifacts.html",
        {"session": build_session_view(session, event_limit=1), **_artifact_context(session)},
    )


def _selected_grid(session: Session, position: int, kind: str, tick: int | None):
    selected = build_transition_view(session, position=position)
    if tick is not None:
        if tick < 0 or tick >= len(selected.observation.ticks):
            raise ValueError(f"animation tick does not exist: {tick}")
        return selected.observation.ticks[tick], None
    if kind == "current":
        return selected.observation.grid, None
    if kind == "before":
        if selected.before is None:
            raise ValueError("initial observation has no before frame")
        return selected.before.grid, None
    if kind == "predicted":
        if selected.transition is None or selected.transition.prediction is None:
            raise ValueError("selected transition has no model prediction")
        return selected.transition.prediction.grid, None
    if kind == "difference":
        if selected.before is None:
            raise ValueError("initial observation has no difference frame")
        return selected.observation.grid, selected.before.grid
    raise ValueError(f"unknown frame kind: {kind}")


async def frame_svg(request: Request) -> Response:
    session = _open_session(request)
    try:
        position = int(request.path_params["position"])
        kind = request.query_params.get("kind", "current")
        raw_tick = request.query_params.get("tick")
        tick = int(raw_tick) if raw_tick is not None else None
        grid, changed_from = _selected_grid(session, position, kind, tick)
        svg = render_grid_svg(grid, changed_from=changed_from)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Timeline records are append-only, so the grids behind a given
    # (position, kind, tick) never change once written.
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


async def event_stream(request: Request) -> Response:
    session = _open_session(request)
    raw_seq = request.headers.get("last-event-id") or request.query_params.get("after")
    try:
        entries = session.events.entries()
        last_seq = entries[-1].seq if raw_seq is None and entries else int(raw_seq or 0)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid event sequence") from exc
    session_id = session.metadata.session_id
    sessions_root = request.app.state.sessions_root

    async def updates():
        nonlocal last_seq
        while not await request.is_disconnected():
            current = Session.open(
                sessions_root=sessions_root,
                session_id=session_id,
            )
            entries = current.events.entries()
            if entries and entries[-1].seq > last_seq:
                last_seq = entries[-1].seq
                yield render_sse_update(last_seq)
            await asyncio.sleep(0.5)

    return StreamingResponse(
        updates(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def create_observer_app(
    *,
    sessions_root: str | Path,
    default_session_id: str | None = None,
) -> Starlette:
    root = Path(sessions_root).resolve()
    app = Starlette(
        debug=False,
        routes=[
            Route("/", index),
            Route("/sessions/{session_id}", session_page),
            Route("/sessions/{session_id}/status", status_fragment),
            Route("/sessions/{session_id}/workspace", workspace_fragment),
            Route("/sessions/{session_id}/event-list", events_fragment),
            Route("/sessions/{session_id}/artifacts", artifacts_fragment),
            Route("/sessions/{session_id}/frames/{position:int}.svg", frame_svg),
            Route("/sessions/{session_id}/events", event_stream),
            Mount("/static", StaticFiles(directory=STATIC_ROOT), name="static"),
        ],
    )
    app.state.sessions_root = root
    app.state.default_session_id = default_session_id
    return app


def serve_observer(
    *,
    sessions_root: str | Path,
    session_id: str,
    host: str,
    port: int,
) -> None:
    app = create_observer_app(
        sessions_root=sessions_root,
        default_session_id=session_id,
    )
    uvicorn.run(app, host=host, port=port)
