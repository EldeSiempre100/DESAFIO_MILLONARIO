from __future__ import annotations

import argparse
import struct
import subprocess
import zlib
import zipfile
from pathlib import Path


IMAGE_MAP = {
    "ppt/media/image2.png": "images/start_background.png",
    "ppt/media/image4.jpeg": "images/game_background.jpg",
    "ppt/media/image5.png": "images/phone.png",
    "ppt/media/image6.png": "images/audience.png",
    "ppt/media/image7.png": "images/navigation.png",
    "ppt/media/image8.jpeg": "images/finish_background.jpg",
}

AUDIO_MAP = {
    "ppt/media/media1.mp3": "audio/intro.mp3",
    "ppt/media/media2.mp3": "audio/question_music.mp3",
    "ppt/media/media5.mp3": "audio/transition.mp3",
    "ppt/media/audio1.wav": "audio/incorrect.wav",
    "ppt/media/audio2.wav": "audio/lifeline.wav",
    "ppt/media/audio3.wav": "audio/correct.wav",
}


def read_member_ignoring_crc(archive_path: Path, member: str) -> bytes:
    """Lee un miembro ZIP usando su cabecera local, incluso si el CRC está dañado."""
    with zipfile.ZipFile(archive_path, "r") as archive:
        info = archive.getinfo(member)

    with archive_path.open("rb") as source:
        source.seek(info.header_offset)
        header = source.read(30)
        (
            signature,
            _version,
            _flags,
            compression,
            _time,
            _date,
            _crc,
            compressed_size,
            uncompressed_size,
            filename_length,
            extra_length,
        ) = struct.unpack("<IHHHHHIIIHH", header)
        if signature != 0x04034B50:
            raise RuntimeError(f"Cabecera ZIP inválida para {member}.")
        source.seek(filename_length + extra_length, 1)
        raw = source.read(compressed_size)

    if compression == zipfile.ZIP_STORED:
        data = raw
    elif compression == zipfile.ZIP_DEFLATED:
        data = zlib.decompress(raw, -zlib.MAX_WBITS)
    else:
        raise RuntimeError(f"Compresión ZIP no compatible: {compression}.")
    if len(data) != uncompressed_size:
        raise RuntimeError(f"Tamaño inesperado al extraer {member}.")
    return data


def extract_member(archive_path: Path, member: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(read_member_ignoring_crc(archive_path, member))


def ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError(
            "Falta imageio-ffmpeg. Instale las dependencias opcionales de assets."
        ) from exc


def transcode_trimmed(
    ffmpeg: str,
    source: Path,
    destination: Path,
    start_seconds: float,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-b:a",
        "128k",
        str(destination),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0 or not destination.exists():
        raise RuntimeError(f"No fue posible normalizar {source.name}.")


def normalize_mp3(ffmpeg: str, source: Path) -> None:
    destination = source.with_name(f".{source.stem}.normalized.mp3")
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-b:a",
        "128k",
        "-write_xing",
        "1",
        str(destination),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0 or not destination.exists():
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"No fue posible normalizar {source.name}.")
    destination.replace(source)


def recover_audience_audio(ffmpeg: str, source: Path, destination: Path) -> None:
    """Recupera los cuadros válidos del MP3 con CRC y tramas dañadas."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-fflags",
        "+discardcorrupt",
        "-err_detect",
        "ignore_err",
        "-i",
        str(source),
        "-ss",
        "17.000",
        "-vn",
        "-af",
        "aresample=async=1:first_pts=0",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0 or not destination.exists():
        raise RuntimeError("No fue posible recuperar el audio del público.")


def build_assets(pptx: Path, output: Path) -> None:
    for member, relative in {**IMAGE_MAP, **AUDIO_MAP}.items():
        extract_member(pptx, member, output / relative)

    raw_dir = output / "audio" / "_raw"
    call_raw = raw_dir / "call_source.mp3"
    audience_raw = raw_dir / "audience_source.mp3"
    extract_member(pptx, "ppt/media/media3.mp3", call_raw)
    extract_member(pptx, "ppt/media/media4.mp3", audience_raw)

    ffmpeg = ffmpeg_executable()
    for filename in ("intro.mp3", "question_music.mp3", "transition.mp3"):
        normalize_mp3(ffmpeg, output / "audio" / filename)
    transcode_trimmed(ffmpeg, call_raw, output / "audio" / "call.mp3", 16.5)
    recover_audience_audio(ffmpeg, audience_raw, output / "audio" / "audience.wav")

    # Los temporales se mantienen fuera del control de versiones solo si se necesita
    # investigar nuevamente el audio dañado.
    if (output / "audio" / "call.mp3").stat().st_size == 0:
        raise RuntimeError("El audio de llamada quedó vacío.")
    if (output / "audio" / "audience.wav").stat().st_size == 0:
        raise RuntimeError("El audio de público quedó vacío.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrae recursos del PPTX de referencia.")
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--output", type=Path, default=Path("assets"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pptx = args.pptx.resolve()
    output = args.output.resolve()
    if not pptx.exists():
        raise SystemExit(f"No existe el archivo: {pptx}")
    output.mkdir(parents=True, exist_ok=True)
    build_assets(pptx, output)
    print(f"Recursos preparados en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
