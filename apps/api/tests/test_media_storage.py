"""Contrato del adaptador GCS, sin cuentas ni objetos remotos."""
import hashlib
from unittest.mock import MagicMock

import pytest
from fierro_api.media_storage import GCSStorage, ObjectConflict, StorageError, build_storage
from google.api_core.exceptions import PreconditionFailed


def test_gcs_exclusive_create_and_lost_ack(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("google.cloud.storage.Client", lambda: client)
    blob = client.bucket.return_value.blob.return_value
    blob.generation = 42
    storage = GCSStorage("private-test")
    assert storage.put("org/1/journal/e/a", b"foto", "image/jpeg") == "42"
    assert blob.upload_from_string.call_args.kwargs["if_generation_match"] == 0
    assert blob.cache_control == "private, max-age=300"
    assert blob.metadata == {"sha256": hashlib.sha256(b"foto").hexdigest()}
    blob.upload_from_string.side_effect = PreconditionFailed("exists")
    blob.size = 4
    assert storage.put("org/1/journal/e/a", b"foto", "image/jpeg") == "42"
    # reload recupera los metadatos del objeto existente, no los de la solicitud.
    blob.reload.side_effect = lambda **_: setattr(blob, "metadata", {"sha256": "otro"})
    with pytest.raises(ObjectConflict):
        storage.put("org/1/journal/e/a", b"foto", "image/jpeg")


def test_gcs_signed_url_uses_workload_identity_and_generation(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("google.cloud.storage.Client", lambda: client)
    credentials = MagicMock()
    credentials.service_account_email = "api@example.iam.gserviceaccount.com"
    credentials.token = "test-token"
    monkeypatch.setattr("google.auth.default", lambda **_: (credentials, "test-project"))
    storage = GCSStorage("private-test")
    blob = client.bucket.return_value.blob.return_value
    blob.generate_signed_url.return_value = "https://storage.example/signed"
    assert storage.signed_url("org/1/journal/e/a", "42").endswith("/signed")
    options = blob.generate_signed_url.call_args.kwargs
    assert options["generation"] == 42
    assert options["expiration"].total_seconds() == 300
    assert options["service_account_email"] == credentials.service_account_email
    assert options["access_token"] == "test-token"


def test_deployed_environment_never_falls_back_to_local_storage(tmp_path):
    with pytest.raises(StorageError, match="FIERRO_MEDIA_BUCKET"):
        build_storage("", str(tmp_path), True)
