"""Validacion por contenido y duracion antes de guardar un adjunto."""
from __future__ import annotations

from io import BytesIO
from math import ceil

MAX_MEDIA_BYTES = 2 * 1024 * 1024
MAX_AUDIO_MS = 120000


class MediaError(ValueError):
    """Formato, tamano o duracion fuera de los limites."""


def validate_media(raw: bytes, kind: str, declared_type: str) -> tuple[bytes, str, int | None]:
    if not raw or len(raw) > MAX_MEDIA_BYTES:
        raise MediaError("Cada archivo debe pesar entre 1 byte y 2 MiB")
    content_type = declared_type.split(";")[0].strip().lower()
    if kind == "photo":
        return _photo(raw, content_type), content_type, None
    if kind == "audio":
        return raw, content_type, _audio_duration(raw, content_type)
    raise MediaError("El adjunto debe ser foto o audio")


def _photo(raw: bytes, content_type: str) -> bytes:
    from PIL import Image, ImageOps, UnidentifiedImageError

    expected = {"image/jpeg": "JPEG", "image/webp": "WEBP"}
    if content_type not in expected:
        raise MediaError("Las fotos deben ser JPEG o WebP")
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format != expected[content_type]:
                raise MediaError("El contenido no coincide con el tipo de foto declarado")
            if max(image.size) > 1024 or getattr(image, "is_animated", False):
                raise MediaError("La foto debe ser estatica y medir hasta 1024 px por lado")
            image.load()
            # La orientacion se aplica antes de quitar EXIF y GPS.
            clean = ImageOps.exif_transpose(image).convert("RGB")
            output = BytesIO()
            clean.save(output, format=expected[content_type], quality=90, exif=b"")
            result = output.getvalue()
            if len(result) > MAX_MEDIA_BYTES:
                raise MediaError("La foto normalizada supera 2 MiB")
            return result
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise MediaError("La foto esta incompleta o no se puede abrir") from exc


def _audio_duration(raw: bytes, content_type: str) -> int:
    import av

    signatures = {
        "audio/webm": raw.startswith(b"\x1a\x45\xdf\xa3"),
        "audio/mp4": len(raw) >= 12 and raw[4:8] == b"ftyp",
    }
    if not signatures.get(content_type):
        raise MediaError("El audio debe ser WebM/Opus o MP4/AAC valido")
    try:
        with av.open(BytesIO(raw), mode="r") as container:
            if len(container.streams.audio) != 1 or container.streams.video:
                raise MediaError("La nota de voz debe contener una pista de audio")
            codec = container.streams.audio[0].codec_context.name
            expected = "opus" if content_type == "audio/webm" else "aac"
            if codec != expected:
                raise MediaError("El codec no coincide con el formato de audio")
            seconds = 0.0
            for frame in container.decode(audio=0):
                seconds += frame.samples / frame.sample_rate
                if seconds > MAX_AUDIO_MS / 1000:
                    raise MediaError("La nota de voz supera 120 segundos")
            duration = ceil(seconds * 1000)
            if duration < 1:
                raise MediaError("La nota de voz esta vacia")
            return duration
    except (av.FFmpegError, ValueError) as exc:
        if isinstance(exc, MediaError):
            raise
        raise MediaError("El audio esta incompleto o no se puede abrir") from exc
