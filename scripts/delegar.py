#!/usr/bin/env python3
"""Delega una tarea acotada a Codex o a Antigravity (agy) sin tocar tu rama.

Existe para que Claude Code reparta trabajo con los otros agentes del usuario.
Cada tarea corre en su propio git worktree y rama (`delegar/<agente>-<slug>`),
asi que lo que haga el otro agente queda como un diff aparte que Claude revisa,
prueba y decide si integrar. Nada se mezcla a la rama actual ni a `main` aqui.

Uso:
    python scripts/delegar.py codex "agrega pruebas para ingest con lote vacio"
    python scripts/delegar.py agy "ajusta el espaciado de la tarjeta de animal"
    python scripts/delegar.py review            # segunda opinion de Codex
    python scripts/delegar.py hook-stop         # lo llama el hook Stop

Las CLIs y sus sesiones viven en la PC del usuario. Si falta una, el script
sale con codigo 2 y lo dice: falla ruidosa, nunca un resultado inventado.
Sin dependencias fuera de la biblioteca estandar, para correr igual en Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGISTROS = RAIZ / ".claude" / "delegaciones"
WORKTREES = RAIZ / ".claude" / "worktrees"
ULTIMA_REVISION = REGISTROS / ".ultima-revision"

# Contexto que recibe el otro agente antes de la tarea. Corto a proposito: las
# reglas completas estan en el repo y el agente las lee desde ahi.
PREAMBULO = """Trabajas en el repo fierroid (Fierro IoT, pesaje de ganado edge-first).
Antes de cambiar nada lee CLAUDE.md y AGENTS.md. Reglas que no se negocian:
- Ninguna lectura de pesaje se pierde. Falla ruidosa, nunca datos falsos.
- Idempotencia por event_id. Diff minimo, solo lo que pide la tarea.
- Sin hardware: usa FIERRO_MOCK_HW=1.
- No hagas commit ni push; deja los cambios en el arbol de trabajo.
Al terminar resume que cambiaste, que comandos corriste y su resultado.

Tarea:
"""


class Falta(RuntimeError):
    """La herramienta necesaria no esta disponible en esta maquina."""


def binario(nombre: str) -> str:
    # shutil.which resuelve los shims .cmd de npm en Windows; pasar la ruta
    # completa evita que subprocess no los encuentre.
    ruta = shutil.which(nombre)
    if ruta is None:
        raise Falta(
            f"`{nombre}` no esta en el PATH. Las delegaciones solo funcionan en la "
            "PC donde esta instalada y con sesion iniciada."
        )
    return ruta


def git(*args: str, cwd: Path = RAIZ) -> str:
    salida = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return salida.stdout.strip()


def slug(texto: str) -> str:
    limpio = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return limpio[:40].rstrip("-") or "tarea"


def crear_worktree(agente: str, tarea: str, base: str) -> tuple[Path, str]:
    marca = time.strftime("%Y%m%d-%H%M%S")
    nombre = f"{agente}-{slug(tarea)}-{marca}"
    rama = f"delegar/{nombre}"
    ruta = WORKTREES / f"delegar-{nombre}"
    WORKTREES.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-b", rama, str(ruta), base)
    return ruta, rama


def comando_agente(agente: str, worktree: Path, registro: Path, modo: str) -> list[str]:
    if agente == "codex":
        # El prompt va por stdin (`-`) para no pelear con el escapado de cmd.exe.
        return [
            binario("codex"), "exec",
            "--sandbox", "workspace-write",
            "--cd", str(worktree),
            "--output-last-message", str(registro),
            "-",
        ]
    return [
        binario("agy"), "--mode", modo,
        "--output-format", "text",
        "--print-timeout", "0",
        "-p",
    ]


def delegar(agente: str, tarea: str, base: str, modo: str, limite: int) -> int:
    binario(agente)  # falla antes de crear el worktree si falta la CLI
    worktree, rama = crear_worktree(agente, tarea, base)
    REGISTROS.mkdir(parents=True, exist_ok=True)
    registro = REGISTROS / f"{worktree.name}.md"
    prompt = PREAMBULO + tarea
    comando = comando_agente(agente, worktree, registro, modo)

    print(f"[delegar] {agente} trabaja en {worktree} (rama {rama})", flush=True)
    try:
        if agente == "codex":
            fin = subprocess.run(
                comando, input=prompt, text=True, encoding="utf-8", timeout=limite
            )
        else:
            fin = subprocess.run(
                [*comando, prompt], cwd=worktree, text=True, encoding="utf-8",
                capture_output=True, timeout=limite,
            )
            registro.write_text(fin.stdout + fin.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired:
        print(f"[delegar] {agente} no termino en {limite}s; worktree intacto.", file=sys.stderr)
        return 3

    cambios = git("status", "--short", cwd=worktree)
    print(f"[delegar] {agente} salio con codigo {fin.returncode}")
    print(f"[delegar] resumen del agente: {registro}")
    if cambios:
        print("[delegar] cambios sin commit en el worktree:")
        print(git("diff", "--stat", cwd=worktree) or cambios)
        print(f"[delegar] revisa con: git -C \"{worktree}\" diff")
    else:
        print("[delegar] el agente no dejo cambios.")
    print(f"[delegar] al terminar: git worktree remove \"{worktree}\" && git branch -D {rama}")
    return fin.returncode


def base_revision() -> str:
    for ref in ("origin/main", "main"):
        try:
            return git("merge-base", "HEAD", ref)
        except subprocess.CalledProcessError:
            continue
    raise Falta("No encuentro `main` ni `origin/main` para comparar.")


def huella_diff(base: str) -> str:
    diff = git("diff", base)  # incluye lo que aun no tiene commit
    return hashlib.sha256(diff.encode("utf-8")).hexdigest() if diff else ""


def revisar(base: str, limite: int) -> tuple[int, str]:
    codex = binario("codex")
    instruccion = (
        PREAMBULO
        + f"Revisa el diff de este repo contra el commit {base} (`git diff {base}`). "
        "No edites archivos. Reporta solo problemas reales: bugs, datos que se pueden "
        "perder, violaciones de idempotencia, valores inventados en vez de fallar. "
        "Para cada uno: archivo:linea, que falla y como. Si no hay nada, di 'Sin hallazgos'."
    )
    REGISTROS.mkdir(parents=True, exist_ok=True)
    registro = REGISTROS / f"review-{time.strftime('%Y%m%d-%H%M%S')}.md"
    fin = subprocess.run(
        [codex, "exec", "--sandbox", "read-only", "--cd", str(RAIZ),
         "--output-last-message", str(registro), "-"],
        input=instruccion, text=True, encoding="utf-8", capture_output=True, timeout=limite,
    )
    texto = registro.read_text(encoding="utf-8") if registro.exists() else fin.stderr
    return fin.returncode, texto.strip()


def hook_stop() -> int:
    """Hook Stop de Claude Code: segunda opinion de Codex sobre el diff nuevo.

    Apagado salvo `FIERRO_CODEX_REVIEW=1`. Sale 0 en silencio cuando no aplica
    (nube sin Codex, sin diff, diff ya revisado) para no estorbar. Cuando Codex
    encuentra algo, sale 2: Claude Code le pasa el texto a Claude, que decide.
    """
    if os.environ.get("FIERRO_CODEX_REVIEW") != "1":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        evento = {}
    if evento.get("stop_hook_active"):
        return 0  # ya continuamos una vez por este hook; no hacer bucle
    if shutil.which("codex") is None:
        print("[delegar] FIERRO_CODEX_REVIEW=1 pero `codex` no esta en el PATH.", file=sys.stderr)
        return 0

    try:
        base = base_revision()
        huella = huella_diff(base)
        previa = ULTIMA_REVISION.read_text(encoding="utf-8") if ULTIMA_REVISION.exists() else ""
        if not huella or huella == previa:
            return 0
        codigo, texto = revisar(base, limite=540)
    except (Falta, subprocess.SubprocessError) as error:
        # Un hook roto no debe frenar el turno; se avisa y se sigue.
        print(f"[delegar] revision de Codex omitida: {error}", file=sys.stderr)
        return 0
    REGISTROS.mkdir(parents=True, exist_ok=True)
    ULTIMA_REVISION.write_text(huella, encoding="utf-8")
    if codigo != 0:
        print(f"[delegar] la revision de Codex fallo (codigo {codigo}): {texto}", file=sys.stderr)
        return 0
    if "sin hallazgos" in texto.lower():
        return 0
    print(
        "Codex reviso el diff y reporta lo siguiente. Verifica cada punto antes de "
        "actuar; descarta lo que no se sostenga:\n\n" + texto,
        file=sys.stderr,
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="accion", required=True)
    for agente in ("codex", "agy"):
        p = sub.add_parser(agente, help=f"delegar una tarea a {agente}")
        p.add_argument("tarea")
        p.add_argument("--base", default="HEAD", help="commit de partida (HEAD)")
        p.add_argument("--limite", type=int, default=1800, help="segundos (1800)")
        if agente == "agy":
            p.add_argument("--modo", default="accept-edits",
                           choices=["accept-edits", "auto", "plan"])
    r = sub.add_parser("review", help="segunda opinion de Codex sobre el diff contra main")
    r.add_argument("--limite", type=int, default=900)
    sub.add_parser("hook-stop", help="punto de entrada del hook Stop")
    args = parser.parse_args()

    try:
        if args.accion == "hook-stop":
            return hook_stop()
        if args.accion == "review":
            codigo, texto = revisar(base_revision(), args.limite)
            print(texto)
            return codigo
        return delegar(args.accion, args.tarea, args.base, getattr(args, "modo", ""),
                       args.limite)
    except Falta as error:
        print(f"[delegar] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
