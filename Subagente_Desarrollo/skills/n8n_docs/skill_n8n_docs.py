"""
skill_n8n_docs.py — Habilidad: Consulta y Documentación Oficial de Nodos n8n
=============================================================================
Herramientas para buscar nodos y consultar esquemas técnicos de parámetros
en la API oficial de n8n para armar flujos JSON precisos sin alucinar propiedades.

Herramientas disponibles:
  - n8n_buscar_nodos           : Localiza nodos oficiales por nombre o categoría
  - n8n_leer_parametros_nodo   : Extrae los parámetros exactos y tipos de un nodo
"""

import json
import requests
from typing import Dict, Any, List
from langchain_core.tools import tool

N8N_NODES_API = "https://api.n8n.io/api/nodes"


def obtener_prompt_n8n_docs() -> str:
    """
    System Prompt especializado y encapsulado para la consulta técnica de nodos n8n
    del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO DOCUMENTACIÓN DE NODOS N8N ACTIVO 🛑]
Eres el Documentador y Analista de Integraciones n8n del Subagente de Desarrollo.
Tu misión es inspeccionar esquemas oficiales de nodos n8n para garantizar que las propiedades, tipos de datos y versiones de cada nodo en un flujo sean exactas y no alucinadas.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PREVIA ANTES DE ENSAMBLAR NODOS:
   - Antes de escribir un nodo complejo en un JSON de workflow, usa `n8n_buscar_nodos` para obtener el identificador canónico exacto (ej. `n8n-nodes-base.slack`, `n8n-nodes-base.httpRequest`).
2. INSPECCIÓN DE PROPIEDADES OBLIGATORIAS:
   - Usa `n8n_leer_parametros_nodo` para cerciorarte de qué parámetros son requeridos (`required: true`) y cuáles son sus tipos y valores por defecto.
3. PREVENCIÓN DE SOBRECARGA:
   - Los resultados de búsqueda y parámetros están acotados para proteger la ventana de contexto. Analiza los resultados específicos devueltos.
"""


@tool
def n8n_buscar_nodos(query: str) -> str:
    """
    Busca nodos de n8n en la API oficial de documentación.
    Útil para conocer el nombre técnico exacto de un nodo (ej: 'slack', 'gmail', 'postgres') y su versión.

    Args:
        query: Término de búsqueda (ej: 'webhook', 'openai', 'sheets').
    """
    try:
        response = requests.get(N8N_NODES_API, timeout=10)
        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "mensaje": f"No se pudo consultar la API oficial de n8n (código {response.status_code})."
            })

        nodos = response.json()
        resultados = []
        q = query.lower()

        for n in nodos:
            nombre = n.get("name", "").lower()
            display = n.get("displayName", "").lower()

            if q in nombre or q in display:
                resultados.append({
                    "name": n.get("name"),
                    "displayName": n.get("displayName"),
                    "description": n.get("description", ""),
                    "version": n.get("version", 1),
                    "group": n.get("group", [])
                })

        return json.dumps({
            "status": "success",
            "coincidencias": len(resultados),
            "resultados": resultados[:15]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_leer_parametros_nodo(nombre_nodo: str) -> str:
    """
    Lee las propiedades técnicas y parámetros obligatorios de un nodo específico de n8n.

    Args:
        nombre_nodo: Identificador canónico del nodo (ej: 'n8n-nodes-base.slack', 'n8n-nodes-base.webhook').
    """
    try:
        response = requests.get(N8N_NODES_API, timeout=10)
        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "mensaje": "API de documentación oficial de n8n inalcanzable."
            })

        nodos = response.json()
        for n in nodos:
            if n.get("name") == nombre_nodo:
                propiedades = n.get("properties", [])
                resumen = []
                for p in propiedades:
                    resumen.append({
                        "name": p.get("name"),
                        "displayName": p.get("displayName"),
                        "type": p.get("type"),
                        "default": p.get("default"),
                        "required": p.get("required", False)
                    })
                return json.dumps({
                    "status": "success",
                    "nodo": nombre_nodo,
                    "propiedades_detectadas": len(resumen),
                    "propiedades": resumen[:30]
                })

        return json.dumps({
            "status": "warning",
            "mensaje": f"Nodo '{nombre_nodo}' no encontrado en la especificación oficial."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_N8N_DOCS = [
    n8n_buscar_nodos,
    n8n_leer_parametros_nodo
]
