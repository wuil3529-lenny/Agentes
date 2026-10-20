"""
skill_buscar_internet.py — Habilidad: Búsqueda Web de Referencias de Diseño y Tendencias
========================================================================================
Herramienta de búsqueda en la web mediante DuckDuckGo Lite para investigar
paletas de colores, patrones de interfaz, benchmarks y referencias de diseño.
Devuelve títulos, URLs reales y resúmenes estructurados.
"""

import re
import json
import urllib.request
import urllib.parse
from html import unescape
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field


def obtener_prompt_buscar_internet() -> str:
    """
    Retorna el System Prompt especializado para la búsqueda web de referencias de diseño.
    """
    return """[🌐 DIRECTIVA OPERATIVA: MODO BÚSQUEDA WEB Y BENCHMARKING DE DISEÑO 🌐]
Eres la Investigadora de Tendencias Visuales y Referencias de Diseño del Subagente de Diseño.
Tu cometido es rastrear la web para encontrar inspiración visual, componentes de vanguardia, paletas cromáticas accesibles y benchmarks de la competencia antes de iniciar un diseño.

DIRECTIVAS OPERATIVAS:
1. INVESTIGACIÓN PREVIA OBLIGATORIA:
   - Antes de maquetar una pieza o definir una identidad, investiga cómo resuelven problemas similares los líderes de la industria (Linear, Apple, Stripe, Airbnb, Dribbble, Behance).
   - Busca combinaciones de colores accesibles WCAG, fuentes emparejadas y estructuras de composición contrastadas.
2. ENFOQUES ESPECIALIZADOS DE BÚSQUEDA:
   - Utiliza `modo_enfoque` según el objetivo:
     * 'paleta_colores'    : Optimiza la búsqueda para códigos HEX, tokens de color y contraste.
     * 'tipografia'        : Optimiza para emparejamiento tipográfico (font pairings) y jerarquía.
     * 'inspiracion_visual': Busca referencias de alta conversión, layouts y micro-interacciones.
     * 'benchmark_marca'   : Analiza identidades de marca y lenguajes visuales consolidados.
     * 'general'           : Búsqueda abierta sin filtros.
3. SÍNTESIS DE RESULTADOS:
   - Extrae únicamente patrones aplicables a la tarea (tokens, ratios, micro-interacciones, copies efectivos y fuentes verificables).
"""


class BuscarReferenciasParams(BaseModel):
    query: str = Field(description="Término de búsqueda (ej. 'paleta de café artesanal oscuro hex', 'pitch deck minimalista fuentes').")
    modo_enfoque: str = Field(default="general", description="Modo especializado: 'general', 'paleta_colores', 'tipografia', 'inspiracion_visual', 'benchmark_marca'.")
    max_results: int = Field(default=5, description="Número máximo de resultados a extraer (máx 10).")


def _limpiar_html_tags(texto: str) -> str:
    """Elimina etiquetas HTML y decodifica entidades."""
    texto_sin_tags = re.sub(r"<[^>]+>", " ", texto)
    return unescape(re.sub(r"\s+", " ", texto_sin_tags).strip())


@tool("buscar_referencias_diseno", args_schema=BuscarReferenciasParams)
def buscar_referencias_diseno(query: str, modo_enfoque: str = "general", max_results: int = 5) -> str:
    """
    Busca información y referencias de diseño en internet mediante DuckDuckGo Lite.
    Devuelve títulos, URLs reales y resúmenes estructurados por enfoque (paletas, tipografía, inspiración).
    """
    try:
        # Enriquecer la búsqueda según el modo de enfoque
        query_enriquecida = query.strip()
        sufijos_enfoque = {
            "paleta_colores": "color palette hex design tokens",
            "tipografia": "typography font pairing visual design",
            "inspiracion_visual": "UI visual design inspiration showcase",
            "benchmark_marca": "brand visual identity guidelines"
        }
        sufijo = sufijos_enfoque.get(modo_enfoque.lower().strip())
        if sufijo and sufijo not in query_enriquecida.lower():
            query_final = f"{query_enriquecida} {sufijo}"
        else:
            query_final = query_enriquecida

        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query_final}).encode("utf-8")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        req = urllib.request.Request(url, data=data, headers=headers)

        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", errors="replace")

        # Parsear bloques de resultados: enlaces + snippets
        resultados: List[Dict[str, Any]] = []
        limite = max(1, min(max_results, 10))

        # Patrón para capturar links result-link y sus snippets subsiguientes
        bloques = html.split("class='result-link'")
        if len(bloques) <= 1:
            bloques = html.split('class="result-link"')

        for i, bloque in enumerate(bloques[1:limite + 1]):
            try:
                # 1. Extraer título
                match_titulo = re.search(r'>([^<]+)</a>', bloque)
                titulo = match_titulo.group(1).strip() if match_titulo else f"Referencia {i + 1}"

                # 2. Extraer URL del bloque anterior o contexto
                # En DuckDuckGo Lite, el href está justo antes del class='result-link'
                bloque_anterior = bloques[i]
                match_href = re.search(r'href=[\'"]([^\'"]+)[\'"]\s*$', bloque_anterior) or re.search(r'href=[\'"]([^\'"]+)[\'"]', bloque_anterior)
                url_resultado = match_href.group(1) if match_href else "https://duckduckgo.com"

                # Limpiar redirecciones de DuckDuckGo si aplican (ej. /l/?uddg=...)
                if "uddg=" in url_resultado:
                    try:
                        param_uddg = urllib.parse.parse_qs(urllib.parse.urlparse(url_resultado).query).get("uddg")
                        if param_uddg:
                            url_resultado = urllib.parse.unquote(param_uddg[0])
                    except Exception:
                        pass

                # 3. Extraer snippet
                snippet = ""
                if "result-snippet" in bloque:
                    parte_snippet = bloque.split("result-snippet")[1]
                    match_snippet = re.search(r'>([^<]+(?:<[^>]+>[^<]+)*?)</td>', parte_snippet)
                    if match_snippet:
                        snippet = _limpiar_html_tags(match_snippet.group(1))

                resultados.append({
                    "posicion": len(resultados) + 1,
                    "titulo": _limpiar_html_tags(titulo),
                    "url": url_resultado,
                    "resumen": snippet or "Sin extracto disponible."
                })
            except Exception:
                continue

        if not resultados:
            return json.dumps({
                "status": "warning",
                "query": query,
                "mensaje": "No se encontraron resultados parseables. Prueba con términos en inglés o palabras clave más concisas."
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "query_original": query,
            "query_ejecutada": query_final,
            "modo_enfoque": modo_enfoque,
            "total_encontrados": len(resultados),
            "resultados": resultados
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Fallo al buscar referencias web: {str(e)}"
        }, ensure_ascii=False)


# Alias canónicos para interoperabilidad limpia
tool_buscar_internet_diseno = buscar_referencias_diseno
tool_buscar_internet_nami = buscar_referencias_diseno  # Compatibilidad retroactiva segura

HERRAMIENTAS_BUSCAR_INTERNET = [buscar_referencias_diseno]
