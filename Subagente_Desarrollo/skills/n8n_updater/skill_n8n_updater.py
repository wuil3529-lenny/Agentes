"""
skill_n8n_updater.py — Habilidad: Monitor de Actualizaciones y Releases de n8n
==============================================================================
Herramientas para consultar versiones liberadas, cambios de esquemas y notas
de lanzamiento oficiales de n8n desde el repositorio en GitHub.

Herramientas disponibles:
  - n8n_obtener_ultimas_novedades : Extrae la versión más reciente y su changelog resumido
"""

import json
import requests
from typing import Dict, Any, List
from langchain_core.tools import tool

N8N_GITHUB_RELEASE_API = "https://api.github.com/repos/n8n-io/n8n/releases/latest"


def obtener_prompt_n8n_updater() -> str:
    """
    System Prompt especializado y encapsulado para el monitoreo de versiones
    y novedades de n8n del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO MONITOR DE ACTUALIZACIONES N8N ACTIVO 🛑]
Eres el Auditor de Versiones y Compatibilidad de n8n del Subagente de Desarrollo.
Tu misión es mantener al sistema informado sobre nuevas versiones de nodos, correcciones de seguridad y deprecaciones en el ecosistema n8n.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. INSPECCIÓN DE NOVEDADES Y CHANGELOGS:
   - Consulta `n8n_obtener_ultimas_novedades` cuando se requiera conocer si un bug conocido en un nodo ya fue resuelto en la última versión o si hay nuevas funcionalidades.
2. ECONOMÍA DE CONTEXTO:
   - Las notas de la release se entregan filtradas y resumidas para evitar saturar la ventana de tokens.
"""


@tool
def n8n_obtener_ultimas_novedades() -> str:
    """
    Consulta la última versión oficial de n8n liberada en GitHub y lee un resumen de su Changelog.
    Útil para verificar nuevas características, breaking changes o correcciones de bugs.
    """
    try:
        response = requests.get(
            N8N_GITHUB_RELEASE_API,
            headers={"User-Agent": "Antigravity-Agent/2.0"},
            timeout=10
        )

        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "mensaje": f"No se pudo consultar el repositorio de n8n en GitHub (código {response.status_code})."
            })

        data = response.json()
        cuerpo = data.get("body", "")
        resumen = cuerpo[:1500] + ("..." if len(cuerpo) > 1500 else "")

        return json.dumps({
            "status": "success",
            "version": data.get("tag_name"),
            "nombre": data.get("name"),
            "fecha": data.get("published_at"),
            "notas_lanzamiento": resumen,
            "url": data.get("html_url")
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_N8N_UPDATER = [
    n8n_obtener_ultimas_novedades
]
