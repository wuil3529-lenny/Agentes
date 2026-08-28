"""
skill_mobile.py — Habilidad: Desarrollo de Apps Móviles
=========================================================
Herramientas para crear aplicaciones móviles multiplataforma.

Stack soportado:
  - Expo (React Native gestionado) → mobile_scaffold_expo()   [más fácil, recomendado]
  - React Native CLI               → mobile_scaffold_rn()     [más control, requiere más config]

Prerrequisitos:
  - Node.js y npm instalados
  - Para Expo: solo npx (se instala automáticamente)
  - Para RN CLI: Android Studio / Xcode según la plataforma objetivo

Documentación en Obsidian: agentes/Zoro_Skills.md
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import json
import subprocess
from pathlib import Path
from langchain_core.tools import tool



def _ejecutar(comando: str, cwd: str, timeout: int = 180) -> dict:
    """Helper interno para ejecutar comandos de Node/npm."""
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
            "stdout": r.stdout[:2000],
            "stderr": r.stderr[:1000],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout superado ({timeout}s).", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def mobile_scaffold_expo(nombre_proyecto: str, directorio_destino: str) -> str:
    """
    Crea una app móvil con Expo (React Native gestionado).
    Opción recomendada: funciona en iOS y Android sin configuración nativa.
    Requiere Node.js. Comando: npx create-expo-app@latest <nombre>

    Args:
        nombre_proyecto: Nombre de la app (ej: "mi-app-movil", "tienda-online")
        directorio_destino: Carpeta padre donde se creará el proyecto (ej: "C:/Users/admin/Documents/Agentes/Zoro/proyectos")
    """
    directorio_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        dest = Path(directorio_destino)
        dest.mkdir(parents=True, exist_ok=True)
        proyecto_path = dest / nombre_proyecto

        cmd = f"npx create-expo-app@latest {nombre_proyecto} --no-install"
        r = _ejecutar(cmd, str(dest), timeout=180)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": "Error creando proyecto Expo. Verifica que Node.js esté instalado.",
                "stderr": r["stderr"]
            })

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "tipo": "Expo (React Native)",
            "ruta": str(proyecto_path),
            "siguiente_paso": [
                f"cd {proyecto_path}",
                "npm install",
                "npx expo start          # Inicia el servidor de desarrollo",
                "                        # Escanea el QR con Expo Go (iOS/Android)",
                "npx expo run:android    # Compila para Android",
                "npx expo run:ios        # Compila para iOS (solo en macOS)"
            ],
            "stdout": r["stdout"][:600]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def mobile_scaffold_rn(nombre_proyecto: str, directorio_destino: str) -> str:
    """
    Crea una app móvil con React Native CLI (modo bare, más control).
    Requiere Node.js, JDK para Android, y Xcode para iOS.
    Comando: npx react-native@latest init <nombre>

    Args:
        nombre_proyecto: Nombre de la app en PascalCase (ej: "MiApp", "TiendaOnline")
        directorio_destino: Carpeta padre donde se creará el proyecto (ej: "C:/Users/admin/Documents/Agentes/Zoro/proyectos")
    """
    directorio_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        dest = Path(directorio_destino)
        dest.mkdir(parents=True, exist_ok=True)
        proyecto_path = dest / nombre_proyecto

        cmd = f"npx react-native@latest init {nombre_proyecto} --skip-install"
        r = _ejecutar(cmd, str(dest), timeout=180)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": "Error creando proyecto React Native CLI. Verifica que Node.js y JDK estén instalados.",
                "stderr": r["stderr"],
                "alternativa": "Usa mobile_scaffold_expo() para una configuración más simple."
            })

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "tipo": "React Native CLI",
            "ruta": str(proyecto_path),
            "siguiente_paso": [
                f"cd {proyecto_path}",
                "npm install",
                "npx react-native run-android   # Requiere Android Studio + emulador",
                "npx react-native run-ios       # Solo en macOS con Xcode"
            ],
            "advertencia": "RN CLI requiere configuración nativa completa (Android Studio / Xcode).",
            "stdout": r["stdout"][:600]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas de este skill
HERRAMIENTAS_MOBILE = [mobile_scaffold_expo, mobile_scaffold_rn]
