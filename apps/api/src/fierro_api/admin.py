"""Administración de la cadena organización → rancho → estación, y de usuarios.

Todo esto existía solo como CLI (`fierro-api-seed-tenants`, `fierro-api-user`),
lo que obligaba a tener acceso directo a la base para dar de alta a alguien o
registrar una estación. Aquí vive la parte de datos; los endpoints y el control
de acceso están en `main.py`.

**Un animal no se asigna a una organización.** La pertenencia se deriva por
`readings → devices → ranches → organizations`, así que lo que se administra es
la cadena. Mover una estación de rancho arrastra toda su historia, y por eso
`asignar_estacion` devuelve cuántas lecturas cambiaron de dueño: hacerlo en
silencio sería cambiarle los datos a alguien sin avisar.
"""

from __future__ import annotations

import re
from typing import Any

from fierro_api.db import require_row

# Minusculas, digitos y guiones. Un slug con mayusculas o espacios rompe las
# URLs de `?org=` y solo se descubre cuando alguien no puede guardar una foto.
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ErrorDeDatos(ValueError):
    """Algo que el cliente puede corregir: un slug malo, un duplicado."""


def validar_slug(valor: str, campo: str) -> str:
    if not SLUG.match(valor):
        raise ErrorDeDatos(
            f"{campo} invalido: '{valor}'. Solo minusculas, digitos y guiones, "
            "por ejemplo 'los-encinos'."
        )
    return valor


def _conectar(dsn: str) -> Any:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(dsn, row_factory=dict_row)


def listar_orgs(dsn: str) -> dict[str, Any]:
    """Arbol completo, mas las estaciones que no cuelgan de ningun rancho.

    Las sin asignar van aparte y no escondidas: sus lecturas entran a la base y
    no aparecen en ninguna vista, que es un fallo silencioso. Verlas listadas es
    la unica forma de que alguien las note.
    """
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.slug AS org, o.name AS org_name,
                   r.slug AS ranch, r.name AS ranch_name,
                   d.device_id,
                   (SELECT count(*) FROM readings x WHERE x.device_id = d.device_id) AS readings
            FROM organizations o
            LEFT JOIN ranches r ON r.org_id = o.id
            LEFT JOIN devices d ON d.ranch_id = r.id
            ORDER BY o.slug, r.slug NULLS FIRST, d.device_id NULLS FIRST
            """
        )
        filas = [dict(f) for f in cur.fetchall()]

        cur.execute(
            """
            SELECT d.device_id,
                   (SELECT count(*) FROM readings x WHERE x.device_id = d.device_id) AS readings
            FROM devices d WHERE d.ranch_id IS NULL ORDER BY d.device_id
            """
        )
        sueltas = [dict(f) for f in cur.fetchall()]

    orgs: dict[str, dict[str, Any]] = {}
    for fila in filas:
        org = orgs.setdefault(
            fila["org"], {"slug": fila["org"], "name": fila["org_name"], "ranches": []}
        )
        if fila["ranch"] is None:
            continue
        ranchos: list[dict[str, Any]] = org["ranches"]
        rancho = next((r for r in ranchos if r["slug"] == fila["ranch"]), None)
        if rancho is None:
            rancho = {"slug": fila["ranch"], "name": fila["ranch_name"], "devices": []}
            ranchos.append(rancho)
        if fila["device_id"] is not None:
            rancho["devices"].append(
                {"device_id": fila["device_id"], "readings": fila["readings"]}
            )

    return {"orgs": list(orgs.values()), "unassigned_devices": sueltas}


def crear_org(dsn: str, *, slug: str, name: str) -> dict[str, Any]:
    validar_slug(slug, "slug")
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM organizations WHERE slug = %s", (slug,))
        if cur.fetchone() is not None:
            raise ErrorDeDatos(f"Ya existe una organizacion con slug '{slug}'.")
        cur.execute(
            "INSERT INTO organizations (slug, name) VALUES (%s, %s) RETURNING slug, name",
            (slug, name),
        )
        return dict(require_row(cur.fetchone(), "crear organizacion"))


def crear_rancho(dsn: str, *, org_slug: str, slug: str, name: str) -> dict[str, Any]:
    validar_slug(slug, "slug")
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM organizations WHERE slug = %s", (org_slug,))
        org = cur.fetchone()
        if org is None:
            raise ErrorDeDatos(f"No existe la organizacion '{org_slug}'.")

        cur.execute(
            "SELECT 1 FROM ranches WHERE org_id = %s AND slug = %s", (org["id"], slug)
        )
        if cur.fetchone() is not None:
            raise ErrorDeDatos(f"'{org_slug}' ya tiene un rancho con slug '{slug}'.")

        cur.execute(
            "INSERT INTO ranches (org_id, slug, name) VALUES (%s, %s, %s) RETURNING slug, name",
            (org["id"], slug, name),
        )
        rancho = dict(require_row(cur.fetchone(), "crear rancho"))
        rancho["org"] = org_slug
        return rancho


def asignar_estacion(
    dsn: str, *, device_id: str, org_slug: str, ranch_slug: str
) -> dict[str, Any]:
    """Registra o mueve una estacion, y dice cuantas lecturas arrastro.

    La estacion puede no existir todavia: se crea la fila. Eso permite
    registrarla **antes** de que llegue su primer heartbeat, que es el orden
    sensato — al reves, sus primeras lecturas entran invisibles.
    """
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, o.slug AS org
            FROM ranches r JOIN organizations o ON o.id = r.org_id
            WHERE o.slug = %s AND r.slug = %s
            """,
            (org_slug, ranch_slug),
        )
        destino = cur.fetchone()
        if destino is None:
            raise ErrorDeDatos(f"No existe el rancho '{ranch_slug}' en '{org_slug}'.")

        cur.execute(
            """
            SELECT o.slug AS org
            FROM devices d
            LEFT JOIN ranches r ON r.id = d.ranch_id
            LEFT JOIN organizations o ON o.id = r.org_id
            WHERE d.device_id = %s
            """,
            (device_id,),
        )
        previo = cur.fetchone()
        org_anterior = previo["org"] if previo else None

        cur.execute(
            """
            INSERT INTO devices (device_id, ranch_id) VALUES (%s, %s)
            ON CONFLICT (device_id) DO UPDATE SET ranch_id = EXCLUDED.ranch_id
            """,
            (device_id, destino["id"]),
        )
        cur.execute("SELECT count(*) AS n FROM readings WHERE device_id = %s", (device_id,))
        # La anotacion no es adorno: `cur` viene de `_conectar`, que devuelve
        # `Any`, asi que mypy no puede resolver el generico de `require_row` e
        # indexar el resultado falla. Decirle el tipo aqui lo fija.
        conteo: dict[str, Any] = require_row(cur.fetchone(), "contar lecturas")
        movidas: int = conteo["n"]
        conn.commit()

    return {
        "device_id": device_id,
        "org": org_slug,
        "ranch": ranch_slug,
        "previous_org": org_anterior,
        "readings_moved": movidas if org_anterior != org_slug else 0,
    }


def listar_usuarios(dsn: str) -> list[dict[str, Any]]:
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.email, u.full_name, u.is_superuser, u.is_active,
                   o.slug AS org, u.last_login_at
            FROM users u LEFT JOIN organizations o ON o.id = u.org_id
            ORDER BY u.email
            """
        )
        return [dict(f) for f in cur.fetchall()]


def desactivar_usuario(dsn: str, *, email: str) -> dict[str, Any]:
    """Desactiva, nunca borra.

    Sus pesajes y su historial de llaves siguen teniendo sentido; borrar la fila
    los dejaria colgando de un usuario que ya no existe. Un usuario inactivo no
    puede canjear su llave, que es el efecto que se busca.
    """
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET is_active = false WHERE email = %s RETURNING email, is_active",
            (email,),
        )
        fila = cur.fetchone()
        if fila is None:
            raise ErrorDeDatos(f"No existe el usuario '{email}'.")
        # Las llaves vivas de un usuario desactivado se revocan aqui: dejarlas
        # activas haria que siguiera entrando hasta que caducaran.
        cur.execute(
            "DELETE FROM api_keys WHERE user_id = (SELECT id FROM users WHERE email = %s)",
            (email,),
        )
        revocadas = cur.rowcount
        conn.commit()

    resultado = dict(fila)
    resultado["keys_revoked"] = revocadas
    return resultado
