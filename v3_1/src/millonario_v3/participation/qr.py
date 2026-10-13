from __future__ import annotations

from pathlib import Path

import segno


def write_room_qr(url: str, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    qr = segno.make(url, error="m")
    qr.save(
        path,
        scale=8,
        border=4,
        dark="#071a63",
        light="#ffffff",
    )
    return path
