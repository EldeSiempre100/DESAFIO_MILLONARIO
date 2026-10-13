from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .models import AVATAR_CATALOG, DEFAULT_AVATAR_ID
from .room import RoomError, RoomManager


def make_event(event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "version": "0.1",
        "event_id": f"evt_{datetime.now(UTC).timestamp():.6f}",
        "type": event_type,
        "issued_at": datetime.now(UTC).isoformat(),
        "payload": payload or {},
    }


class ConnectionHub:
    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, participant_id: str, websocket: WebSocket) -> None:
        old = self.connections.get(participant_id)
        if old is not None and old is not websocket:
            try:
                await old.close(code=4000)
            except RuntimeError:
                pass
        self.connections[participant_id] = websocket

    async def disconnect(self, participant_id: str, websocket: WebSocket) -> None:
        if self.connections.get(participant_id) is websocket:
            self.connections.pop(participant_id, None)

    async def broadcast(
        self,
        event: dict[str, Any],
        participant_ids: set[str] | None = None,
    ) -> None:
        stale: list[tuple[str, WebSocket]] = []
        for participant_id, websocket in list(self.connections.items()):
            if participant_ids is not None and participant_id not in participant_ids:
                continue
            try:
                await websocket.send_json(event)
            except (RuntimeError, OSError):
                stale.append((participant_id, websocket))
        for participant_id, websocket in stale:
            await self.disconnect(participant_id, websocket)

    def schedule(
        self,
        event: dict[str, Any],
        participant_ids: set[str] | None = None,
    ) -> None:
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(
            self.broadcast(event, participant_ids),
            loop,
        )


class JoinBody(BaseModel):
    alias: str = Field(min_length=2, max_length=24)
    avatar: str = Field(default=DEFAULT_AVATAR_ID, min_length=1, max_length=30)
    device_id: str = Field(min_length=1, max_length=80)
    client_version: str = Field(default="3.1.4", max_length=20)


class ReconnectBody(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class HeartbeatBody(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class AnswerBody(BaseModel):
    opening_id: str = Field(min_length=5, max_length=100)
    answer: str = Field(min_length=1, max_length=1)


class LeaveBody(BaseModel):
    token: str = Field(min_length=16, max_length=200)


def _http_error(error: RoomError) -> HTTPException:
    status = {
        "room_full": 409,
        "room_locked": 409,
        "alias_taken": 409,
        "device_registered": 409,
        "invalid_token": 401,
        "not_found": 404,
    }.get(error.code, 400)
    return HTTPException(
        status_code=status,
        detail={"code": error.code, "message": str(error)},
    )


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "missing_token", "message": "Falta la identidad de sala."},
        )
    return authorization[7:].strip()


def create_app(
    manager: RoomManager,
    static_dir: str | Path,
    hub: ConnectionHub | None = None,
) -> FastAPI:
    mobile_dir = Path(static_dir)
    connection_hub = hub or ConnectionHub()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        connection_hub.loop = asyncio.get_running_loop()
        yield
        connection_hub.loop = None

    app = FastAPI(
        title="Millonario educativo V3.1.4",
        version="3.1.4",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.room_manager = manager
    app.state.connection_hub = connection_hub
    app.mount("/mobile", StaticFiles(directory=mobile_dir), name="mobile")

    def validate_legacy_room(room_code: str | None) -> None:
        if room_code is not None and room_code != manager.room_code:
            raise HTTPException(status_code=404, detail="Sala no encontrada.")

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse(mobile_dir / "index.html")

    @app.get("/health")
    async def health() -> dict[str, object]:
        snapshot = manager.host_snapshot()
        return {
            "status": "ok",
            "version": "3.1.4",
            "room_status": snapshot["status"],
            "enrolled": snapshot["enrolled"],
        }

    @app.get("/sala/{room_code}")
    async def room_page(room_code: str) -> RedirectResponse:
        # Enlaces V3.1 antiguos continúan funcionando, pero ya no determinan
        # qué sala usa el teléfono: cada ejecutable aloja una sola sala activa.
        return RedirectResponse(url="/")

    @app.get("/api/v1/bootstrap")
    @app.get("/api/v1/rooms/{room_code}/bootstrap")
    async def bootstrap(room_code: str | None = None) -> dict[str, object]:
        validate_legacy_room(room_code)
        snapshot = manager.public_snapshot()
        return {
            "room_code": snapshot["room_code"],
            "status": snapshot["status"],
            "capacity": snapshot["capacity"],
            "enrolled": snapshot["enrolled"],
            "ws_url": "/ws/v1/room",
            "avatars": list(AVATAR_CATALOG),
        }

    @app.post("/api/v1/join")
    @app.post("/api/v1/rooms/{room_code}/join")
    async def join(body: JoinBody, room_code: str | None = None) -> dict[str, object]:
        validate_legacy_room(room_code)
        try:
            result = manager.join(body.alias, body.device_id, body.avatar)
        except RoomError as error:
            raise _http_error(error) from error
        return {
            "participant_id": result.participant.participant_id,
            "alias": result.participant.alias,
            "avatar": result.participant.avatar,
            "avatar_symbol": result.participant.public_dict()["avatar_symbol"],
            "token": result.token,
            "role": result.participant.role,
            "ws_url": "/ws/v1/room",
        }

    @app.post("/api/v1/reconnect")
    @app.post("/api/v1/rooms/{room_code}/reconnect")
    async def reconnect(
        body: ReconnectBody,
        room_code: str | None = None,
    ) -> dict[str, object]:
        validate_legacy_room(room_code)
        try:
            participant = manager.reconnect(body.token)
        except RoomError as error:
            raise _http_error(error) from error
        return {
            "participant_id": participant.participant_id,
            "alias": participant.alias,
            "avatar": participant.avatar,
            "avatar_symbol": participant.public_dict()["avatar_symbol"],
            "role": participant.role,
            "ws_url": "/ws/v1/room",
        }

    @app.post("/api/v1/heartbeat")
    @app.post("/api/v1/rooms/{room_code}/heartbeat")
    async def heartbeat(
        body: HeartbeatBody,
        room_code: str | None = None,
    ) -> dict[str, str]:
        validate_legacy_room(room_code)
        try:
            manager.heartbeat(body.token)
        except RoomError as error:
            raise _http_error(error) from error
        return {"status": "ok"}

    @app.post("/api/v1/answers", status_code=202)
    @app.post("/api/v1/rooms/{room_code}/answers", status_code=202)
    async def answer(
        body: AnswerBody,
        authorization: str | None = Header(default=None),
        room_code: str | None = None,
    ) -> dict[str, object]:
        validate_legacy_room(room_code)
        token = _bearer_token(authorization)
        try:
            result = manager.submit_answer(
                token=token,
                opening_id=body.opening_id,
                answer=body.answer,
            )
        except RoomError as error:
            raise _http_error(error) from error
        return result.to_dict()

    @app.post("/api/v1/leave")
    @app.post("/api/v1/rooms/{room_code}/leave")
    async def leave(body: LeaveBody, room_code: str | None = None) -> dict[str, str]:
        validate_legacy_room(room_code)
        try:
            participant = manager.authenticate(body.token)
            manager.set_connected(participant.participant_id, False)
        except RoomError as error:
            raise _http_error(error) from error
        return {"status": "ok"}

    @app.websocket("/ws/v1/room")
    @app.websocket("/ws/v1/rooms/{room_code}")
    async def websocket_room(
        websocket: WebSocket,
        token: str,
        room_code: str | None = None,
    ) -> None:
        if room_code is not None and room_code != manager.room_code:
            await websocket.close(code=4404)
            return
        try:
            participant = manager.authenticate(token)
        except RoomError:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        await connection_hub.connect(participant.participant_id, websocket)
        manager.set_connected(participant.participant_id, True)
        await websocket.send_json(
            make_event(
                "room.snapshot",
                manager.public_snapshot(participant.participant_id),
            )
        )
        try:
            while True:
                message = await websocket.receive_json()
                message_type = str(message.get("type", ""))
                if message_type == "heartbeat":
                    manager.heartbeat(token)
                    await websocket.send_json(make_event("heartbeat", {"status": "ok"}))
                elif message_type == "answer.submit":
                    result = manager.submit_answer(
                        token=token,
                        opening_id=str(message.get("opening_id", "")),
                        answer=str(message.get("alternative", "")),
                    )
                    await websocket.send_json(make_event("answer.ack", result.to_dict()))
                else:
                    await websocket.send_json(
                        make_event(
                            "error",
                            {
                                "code": "unknown_event",
                                "message": "Evento no reconocido.",
                            },
                        )
                    )
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await connection_hub.disconnect(participant.participant_id, websocket)
            manager.set_connected(participant.participant_id, False)

    return app
