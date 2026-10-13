from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Iterable

import uvicorn

from .api import ConnectionHub, create_app, make_event
from .network import NetworkInfo, detect_lan_ip, find_available_port
from .qr import write_room_qr
from .room import RoomManager


class ParticipationService:
    """Aloja FastAPI/Uvicorn en un hilo controlado por la aplicación Qt."""

    def __init__(
        self,
        *,
        static_dir: str | Path,
        runtime_dir: str | Path,
    ) -> None:
        self.static_dir = Path(static_dir)
        self.runtime_dir = Path(runtime_dir)
        self.manager: RoomManager | None = None
        self.hub: ConnectionHub | None = None
        self.network: NetworkInfo | None = None
        self.qr_path: Path | None = None
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._server is not None and self._server.started)

    @property
    def room_url(self) -> str:
        return self.network.local_url if self.network is not None else ""

    def start(
        self,
        *,
        session_id: str,
        room_code: str,
        max_participants: int = 30,
        preferred_port: int = 8787,
    ) -> NetworkInfo:
        self.stop()
        ip = detect_lan_ip()
        port = find_available_port(preferred_port)
        warning = (
            "No se detectó una red local; solo este computador podrá ingresar."
            if ip.startswith("127.")
            else ""
        )
        # Cada ejecutable publica una única sala. El QR no necesita incorporar
        # ni conservar el código interno, evitando enlaces obsoletos.
        url = f"http://{ip}:{port}/"
        self.network = NetworkInfo(ip=ip, port=port, local_url=url, warning=warning)
        self.manager = RoomManager(
            session_id=session_id,
            room_code=room_code,
            max_participants=max_participants,
        )
        self.hub = ConnectionHub()
        app = create_app(self.manager, self.static_dir, self.hub)
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=port,
            log_level="warning",
            access_log=False,
            loop="asyncio",
            http="h11",
            ws="websockets-sansio",
            lifespan="on",
            ws_max_size=64 * 1024,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run,
            name="millonario-local-server",
            daemon=True,
        )
        self._thread.start()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self._server.started:
                break
            if self._thread is not None and not self._thread.is_alive():
                break
            time.sleep(0.05)
        if not self._server.started:
            self.stop()
            raise RuntimeError("El servidor local no pudo iniciar.")
        self.qr_path = write_room_qr(url, self.runtime_dir / "room_qr.svg")
        return self.network

    def broadcast(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        participant_ids: Iterable[str] | None = None,
    ) -> None:
        if self.hub is None:
            return
        targets = set(participant_ids) if participant_ids is not None else None
        self.hub.schedule(make_event(event_type, payload), targets)

    def broadcast_snapshot(self) -> None:
        manager = self.manager
        if manager is None:
            return
        for participant in list(manager.participants.values()):
            if participant.removed:
                continue
            self.broadcast(
                "room.snapshot",
                manager.public_snapshot(participant.participant_id),
                participant_ids={participant.participant_id},
            )

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        if server is not None:
            server.should_exit = True
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        self._server = None
        self._thread = None
        self.hub = None
        self.manager = None
