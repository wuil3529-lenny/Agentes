"""
skill_git.py — Habilidad: Control de Versiones Git
====================================================
Herramientas para gestionar repositorios Git de forma autónoma.
Zoro puede inicializar repos, hacer commits, manejar ramas y sincronizar
con remotos como parte de sus misiones de desarrollo de software.

Herramientas disponibles:
  - git_init       : Inicializa un repositorio Git en un directorio
  - git_status     : Estado del repositorio (archivos modificados, sin seguimiento)
  - git_add        : Agrega archivos al staging area
  - git_commit     : Hace un commit con mensaje
  - git_log        : Historial de commits recientes
  - git_branch     : Lista, crea o elimina ramas
  - git_checkout   : Cambia de rama o crea una nueva
  - git_clone      : Clona un repositorio remoto
  - git_pull       : Descarga y fusiona cambios del remoto
  - git_push       : Sube commits al repositorio remoto
  - git_diff       : Diferencias entre working tree y último commit

Requisitos:
  - Git instalado y disponible en PATH (git version 2.52.0.windows.1 ✅)

Documentación en Obsidian: agentes/Zoro_Skills.md
"""

import json
import subprocess
from pathlib import Path
from langchain_core.tools import tool


# ─── Helper interno ────────────────────────────────────────────────────────────

def _git(args: list[str], cwd: str, timeout: int = 60) -> dict:
    """
    Ejecuta un subcomando git y retorna stdout, stderr y código de retorno.
    NO usa shell=True para evitar inyección de comandos.
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
        return {"ok": False, "stdout": "", "stderr": "Git no encontrado en PATH. Verifica la instalación.", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


# ══════════════════════════════════════════════════════════════════════════════
# Herramientas Git
# ══════════════════════════════════════════════════════════════════════════════

@tool
def git_init(directorio: str, rama_inicial: str) -> str:
    """
    Inicializa un nuevo repositorio Git vacío en el directorio especificado.
    Si el repositorio ya existe, no hace nada destructivo.

    Args:
        directorio: Ruta absoluta del directorio donde inicializar el repo
                    (ej: C:/Users/admin/proyectos/mi-app)
        rama_inicial: Nombre de la rama principal (ej: "main" o "master")
    """
    try:
        Path(directorio).mkdir(parents=True, exist_ok=True)
        
        # --- Mitigacion de Seguridad ---
        # Crear .gitignore por defecto si no existe para evitar leaks de credenciales (Reporte de Robin)
        gitignore_path = Path(directorio) / ".gitignore"
        if not gitignore_path.exists():
            contenido_seguro = ".env\n*.env\n.env.*\n*.key\n*.pem\n__pycache__/\n.venv/\nnode_modules/\n"
            gitignore_path.write_text(contenido_seguro, encoding="utf-8")
        # -------------------------------
        
        r = _git(["init", f"--initial-branch={rama_inicial}"], directorio)

        if not r["ok"] and "unknown switch" in r["stderr"]:
            # Git antiguo que no soporta --initial-branch
            r = _git(["init"], directorio)

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "rama_inicial": rama_inicial,
            "mensaje": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_status(directorio: str) -> str:
    """
    Muestra el estado actual del repositorio Git:
    archivos modificados, sin seguimiento (untracked), staged y rama actual.

    Args:
        directorio: Ruta absoluta al directorio del repositorio Git
    """
    try:
        r = _git(["status", "--short", "--branch"], directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "estado": r["stdout"],
            "error": r["stderr"] if not r["ok"] else None
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_add(directorio: str, patron: str) -> str:
    """
    Agrega archivos al staging area (índice) de Git para el próximo commit.

    Args:
        directorio: Ruta absoluta al repositorio Git
        patron: Patrón de archivos a agregar. Ejemplos:
                "."          → todos los archivos modificados y nuevos
                "src/"       → toda la carpeta src/
                "app.py"     → un archivo específico
                "*.js"       → todos los archivos .js
    """
    try:
        r = _git(["add", "--", patron], directorio)
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "patron_agregado": patron,
            "mensaje": r["stdout"] or ("Archivos agregados al staging." if r["ok"] else r["stderr"])
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_commit(directorio: str, mensaje: str) -> str:
    """
    Crea un commit con los archivos en staging y el mensaje indicado.
    Configura un autor genérico si el repo aún no tiene user.name/user.email.

    Args:
        directorio: Ruta absoluta al repositorio Git
        mensaje: Mensaje descriptivo del commit (ej: "feat: agregar autenticación JWT")
    """
    try:
        # Configurar identidad temporal si no está definida globalmente
        _git(["config", "user.email", "zoro@straw-hat.crew"], directorio)
        _git(["config", "user.name", "Roronoa Zoro"], directorio)

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
def git_log(directorio: str, cantidad: int) -> str:
    """
    Muestra el historial de commits recientes del repositorio.

    Args:
        directorio: Ruta absoluta al repositorio Git
        cantidad: Número de commits a mostrar (ej: 10). Máximo recomendado: 50.
    """
    try:
        limite = min(max(1, cantidad), 50)  # Clamp entre 1 y 50
        r = _git(
            ["log", f"-{limite}", "--oneline", "--decorate", "--graph"],
            directorio
        )
        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "directorio": directorio,
            "commits_mostrados": limite,
            "historial": r["stdout"],
            "error": r["stderr"] if not r["ok"] else None
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_branch(directorio: str, accion: str, nombre_rama: str) -> str:
    """
    Gestiona ramas del repositorio: listar, crear o eliminar.

    Args:
        directorio: Ruta absoluta al repositorio Git
        accion: Acción a realizar:
                "listar"   → muestra todas las ramas (locales y remotas)
                "crear"    → crea una nueva rama sin cambiar a ella
                "eliminar" → elimina la rama especificada (solo si ya fue mergeada)
        nombre_rama: Nombre de la rama para "crear" o "eliminar".
                     Usar "" si la acción es "listar".
    """
    try:
        if accion == "listar":
            r = _git(["branch", "-a", "-v"], directorio)
        elif accion == "crear":
            if not nombre_rama:
                return json.dumps({"status": "error", "mensaje": "Se requiere nombre_rama para crear."})
            r = _git(["branch", "--", nombre_rama], directorio)
        elif accion == "eliminar":
            if not nombre_rama:
                return json.dumps({"status": "error", "mensaje": "Se requiere nombre_rama para eliminar."})
            r = _git(["branch", "-d", "--", nombre_rama], directorio)
        else:
            return json.dumps({"status": "error", "mensaje": f"Acción no válida: '{accion}'. Usa 'listar', 'crear' o 'eliminar'."})

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "accion": accion,
            "rama": nombre_rama or "(todas)",
            "resultado": r["stdout"] or r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def git_checkout(directorio: str, rama: str, crear_nueva: bool) -> str:
    """
    Cambia a una rama existente o crea y cambia a una nueva rama.

    Args:
        directorio: Ruta absoluta al repositorio Git
        rama: Nombre de la rama destino (ej: "develop", "feature/auth")
        crear_nueva: Si True, crea la rama y cambia a ella en un solo paso
                     (equivalente a `git checkout -b <rama>`).
                     Si False, solo cambia a una rama existente.
    """
    try:
        args = ["checkout"]
        if crear_nueva:
            args.append("-b")
        args.append("--")
        args.append(rama)

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
        url_repositorio: URL del repositorio a clonar.
                         Soporta HTTPS y SSH:
                         - "https://github.com/usuario/repo.git"
                         - "git@github.com:usuario/repo.git"
        directorio_destino: Ruta absoluta donde se clonará el repositorio
                            (ej: C:/Users/admin/proyectos/mi-clon)
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
def git_pull(directorio: str, remoto: str, rama: str) -> str:
    """
    Descarga y fusiona los cambios del repositorio remoto en la rama actual.

    Args:
        directorio: Ruta absoluta al repositorio Git local
        remoto: Nombre del remoto (normalmente "origin")
        rama: Nombre de la rama remota a traer (ej: "main", "develop").
              Usar "" para hacer pull de la rama actual configurada por tracking.
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
def git_push(directorio: str, remoto: str, rama: str) -> str:
    """
    Sube los commits locales al repositorio remoto.

    Args:
        directorio: Ruta absoluta al repositorio Git local
        remoto: Nombre del remoto (normalmente "origin")
        rama: Nombre de la rama a empujar (ej: "main", "feature/nueva-funcion").
              Usar "" para empujar la rama actual con su tracking configurado.
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
def git_diff(directorio: str, comparar_staged: bool) -> str:
    """
    Muestra las diferencias de código entre el estado actual y el último commit.

    Args:
        directorio: Ruta absoluta al repositorio Git
        comparar_staged: Si True, muestra diferencias entre staging y último commit
                         (equivalente a `git diff --cached`).
                         Si False, muestra diferencias entre working tree y staging
                         (equivalente a `git diff`).
    """
    try:
        args = ["diff"]
        if comparar_staged:
            args.append("--cached")

        # Limitar la salida para no saturar el contexto del LLM
        args += ["--stat", "--unified=3"]

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


# ─── Lista de herramientas exportadas ──────────────────────────────────────────
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
