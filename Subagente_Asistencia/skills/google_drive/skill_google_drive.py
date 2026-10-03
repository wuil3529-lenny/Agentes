"""
skill_google_drive.py — Navegación y Búsqueda en Google Drive
=============================================================
Habilidad del Subagente de Asistencia para buscar, explorar y localizar
archivos, carpetas y documentos en Google Drive mediante la API oficial.

Herramientas disponibles:
  - tool_google_drive_buscar   : Búsqueda flexible por nombre o consulta avanzada de Drive.
  - tool_google_drive_recientes: Lista los archivos modificados recientemente en la unidad.
  - obtener_prompt_google_drive: System Prompt especializado para inyección bajo demanda.
"""

from typing import Optional
from langchain_core.tools import tool

# Importar servicio oficial de Google Workspace
try:
    from Subagente_Asistencia.skills.google_workspace.skill_google import obtener_servicio
except ImportError:
    try:
        from skills.google_workspace.skill_google import obtener_servicio
    except ImportError:
        try:
            from skill_google_sanji import obtener_servicio
        except ImportError:
            obtener_servicio = None


def obtener_prompt_google_drive() -> str:
    """
    System Prompt especializado y encapsulado para el Navegador y Archivista de Google Drive.
    """
    return """[🛑 HARD-STOP: MODO GESTIÓN Y BÚSQUEDA EN GOOGLE DRIVE ACTIVO 🛑]
Eres el Archivista Digital y Navegador Documental del Subagente de Asistencia.
Tu misión es localizar, auditar y suministrar enlaces directos a los recursos almacenados en Google Drive de forma rápida y estructurada.

DIRECTIVAS OPERATIVAS OBLIGATORIAS:
1. TRADUCCIÓN INTELIGENTE DE BÚSQUEDA:
   - Cuando el usuario o un agente solicite buscar por un término simple (ej. "factura", "auditoria"), formula la consulta adecuada asegurando excluir la papelera (`trashed = false`).
2. ENLACES DIRECTOS Y METADATOS:
   - Toda respuesta debe incluir el Nombre del archivo, su Tipo (Documento Docs, Hoja de Cálculo, PDF, etc.), la fecha de última modificación y el enlace de apertura directa (`webViewLink`).
3. CONFIDENCIALIDAD Y ALCANCE:
   - No expongas IDs de archivo como dato principal; prioriza el Nombre reconocible y la URL accesible.
"""


def _formatear_mime_type(mime: str) -> str:
    """Traduce mimeTypes de Google a etiquetas legibles."""
    mapa = {
        'application/vnd.google-apps.document': '📄 Google Docs',
        'application/vnd.google-apps.spreadsheet': '📊 Google Sheets',
        'application/vnd.google-apps.presentation': '📑 Google Slides',
        'application/vnd.google-apps.folder': '📁 Carpeta',
        'application/pdf': '📕 Documento PDF',
        'image/png': '🖼️ Imagen PNG',
        'image/jpeg': '🖼️ Imagen JPG',
        'text/plain': '📝 Archivo de Texto',
    }
    return mapa.get(mime, f"📦 {mime.split('/')[-1].upper()}")


@tool
def tool_google_drive_buscar(
    query: str,
    max_results: int = 10,
    solo_documentos: bool = False
) -> str:
    """
    Busca archivos o carpetas en Google Drive usando un término clave o una sintaxis de consulta avanzada.
    Devuelve los nombres, tipos, fecha de última modificación y enlaces directos de visualización.

    Args:
        query: Término de búsqueda (ej. "auditoria") o consulta de Google Drive (ej. "name contains 'reporte'").
        max_results: Cantidad máxima de resultados a listar (por defecto 10).
        solo_documentos: Si es True, filtra únicamente archivos de Google Docs.
    """
    if obtener_servicio is None:
        return "Error: El cliente de autenticación de Google Workspace no está disponible."

    try:
        service = obtener_servicio('drive', 'v3')

        # Construir consulta segura
        q_limpia = query.strip()
        if "=" not in q_limpia and "contains" not in q_limpia:
            # Sintaxis amigable: búsqueda por coincidencia de nombre o contenido
            q_construida = f"(name contains '{q_limpia}' or fullText contains '{q_limpia}') and trashed = false"
        else:
            q_construida = q_limpia
            if "trashed" not in q_construida:
                q_construida += " and trashed = false"

        if solo_documentos and "mimeType" not in q_construida:
            q_construida += " and mimeType = 'application/vnd.google-apps.document'"

        campos = "nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, size)"
        results = service.files().list(
            q=q_construida,
            pageSize=min(max_results, 50),
            fields=campos
        ).execute()

        archivos = results.get('files', [])
        if not archivos:
            return f"🔍 No se encontraron archivos en Google Drive coincidentes con: '{query}'."

        lineas = [f"📁 **Archivos Encontrados en Google Drive ({len(archivos)} resultados):**\n"]
        for f in archivos:
            nombre = f.get('name', '(Sin nombre)')
            tipo = _formatear_mime_type(f.get('mimeType', ''))
            link = f.get('webViewLink', f"https://drive.google.com/open?id={f.get('id')}")
            mod_time = f.get('modifiedTime', '')[:10]
            
            lineas.append(f"- **{nombre}** | {tipo}")
            lineas.append(f"  🔗 Enlace: {link}  (Modificado: {mod_time})")

        return "\n".join(lineas)

    except Exception as e:
        return f"Error al buscar en Google Drive: {str(e)}"


@tool
def tool_google_drive_recientes(max_results: int = 10) -> str:
    """
    Lista los archivos modificados o creados más recientemente en Google Drive.
    Útil para auditorías rápidas o localizar los últimos informes generados.

    Args:
        max_results: Cantidad máxima de archivos recientes a listar (por defecto 10).
    """
    if obtener_servicio is None:
        return "Error: El cliente de autenticación de Google Workspace no está disponible."

    try:
        service = obtener_servicio('drive', 'v3')
        campos = "files(id, name, mimeType, webViewLink, modifiedTime)"
        
        results = service.files().list(
            q="trashed = false",
            orderBy="modifiedTime desc",
            pageSize=min(max_results, 25),
            fields=campos
        ).execute()

        archivos = results.get('files', [])
        if not archivos:
            return "🔍 No se encontraron archivos recientes en Google Drive."

        lineas = [f"🕒 **Archivos Modificados Recientemente en Google Drive ({len(archivos)} listados):**\n"]
        for f in archivos:
            nombre = f.get('name', '(Sin nombre)')
            tipo = _formatear_mime_type(f.get('mimeType', ''))
            link = f.get('webViewLink', f"https://drive.google.com/open?id={f.get('id')}")
            mod_time = f.get('modifiedTime', '')[:16].replace('T', ' ')
            
            lineas.append(f"- **{nombre}** | {tipo}")
            lineas.append(f"  🔗 Enlace: {link}  (Última edición: {mod_time})")

        return "\n".join(lineas)

    except Exception as e:
        return f"Error al listar archivos recientes en Google Drive: {str(e)}"
