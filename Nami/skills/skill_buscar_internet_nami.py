import urllib.request
import urllib.parse

from langchain_core.tools import tool

@tool
def tool_buscar_internet_nami(query: str, max_results: int = 5) -> str:
    """
    Busca información en internet usando DuckDuckGo Lite.
    Útil para investigar paletas de colores, estilos visuales, referencias de diseño UI/UX o marcas específicas en internet.
    """
    try:
        url = 'https://lite.duckduckgo.com/lite/'
        data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
        # Parseo simple buscando resultados (muy básico para lite.duckduckgo)
        lines = []
        if 'result-snippet' in html:
            # Quick extraction without external dependencies if bs4 is missing
            parts = html.split("class='result-snippet'")
            for i, p in enumerate(parts[1:max_results+1]):
                snippet = p.split('>', 1)[1].split('</td>', 1)[0].strip()
                # Clean basic HTML tags
                snippet = snippet.replace('<b>', '').replace('</b>', '').replace('<br>', ' ').strip()
                lines.append(f"{i+1}. {snippet}")
        else:
            return "No se encontraron resultados fáciles de extraer. Intenta ser más específico."
            
        return "Resultados de búsqueda:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error en la búsqueda: {str(e)}"
