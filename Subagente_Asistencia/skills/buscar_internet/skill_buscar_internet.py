"""
skill_buscar_internet.py — Investigación y Búsqueda de Información en Internet
==============================================================================
Habilidad del Subagente de Asistencia para consultar datos, empresas, contactos,
direcciones, noticias y documentación web en tiempo real sin requerir credenciales
propietarias, empleando DuckDuckGo Lite con saneamiento robusto de HTML.

Utilidades disponibles:
  - tool_buscar_internet         : Realiza búsquedas web y extrae snippets limpios.
  - obtener_prompt_buscar_internet : System Prompt especializado para inyección bajo demanda.
"""

import re
import html
import urllib.request
import urllib.parse
from typing import Optional, List
from langchain_core.tools import tool


def obtener_prompt_buscar_internet() -> str:
    """
    System Prompt especializado y encapsulado para el modo de investigación y búsqueda web
    del Subagente de Asistencia.
    """
    return """[🛑 HARD-STOP: MODO INVESTIGACIÓN Y BÚSQUEDA WEB DE ASISTENCIA ACTIVO 🛑]
Eres el Asistente de Investigación y Búsqueda Web del Subagente de Asistencia.
Tu misión es consultar fuentes abiertas en tiempo real para recopilar datos de empresas, contactos, servicios, itinerarios, noticias y documentación con rigor técnico y síntesis ejecutiva.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PROACTIVA ANTE INCERTIDUMBRE:
   - Si una orden de asistencia requiere datos externos que no están presentes en la memoria ni en los documentos del usuario (ej. horarios de atención, números de contacto, enlaces oficiales, detalles de herramientas), invoca `tool_buscar_internet`.
2. FORMULACIÓN PRECISA DE CONSULTAS:
   - Diseña queries concisas y directas (ej. "sede central Stripe Madrid contacto", "vuelos Caracas Madrid itinerarios 2026", "documentacion Google Workspace API python").
3. SÍNTESIS OBJETIVA Y PRIVACIDAD:
   - Sintetiza únicamente los datos relevantes y contrastados. Prohibido alucinar URLs, correos o números de teléfono que no figuren en los resultados extraídos.
4. CERO SATURACIÓN DE CONTEXTO:
   - Limita los resultados a los snippets pertinentes para no sobrecargar el historial de conversación.
"""

# Alias de compatibilidad
obtener_prompt_buscar_en_internet = obtener_prompt_buscar_internet


def _limpiar_html(texto: str) -> str:
    """Elimina etiquetas HTML y decodifica entidades especiales."""
    texto_sin_tags = re.sub(r"<[^>]+>", " ", texto)
    texto_decodificado = html.unescape(texto_sin_tags)
    return re.sub(r"\s+", " ", texto_decodificado).strip()


@tool
def tool_buscar_internet(query: str, max_results: int = 5) -> str:
    """
    Busca información y datos en internet mediante DuckDuckGo Lite.
    Útil para consultar empresas, datos de contacto, noticias, servicios o resolver dudas generales.

    Args:
        query: Consulta en lenguaje natural o palabras clave (ej: 'horario embajada españa caracas').
        max_results: Cantidad máxima de resultados a devolver (por defecto 5, máximo 10).
    """
    if not query or not query.strip():
        return "Error: La consulta de búsqueda no puede estar vacía."

    max_r = max(1, min(int(max_results), 10))

    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query.strip()}).encode("utf-8")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        req = urllib.request.Request(url, data=data, headers=headers)

        with urllib.request.urlopen(req, timeout=12) as response:
            contenido_html = response.read().decode("utf-8", errors="replace")

        lineas = []
        if "result-snippet" in contenido_html:
            bloques = contenido_html.split("class='result-snippet'")
            for idx, bloque in enumerate(bloques[1:max_r + 1], 1):
                try:
                    contenido_crudo = bloque.split(">", 1)[1].split("</td>", 1)[0]
                    snippet_limpio = _limpiar_html(contenido_crudo)
                    if snippet_limpio:
                        lineas.append(f"{idx}. {snippet_limpio}")
                except Exception:
                    continue

        if not lineas:
            # Fallback para estructuras alternativas de DuckDuckGo
            coincidencias = re.findall(r'<td[^>]*class=["\']result-snippet["\'][^>]*>(.*?)</td>', contenido_html, re.DOTALL | re.IGNORECASE)
            for idx, c in enumerate(coincidencias[:max_r], 1):
                s = _limpiar_html(c)
                if s:
                    lineas.append(f"{idx}. {s}")

        if not lineas:
            return f"No se encontraron resultados directos para la búsqueda: '{query}'. Intenta reformular con términos más específicos."

        return f"🌐 **Resultados de Búsqueda Web para:** '{query}'\n\n" + "\n\n".join(lineas)

    except urllib.error.URLError as e:
        return f"Error de conexión al consultar el motor de búsqueda: {e.reason}"
    except Exception as e:
        return f"Error inesperado al buscar en internet: {str(e)}"


# Alias de compatibilidad
tool_buscar_en_internet = tool_buscar_internet
tool_buscar_internet_sanji = tool_buscar_internet

__all__ = [
    "tool_buscar_internet",
    "tool_buscar_en_internet",
    "tool_buscar_internet_sanji",
    "obtener_prompt_buscar_internet",
    "obtener_prompt_buscar_en_internet",
]
