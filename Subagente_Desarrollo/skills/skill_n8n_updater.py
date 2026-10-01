"""
skill_n8n_updater.py — Habilidad: Actualizaciones de n8n
========================================================
Mantiene a Zoro al tanto de las últimas versiones y cambios 
de n8n extrayendo notas desde GitHub.
"""

import json
import requests
from langchain_core.tools import tool

N8N_GITHUB_RELEASE_API = "https://api.github.com/repos/n8n-io/n8n/releases/latest"

@tool
def n8n_obtener_ultimas_novedades() -> str:
    """
    Consulta la última versión de n8n liberada en GitHub y lee el Changelog.
    Útil para saber si un nodo tiene nuevas características o se corrigieron bugs.
    """
    try:
        response = requests.get(N8N_GITHUB_RELEASE_API, timeout=10)
        
        if response.status_code != 200:
            return json.dumps({"status": "error", "mensaje": "No se pudo contactar a GitHub."})
            
        data = response.json()
        
        # Extraemos lo más relevante del cuerpo de la release
        cuerpo = data.get("body", "")
        # Tomamos solo un resumen de los primeros 1500 caracteres para no sobrecargar el LLM
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

# Exportar las herramientas
HERRAMIENTAS_N8N_UPDATER = [n8n_obtener_ultimas_novedades]
