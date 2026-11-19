"""Objetos privados del Diario. Implementaciones local y GCS con creacion exclusiva."""
from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Protocol


class StorageError(RuntimeError):
    """El archivo no se pudo guardar o leer."""


class ObjectConflict(StorageError):
    """La clave ya contiene otros bytes."""


class MediaStorage(Protocol):
    def put(self, key: str, raw: bytes, content_type: str) -> str: ...
    def read(self, key: str, generation: str) -> bytes: ...
    def signed_url(self, key: str, generation: str) -> str | None: ...


class LocalStorage:
    def __init__(self, directory: str) -> None:
        self.root = Path(directory).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Ruta de archivo invalida")
        return path

    def put(self, key: str, raw: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        # El nombre final solo aparece cuando todos los bytes quedaron en disco.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary_name = temporary.name
            temporary.write(raw)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            try:
                os.link(temporary_name, path)
            except FileExistsError:
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ObjectConflict("El adjunto ya contiene otro archivo") from None
        finally:
            Path(temporary_name).unlink(missing_ok=True)
        return digest

    def read(self, key: str, generation: str) -> bytes:
        try:
            raw = self._path(key).read_bytes()
        except OSError as exc:
            raise StorageError("El archivo no esta disponible") from exc
        if hashlib.sha256(raw).hexdigest() != generation:
            raise StorageError("El archivo no coincide con su version registrada")
        return raw

    def signed_url(self, key: str, generation: str) -> None:
        return None


class GCSStorage:
    def __init__(self, bucket: str) -> None:
        from google.cloud import storage

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket)

    def put(self, key: str, raw: bytes, content_type: str) -> str:
        from google.api_core.exceptions import PreconditionFailed

        blob = self.bucket.blob(key)
        digest = hashlib.sha256(raw).hexdigest()
        blob.metadata = {"sha256": digest}
        blob.cache_control = "private, max-age=300"
        blob.content_disposition = "inline"
        try:
            blob.upload_from_string(
                raw, content_type=content_type, if_generation_match=0, timeout=30,
            )
        except PreconditionFailed:
            blob.reload(timeout=15)
            if (blob.metadata or {}).get("sha256") != digest or blob.size != len(raw):
                raise ObjectConflict("El adjunto ya contiene otro archivo") from None
        return str(blob.generation)

    def read(self, key: str, generation: str) -> bytes:
        blob = self.bucket.blob(key, generation=int(generation))
        return bytes(blob.download_as_bytes(timeout=30))

    def signed_url(self, key: str, generation: str) -> str:
        import google.auth
        from google.auth.credentials import Signing
        from google.auth.transport.requests import Request

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        options = {}
        if not isinstance(credentials, Signing):
            credentials.refresh(Request())  # type: ignore[no-untyped-call]
            email = getattr(credentials, "service_account_email", None)
            if not email or email == "default":
                raise StorageError("Falta la identidad de firma de la API")
            options = {"service_account_email": email, "access_token": credentials.token}
        url = self.bucket.blob(key).generate_signed_url(
            version="v4", expiration=timedelta(minutes=5), method="GET",
            generation=int(generation), credentials=credentials, **options,
        )
        return str(url)


@lru_cache(maxsize=4)
def build_storage(bucket: str, directory: str, deployed: bool) -> MediaStorage:
    if bucket:
        return GCSStorage(bucket)
    if deployed:
        raise StorageError("Configura FIERRO_MEDIA_BUCKET para usar adjuntos")
    return LocalStorage(directory)
