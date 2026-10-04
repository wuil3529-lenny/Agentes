"""
skill_limpiar_workspace.py — Habilidad: Higienización y Orden del Entorno de Trabajo
======================================================================================
Herramientas para mantener la estructura oficial del Subagente de Desarrollo,
purgar cachés (`__pycache__`, artefactos de compilación) y trasladar archivos
efímeros a la zona de cuarentena y scratch en `/app/Archivos_temporales/`.

Herramientas disponibles:
  - tool_limpiar_workspace       : Purga selectiva de cachés y temporales del entorno
  - tool_limpiar_habitacion      : Rutina estricta de estructura de directorios y orden
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_BASE_PATH = _APP_ROOT / _AGENTE
_TEMP = _APP_ROOT / "Archivos_temporales"

CARPETAS_OFICIALES = {"_agents", ".agents", "skills", "n8n-mcp-skills", "proyectos"}
ARCHIVOS_RAIZ_OFICIALES = {
    "subagente_desarrollo_agent.py",
    "Perfil_Subagente_Desarrollo.py",
    "Perfil_Subagente_Desarrollo.md"
}


def obtener_prompt_limpiar_workspace() -> str:
    """
    System Prompt especializado y encapsulado para el mantenimiento e higiene del entorno.
    """
    return """[🛑 HARD-STOP: MODO LIMPIEZA Y MANTENIMIENTO DEL WORKSPACE ACTIVO 🛑]
Eres el Operador de Higiene y Mantenimiento del Workspace del Subagente de Desarrollo.
Tu misión es erradicar archivos huérfanos, purgar compilaciones obsoletas y cachés (`__pycache__`) y mantener el territorio del agente ordenado y conforme al estándar de la tripulación.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRESERVACIÓN DE ENTREGABLES Y CÓDIGO:
   - NUNCA elimines carpetas de proyectos activos en `/app/Subagente_Desarrollo/proyectos/` ni módulos de `/app/Subagente_Desarrollo/skills/`.
2. PURGA EXCLUSIVA DE TEMPORALES Y CACHÉ:
   - La limpieza se enfoca en carpetas `__pycache__`, archivos `.pyc`, `.tmp` y temporales en `Archivos_temporales/`.
"""


def _limpiar_estructura() -> Dict[str, Any]:
    _TEMP.mkdir(parents=True, exist_ok=True)
    reporte = {
        "cache_eliminada": 0,
        "archivos_reubicados": 0,
        "carpetas_aseguradas": []
    }

    # 1. Asegurar existencia de las carpetas oficiales
    for dir_oficial in CARPETAS_OFICIALES:
        carpeta_path = _BASE_PATH / dir_oficial
        if not carpeta_path.exists():
            carpeta_path.mkdir(parents=True, exist_ok=True)
            reporte["carpetas_aseguradas"].append(dir_oficial)

    # 2. Eliminar __pycache__ en raíz y subcarpetas
    if _BASE_PATH.exists():
        for cache_dir in _BASE_PATH.rglob("__pycache__"):
            if cache_dir.is_dir():
                try:
                    shutil.rmtree(cache_dir)
                    reporte["cache_eliminada"] += 1
                except Exception:
                    pass

    return reporte


@tool
def tool_limpiar_workspace() -> str:
    """
    Ejecuta una purga higiénica de cachés (__pycache__) y valida la estructura de carpetas en el entorno de desarrollo.
    """
    try:
        reporte = _limpiar_estructura()
        return json.dumps({
            "status": "success",
            "reporte": reporte,
            "mensaje": f"Limpieza completada: {reporte['cache_eliminada']} carpetas de caché purgadas."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_limpiar_habitacion() -> str:
    """
    Alias canónico de la rutina de orden y limpieza para el Subagente de Desarrollo.
    """
    return tool_limpiar_workspace.invoke({})


HERRAMIENTAS_LIMPIAR_WORKSPACE = [
    tool_limpiar_workspace,
    tool_limpiar_habitacion
]
