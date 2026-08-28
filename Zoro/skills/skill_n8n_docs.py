"""
skill_n8n_docs.py — Habilidad: Documentación Oficial de n8n
===========================================================
Permite a Zoro buscar y leer documentación de los nodos de n8n para
armar flujos JSON precisos sin inventar parámetros.
"""

import json
import requests
from langchain_core.tools import tool

N8N_NODES_API = "https://api.n8n.io/api/nodes"

@tool
def n8n_buscar_nodos(query: str) -> str:
    """
    Busca nodos de n8n en la API oficial. 
    Usa esta herramienta cuando necesites saber cómo se llama exactamente 
    un nodo (ej: 'slack', 'gmail', 'openai') y qué versión tiene.
    """
    try:
        response = requests.get(N8N_NODES_API, timeout=10)
        if response.status_code != 200:
            return json.dumps({"status": "error", "mensaje": "No se pudo contactar la API de n8n."})
        
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
            "resultados": resultados[:15] # Limitar a 15 para no saturar el contexto
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})

@tool
def n8n_leer_parametros_nodo(nombre_nodo: str) -> str:
    """
    Lee las propiedades (parámetros) técnicas de un nodo específico.
    Usa el nombre exacto del nodo (ej: 'n8n-nodes-base.slack').
    """
    try:
        response = requests.get(N8N_NODES_API, timeout=10)
        if response.status_code != 200:
            return json.dumps({"status": "error", "mensaje": "API inalcanzable."})
        
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
                    "propiedades": resumen
                })
                
        return json.dumps({"status": "warning", "mensaje": f"Nodo '{nombre_nodo}' no encontrado."})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})

# Exportar las herramientas
HERRAMIENTAS_N8N_DOCS = [n8n_buscar_nodos, n8n_leer_parametros_nodo]
