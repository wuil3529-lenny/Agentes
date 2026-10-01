"""
skill_n8n_templates.py — Habilidad: Plantillas de la Comunidad
==============================================================
Permite a Zoro buscar, analizar e importar flujos de trabajo 
creados por la comunidad de n8n.
"""

import json
import requests
from langchain_core.tools import tool

N8N_TEMPLATES_API = "https://api.n8n.io/api/templates/workflows"

@tool
def n8n_buscar_plantillas(query: str) -> str:
    """
    Busca flujos de trabajo creados por la comunidad en la galería de n8n.
    Usa términos clave en inglés preferiblemente (ej: 'slack to sheets', 'openai agent').
    """
    try:
        url = f"{N8N_TEMPLATES_API}?search={query}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return json.dumps({"status": "error", "mensaje": f"API error: {response.status_code}"})
            
        data = response.json()
        workflows = data.get("workflows", [])
        
        resultados = []
        for w in workflows[:10]: # Devolvemos top 10
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
    Obtiene el JSON completo de una plantilla comunitaria por su ID.
    Usa esta herramienta cuando hayas encontrado una plantilla que parezca útil
    y quieras analizar sus nodos y conexiones.
    """
    try:
        url = f"{N8N_TEMPLATES_API}/{template_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return json.dumps({"status": "error", "mensaje": f"No se encontró la plantilla {template_id}"})
            
        data = response.json()
        workflow = data.get("workflow", {})
        
        # Formatear el resultado
        return json.dumps({
            "status": "success",
            "id": template_id,
            "name": workflow.get("name"),
            "nodes": workflow.get("nodes"),
            "connections": workflow.get("connections")
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})

# Exportar las herramientas
HERRAMIENTAS_N8N_TEMPLATES = [n8n_buscar_plantillas, n8n_obtener_plantilla]
