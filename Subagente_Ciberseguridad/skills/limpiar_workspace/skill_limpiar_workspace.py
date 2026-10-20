"""
skill_limpiar_workspace.py — Rutina de Orden, Higiene y Limpieza del Workspace
=============================================================================
Habilidad del Subagente de Ciberseguridad para mantener el orden, la higiene
y la conformidad arquitectónica de su espacio de trabajo y del ecosistema:
- Carpetas Oficiales: _agents, informes, reportes, skills
- Archivos Oficiales en Raíz: subagente_ciberseguridad_agent.py
- Archivos Oficiales en _agents: agente.md
- Purga directorios temporales de caché (__pycache__, .pytest_cache)
- Reubica cualquier archivo basura o volátil a Archivos_temporales/
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["robin", "subagente_ciberseguridad"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Ciberseguridad"
_BASE_PATH = _APP_ROOT / _AGENTE

CARPETAS_OFICIALES = {
    ".agents",
    "_agents",
    "informes",
    "reportes",
    "skills"
}

ARCHIVOS_RAIZ_OFICIALES = {
    "subagente_ciberseguridad_agent.py"
}

ARCHIVOS_AGENTS_OFICIALES = {
    "agente.md"
}


def obtener_prompt_limpiar_workspace() -> str:
    """
    System Prompt especializado y encapsulado para la higiene y orden del workspace.
    """
    return """[🛑 HARD-STOP: MODO HIGIENE Y LIMPIEZA DE WORKSPACE ACTIVO 🛑]
Eres el Oficial de Higiene, Orden y Conformidad Estructural del Subagente de Ciberseguridad.
Tu misión es auditar, purgar residuos temporales y preservar la arquitectura canónica de directorios del subagente con rigor técnico y determinismo.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. HIGIENE POST-EJECUCIÓN:
   - Al terminar tareas complejas de escaneo o generación de reportes, ejecuta `tool_limpiar_habitacion` para purgar cachés de compilación (__pycache__) y asegurar que ningún archivo temporal quede suelto fuera de `reportes/` o `informes/`.
2. SCRATCH CENTRALIZADO:
   - Todo archivo volátil o de prueba debe residir en `/app/Archivos_temporales/` con prefijo `ciberseguridad_` o `robin_`.
3. PRESERVACIÓN DE ENTREGABLES (ZERO-LOSS):
   - Nunca elimines destructivamente reportes en `reportes/` ni informes en `informes/`. La purga solo aplica a cachés y archivos no oficiales fuera de lugar.
"""


@tool
def tool_limpiar_habitacion() -> str:
    """
    Inspecciona y limpia la habitación del Subagente de Ciberseguridad:
    1. Asegura la existencia de las carpetas oficiales (_agents, reportes, informes, skills).
    2. Purga cachés compiladas (__pycache__).
    3. Reubica archivos no oficiales sueltos hacia Archivos_temporales/ en la raíz.
    """
    try:
        archivos_temporales_path = _APP_ROOT / "Archivos_temporales"
        archivos_temporales_path.mkdir(parents=True, exist_ok=True)

        reporte = {
            "carpetas_verificadas": [],
            "cache_eliminada": 0,
            "archivos_reubicados": 0,
            "detalles": []
        }

        # 1. Asegurar carpetas oficiales
        for dir_oficial in CARPETAS_OFICIALES:
            carpeta_path = _BASE_PATH / dir_oficial
            if not carpeta_path.exists():
                carpeta_path.mkdir(parents=True, exist_ok=True)
                reporte["detalles"].append(f"Carpeta oficial creada: {dir_oficial}")
            reporte["carpetas_verificadas"].append(dir_oficial)

        # 2. Purgar __pycache__
        for cache_dir in _BASE_PATH.rglob("__pycache__"):
            if cache_dir.is_dir():
                try:
                    shutil.rmtree(cache_dir)
                    reporte["cache_eliminada"] += 1
                except Exception as e:
                    print(f"[Ciberseguridad Limpieza] Error eliminando {cache_dir}: {e}")

        # 3. Reubicar archivos huérfanos en la raíz del agente
        for item in _BASE_PATH.iterdir():
            if item.is_file() and item.name not in ARCHIVOS_RAIZ_OFICIALES:
                dest = archivos_temporales_path / f"ciberseguridad_{item.name}"
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                    reporte["detalles"].append(f"Archivo suelto reubicado: {item.name} -> {dest.name}")
                except Exception as e:
                    reporte["detalles"].append(f"Error moviendo {item.name}: {e}")

        return json.dumps({
            "status": "success",
            "agente": _AGENTE,
            "resumen": reporte
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_limpiar_workspace() -> str:
    """
    Ejecuta una limpieza preventiva del workspace completo: purga __pycache__ y
    verifica que la carpeta centralizada Archivos_temporales/ exista y esté lista.
    """
    try:
        temp_dir = _APP_ROOT / "Archivos_temporales"
        temp_dir.mkdir(parents=True, exist_ok=True)

        caches_eliminadas = 0
        for cache in _APP_ROOT.glob("**/__pycache__"):
            if cache.is_dir() and ".git" not in cache.parts:
                try:
                    shutil.rmtree(cache)
                    caches_eliminadas += 1
                except Exception:
                    pass

        return json.dumps({
            "status": "success",
            "mensaje": f"Workspace higienizado. {caches_eliminadas} carpetas __pycache__ purgadas.",
            "archivos_temporales_path": str(temp_dir)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_LIMPIEZA = [
    tool_limpiar_habitacion,
    tool_limpiar_workspace,
]
