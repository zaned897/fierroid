"""`delegar.py limpiar` solo quita lo que el script creo, contra un repo git real."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "delegar.py"


def _cargar():
    spec = importlib.util.spec_from_file_location("delegar", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    _git(raiz, "init", "-q", "-b", "main")
    _git(raiz, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
         "--allow-empty", "-m", "inicio")
    return raiz


def test_limpiar_respeta_worktrees_ajenos(repo: Path, monkeypatch) -> None:
    delegar = _cargar()
    worktrees = repo / ".claude" / "worktrees"
    monkeypatch.setattr(delegar, "RAIZ", repo)
    monkeypatch.setattr(delegar, "WORKTREES", worktrees)
    monkeypatch.setattr(delegar, "git", lambda *a, cwd=repo: _git(cwd, *a))

    propio, rama_propia = delegar.crear_worktree("codex", "una tarea", "HEAD")
    ajeno = worktrees / "agent-favicon"  # como los de Claude Code o del usuario
    _git(repo, "worktree", "add", "-q", "-b", "claude/favicon", str(ajeno), "HEAD")
    (ajeno / "trabajo.txt").write_text("sin commit", encoding="utf-8")
    disfrazado = worktrees / "delegar-a-mano"  # nombre parecido, rama del usuario
    _git(repo, "worktree", "add", "-q", "-b", "mi-rama", str(disfrazado), "HEAD")

    assert delegar.limpiar() == 0

    assert not propio.exists()
    assert (ajeno / "trabajo.txt").read_text(encoding="utf-8") == "sin commit"
    assert disfrazado.exists()
    ramas = _git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert rama_propia not in ramas
    assert {"claude/favicon", "mi-rama", "main"} <= set(ramas)
