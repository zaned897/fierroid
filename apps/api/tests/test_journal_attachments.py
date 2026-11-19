"""Adjuntos con Postgres real y objetos aislados en memoria."""
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fierro_api.media_storage import LocalStorage, ObjectConflict, StorageError
from fierro_api.media_validation import MAX_MEDIA_BYTES, MediaError, validate_media

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")


class FakeStorage:
    def __init__(self):
        self.objects = {}
        self.fail_after_write = False

    def put(self, key, raw, content_type):
        digest = hashlib.sha256(raw).hexdigest()
        if key in self.objects and self.objects[key][0] != raw:
            raise ObjectConflict("Otro archivo")
        self.objects[key] = (raw, digest)
        if self.fail_after_write:
            self.fail_after_write = False
            raise StorageError("Respuesta perdida despues de guardar")
        return digest

    def read(self, key, generation):
        return self.objects[key][0]

    def signed_url(self, key, generation):
        return None


def photo(fmt="JPEG", color="green", size=(32, 32)):
    from PIL import Image

    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format=fmt)
    return stream.getvalue()


def audio(fmt="webm", seconds=1):
    import av

    output = BytesIO()
    codec = "libopus" if fmt == "webm" else "aac"
    with av.open(output, "w", format=fmt) as container:
        stream = container.add_stream(codec, rate=48000)
        stream.layout = "mono"
        for index in range(seconds * 50):
            frame = av.AudioFrame(format="fltp", layout="mono", samples=960)
            frame.sample_rate = 48000
            frame.time_base = Fraction(1, 48000)
            frame.pts = index * 960
            frame.planes[0].update(bytes(frame.planes[0].buffer_size))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return output.getvalue()


@pytest.fixture
def world(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser, create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
    prefix = "media" + uuid4().hex[:12]
    emails = [f"{prefix}-{index}@example.test" for index in range(2)]
    for email, org in zip(emails, ["los-encinos", "valle-verde"], strict=True):
        create_user(DSN, email=email, org_slug=org)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT u.id,u.email,u.org_id,o.slug FROM users u JOIN organizations o "
                    "ON o.id=u.org_id WHERE u.email=ANY(%s) ORDER BY u.email", (emails,))
        users = [AuthUser(*row, False) for row in cur.fetchall()]
    storage = FakeStorage()
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    main.app.dependency_overrides[main.media_storage] = lambda: storage
    with TestClient(main.app) as client:
        entry_id = str(uuid4())
        payload = {"entry_id": entry_id, "occurred_at": "2026-11-18T12:00:00Z",
                   "category": "observacion", "body": "Revision del corral.",
                   "animals": [prefix]}
        assert client.post("/v1/journal", json=payload).status_code == 200
        yield client, users, prefix, entry_id, storage
    main.app.dependency_overrides.pop(main.current_user, None)
    main.app.dependency_overrides.pop(main.media_storage, None)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        authors = [user.id for user in users]
        cur.execute("DELETE FROM journal_attachments WHERE entry_id IN "
                    "(SELECT entry_id FROM journal_entries WHERE author_id=ANY(%s))", (authors,))
        cur.execute("DELETE FROM journal_entries WHERE author_id=ANY(%s)", (authors,))
        cur.execute("DELETE FROM animals WHERE tag_id=%s", (prefix,))
        cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))


def send(client, entry_id, attachment_id=None, raw=None, content_type="image/jpeg", kind="photo"):
    return client.post(f"/v1/journal/{entry_id}/attachments", data={
        "attachment_id": attachment_id or str(uuid4()), "kind": kind,
    }, files={"file": ("archivo", photo() if raw is None else raw, content_type)})


def test_upload_retry_metadata_and_private_download(world):
    client, _, _, entry_id, storage = world
    attachment_id = str(uuid4())
    first = send(client, entry_id, attachment_id)
    assert first.status_code == 200
    assert send(client, entry_id, attachment_id).json() == first.json()
    assert len(storage.objects) == 1
    assert send(client, entry_id, attachment_id, raw=photo(color="red")).status_code == 409
    path = f"/v1/journal/{entry_id}/attachments"
    assert client.get(path).json()["attachments"] == [first.json()]
    notes = client.get("/v1/journal").json()["entries"]
    note = next(entry for entry in notes if entry["entry_id"] == entry_id)
    assert len(note["attachments"]) == 1
    assert set(note["attachments"][0]) == set(first.json())
    assert "storage_key" not in note["attachments"][0]
    location = client.get(path + "/" + attachment_id).json()
    download = client.get(location["url"])
    assert download.status_code == 200
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["cache-control"].startswith("private")
    assert download.headers["content-type"] == "image/jpeg"


def test_file_written_before_failure_is_reconciled_by_retry(world):
    client, _, _, entry_id, storage = world
    attachment_id = str(uuid4())
    storage.fail_after_write = True
    assert send(client, entry_id, attachment_id).status_code == 503
    assert client.get(f"/v1/journal/{entry_id}/attachments").json()["attachments"] == []
    assert len(storage.objects) == 1
    assert send(client, entry_id, attachment_id).status_code == 200
    assert len(storage.objects) == 1


def test_concurrent_retry_and_limits(world):
    from fierro_api.journal_attachments import upload

    client, users, _, entry_id, storage = world
    args = {"org": users[0].org_slug, "entry_id": UUID(entry_id), "attachment_id": uuid4(),
            "kind": "photo", "raw": photo(), "content_type": "image/jpeg", "storage": storage}
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: upload(DSN, **args), range(2)))
    assert results[0] == results[1]
    assert len(storage.objects) == 1
    for _ in range(5):
        assert send(client, entry_id).status_code == 200
    assert send(client, entry_id).status_code == 400
    assert send(client, entry_id, str(args["attachment_id"])).status_code == 200


def test_scope_covers_animal_relationship_and_all_attachment_routes(world):
    from fierro_api import main

    client, users, tag, entry_id, storage = world
    response = send(client, entry_id)
    attachment_id = response.json()["attachment_id"]
    general = f"/v1/journal/{entry_id}/attachments"
    animal = f"/v1/animals/{tag}/journal/{entry_id}/attachments"
    assert client.get(animal).status_code == 200
    assert client.get(animal.replace(tag, "otro-animal")).status_code == 404
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    for path in [general, animal]:
        for suffix in ["", f"/{attachment_id}", f"/{attachment_id}/content"]:
            assert client.get(path + suffix, params={"org": users[0].org_slug}).status_code == 404
    assert send(client, entry_id).status_code == 404
    assert len(storage.objects) == 1
    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get(general).status_code == 400
    assert send(client, entry_id).status_code == 400
    assert client.get(general, params={"org": users[0].org_slug}).status_code == 200


@pytest.mark.parametrize(("raw", "mime", "kind"), [
    (b"<html>hola</html>", "image/jpeg", "photo"),
    (b"RIFFfake", "image/webp", "photo"),
    (b"\xff\xd8\xff", "image/jpeg", "photo"),
    (b"\x1a\x45\xdf\xa3fake", "audio/webm", "audio"),
    (b"0123ftypfake", "audio/mp4", "audio"),
    (b"", "image/jpeg", "photo"),
    (b"x" * (MAX_MEDIA_BYTES + 1), "image/jpeg", "photo"),
])
def test_fake_truncated_and_oversized_files_are_rejected(world, raw, mime, kind):
    client, _, _, entry_id, storage = world
    assert send(client, entry_id, raw=raw, content_type=mime, kind=kind).status_code == 400
    assert not storage.objects


def test_supported_media_and_declared_type_mismatch(world):
    client, _, _, entry_id, _ = world
    assert send(client, entry_id, raw=photo("WEBP"), content_type="image/webp").status_code == 200
    assert send(client, entry_id, raw=photo("PNG"), content_type="image/png").status_code == 400
    assert send(client, entry_id, content_type="image/webp").status_code == 400
    assert send(client, entry_id, raw=photo(size=(1025, 20))).status_code == 400
    for fmt in ("webm", "mp4"):
        response = send(client, entry_id, raw=audio(fmt), content_type=f"audio/{fmt}", kind="audio")
        assert response.status_code == 200
        assert 900 <= response.json()["duration_ms"] <= 1100


def test_audio_over_two_minutes_is_rejected():
    with pytest.raises(MediaError, match="120 segundos"):
        validate_media(audio(seconds=121), "audio", "audio/webm")


def test_local_storage_atomic_retry_and_path_boundary(tmp_path):
    storage = LocalStorage(str(tmp_path))
    key = "org/1/journal/entry/attachment"
    generation = storage.put(key, b"contenido", "image/jpeg")
    assert storage.put(key, b"contenido", "image/jpeg") == generation
    assert storage.read(key, generation) == b"contenido"
    with pytest.raises(ObjectConflict):
        storage.put(key, b"otro", "image/jpeg")
    with pytest.raises(StorageError):
        storage.put("../fuera", b"otro", "image/jpeg")
