from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NetworkInfo:
    ip: str
    port: int
    local_url: str
    warning: str = ""


def detect_lan_ip() -> str:
    candidates: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            candidates.append(probe.getsockname()[0])
    except OSError:
        pass
    try:
        _, _, addresses = socket.gethostbyname_ex(socket.gethostname())
        candidates.extend(addresses)
    except OSError:
        pass
    for address in candidates:
        if address and not address.startswith("127.") and ":" not in address:
            return address
    return "127.0.0.1"


def find_available_port(preferred: int = 8787, attempts: int = 20) -> int:
    for port in range(preferred, preferred + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    raise OSError("No existe un puerto local disponible para la sala.")
