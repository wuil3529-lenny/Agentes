import os
from langchain_core.tools import tool
from skill_google_sanji import obtener_servicio

@tool
def tool_google_drive_buscar(query: str) -> str:
    """
    Busca archivos en Google Drive usando una consulta.
    Ejemplo de query: "name contains 'reporte'" o "mimeType='application/vnd.google-apps.document'".
    Devuelve una lista con los IDs y Nombres de los archivos encontrados.
    """
    try:
        service = obtener_servicio('drive', 'v3')
        results = service.files().list(q=query, pageSize=10, fields="nextPageToken, files(id, name, mimeType)").execute()
        items = results.get('files', [])
        if not items:
            return "No se encontraron archivos en Google Drive."
        
        lines = ["Archivos encontrados:"]
        for item in items:
            lines.append(f"- ID: {item['id']} | Nombre: {item['name']} | Tipo: {item['mimeType']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error en Google Drive: {str(e)}"
