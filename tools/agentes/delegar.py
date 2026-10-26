#!/usr/bin/env python3
"""Delega una tarea acotada a Codex o a Antigravity (agy) sin tocar tu rama.

Existe para que Claude Code reparta trabajo con los otros agentes del usuario.
Cada tarea corre en su propio git worktree y rama (`delegar/<agente>-<slug>`),
asi que lo que haga el otro agente queda como un diff aparte que Claude revisa,
prueba y decide si integrar. Nada se mezcla a la rama actual ni a `main` aqui.

Uso:
    python tools/agentes/delegar.py estado          # que CLIs hay en esta maquina
    python tools/agentes/delegar.py codex "agrega pruebas para el caso de lista vacia"
    python tools/agentes/delegar.py agy "aplica el espaciado aprobado a la tarjeta"
    python tools/agentes/delegar.py review          # segunda opinion de Codex
    python tools/agentes/delegar.py limpiar         # borra worktrees y ramas delegar/*
    python tools/agentes/delegar.py hook-stop       # lo llama el hook Stop

Las CLIs y sus sesiones viven en la PC del usuario. Si falta una, el script
sale con codigo 2 y lo dice: falla ruidosa, nunca un resultado inventado.
Sin dependencias fuera de la biblioteca estandar, para correr igual en Windows.

Lo propio de cada proyecto vive en `preambulo.md` (y, si hace falta, en
`revision.md`, que dice que cuenta como problema en una revision), junto a
este archivo; el script es igual en todos los repos.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
# agy sale con 0 aunque el modo headless le niegue un permiso y no haga nada.
AGY_SIN_TRABAJO = ("no output produced", "auto-denied")

REGISTROS = RAIZ / ".claude" / "delegaciones"
WORKTREES = RAIZ / ".claude" / "worktrees"
ULTIMA_REVISION = REGISTROS / ".ultima-revision"
PREFIJO_RAMA = "delegar/"

# Variable que prende el hook de revision. Apagada por defecto: cada revision
# gasta cuota de ChatGPT y tarda.
VARIABLE_REVISION = "CODEX_REVIEW"

PREAMBULO_GENERICO = """Antes de cambiar nada lee AGENTS.md en la raiz del repo.
- Diff minimo, solo lo que pide la tarea. Falla ruidosa, nunca datos inventados.
- No hagas commit ni push; deja los cambios en el arbol de trabajo.
Al terminar resume que cambiaste, que comandos corriste y su resultado.
"""

CRITERIO_REVISION = (
    "Reporta solo problemas reales: bugs, regresiones, datos o precios inventados, "
    "secretos en el diff, enlaces o SEO rotos, y lo que contradiga AGENTS.md. "
    "Para cada uno: archivo:linea, que falla y como. Si no hay nada, di 'Sin hallazgos'."
)


class Falta(RuntimeError):
    """La herramienta necesaria no esta disponible en esta maquina."""


def preambulo() -> str:
    archivo = AQUI / "preambulo.md"
    texto = archivo.read_text(encoding="utf-8") if archivo.exists() else PREAMBULO_GENERICO
    return texto.rstrip() + "\n\nTarea:\n"


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
    rama = f"{PREFIJO_RAMA}{nombre}"
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
    # agy -p niega cualquier comando (su modo request-review no se puede
    # confirmar sin terminal), asi que solo lee y edita; Claude corre las pruebas.
    prompt = preambulo() + tarea
    if agente == "agy":
        aviso = "No corras comandos de terminal: solo lee y edita archivos.\n"
        prompt = preambulo() + aviso + tarea
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

    codigo = fin.returncode
    if agente == "agy" and codigo == 0:
        salida = registro.read_text(encoding="utf-8").lower()
        if any(marca in salida for marca in AGY_SIN_TRABAJO):
            print("[delegar] agy no trabajo: el modo headless le nego un permiso. "
                  "Ver tools/agentes/README.md (permisos de agy).", file=sys.stderr)
            codigo = 4

    print(f"[delegar] {agente} salio con codigo {fin.returncode}; delegar devuelve {codigo}")
    print(f"[delegar] resumen del agente: {registro}")
    # Marca los archivos nuevos (sin stagear contenido) para que `git diff`
    # los muestre y se puedan integrar junto con lo demas.
    git("add", "--intent-to-add", "--all", cwd=worktree)
    if git("status", "--porcelain", cwd=worktree):
        print("[delegar] cambios en el worktree:")
        print(git("diff", "HEAD", "--stat", cwd=worktree))
        print(f"[delegar] revisa con: git -C \"{worktree}\" diff HEAD")
        print(f"[delegar] integra con: git -C \"{worktree}\" diff HEAD --binary | git apply")
    else:
        print("[delegar] el agente no dejo cambios.")
    print("[delegar] al terminar: python tools/agentes/delegar.py limpiar")
    return codigo


def rama_principal() -> str:
    try:
        return git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        return "origin/main"


def base_revision() -> str:
    for ref in dict.fromkeys((rama_principal(), "origin/main", "main")):
        try:
            return git("merge-base", "HEAD", ref)
        except subprocess.CalledProcessError:
            continue
    raise Falta("No encuentro la rama principal (origin/HEAD, origin/main ni main) para comparar.")


def huella_diff(base: str) -> str:
    # Incluye lo que no tiene commit y el contenido de los archivos nuevos sin
    # rastrear. Lo ignorado (.claude/delegaciones/) queda fuera, si no cada
    # registro de revision cambiaria la huella y se revisaria en bucle.
    diff = git("diff", base)
    huella = hashlib.sha256(diff.encode("utf-8"))
    nuevos = git("ls-files", "--others", "--exclude-standard").splitlines()
    for nombre in sorted(nuevos):
        ruta = RAIZ / nombre
        huella.update(nombre.encode("utf-8"))
        if ruta.is_file():
            huella.update(ruta.read_bytes())
    return huella.hexdigest() if diff or nuevos else ""


def criterio_revision() -> str:
    # Un proyecto puede afinar que cuenta como problema real en revision.md.
    archivo = AQUI / "revision.md"
    return archivo.read_text(encoding="utf-8").strip() if archivo.exists() else CRITERIO_REVISION


def revisar(base: str, limite: int) -> tuple[int, str]:
    codex = binario("codex")
    instruccion = (
        preambulo()
        + f"Revisa el diff contra el commit {base} (`git diff {base}`, `git status`). "
        "No edites archivos. " + criterio_revision()
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

    Apagado salvo `CODEX_REVIEW=1`. Sale 0 en silencio cuando no aplica
    (nube sin Codex, sin diff, diff ya revisado) para no estorbar. Cuando Codex
    encuentra algo, sale 2: Claude Code le pasa el texto a Claude, que decide.
    """
    if os.environ.get(VARIABLE_REVISION) != "1":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        evento = {}
    if evento.get("stop_hook_active"):
        return 0  # ya continuamos una vez por este hook; no hacer bucle
    if shutil.which("codex") is None:
        print(f"[delegar] {VARIABLE_REVISION}=1 pero `codex` no esta en el PATH.", file=sys.stderr)
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
    if codigo != 0:
        # Sin guardar la huella: el mismo diff se vuelve a revisar la proxima vez.
        print(f"[delegar] la revision de Codex fallo (codigo {codigo}): {texto}", file=sys.stderr)
        return 0
    REGISTROS.mkdir(parents=True, exist_ok=True)
    ULTIMA_REVISION.write_text(huella, encoding="utf-8")
    if "sin hallazgos" in texto.lower():
        return 0
    print(
        "Codex reviso el diff y reporta lo siguiente. Verifica cada punto antes de "
        "actuar; descarta lo que no se sostenga:\n\n" + texto,
        file=sys.stderr,
    )
    return 2


def estado() -> int:
    """Dice que agentes puede usar esta maquina. Nunca falla: solo informa."""
    for nombre, uso in (("codex", "delegar y revisar"), ("agy", "delegar UI y lecturas")):
        ruta = shutil.which(nombre)
        if ruta is None:
            print(f"[delegar] {nombre}: no instalado ({uso} no disponible aqui)")
            continue
        try:
            version = subprocess.run(
                [ruta, "--version"], capture_output=True, text=True, timeout=20
            ).stdout.strip().splitlines()
        except (OSError, subprocess.SubprocessError):
            version = []
        print(f"[delegar] {nombre}: {version[0] if version else 'instalado'} ({ruta})")
    revision = "prendida" if os.environ.get(VARIABLE_REVISION) == "1" else "apagada"
    print(f"[delegar] revision automatica de Codex ({VARIABLE_REVISION}): {revision}")
    return 0


def limpiar() -> int:
    """Quita los worktrees y ramas que dejo este script. No toca otras ramas."""
    quitados = 0
    for bloque in git("worktree", "list", "--porcelain").split("\n\n"):
        lineas = bloque.splitlines()
        ruta = next((x[9:] for x in lineas if x.startswith("worktree ")), "")
        if ruta and Path(ruta).resolve().parent == WORKTREES.resolve():
            git("worktree", "remove", "--force", ruta)
            quitados += 1
    git("worktree", "prune")
    ramas = git("branch", "--list", f"{PREFIJO_RAMA}*", "--format=%(refname:short)").splitlines()
    for rama in filter(None, ramas):
        git("branch", "-D", rama)
    print(f"[delegar] {quitados} worktrees y {len([r for r in ramas if r])} ramas quitadas")
    return 0


def main() -> int:
    # En Windows la consola usa cp1252 y los acentos salen corruptos.
    for flujo in (sys.stdout, sys.stderr):
        if isinstance(flujo, io.TextIOWrapper):
            flujo.reconfigure(encoding="utf-8")
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
    sub.add_parser("estado", help="que CLIs de agentes hay en esta maquina")
    sub.add_parser("limpiar", help="quitar worktrees y ramas delegar/*")
    sub.add_parser("hook-stop", help="punto de entrada del hook Stop")
    args = parser.parse_args()

    try:
        if args.accion == "hook-stop":
            return hook_stop()
        if args.accion == "estado":
            return estado()
        if args.accion == "limpiar":
            return limpiar()
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
