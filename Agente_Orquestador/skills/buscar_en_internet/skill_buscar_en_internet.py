"""
skill_buscar_en_internet.py — Investigación y Búsqueda Técnica en Internet
==========================================================================
Habilidad del Agente Orquestador para consultar documentación técnica, APIs
y especificaciones web actualizadas en tiempo real sin dependencias externas pesadas.
"""

import urllib.request
import urllib.parse
from typing import Optional
from langchain_core.tools import tool


def obtener_prompt_buscar_en_internet() -> str:
    """
    System Prompt especializado y encapsulado para el modo de investigación
    y búsqueda técnica en la web.
    """
    return """[🛑 HARD-STOP: MODO INVESTIGACIÓN Y BÚSQUEDA TÉCNICA EN INTERNET ACTIVO 🛑]
Eres el Investigador de Inteligencia Técnica y Búsqueda Web del Agente Orquestador.
Tu misión es consultar documentación técnica en tiempo real, investigar librerías, resolver dudas sobre APIs y explorar especificaciones web actualizadas, garantizando que el diseño de planes y la toma de decisiones se fundamenten en información fidedigna y vigente.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PROACTIVA ANTE INCERTIDUMBRE:
   - Ante cualquier tecnología, librería o cambio de versión que no conozcas con certeza absoluta, invoca `tool_buscar_en_internet` antes de emitir recomendaciones o redactar código.
2. FORMULACIÓN PRECISA DE QUERIES:
   - Construye búsquedas técnicas concisas y específicas (ej. "fastapi websocket disconnect handling python", "pillow save webp optimize parameters").
3. SÍNTESIS OBJETIVA Y CITACIÓN:
   - Sintetiza los hallazgos directamente aplicables al requerimiento del Usuario, evitando copiar código no verificado o texto innecesario que sature la ventana de contexto.
4. CERO ALUCINACIONES:
   - Si no encuentras documentación oficial para una función solicitada, repórtalo con transparencia en lugar de inventar parámetros o métodos inexistentes.
"""

obtener_prompt_buscar_internet = obtener_prompt_buscar_en_internet


@tool
def tool_buscar_en_internet(query: str, max_results: int = 5) -> str:
    """
    Busca información y documentación técnica en internet usando DuckDuckGo Lite.
    Útil para investigar conceptos técnicos, librerías, herramientas o plataformas 
    que el usuario mencione durante las entrevistas o planificación y que desconozcas.

    Args:
        query: Consulta técnica en lenguaje natural o palabras clave (ej: 'fastapi lifespan vs on_event').
        max_results: Cantidad máxima de resultados a extraer (por defecto 5).
    """
    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, data=data, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")

        # Parseo de resultados de DuckDuckGo Lite
        lineas = []
        if "result-snippet" in html:
            partes = html.split("class='result-snippet'")
            for i, p in enumerate(partes[1 : max_results + 1]):
                snippet = p.split(">", 1)[1].split("</td>", 1)[0].strip()
                # Limpiar etiquetas HTML básicas
                snippet = snippet.replace("<b>", "").replace("</b>", "").replace("<br>", " ").strip()
                lineas.append(f"{i + 1}. {snippet}")
        else:
            return "No se encontraron resultados fáciles de extraer. Intenta formular una búsqueda más específica."

        return f"Resultados de búsqueda web para '{query}':\n" + "\n".join(lineas)
    except Exception as e:
        return f"Error en la búsqueda en internet: {str(e)}"
