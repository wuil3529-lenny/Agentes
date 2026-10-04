"""
skill_n8n_templates.py — Habilidad: Plantillas de la Comunidad n8n
===================================================================
Herramientas para buscar, explorar e importar flujos de trabajo preconstruidos
desde la galería oficial comunitaria de n8n.

Herramientas disponibles:
  - n8n_buscar_plantillas  : Busca flujos comunitarios por palabras clave
  - n8n_obtener_plantilla  : Descarga el JSON completo y estructura de una plantilla por su ID
"""

import json
import requests
from typing import Dict, Any, List
from langchain_core.tools import tool

N8N_TEMPLATES_API = "https://api.n8n.io/api/templates/workflows"


def obtener_prompt_n8n_templates() -> str:
    """
    System Prompt especializado y encapsulado para la búsqueda y reutilización
    de plantillas de la comunidad n8n del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO PLANTILLAS COMUNITARIAS N8N ACTIVO 🛑]
Eres el Especialista en Plantillas y Reutilización de Workflows n8n del Subagente de Desarrollo.
Tu misión es acelerar el desarrollo aprovechando las mejores prácticas y arquitecturas probadas por la comunidad oficial de n8n.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. IDIOMA DE BÚSQUEDA TÉCNICA:
   - Realiza búsquedas preferentemente en inglés (`query="slack to sheets"`, `"telegram bot ai"`, `"gmail webhook"`) para maximizar los aciertos en la galería oficial.
2. AUDITORÍA DE PLANTILLA ANTES DE IMPLEMENTAR:
   - Al obtener una plantilla con `n8n_obtener_plantilla`, inspecciona sus nodos y conexiones. Reemplaza siempre cualquier credencial o webhook de muestra por los valores específicos de la tripulación.
"""


@tool
def n8n_buscar_plantillas(query: str) -> str:
    """
    Busca flujos de trabajo creados por la comunidad en la galería oficial de plantillas de n8n.
    Usa términos clave en inglés preferiblemente (ej: 'slack to sheets', 'openai agent', 'postgres backup').

    Args:
        query: Término de búsqueda en inglés o temático.
    """
    try:
        url = f"{N8N_TEMPLATES_API}?search={query}"
        response = requests.get(url, timeout=12)

        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "mensaje": f"Error al consultar la galería de plantillas de n8n (código {response.status_code})."
            })

        data = response.json()
        workflows = data.get("workflows", [])

        resultados = []
        for w in workflows[:10]:
            resultados.append({
                "id": w.get("id"),
                "name": w.get("name"),
                "createdAt": w.get("createdAt"),
                "user": w.get("user", {}).get("username")
            })

        return json.dumps({
            "status": "success",
            "total_encontrados": data.get("totalWorkflows", 0),
            "resultados": resultados
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_obtener_plantilla(template_id: int) -> str:
    """
    Obtiene el JSON completo de una plantilla comunitaria de n8n por su ID numérico.

    Args:
        template_id: ID numérico de la plantilla (obtenido previamente mediante n8n_buscar_plantillas).
    """
    try:
        url = f"{N8N_TEMPLATES_API}/{template_id}"
        response = requests.get(url, timeout=12)

        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "mensaje": f"No se encontró la plantilla con ID {template_id}."
            })

        data = response.json()
        workflow = data.get("workflow", {})

        return json.dumps({
            "status": "success",
            "id": template_id,
            "name": workflow.get("name"),
            "nodes": workflow.get("nodes"),
            "connections": workflow.get("connections")
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_N8N_TEMPLATES = [
    n8n_buscar_plantillas,
    n8n_obtener_plantilla
]
