"""
skill_mobile.py — Habilidad: Desarrollo de Aplicaciones Móviles
================================================================
Herramientas para generar proyectos móviles multiplataforma (iOS y Android)
utilizando el ecosistema React Native gestionado (Expo) y bare CLI.

Herramientas disponibles:
  - mobile_scaffold_expo : Inicializa una app móvil con Expo (recomendado, multiplataforma ágil)
  - mobile_scaffold_rn   : Inicializa una app móvil con React Native CLI (bare workflow)
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


def obtener_prompt_mobile() -> str:
    """
    System Prompt especializado y encapsulado para el desarrollo de aplicaciones móviles
    del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO DESARROLLO DE APLICACIONES MÓVILES ACTIVO 🛑]
Eres el Arquitecto e Ingeniero de Software Móvil del Subagente de Desarrollo.
Tu misión es estructurar aplicaciones móviles multiplataforma nativas para iOS y Android con altos estándares de rendimiento, UX fluida y tooling moderno.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. SELECCIÓN DE ENFOQUE (EXPO FIRST):
   - Prefiere SIEMPRE `mobile_scaffold_expo` como primera opción. Expo elimina la necesidad de compilar código nativo de Android/iOS localmente y permite pruebas inmediatas mediante Expo Go escaneando un código QR.
   - Utiliza `mobile_scaffold_rn` únicamente si la misión exige módulos nativos en C++/Objective-C/Kotlin incompatibles con el entorno gestionado de Expo.
2. RUTAS DE ALOJAMIENTO:
   - Todo proyecto móvil debe crearse bajo `/app/Subagente_Desarrollo/proyectos/<nombre_app>/`.
3. CONFIGURACIÓN SIN BLOQUEOS:
   - Los comandos de scaffolding móvil usan flags de no instalación inmediata (`--no-install` o `--skip-install`) para evitar saturar el contenedor o congelar la terminal por descargas masivas no requeridas en la fase inicial.
"""


def _ejecutar(comando: str, cwd: str, timeout: int = 180) -> Dict[str, Any]:
    """Helper interno seguro para comandos de terminal móvil."""
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
                "stderr": f"Directorio no encontrado: {cwd}",
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
            "stdout": r.stdout.strip()[:3000],
            "stderr": r.stderr.strip()[:1500],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout superado ({timeout}s).", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def mobile_scaffold_expo(nombre_proyecto: str, directorio_destino: str = "") -> str:
    """
    Crea una aplicación móvil multiplataforma gestionada con Expo (React Native).
    Opción recomendada por defecto para iOS y Android.

    Args:
        nombre_proyecto: Nombre de la aplicación (ej: 'app-pedidos', 'cliente-movil').
        directorio_destino: Carpeta contenedora. Si se omite, se aloja en '/app/Subagente_Desarrollo/proyectos/'.
    """
    try:
        dest_base = Path(directorio_destino) if directorio_destino else _PROYECTOS
        dest_base.mkdir(parents=True, exist_ok=True)
        proyecto_path = dest_base / nombre_proyecto

        cmd = f"npx create-expo-app@latest {nombre_proyecto} --no-install"
        r = _ejecutar(cmd, str(dest_base), timeout=180)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": f"No se pudo crear el proyecto Expo: {r['stderr']}",
                "sugerencia": "Verifica si Node.js y npx están instalados y accesibles en el PATH."
            })

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "tipo": "Expo (React Native Gestionado)",
            "ruta": str(proyecto_path),
            "siguiente_paso": [
                f"cd {proyecto_path}",
                "npm install",
                "npx expo start"
            ],
            "mensaje": f"Estructura base de aplicación móvil Expo creada en {proyecto_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def mobile_scaffold_rn(nombre_proyecto: str, directorio_destino: str = "") -> str:
    """
    Crea una aplicación móvil con React Native CLI nativo (bare workflow).
    Requiere Node.js, JDK y configuración de Android Studio / Xcode.

    Args:
        nombre_proyecto: Nombre de la app en PascalCase (ej: 'AppClientes', 'PortalMovil').
        directorio_destino: Carpeta contenedora. Si se omite, se aloja en '/app/Subagente_Desarrollo/proyectos/'.
    """
    try:
        dest_base = Path(directorio_destino) if directorio_destino else _PROYECTOS
        dest_base.mkdir(parents=True, exist_ok=True)
        proyecto_path = dest_base / nombre_proyecto

        cmd = f"npx react-native@latest init {nombre_proyecto} --skip-install"
        r = _ejecutar(cmd, str(dest_base), timeout=180)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": f"Error creando el proyecto React Native CLI: {r['stderr']}",
                "alternativa": "Usa mobile_scaffold_expo para un entorno multiplataforma sin requerimientos de SDK nativos."
            })

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "tipo": "React Native Bare CLI",
            "ruta": str(proyecto_path),
            "siguiente_paso": [
                f"cd {proyecto_path}",
                "npm install",
                "npx react-native run-android"
            ],
            "mensaje": f"Proyecto React Native CLI generado exitosamente en {proyecto_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_MOBILE = [
    mobile_scaffold_expo,
    mobile_scaffold_rn
]
