"""Rancho demo por cuenta (016).

Cada cuenta real puede tener UNA organizacion hermana con `es_demo = true`
donde viven los datos de demostracion. Los usuarios de la cuenta la abren con
`?org=<slug-demo>` (ver `main._scope`) y la web la anuncia con un aviso fijo.

Separar por organizacion, y no con una marca por fila, es lo que permite que
los datos reales de las basculas lleguen sin mezclarse ni requerir purga: ver
el comentario de `migrations/016_demo_orgs.sql`.

`purgar_demo` es el unico lugar del repo que borra del libro de dinero, y solo
lo hace sobre una organizacion marcada como demo cuyas estaciones no tienen
ni un pesaje que no sea de demo. Cualquier otra cosa es un error ruidoso.
"""

from __future__ import annotations

from typing import Any

from fierro_api.admin import ErrorDeDatos, _conectar
from fierro_api.db import require_row

# Unica fuente de pesajes que una purga acepta borrar. La escriben los
# generadores de demo (scripts/seed_demo_hato.py, scripts/seed_demo_cuentas.py).
FUENTE_DEMO = "demo"

SUFIJO = "-demo"


def slug_demo(org_slug: str) -> str:
    return f"{org_slug}{SUFIJO}"


def asegurar_demo(dsn: str, *, org_slug: str) -> dict[str, Any]:
    """Crea (o devuelve) el rancho demo de una cuenta real. Idempotente."""
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, slug, name, es_demo FROM organizations WHERE slug = %s", (org_slug,)
        )
        real = cur.fetchone()
        if real is None:
            raise ErrorDeDatos(f"No existe la organizacion '{org_slug}'.")
        if real["es_demo"]:
            raise ErrorDeDatos(f"'{org_slug}' ya es un rancho demo; no lleva demo propio.")

        cur.execute(
            "SELECT slug, name FROM organizations WHERE demo_de_org_id = %s", (real["id"],)
        )
        existente = cur.fetchone()
        if existente is not None:
            return {**dict(existente), "demo_de": org_slug, "creado": False}

        slug = slug_demo(org_slug)
        cur.execute("SELECT es_demo FROM organizations WHERE slug = %s", (slug,))
        if cur.fetchone() is not None:
            # Una organizacion real que casualmente se llama asi: no se adopta
            # como demo, se detiene. Convertirla borraria datos reales al purgar.
            raise ErrorDeDatos(
                f"Ya existe '{slug}' y no es el demo de '{org_slug}'. Renombrala primero."
            )
        cur.execute(
            """
            INSERT INTO organizations (slug, name, es_demo, demo_de_org_id)
            VALUES (%s, %s, true, %s) RETURNING slug, name
            """,
            (slug, f"{real['name']} (demo)", real["id"]),
        )
        fila: dict[str, Any] = dict(require_row(cur.fetchone(), "crear rancho demo"))
        return {**fila, "demo_de": org_slug, "creado": True}


def purgar_demo(dsn: str, *, org_slug: str) -> dict[str, Any]:
    """Borra el rancho demo de una cuenta real con todo su contenido.

    Una sola transaccion: o se borra todo o nada. Devuelve cuantas filas
    salieron de cada tabla, para que nadie borre a ciegas.
    """
    with _conectar(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.slug FROM organizations d
            JOIN organizations r ON r.id = d.demo_de_org_id
            WHERE r.slug = %s AND d.es_demo
            """,
            (org_slug,),
        )
        demo = cur.fetchone()
        if demo is None:
            raise ErrorDeDatos(f"'{org_slug}' no tiene rancho demo.")
        org_id = demo["id"]

        cur.execute(
            """
            SELECT DISTINCT x.source, x.device_id FROM readings x
            JOIN devices dv ON dv.device_id = x.device_id
            JOIN ranches ra ON ra.id = dv.ranch_id
            WHERE ra.org_id = %s AND x.source <> %s
            LIMIT 5
            """,
            (org_id, FUENTE_DEMO),
        )
        ajenas = cur.fetchall()
        if ajenas:
            # Una bascula real asignada por error al rancho demo: sus pesajes
            # son reales y el invariante raiz manda. Primero se mueve la estacion.
            detalle = ", ".join(f"{f['device_id']} ({f['source']})" for f in ajenas)
            raise ErrorDeDatos(
                f"El rancho demo '{demo['slug']}' tiene pesajes que no son de demo: "
                f"{detalle}. Mueve esas estaciones a su rancho real antes de purgar."
            )

        cur.execute("SELECT email FROM users WHERE org_id = %s ORDER BY email", (org_id,))
        usuarios = [f["email"] for f in cur.fetchall()]
        if usuarios:
            raise ErrorDeDatos(
                f"El rancho demo '{demo['slug']}' tiene usuarios propios: "
                f"{', '.join(usuarios)}. Muevelos o desactivalos antes de purgar."
            )

        borrado: dict[str, int] = {}

        # Las anulaciones apuntan a otros movimientos con RESTRICT: se borra
        # de afuera hacia adentro, primero lo que nadie referencia.
        total = 0
        while True:
            cur.execute(
                """
                DELETE FROM money_movements m
                WHERE m.org_id = %s AND NOT EXISTS (
                  SELECT 1 FROM money_movements v WHERE v.voids_movement_id = m.movement_id
                )
                """,
                (org_id,),
            )
            if cur.rowcount == 0:
                break
            total += cur.rowcount
        borrado["money_movements"] = total

        cur.execute("DELETE FROM journal_entries WHERE org_id = %s", (org_id,))
        borrado["journal_entries"] = cur.rowcount
        cur.execute(
            "DELETE FROM animal_journal WHERE animal_id IN "
            "(SELECT id FROM animals WHERE org_id = %s)",
            (org_id,),
        )
        borrado["animal_journal"] = cur.rowcount
        cur.execute("DELETE FROM animals WHERE org_id = %s", (org_id,))
        borrado["animals"] = cur.rowcount

        cur.execute(
            """
            DELETE FROM readings WHERE device_id IN (
              SELECT dv.device_id FROM devices dv JOIN ranches ra ON ra.id = dv.ranch_id
              WHERE ra.org_id = %s
            )
            """,
            (org_id,),
        )
        borrado["readings"] = cur.rowcount
        cur.execute(
            "DELETE FROM devices WHERE ranch_id IN (SELECT id FROM ranches WHERE org_id = %s)",
            (org_id,),
        )
        borrado["devices"] = cur.rowcount
        cur.execute("DELETE FROM ranches WHERE org_id = %s", (org_id,))
        borrado["ranches"] = cur.rowcount
        cur.execute("DELETE FROM organizations WHERE id = %s AND es_demo", (org_id,))
        borrado["organizations"] = cur.rowcount
        conn.commit()

    return {"org": demo["slug"], "demo_de": org_slug, "borrado": borrado}
