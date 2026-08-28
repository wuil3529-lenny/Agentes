"""
skill_software.py — Habilidad: Desarrollo de Software Python
==============================================================
Herramientas para crear, ejecutar y gestionar proyectos de software en Python.

Capacidades:
  - Ejecutar scripts Python           → python_ejecutar_script()
  - Instalar paquetes con pip         → python_pip_instalar()
  - Crear entornos virtuales          → python_crear_venv()

Stack soportado:
  - Python 3.x (scripts, APIs, automatizaciones)
  - FastAPI / Flask (APIs REST)
  - venv (entornos virtuales)
  - pip (gestión de dependencias)

Documentación en Obsidian: agentes/Zoro_Skills.md
"""

import json
import subprocess
import sys
from pathlib import Path
from langchain_core.tools import tool


def _ejecutar(comando: str, cwd: str, timeout: int = 120) -> dict:
    """Helper interno para ejecutar comandos Python/pip."""
    try:
        caracteres_peligrosos = ['&', '|', ';', '>', '<', '$', '`']
        if any(c in comando for c in caracteres_peligrosos):
            return json.dumps({"status": "error", "mensaje": "Violación de seguridad: inyección de comandos detectada."})

        r = subprocess.run(
            comando, shell=True, cwd=cwd,
            capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout[:3000],
            "stderr": r.stderr[:1500],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout superado ({timeout}s).", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def python_ejecutar_script(ruta_script: str, argumentos: str) -> str:
    """
    Ejecuta un script Python y retorna su salida (stdout + stderr).

    Args:
        ruta_script: Ruta absoluta al script .py a ejecutar (ej: C:/proyecto/app.py)
        argumentos: Argumentos de línea de comandos para el script (ej: "--debug --port 8080")
                    Usar "" si no hay argumentos.
    """
    try:
        script = Path(ruta_script)
        if not script.exists():
            return json.dumps({"status": "error", "mensaje": f"Script no encontrado: {ruta_script}"})

        python_exe = sys.executable  # Usa el Python actual del sistema
        cmd = f'"{python_exe}" "{script}" {argumentos}'.strip()
        r = _ejecutar(cmd, str(script.parent), timeout=60)

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "script": ruta_script,
            "codigo_retorno": r["code"],
            "stdout": r["stdout"],
            "stderr": r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def python_pip_instalar(paquetes: str, directorio_proyecto: str) -> str:
    """
    Instala paquetes Python con pip en el entorno del proyecto.
    Si existe un entorno virtual (.venv) en el directorio, lo usa automáticamente.

    Args:
        paquetes: Paquetes a instalar separados por espacio (ej: "fastapi uvicorn requests")
        directorio_proyecto: Directorio raíz del proyecto (ej: C:/Users/admin/mi-api)
    """
    try:
        proyecto = Path(directorio_proyecto)

        # Detectar si hay un entorno virtual activo en el proyecto
        venv_pip = proyecto / ".venv" / "Scripts" / "pip.exe"  # Windows
        if not venv_pip.exists():
            venv_pip = proyecto / ".venv" / "bin" / "pip"       # Unix
        
        if venv_pip.exists():
            cmd = f'"{venv_pip}" install {paquetes}'
        else:
            cmd = f'pip install {paquetes}'

        r = _ejecutar(cmd, str(proyecto), timeout=120)

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "paquetes": paquetes,
            "venv_usado": venv_pip.exists(),
            "stdout": r["stdout"],
            "stderr": r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def python_crear_venv(directorio_proyecto: str) -> str:
    """
    Crea un entorno virtual Python en el directorio del proyecto.
    El entorno se crea en la subcarpeta '.venv'.
    Crea también un requirements.txt vacío si no existe.

    Args:
        directorio_proyecto: Directorio raíz del proyecto (ej: C:/Users/admin/mi-api)
    """
    try:
        proyecto = Path(directorio_proyecto)
        proyecto.mkdir(parents=True, exist_ok=True)
        venv_path = proyecto / ".venv"

        python_exe = sys.executable
        cmd = f'"{python_exe}" -m venv "{venv_path}"'
        r = _ejecutar(cmd, str(proyecto), timeout=60)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": "Error creando el entorno virtual.",
                "stderr": r["stderr"]
            })

        # Crear requirements.txt vacío si no existe
        req_file = proyecto / "requirements.txt"
        if not req_file.exists():
            req_file.write_text("# Dependencias del proyecto\n", encoding="utf-8")

        # Crear .gitignore básico si no existe
        gitignore = proyecto / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(".venv/\n__pycache__/\n*.pyc\n.env\n", encoding="utf-8")

        return json.dumps({
            "status": "success",
            "venv": str(venv_path),
            "activar_windows": str(venv_path / "Scripts" / "activate"),
            "activar_unix": str(venv_path / "bin" / "activate"),
            "archivos_creados": [
                str(req_file) if not req_file.exists() else None,
                str(gitignore) if not gitignore.exists() else None
            ],
            "siguiente_paso": f"Activar con: {venv_path / 'Scripts' / 'activate'}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas de este skill
HERRAMIENTAS_SOFTWARE = [python_ejecutar_script, python_pip_instalar, python_crear_venv]
