"""
skill_software.py — Habilidad: Desarrollo y Entornos de Software Python
========================================================================
Herramientas para crear, aislar y ejecutar proyectos de software en Python.
Soporte para virtualenvs, instalación de paquetes y ejecución de scripts.

Herramientas disponibles:
  - python_ejecutar_script : Ejecuta un script Python capturando stdout/stderr
  - python_pip_instalar    : Instala paquetes con pip (detectando .venv automáticamente)
  - python_crear_venv      : Crea un entorno virtual aislado con requirements.txt y .gitignore
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_software() -> str:
    """
    System Prompt especializado y encapsulado para el desarrollo y ejecución
    de software en Python del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO DESARROLLO DE SOFTWARE PYTHON ACTIVO 🛑]
Eres el Ingeniero de Software Backend y Entornos de Ejecución del Subagente de Desarrollo.
Tu misión es construir, aislar y ejecutar código Python con estándares de producción, gestión limpia de dependencias y aislamiento estricto en entornos virtuales.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. AISLAMIENTO DE DEPENDENCIAS (.venv OBLIGATORIO):
   - Para proyectos medianos o grandes, crea SIEMPRE un entorno virtual con `python_crear_venv` antes de instalar librerías.
   - Toda dependencia debe quedar documentada en un archivo `requirements.txt` en la raíz del proyecto.
2. EJECUCIÓN SEGURA DE SCRIPTS:
   - Antes de ejecutar un script con `python_ejecutar_script`, valida que el archivo exista en disco y que sus insumos o argumentos sean correctos.
   - Monitorea el código de retorno. Si un script arroja un código distinto de 0, analiza el `stderr` inmediatamente para corregir el fallo antes de volver a intentar.
3. PREVENCIÓN DE INYECCIÓN DE COMANDOS:
   - Nunca pases argumentos concatenados con caracteres de control de shell peligrosos (`&`, `|`, `;`, `>`, `<`, `$`).
4. VERIFICACIÓN Y AUTOCORRECCIÓN:
   - Si una librería falta durante la ejecución (`ModuleNotFoundError`), utiliza `python_pip_instalar` para resolverla de forma quirúrgica y actualiza el `requirements.txt`.
"""


def _ejecutar(comando: str, cwd: str, timeout: int = 120) -> Dict[str, Any]:
    """Helper interno resiliente para ejecutar comandos Python/pip."""
    try:
        caracteres_peligrosos = ['&', '|', ';', '>', '<', '$', '`']
        if any(c in comando for c in caracteres_peligrosos):
            return {
                "ok": False,
                "stdout": "",
                "stderr": "Violación de seguridad: inyección de comandos o caracteres de control detectados.",
                "code": -1
            }

        dir_cwd = Path(cwd)
        if not dir_cwd.exists():
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Directorio de trabajo no encontrado: {cwd}",
                "code": -1
            }

        r = subprocess.run(
            comando,
            shell=True,
            cwd=str(dir_cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip()[:3500],
            "stderr": r.stderr.strip()[:2000],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout superado ({timeout}s).", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def python_ejecutar_script(ruta_script: str, argumentos: str = "") -> str:
    """
    Ejecuta un script Python y retorna su salida (stdout, stderr y código de retorno).

    Args:
        ruta_script: Ruta absoluta al script .py a ejecutar (ej: /app/Subagente_Desarrollo/proyectos/mi_app/main.py).
        argumentos: Argumentos de línea de comandos para el script (ej: '--debug --port 8080'). Dejar vacío si no hay argumentos.
    """
    try:
        script = Path(ruta_script)
        if not script.exists():
            return json.dumps({
                "status": "error",
                "mensaje": f"Script no encontrado en disco: {ruta_script}"
            })

        # Detectar si hay un entorno virtual en la carpeta del script o en sus ancestros
        python_exe = sys.executable
        proyecto = script.parent
        venv_python_win = proyecto / ".venv" / "Scripts" / "python.exe"
        venv_python_nix = proyecto / ".venv" / "bin" / "python"

        if venv_python_win.exists():
            python_exe = str(venv_python_win)
        elif venv_python_nix.exists():
            python_exe = str(venv_python_nix)

        args_limpios = argumentos.strip() if argumentos else ""
        cmd = f'"{python_exe}" "{script}" {args_limpios}'.strip()
        r = _ejecutar(cmd, str(script.parent), timeout=120)

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "script": str(script),
            "interprete_usado": python_exe,
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
    Si existe un entorno virtual (.venv) en el directorio, lo utiliza automáticamente.

    Args:
        paquetes: Paquetes a instalar separados por espacio (ej: 'fastapi uvicorn requests').
        directorio_proyecto: Directorio raíz del proyecto (ej: /app/Subagente_Desarrollo/proyectos/mi_app).
    """
    try:
        proyecto = Path(directorio_proyecto)
        if not proyecto.exists():
            return json.dumps({
                "status": "error",
                "mensaje": f"Directorio del proyecto no encontrado: {directorio_proyecto}"
            })

        # Detectar si existe un entorno virtual activo en el proyecto
        venv_pip_win = proyecto / ".venv" / "Scripts" / "pip.exe"
        venv_pip_nix = proyecto / ".venv" / "bin" / "pip"

        if venv_pip_win.exists():
            cmd = f'"{venv_pip_win}" install {paquetes}'
            usando_venv = True
        elif venv_pip_nix.exists():
            cmd = f'"{venv_pip_nix}" install {paquetes}'
            usando_venv = True
        else:
            cmd = f'"{sys.executable}" -m pip install {paquetes}'
            usando_venv = False

        r = _ejecutar(cmd, str(proyecto), timeout=180)

        return json.dumps({
            "status": "success" if r["ok"] else "error",
            "paquetes": paquetes,
            "directorio": str(proyecto),
            "venv_usado": usando_venv,
            "stdout": r["stdout"],
            "stderr": r["stderr"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def python_crear_venv(directorio_proyecto: str) -> str:
    """
    Crea un entorno virtual Python (.venv) en el directorio del proyecto especificado.
    Auto-genera un requirements.txt y un .gitignore si no existen.

    Args:
        directorio_proyecto: Directorio raíz donde se alojará el entorno virtual (ej: /app/Subagente_Desarrollo/proyectos/mi_app).
    """
    try:
        proyecto = Path(directorio_proyecto)
        proyecto.mkdir(parents=True, exist_ok=True)
        venv_path = proyecto / ".venv"

        python_exe = sys.executable
        cmd = f'"{python_exe}" -m venv "{venv_path}"'
        r = _ejecutar(cmd, str(proyecto), timeout=90)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": f"Error creando el entorno virtual: {r['stderr']}",
                "stderr": r["stderr"]
            })

        # Crear requirements.txt inicial si no existe
        req_file = proyecto / "requirements.txt"
        req_creado = False
        if not req_file.exists():
            req_file.write_text("# Dependencias del proyecto\n", encoding="utf-8")
            req_creado = True

        # Crear .gitignore básico si no existe
        gitignore_file = proyecto / ".gitignore"
        git_creado = False
        if not gitignore_file.exists():
            gitignore_file.write_text(".venv/\n__pycache__/\n*.pyc\n.env\n", encoding="utf-8")
            git_creado = True

        return json.dumps({
            "status": "success",
            "venv": str(venv_path),
            "directorio": str(proyecto),
            "requirements_creado": req_creado,
            "gitignore_creado": git_creado,
            "mensaje": "Entorno virtual .venv creado y configurado exitosamente."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_SOFTWARE = [
    python_ejecutar_script,
    python_pip_instalar,
    python_crear_venv
]
