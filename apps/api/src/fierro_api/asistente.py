"""Asistente "Pregúntale a tu hato" (#110).

Claude contesta preguntas del ganadero, pero cada número sale de una
herramienta que lee los pesajes de SU organización (`hato.py`). La clave de
Anthropic vive solo en el servidor; el navegador nunca la ve. Las herramientas
son de solo lectura y reciben los datos ya acotados por la sesión, así que un
texto como "muéstrame el rancho de al lado" no tiene con qué cumplirse.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

from fierro_api import hato

MODELO = "claude-opus-5-5"
MAX_VUELTAS = 6
MAX_HISTORIAL = 10

SISTEMA = """Eres el asistente de Fierro, una báscula para ganado. Contestas en español de México, \
claro y breve, a un ganadero que pregunta por su propio hato.

Reglas:
- Todo número sobre el hato (animales, pesos, ganancias, fechas) sale de una herramienta. \
Nunca lo estimes ni lo inventes. Si ninguna herramienta tiene el dato (precio, raza, vacunas, \
dueño), di que Fierro no lo tiene registrado.
- Di en una frase qué contaste y qué dejaste fuera, con la regla que devuelve la herramienta.
- Si una herramienta dice lectura_incompleta, avisa que solo revisaste los pesajes más recientes.
- Escribe los aretes tal cual (por ejemplo BEDE50D3) para que la app los convierta en enlaces.
- Usa listas cortas y kg con un decimal como máximo. Sin tablas ni encabezados.
- Solo lees datos: no puedes cambiar, borrar ni mover animales; si te lo piden, dilo."""

HERRAMIENTAS: list[dict[str, Any]] = [
    {
        "name": "resumen_hato",
        "description": (
            "Cuántos animales hay registrados (pesados o con ficha), cuántos se han pesado, "
            "el peso total del hato (suma del último pesaje estable de cada animal, "
            "sin atípicos ni pruebas), quiénes quedaron fuera del total y la fecha "
            "del pesaje más viejo que entra."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "animales_a_revisar",
        "description": (
            "Animales con problemas: los que llevan varios pesajes seguidos sin ganar peso, el de "
            "ganancia diaria más baja, los que tienen el último pesaje atípico y los que no "
            "se pesan desde hace muchos días. Devuelve también la mediana de ganancia del "
            "resto y la regla usada."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "pesajes": {
                    "type": "integer",
                    "description": "Pesajes seguidos sin ganar para ser rezagado. Normal: 2.",
                },
                "dias_sin_pesar": {
                    "type": "integer",
                    "description": "Días sin pesaje para avisar. Normal: 30.",
                },
            },
            "required": ["pesajes", "dias_sin_pesar"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ficha_animal",
        "description": (
            "Ficha de un arete: alias, notas, sus últimos pesajes estables "
            "(marcando los atípicos), "
            "ganancia diaria y bitácora reciente."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"tag_id": {"type": "string", "description": "Arete exacto."}},
            "required": ["tag_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "buscar_animales",
        "description": (
            "Busca animales por parte del arete o del alias, y/o por rango de su "
            "último peso limpio. "
            "Usa null en los campos que no apliquen."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "texto": {"type": ["string", "null"]},
                "peso_min_kg": {"type": ["number", "null"]},
                "peso_max_kg": {"type": ["number", "null"]},
            },
            "required": ["texto", "peso_min_kg", "peso_max_kg"],
            "additionalProperties": False,
        },
    },
]


class AsistenteNoDisponible(RuntimeError):
    """Sin clave, sin red o Claude no contestó: se dice, no se inventa."""


class CupoAgotado(RuntimeError):
    pass


class DatosHato(Protocol):
    lecturas: list[dict[str, Any]]
    fichas: list[dict[str, Any]]
    truncado: bool

    def bitacora(self, tag_id: str) -> list[dict[str, Any]]: ...


@dataclass
class Cupo:
    """Tope diario de preguntas por organización.

    Vive en memoria del proceso: un reinicio lo pone en cero. Basta para que
    un error en la PWA no gaste la cuenta de API en una noche; un cobro por
    plan necesitaría guardarlo en Postgres.
    """

    limite: int
    _cuentas: dict[tuple[str, date], int] = field(default_factory=dict)
    _candado: threading.Lock = field(default_factory=threading.Lock)

    def tomar(self, org: str, hoy: date) -> None:
        if self.limite <= 0:
            return
        with self._candado:
            clave = (org, hoy)
            if self._cuentas.get(clave, 0) >= self.limite:
                raise CupoAgotado(
                    f"Ya se hicieron las {self.limite} preguntas de hoy para este rancho. "
                    "Vuelve a intentar mañana."
                )
            self._cuentas = {k: v for k, v in self._cuentas.items() if k[1] == hoy}
            self._cuentas[clave] = self._cuentas.get(clave, 0) + 1


def _correr(
    nombre: str, entrada: dict[str, Any], datos: DatosHato, ahora: datetime
) -> dict[str, Any]:
    if nombre == "resumen_hato":
        return hato.resumen_hato(datos.lecturas, datos.fichas, truncado=datos.truncado)
    if nombre == "animales_a_revisar":
        return hato.animales_a_revisar(
            datos.lecturas,
            ahora=ahora,
            pesajes=max(1, int(entrada.get("pesajes") or hato.REZAGO["pesajes"])),
            dias_sin_pesar=max(1, int(entrada.get("dias_sin_pesar") or 30)),
            truncado=datos.truncado,
        )
    if nombre == "ficha_animal":
        tag = str(entrada.get("tag_id") or "").strip()
        ficha = hato.ficha_animal(datos.lecturas, datos.fichas, tag)
        if ficha is None:
            return {"error": f"No hay ningún animal con arete {tag} en este rancho."}
        return {**ficha, "bitacora": datos.bitacora(tag)[:10], "lectura_incompleta": datos.truncado}
    if nombre == "buscar_animales":
        return {
            **hato.buscar_animales(
                datos.lecturas,
                datos.fichas,
                texto=entrada.get("texto") or None,
                peso_min_kg=entrada.get("peso_min_kg"),
                peso_max_kg=entrada.get("peso_max_kg"),
            ),
            "lectura_incompleta": datos.truncado,
        }
    return {"error": f"Herramienta desconocida: {nombre}"}


def _consulta(nombre: str, resultado: dict[str, Any]) -> dict[str, Any]:
    """Lo que la pantalla muestra como "qué revisé" arriba de la respuesta."""
    return {
        "herramienta": nombre,
        "pesajes_revisados": resultado.get("pesajes_revisados"),
        "animales": resultado.get("animales_registrados", resultado.get("animales_comparables")),
        "lectura_incompleta": bool(resultado.get("lectura_incompleta")),
        "error": resultado.get("error"),
    }


def _historial(previos: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Solo texto de turnos anteriores: lo que se vio en pantalla, sin herramientas.

    La conversación empieza por el usuario y alterna; un historial manipulado
    desde el navegador no puede colar un turno de sistema.
    """
    mensajes: list[dict[str, Any]] = []
    for turno in previos[-MAX_HISTORIAL:]:
        rol = turno.get("rol")
        texto = (turno.get("texto") or "").strip()
        if rol not in ("usuario", "asistente") or not texto:
            continue
        role = "user" if rol == "usuario" else "assistant"
        if not mensajes and role != "user":
            continue
        if mensajes and mensajes[-1]["role"] == role:
            mensajes[-1]["content"] += "\n\n" + texto
        else:
            mensajes.append({"role": role, "content": texto})
    if mensajes and mensajes[-1]["role"] == "user":
        mensajes.pop()
    return mensajes


def responder(
    cliente: Any,
    *,
    pregunta: str,
    previos: list[dict[str, str]],
    cargar: Callable[[], DatosHato],
    modelo: str = MODELO,
    ahora: datetime | None = None,
) -> dict[str, Any]:
    """Bucle de herramientas. Los datos se cargan una vez, la primera vez que se piden."""
    ahora = ahora or datetime.now(UTC)
    datos: DatosHato | None = None
    mensajes = [*_historial(previos), {"role": "user", "content": pregunta}]
    consultas: list[dict[str, Any]] = []
    aretes: set[str] = set()

    for _ in range(MAX_VUELTAS):
        respuesta = cliente.beta.messages.create(
            model=modelo,
            max_tokens=16000,
            system=SISTEMA,
            tools=HERRAMIENTAS,
            messages=mensajes,
            output_config={"effort": "medium"},
            # Si un clasificador de seguridad rechaza por error, la API reintenta
            # en el modelo de respaldo dentro de la misma llamada.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if respuesta.stop_reason == "refusal":
            return {
                "respuesta": (
                    "No puedo contestar esa pregunta. "
                    "Prueba preguntando por tus animales o sus pesajes."
                ),
                "consultas": consultas,
                "aretes": [],
            }
        if respuesta.stop_reason == "max_tokens":
            raise AsistenteNoDisponible(
                "La respuesta se cortó antes de terminar. Intenta con una pregunta más corta."
            )
        usos = [b for b in respuesta.content if b.type == "tool_use"]
        if respuesta.stop_reason != "tool_use" or not usos:
            texto = "\n\n".join(b.text for b in respuesta.content if b.type == "text").strip()
            if not texto:
                raise AsistenteNoDisponible("El asistente no devolvió respuesta.")
            return {
                "respuesta": texto,
                "consultas": consultas,
                "aretes": sorted(a for a in aretes if re.search(rf"\b{re.escape(a)}\b", texto)),
            }

        mensajes.append({"role": "assistant", "content": respuesta.content})
        if datos is None:
            datos = cargar()
            aretes = {lectura["tag_id"] for lectura in datos.lecturas if lectura.get("tag_id")}
            aretes |= {f["tag_id"] for f in datos.fichas if f.get("tag_id")}
        resultados = []
        for uso in usos:
            resultado = _correr(uso.name, dict(uso.input or {}), datos, ahora)
            consultas.append(_consulta(uso.name, resultado))
            resultados.append(
                {
                    "type": "tool_result",
                    "tool_use_id": uso.id,
                    "content": json.dumps(resultado, ensure_ascii=False, default=str),
                    **({"is_error": True} if "error" in resultado else {}),
                }
            )
        mensajes.append({"role": "user", "content": resultados})

    raise AsistenteNoDisponible(
        "El asistente dio demasiadas vueltas sin contestar. Intenta de nuevo."
    )
