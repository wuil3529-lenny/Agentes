"""
skill_git.py — Habilidad: Control de Versiones Git
====================================================
Herramientas para gestionar repositorios Git de forma autónoma con rigor técnico,
blindaje contra fugas de credenciales y buenas prácticas de versionado.

Herramientas disponibles:
  - git_init       : Inicializar nuevo repositorio con .gitignore seguro
  - git_status     : Inspección de estado (staged, unstaged, untracked, branch)
  - git_add        : Agregar archivos al staging area con patrones controlados
  - git_commit     : Creación de commits estructurados bajo Conventional Commits
  - git_log        : Historial gráfico y resumido de commits
  - git_branch     : Listar, crear o eliminar ramas
  - git_checkout   : Conmutar de rama o crear rama nueva
  - git_clone      : Clonar repositorios remotos (HTTPS / SSH)
  - git_pull       : Sincronizar y fusionar cambios desde el repositorio remoto
  - git_push       : Publicar commits hacia el remoto
  - git_diff       : Diferencias de código (staged vs working tree)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_git() -> str:
    """
    System Prompt especializado y encapsulado para el control de versiones con Git
    del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO CONTROL DE VERSIONES GIT ACTIVO 🛑]
Eres el Especialista en Control de Versiones y Arquitectura de Código del Subagente de Desarrollo.
Tu misión es gestionar la evolución histórica del software con precisión quirúrgica, asegurando que cada repositorio mantenga un historial limpio, trazable y libre de fugas de seguridad.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. SEGURIDAD Y PREVENCIÓN DE FUGAS (.gitignore PRIMERO):
   - Todo nuevo repositorio inicializado con `git_init` DEBE contar con un archivo `.gitignore` estricto que excluya `.env`, claves privadas (`*.pem`, `*.key`), tokens de acceso (`token.json`), entornos virtuales (`.venv/`) y dependencias (`node_modules/`, `__pycache__/`).
   - NUNCA agregues archivos de credenciales al staging area con `git_add`.
2. ESTÁNDAR DE COMMITS CONVENCIONALES (Conventional Commits):
   - Redacta mensajes de commit en español con prefijos semánticos formales:
     - `feat:` Nueva funcionalidad para el usuario o sistema.
     - `fix:` Corrección de un fallo o error en el código.
     - `refactor:` Reestructuración interna sin alterar el comportamiento.
     - `test:` Inclusión o ajuste de suites de prueba.
     - `docs:` Modificaciones o creación de documentación.
     - `chore:` Tareas rutinarias, configuración de build o dependencias.
3. INSPECCIÓN PREVIA OBLIGATORIA:
   - Antes de ejecutar `git_commit`, consulta SIEMPRE `git_status` y `git_diff` para verificar exactamente qué cambios van a consolidarse.
4. INTEGRIDAD DE RAMAS:
   - No realices commits ciegos directamente sobre ramas productivas si la misión exige aislamiento en una rama de características (`feature/...` o `fix/...`).
5. PREVENCIÓN DE COMANDOS DESTRUCTIVOS:
   - Quedan prohibidos `git reset --hard` sobre referencias desconocidas, `git clean -fdx` indiscriminados o `git push --force` destructivos sin autorización explícita.
"""


def _normalizar(ruta: str) -> str:
    return str(Path(ruta).resolve()).replace("\\", "/")


def _git(args: List[str], cwd: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Ejecuta un subcomando git de manera segura evitando inyección de shell.
    """
    try:
        directorio = Path(cwd)
        if not directorio.exists():
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Directorio no encontrado: {cwd}",
                "code": -1
            }

        resultado = subprocess.run(
            ["git"] + args,
            cwd=str(directorio),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        return {
            "ok": resultado.returncode == 0,
            "stdout": resultado.stdout.strip()[:4000],
            "stderr": resultado.stderr.strip()[:2000],
            "code": resultado.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout superado ({timeout}s).", "code": -1}
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "Git no encontrado en PATH del sistema. Verifica la instalación.", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def git_init(directorio: str, rama_inicial: str = "main") -> str:
    """
    Inicializa un nuevo repositorio Git en el directorio especificado.
    Crea automáticamente un .gitignore robusto para prevenir fugas de secretos.

    Args:
        directorio: Ruta absoluta del directorio donde inicializar el repo (ej: /app/Subagente_Desarrollo/proyectos/mi_app).
        rama_inicial: Nombre de la rama principal por defecto (ej: 'main').
    """
    try:
        dir_path = Path(directorio)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Mitigación preventiva: generar .gitignore estricto
        gitignore_path = dir_path / ".gitignore"
        if not gitignore_path.exists():
            contenido_seguro = (
                "# Secretos y credenciales\n"
                ".env\n*.env\n.env.*\n*.key\n*.pem\ntoken.json\ncredentials.json\n\n"
                "# Python y entornos virtuales\n"
                "__pycache__/\n*.py[cod]\n*$py.class\n.venv/\nenv/\nvenv/\n\n"
                "# Node.js\n"
                "node_modules/\nnpm-debug.log*\n\n"
                "# Archivos de sistema y temporales\n"
                ".DS_Store\nThumbs.db\n*.tmp\n"
            )
            gitignore_path.write_text(contenido_seguro, encoding="utf-8")

        r = _git(["init", f"--initial-branch={rama_inicial}"], directorio)
        if not r["ok"] and "unknown switch" in r["stderr"]:
            # Fallback para versiones antiguas de Git que no soportan --initial-branch
            r = _git(["init"], directorio)

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "rama_inicial": rama_inicial,
            "mensaje": r["stdout"] or r["stderr"],
            "gitignore_protegido": True
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_status(directorio: str) -> str:
    """
    Inspecciona y devuelve el estado actual del repositorio Git:
    rama activa, archivos staged, modificados y untracked.

    Args:
        directorio: Ruta absoluta al directorio del repositorio Git.
    """
    try:
        r = _git(["status", "--short", "--branch"], directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "estado": r["stdout"] if r["stdout"] else "(árbol de trabajo limpio)",
            "error": r["stderr"] if not r["ok"] else None
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_add(directorio: str, patron: str = ".") -> str:
    """
    Agrega archivos al staging area (índice) de Git para el próximo commit.

    Args:
        directorio: Ruta absoluta al repositorio Git.
        patron: Patrón de archivos a agregar (ej: '.', 'src/', 'app.py', '*.ts').
    """
    try:
        r = _git(["add", "--", patron], directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "patron_agregado": patron,
            "mensaje": r["stdout"] or ("Archivos agregados al staging exitosamente." if r["ok"] else r["stderr"])
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_commit(directorio: str, mensaje: str) -> str:
    """
    Crea un commit formal con los archivos en staging y un mensaje semántico estructurado.

    Args:
        directorio: Ruta absoluta al repositorio Git.
        mensaje: Mensaje descriptivo bajo Conventional Commits (ej: 'feat: implementar motor de autenticación JWT').
    """
    try:
        # Configurar identidad de commit por defecto si el repo es local
        _git(["config", "user.email", "desarrollo@tripulacion.local"], directorio)
        _git(["config", "user.name", "Subagente_Desarrollo"], directorio)

        r = _git(["commit", "-m", mensaje], directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "mensaje_commit": mensaje,
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_log(directorio: str, cantidad: int = 10) -> str:
    """
    Muestra el historial cronológico de commits recientes del repositorio.

    Args:
        directorio: Ruta absoluta al repositorio Git.
        cantidad: Número máximo de commits a mostrar (ej: 10, máximo 50).
    """
    try:
        limite = min(max(1, cantidad), 50)
        r = _git(["log", f"-{limite}", "--oneline", "--decorate", "--graph"], directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "commits_mostrados": limite,
            "historial": r["stdout"] if r["stdout"] else "(sin commits registrados aún)",
            "error": r["stderr"] if not r["ok"] else None
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_branch(directorio: str, accion: str = "listar", nombre_rama: str = "") -> str:
    """
    Gestiona ramas en el repositorio Git: listar, crear o eliminar.

    Args:
        directorio: Ruta absoluta al repositorio Git.
        accion: 'listar' (ver todas las ramas), 'crear' (crear rama nueva), 'eliminar' (borrar rama mergeada).
        nombre_rama: Nombre de la rama para crear o eliminar (dejar vacío para listar).
    """
    try:
        if accion == "listar":
            r = _git(["branch", "-a", "-v"], directorio)
        elif accion == "crear":
            if not nombre_rama:
                return json.dumps({"status": "error", "mensaje": "Se requiere el parámetro 'nombre_rama' para crear una rama."})
            r = _git(["branch", "--", nombre_rama], directorio)
        elif accion == "eliminar":
            if not nombre_rama:
                return json.dumps({"status": "error", "mensaje": "Se requiere el parámetro 'nombre_rama' para eliminar una rama."})
            r = _git(["branch", "-d", "--", nombre_rama], directorio)
        else:
            return json.dumps({"status": "error", "mensaje": f"Acción inválida '{accion}'. Usa 'listar', 'crear' o 'eliminar'."})

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "accion": accion,
            "rama": nombre_rama or "(todas)",
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_checkout(directorio: str, rama: str, crear_nueva: bool = False) -> str:
    """
    Conmuta a una rama existente o crea una nueva rama y cambia a ella.

    Args:
        directorio: Ruta absoluta al repositorio Git.
        rama: Nombre de la rama destino (ej: 'develop', 'feature/login').
        crear_nueva: Si es True, ejecuta 'git checkout -b <rama>'; si es False, solo cambia a una rama existente.
    """
    try:
        args = ["checkout"]
        if crear_nueva:
            args.append("-b")
        args.extend(["--", rama])

        r = _git(args, directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "rama_destino": rama,
            "rama_creada": crear_nueva,
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_clone(url_repositorio: str, directorio_destino: str) -> str:
    """
    Clona un repositorio remoto en el directorio local especificado.

    Args:
        url_repositorio: URL HTTPS o SSH del repositorio remoto a clonar.
        directorio_destino: Ruta absoluta donde se alojará el repositorio clonado.
    """
    try:
        destino = Path(directorio_destino)
        destino.mkdir(parents=True, exist_ok=True)

        r = _git(["clone", "--", url_repositorio, str(destino)], str(destino.parent), timeout=120)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "url": url_repositorio,
            "destino": directorio_destino,
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_pull(directorio: str, remoto: str = "origin", rama: str = "") -> str:
    """
    Descarga y fusiona cambios desde el repositorio remoto a la rama local actual.

    Args:
        directorio: Ruta absoluta al repositorio Git local.
        remoto: Nombre del repositorio remoto (normalmente 'origin').
        rama: Nombre de la rama a traer (ej: 'main'). Dejar vacío para usar la rama de tracking actual.
    """
    try:
        args = ["pull", "--", remoto]
        if rama:
            args.append(rama)

        r = _git(args, directorio, timeout=120)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "remoto": remoto,
            "rama": rama or "(tracking actual)",
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_push(directorio: str, remoto: str = "origin", rama: str = "") -> str:
    """
    Publica los commits locales hacia el repositorio remoto configurado.

    Args:
        directorio: Ruta absoluta al repositorio Git local.
        remoto: Nombre del repositorio remoto (normalmente 'origin').
        rama: Nombre de la rama a empujar (ej: 'main'). Dejar vacío para usar la rama actual.
    """
    try:
        args = ["push", "--", remoto]
        if rama:
            args.append(rama)

        r = _git(args, directorio, timeout=120)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "remoto": remoto,
            "rama": rama or "(rama actual)",
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_diff(directorio: str, comparar_staged: bool = False) -> str:
    """
    Muestra las diferencias de código entre el estado actual y el último commit.

    Args:
        directorio: Ruta absoluta al repositorio Git.
        comparar_staged: Si es True, compara staging con HEAD ('git diff --cached').
                         Si es False, compara el working tree con staging ('git diff').
    """
    try:
        args = ["diff"]
        if comparar_staged:
            args.append("--cached")
        args.extend(["--stat", "--unified=3"])

        r = _git(args, directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "modo": "staged (cached)" if comparar_staged else "working tree",
            "diff": r["stdout"] if r["stdout"] else "(sin cambios detectados)",
            "error": r["stderr"] if not r["ok"] else None
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_GIT = [
    git_init,
    git_status,
    git_add,
    git_commit,
    git_log,
    git_branch,
    git_checkout,
    git_clone,
    git_pull,
    git_push,
    git_diff,
]
