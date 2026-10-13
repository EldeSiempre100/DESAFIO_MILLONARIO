from __future__ import annotations

import asyncio
import io
import os
import threading
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Literal

import segno
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from millonario_v3.participation.models import AVATAR_CATALOG, SubmissionStatus
from millonario_v3.participation.room import RoomError
from millonario_v3.session import SessionState

from . import REPOSITORY_ROOT
from .auth import AdminSessions
from .registry import (
    LIFELINE_DURATION_MS,
    QUALIFIER_DURATION_MS,
    QUESTION_DURATION_MS,
    OnlineRoom,
    RoomRegistry,
)


ONLINE_ROOT = REPOSITORY_ROOT / "online"
STATIC_ROOT = ONLINE_ROOT / "static"
V3_ASSET_ROOT = REPOSITORY_ROOT / "v3_1" / "assets"
COOKIE_NAME = "desafio_session"


def _configured_capacity() -> int:
    try:
        return max(2, min(30, int(os.environ.get("MAX_PARTICIPANTS", "30"))))
    except ValueError:
        return 30


environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
if environment == "production" and not admin_password:
    raise RuntimeError("ADMIN_PASSWORD es obligatorio en producción.")
sessions = AdminSessions(admin_password or "desafio")
registry = RoomRegistry(
    REPOSITORY_ROOT / "v3_1" / "projects" / "demo.juego",
    max_participants=_configured_capacity(),
)


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class CreateGameBody(BaseModel):
    bank_id: str = Field(default="main", min_length=1, max_length=80)


class JoinBody(BaseModel):
    alias: str = Field(min_length=2, max_length=24)
    device_id: str = Field(min_length=8, max_length=120)
    avatar: str = Field(default="explorer", min_length=2, max_length=30)


class ReconnectBody(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class PlayerSelectionBody(BaseModel):
    participant_ids: list[str] = Field(min_length=2, max_length=2)


class GameSettingsBody(BaseModel):
    questions_per_round: Literal[1, 3, 5] = 5


class OpenQuestionBody(BaseModel):
    duration_seconds: int = Field(default=45, ge=5, le=120)


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[key]
            while attempts and now - attempts[0] > window_seconds:
                attempts.popleft()
            if len(attempts) >= limit:
                return False
            attempts.append(now)
            return True


class PlayerHub:
    def __init__(self) -> None:
        self._connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def connect(self, room_code: str, participant_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            previous = self._connections[room_code].get(participant_id)
            self._connections[room_code][participant_id] = websocket
        if previous is not None and previous is not websocket:
            try:
                await previous.close(code=4001, reason="Conexión reemplazada")
            except RuntimeError:
                pass

    async def disconnect(self, room_code: str, participant_id: str, websocket: WebSocket) -> bool:
        async with self._lock:
            connections = self._connections.get(room_code, {})
            if connections.get(participant_id) is not websocket:
                return False
            connections.pop(participant_id, None)
            if not connections:
                self._connections.pop(room_code, None)
            return True

    async def broadcast(
        self,
        room_code: str,
        message: dict[str, Any],
        participant_ids: set[str] | None = None,
    ) -> None:
        async with self._lock:
            connections = list(self._connections.get(room_code, {}).items())
        stale: list[tuple[str, WebSocket]] = []
        for participant_id, websocket in connections:
            if participant_ids is not None and participant_id not in participant_ids:
                continue
            try:
                await websocket.send_json(message)
            except (RuntimeError, OSError):
                stale.append((participant_id, websocket))
        for participant_id, websocket in stale:
            await self.disconnect(room_code, participant_id, websocket)

    async def broadcast_snapshots(self, room: OnlineRoom) -> None:
        async with self._lock:
            connections = list(self._connections.get(room.room_code, {}).items())
        stale: list[tuple[str, WebSocket]] = []
        for participant_id, websocket in connections:
            try:
                await websocket.send_json(
                    event("room.snapshot", room.player_snapshot(participant_id))
                )
            except (RuntimeError, OSError):
                stale.append((participant_id, websocket))
        for participant_id, websocket in stale:
            await self.disconnect(room.room_code, participant_id, websocket)


class PhaseTimers:
    def __init__(self) -> None:
        self._tasks: dict[tuple[str, str], asyncio.Task[None]] = {}

    def schedule(
        self,
        room_code: str,
        name: str,
        duration_ms: int,
        callback: Callable[[], Awaitable[None]],
    ) -> None:
        self.cancel(room_code, name)

        async def runner() -> None:
            try:
                await asyncio.sleep(max(0, duration_ms) / 1000)
                await callback()
            except asyncio.CancelledError:
                return
            finally:
                current = self._tasks.get((room_code, name))
                if current is asyncio.current_task():
                    self._tasks.pop((room_code, name), None)

        self._tasks[(room_code, name)] = asyncio.create_task(runner())

    def cancel(self, room_code: str, name: str) -> None:
        task = self._tasks.pop((room_code, name), None)
        if task is not None and not task.done():
            task.cancel()

    def cancel_room(self, room_code: str) -> None:
        for code, name in list(self._tasks):
            if code == room_code:
                self.cancel(code, name)


limiter = SlidingWindowLimiter()
hub = PlayerHub()
timers = PhaseTimers()
app = FastAPI(
    title="Desafío Millonario",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/assets", StaticFiles(directory=STATIC_ROOT), name="assets")
app.mount("/media", StaticFiles(directory=V3_ASSET_ROOT), name="media")


def event(event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": event_type, "payload": payload or {}}


def room_error(error: RoomError) -> HTTPException:
    status = {
        "not_found": 404,
        "bank_not_found": 404,
        "invalid_token": 401,
        "room_full": 409,
        "room_locked": 409,
        "alias_taken": 409,
        "not_enough_participants": 409,
        "invalid_state": 409,
        "invalid_selection": 422,
        "invalid_lifeline": 422,
        "invalid_bank": 422,
        "no_question": 409,
        "no_opening": 409,
    }.get(error.code, 400)
    return HTTPException(
        status_code=status,
        detail={"code": error.code, "message": str(error)},
    )


def require_admin(
    session_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str:
    if not sessions.valid(session_token):
        raise HTTPException(status_code=401, detail="Debes iniciar sesión.")
    return str(session_token)


def absolute_url(request: Request, path: str) -> str:
    public_base = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    base = public_base or str(request.base_url).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


async def _expire_qualifier(room_code: str, opening_id: str) -> None:
    try:
        room = registry.get(room_code)
        room.close_qualifier(expected_opening_id=opening_id)
    except RoomError:
        return
    await hub.broadcast_snapshots(room)


async def _expire_question(room_code: str, opening_id: str) -> None:
    try:
        room = registry.get(room_code)
        room.timeout_question(expected_opening_id=opening_id)
    except RoomError:
        return
    await hub.broadcast_snapshots(room)


async def _expire_lifeline(room_code: str, opening_id: str) -> None:
    try:
        room = registry.get(room_code)
        room.finish_timed_lifeline(expected_opening_id=opening_id)
    except RoomError:
        return
    timers.schedule(
        room_code,
        "question",
        room.question_remaining_ms,
        lambda: _expire_question(room_code, room.question_opening_id),
    )
    await hub.broadcast_snapshots(room)


def _schedule_qualifier(room: OnlineRoom) -> None:
    opening = room.manager.current_opening
    assert opening is not None
    timers.schedule(
        room.room_code,
        "qualifier",
        opening.duration_ms,
        lambda: _expire_qualifier(room.room_code, opening.opening_id),
    )


def _schedule_question(room: OnlineRoom) -> None:
    opening_id = room.question_opening_id
    timers.schedule(
        room.room_code,
        "question",
        room.question_remaining_ms,
        lambda: _expire_question(room.room_code, opening_id),
    )


def _schedule_lifeline(room: OnlineRoom) -> None:
    opening_id = room.lifeline_opening_id
    timers.schedule(
        room.room_code,
        "lifeline",
        LIFELINE_DURATION_MS,
        lambda: _expire_lifeline(room.room_code, opening_id),
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "active_rooms": registry.active_count()}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/")
async def landing_page() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/admin")
async def admin_page() -> FileResponse:
    return FileResponse(STATIC_ROOT / "admin.html")


@app.get("/host/{room_code}", name="host_page")
async def host_page(room_code: str) -> FileResponse:
    del room_code
    return FileResponse(STATIC_ROOT / "host.html")


@app.get("/join/{room_code}", name="join_page")
async def join_page(room_code: str) -> FileResponse:
    del room_code
    return FileResponse(STATIC_ROOT / "play.html")


@app.post("/api/auth/login")
async def login(body: LoginBody, response: Response, request: Request) -> dict[str, str]:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(f"login:{client}", limit=8, window_seconds=60):
        raise HTTPException(status_code=429, detail="Espera un momento antes de reintentar.")
    session = sessions.login(body.password)
    if session is None:
        raise HTTPException(status_code=401, detail="La clave no es correcta.")
    response.set_cookie(
        COOKIE_NAME,
        session.token,
        httponly=True,
        secure=environment == "production",
        samesite="strict",
        max_age=12 * 60 * 60,
        path="/",
    )
    return {"status": "ok"}


@app.get("/api/auth/session")
async def auth_session(_: str = Depends(require_admin)) -> dict[str, bool]:
    return {"authenticated": True}


@app.post("/api/auth/logout")
async def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> dict[str, str]:
    sessions.logout(session_token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@app.get("/api/banks")
async def list_banks(_: str = Depends(require_admin)) -> dict[str, Any]:
    return {"banks": registry.banks()}


@app.post("/api/games", status_code=201)
async def create_game(
    body: CreateGameBody,
    request: Request,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        room = registry.create(body.bank_id)
    except RoomError as error:
        raise room_error(error) from error
    return {
        "game_id": room.game_id,
        "room_code": room.room_code,
        "host_url": absolute_url(request, f"host/{room.room_code}"),
        "join_url": absolute_url(request, f"join/{room.room_code}"),
        "qr_url": absolute_url(request, f"api/rooms/{room.room_code}/qr"),
    }


@app.get("/api/games/{room_code}")
async def game_snapshot(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        return registry.get(room_code).host_snapshot()
    except RoomError as error:
        raise room_error(error) from error


@app.post("/api/games/{room_code}/settings")
async def configure_game(
    room_code: str,
    body: GameSettingsBody,
    _: str = Depends(require_admin),
) -> dict[str, int]:
    try:
        room = registry.get(room_code)
        return room.configure_questions_per_round(body.questions_per_round)
    except RoomError as error:
        raise room_error(error) from error


@app.post("/api/games/{room_code}/qualifier/start")
async def start_qualifier(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.start_qualifier()
    except RoomError as error:
        raise room_error(error) from error
    _schedule_qualifier(room)
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/qualifier/close")
async def close_qualifier(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.close_qualifier()
    except RoomError as error:
        raise room_error(error) from error
    timers.cancel(room_code, "qualifier")
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/selection/start")
async def start_selection(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.begin_player_selection()
    except RoomError as error:
        raise room_error(error) from error
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/players/confirm")
async def confirm_players(
    room_code: str,
    body: PlayerSelectionBody,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.confirm_players(body.participant_ids)
    except RoomError as error:
        raise room_error(error) from error
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/rounds/start")
async def start_round(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.start_round()
    except RoomError as error:
        raise room_error(error) from error
    _schedule_question(room)
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/questions/next")
async def next_question(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.advance_after_answer()
    except RoomError as error:
        raise room_error(error) from error
    if room.state is SessionState.QUESTION_ACTIVE:
        _schedule_question(room)
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/rounds/advance")
async def advance_round(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.advance_after_round()
    except RoomError as error:
        raise room_error(error) from error
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/lifelines/{name}")
async def use_lifeline(
    room_code: str,
    name: Literal["fifty", "phone", "audience"],
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        if name == "fifty":
            payload = room.use_fifty()
        else:
            payload = room.start_timed_lifeline(name)
    except RoomError as error:
        raise room_error(error) from error
    if name != "fifty":
        timers.cancel(room_code, "question")
        _schedule_lifeline(room)
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/lifelines/close")
async def close_lifeline(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        payload = room.finish_timed_lifeline()
    except RoomError as error:
        raise room_error(error) from error
    timers.cancel(room_code, "lifeline")
    _schedule_question(room)
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/replay")
async def replay(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        previous_plan = room.plan_ids
        payload = room.repeat()
        if room.plan_ids == previous_plan:
            payload = room.host_snapshot()
    except RoomError as error:
        raise room_error(error) from error
    timers.cancel_room(room_code)
    await hub.broadcast_snapshots(room)
    return payload


# Compatibilidad de rutas existentes: ahora siguen la máquina de estados canónica.
@app.post("/api/games/{room_code}/questions/open")
async def open_question_compat(
    room_code: str,
    body: OpenQuestionBody,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    del body
    try:
        room = registry.get(room_code)
        if room.state is SessionState.LOBBY_OPEN:
            payload = room.start_qualifier(duration_ms=QUALIFIER_DURATION_MS)
            _schedule_qualifier(room)
        elif room.state is SessionState.ROUND_INTRO:
            payload = room.start_round(duration_ms=QUESTION_DURATION_MS)
            _schedule_question(room)
        elif room.state is SessionState.ANSWER_REVEALED:
            payload = room.advance_after_answer()
            if room.state is SessionState.QUESTION_ACTIVE:
                _schedule_question(room)
        else:
            raise RoomError("invalid_state", "No corresponde abrir una pregunta en esta fase.")
    except RoomError as error:
        raise room_error(error) from error
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/questions/close")
async def close_question_compat(room_code: str, _: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        if room.state is SessionState.QUALIFIER_OPEN:
            payload = room.close_qualifier()
            timers.cancel(room_code, "qualifier")
        elif room.state is SessionState.QUESTION_ACTIVE:
            payload = room.timeout_question()
            timers.cancel(room_code, "question")
        else:
            raise RoomError("invalid_state", "No hay respuestas abiertas para cerrar.")
    except RoomError as error:
        raise room_error(error) from error
    await hub.broadcast_snapshots(room)
    return payload


@app.post("/api/games/{room_code}/finish")
async def finish_game(room_code: str, _: str = Depends(require_admin)) -> dict[str, str]:
    try:
        room = registry.get(room_code)
        room.close()
    except RoomError as error:
        raise room_error(error) from error
    timers.cancel_room(room_code)
    await hub.broadcast_snapshots(room)
    return {"status": "finished"}


@app.get("/api/rooms/{room_code}/bootstrap")
async def room_bootstrap(room_code: str) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        snapshot = room.manager.public_snapshot()
    except RoomError as error:
        raise room_error(error) from error
    return {
        "room_code": room.room_code,
        "status": snapshot["status"],
        "state": room.state.value,
        "capacity": snapshot["capacity"],
        "enrolled": snapshot["enrolled"],
        "avatars": list(AVATAR_CATALOG),
    }


@app.get("/api/rooms/{room_code}/qr")
async def room_qr(room_code: str, request: Request) -> Response:
    try:
        registry.get(room_code)
    except RoomError as error:
        raise room_error(error) from error
    output = io.BytesIO()
    segno.make(absolute_url(request, f"join/{room_code}"), error="m").save(
        output,
        kind="svg",
        scale=8,
        border=3,
        dark="#08164f",
        light="#ffffff",
    )
    return Response(
        content=output.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/rooms/{room_code}/join")
async def join_room(room_code: str, body: JoinBody, request: Request) -> dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(f"join:{client}:{room_code}", limit=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Espera un momento antes de reintentar.")
    try:
        room = registry.get(room_code)
        joined = room.manager.join(body.alias, body.device_id, body.avatar)
    except RoomError as error:
        raise room_error(error) from error
    return {
        "participant_id": joined.participant.participant_id,
        "alias": joined.participant.alias,
        "avatar": joined.participant.avatar,
        "avatar_symbol": joined.participant.public_dict()["avatar_symbol"],
        "token": joined.token,
        "websocket_url": f"/ws/rooms/{room_code}",
    }


@app.post("/api/rooms/{room_code}/reconnect")
async def reconnect_room(room_code: str, body: ReconnectBody) -> dict[str, Any]:
    try:
        room = registry.get(room_code)
        participant = room.manager.reconnect(body.token)
    except RoomError as error:
        raise room_error(error) from error
    return {
        "participant_id": participant.participant_id,
        "alias": participant.alias,
        "avatar": participant.avatar,
        "avatar_symbol": participant.public_dict()["avatar_symbol"],
        "role": participant.role,
        "websocket_url": f"/ws/rooms/{room_code}",
    }


@app.websocket("/ws/rooms/{room_code}")
async def player_websocket(websocket: WebSocket, room_code: str, token: str) -> None:
    try:
        room = registry.get(room_code)
        participant = room.manager.authenticate(token)
    except RoomError:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    await hub.connect(room_code, participant.participant_id, websocket)
    room.manager.set_connected(participant.participant_id, True)
    await websocket.send_json(event("room.snapshot", room.player_snapshot(participant.participant_id)))
    try:
        while True:
            message = await websocket.receive_json()
            message_type = str(message.get("type", ""))
            if message_type == "heartbeat":
                room.manager.heartbeat(token)
                await websocket.send_json(event("heartbeat", {"status": "ok"}))
                continue
            if message_type != "answer.submit":
                await websocket.send_json(event("error", {"message": "Mensaje no reconocido."}))
                continue
            opening_id = str(message.get("opening_id", ""))
            alternative = str(message.get("alternative", ""))
            state_before = room.state
            if state_before is SessionState.QUESTION_ACTIVE:
                result, revealed = room.submit_regular_answer(
                    token=token,
                    opening_id=opening_id,
                    answer=alternative,
                )
                await websocket.send_json(event("answer.ack", result))
                if revealed:
                    timers.cancel(room_code, "question")
                    await hub.broadcast_snapshots(room)
            elif state_before in {SessionState.QUALIFIER_OPEN, SessionState.LIFELINE_ACTIVE}:
                result = room.manager.submit_answer(
                    token=token,
                    opening_id=opening_id,
                    answer=alternative,
                )
                await websocket.send_json(event("answer.ack", result.to_dict()))
                if result.status is SubmissionStatus.ACCEPTED:
                    await websocket.send_json(
                        event("room.snapshot", room.player_snapshot(participant.participant_id))
                    )
            else:
                await websocket.send_json(
                    event("answer.ack", {"status": "late", "message": "La respuesta ya no está disponible."})
                )
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        disconnected = await hub.disconnect(room_code, participant.participant_id, websocket)
        if disconnected:
            room.manager.set_connected(participant.participant_id, False)
