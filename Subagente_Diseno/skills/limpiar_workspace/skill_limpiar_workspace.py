"""
skill_limpiar_workspace.py — Higiene de Workspace, Sanitización y Orden
========================================================================
Herramientas para mantener la estructura oficial de Subagente_Diseno:
- 3 Carpetas oficiales: _agents, informes, skills
- Archivos raíz oficiales: subagente_diseno_agent.py, requirements.txt
- Purga de __pycache__ y reubicación de temporales a Archivos_temporales/
"""

import os
import shutil
import json
from pathlib import Path
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_BASE_PATH = _APP_ROOT / "Subagente_Diseno"
_TEMP_PATH = _APP_ROOT / "Archivos_temporales"

CARPETAS_OFICIALES = {"_agents", "informes", "skills"}
ARCHIVOS_RAIZ_OFICIALES = {"subagente_diseno_agent.py", "requirements.txt"}


def obtener_prompt_limpiar_workspace() -> str:
    """
    Retorna el System Prompt especializado para la higiene del espacio de trabajo.
    """
    return """[🧹 DIRECTIVA OPERATIVA: MODO HIGIENE Y LIMPIEZA DE WORKSPACE 🧹]
Eres la Responsable de Higiene, Orden y Sanitización del Subagente de Diseño.
Tu cometido es garantizar que el directorio `/app/Subagente_Diseno/` se mantenga estrictamente estructurado sin archivos residuales, logs huérfanos o duplicidades.

DIRECTIVAS OPERATIVAS:
1. ESTRUCTURA CANÓNICA OBLIGATORIA:
   - 3 Carpetas Oficiales: `_agents/`, `informes/`, `skills/`.
   - Archivos en la Raíz: `subagente_diseno_agent.py`, `requirements.txt`.
2. REGLA CERO BASURA:
   - Todo archivo temporal, borrador o scratch debe canalizarse a `/app/Archivos_temporales/` con prefijo `diseno_`.
   - Prohibido dejar prototipos HTML o imágenes sueltas en la raíz del agente; deben residir en `informes/`.
"""


def _ejecutar_limpieza() -> dict:
    _TEMP_PATH.mkdir(parents=True, exist_ok=True)
    reporte = {
        "status": "success",
        "cache_eliminada": 0,
        "archivos_reubicados": 0,
        "carpetas_verificadas": list(CARPETAS_OFICIALES)
    }

    # 1. Asegurar existencia de las 3 carpetas oficiales
    for c in CARPETAS_OFICIALES:
        ( _BASE_PATH / c ).mkdir(parents=True, exist_ok=True)

    # 2. Purgar __pycache__
    for p in _BASE_PATH.rglob("__pycache__"):
        try:
            shutil.rmtree(p)
            reporte["cache_eliminada"] += 1
        except Exception:
            pass

    # 3. Reubicar archivos sueltos no oficiales de la raíz a informes o Archivos_temporales
    for item in _BASE_PATH.iterdir():
        if item.is_file():
            if item.name not in ARCHIVOS_RAIZ_OFICIALES:
                # Si es un asset de diseño (imagen, html, json), a informes
                if item.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".html", ".mp4", ".md"] and not item.name.startswith("Perfil_"):
                    dest = _BASE_PATH / "informes" / item.name
                else:
                    dest = _TEMP_PATH / f"diseno_{item.name}"
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                except Exception:
                    pass

    return reporte


@tool
def tool_limpiar_workspace_diseno() -> str:
    """
    Ejecuta la rutina de orden y limpieza para mantener la estructura oficial del Subagente de Diseño.
    """
    try:
        res = _ejecutar_limpieza()
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


# Alias de compatibilidad retroactiva
tool_limpiar_habitacion_nami = tool_limpiar_workspace_diseno


@tool
def tool_limpiar_workspace() -> str:
    """
    Sanitiza el espacio de trabajo del Subagente de Diseño purgando archivos temporales y cachés.
    """
    try:
        res = _ejecutar_limpieza()
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


HERRAMIENTAS_LIMPIAR_WORKSPACE = [
    tool_limpiar_workspace_diseno,
    tool_limpiar_workspace
]

