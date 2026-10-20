"""
skill_presentaciones.py — Habilidad: Presentaciones Ejecutivas, Marp y Visor HTML Interactivo
=============================================================================================
Herramientas para compilación de presentaciones de alto impacto en Markdown Marp
y renderizado simultáneo de un visor HTML interactivo autocontenido listo para navegador.
"""

import os
import re
import json
import datetime
from pathlib import Path
from html import escape
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_INFORMES = _APP_ROOT / "Subagente_Diseno" / "informes"
_INFORMES.mkdir(parents=True, exist_ok=True)


def obtener_prompt_presentaciones() -> str:
    """
    Retorna el System Prompt especializado para la creación de presentaciones ejecutivas y pitch decks.
    """
    return """[📊 DIRECTIVA OPERATIVA: MODO PRESENTACIONES EJECUTIVAS Y PITCH DECKS 📊]
Eres la Diseñadora de Presentaciones y Pitch Decks Ejecutivos del Subagente de Diseño.
Tu objetivo es estructurar presentaciones ejecutivas de alto impacto visual y conceptual utilizando Markdown compatible con Marp Core y compilando automáticamente visores HTML interactivos listos para navegador.

DIRECTIVAS OPERATIVAS:
1. ARQUITECTURA DE DIAPOSITIVAS:
   - Diapositiva 1 (Portada): Título contundente, subtítulo clarificador, autor y fecha.
   - Diapositiva 2 (Agenda / Tesis Central): De 3 a 4 pilares estratégicos.
   - Diapositivas 3 a N-1 (Cuerpo y Métricas): Regla 1-Idea-Por-Slide. Uso de KPI cards destacadas y listas claras de 3 a 4 puntos.
   - Diapositiva Final (Conclusiones / Next Steps): Resumen de decisiones requeridas y llamada a la acción (Action Items).
2. TEMAS Y COMPONENTES VISUALES:
   - Estilo 'dark_executive': Paleta Slate 950 (#0B0F19), tarjetas (#1E293B), acentos índigo (#6366F1) o esmeralda (#10B981).
   - Estilo 'clean_modern'   : Paleta clara editorial suiza con alto contraste y bordes finos.
   - Estilo 'pitch_deck'     : Enfoque en métricas numéricas grandes, tracción y comparativas de mercado.
3. DOBLE ENTREGABLE COMPILADO:
   - Cada ejecución genera:
     a) El archivo `.md` estructurado para Marp CLI / VS Code.
     b) El archivo `.html` interactivo autocontenido para abrir de inmediato en el navegador con navegación por teclado (flechas, espacio, F para pantalla completa).
"""


def _transformar_ruta(ruta: str, extension: str = ".md") -> Path:
    if not isinstance(ruta, str) or not ruta.strip():
        return _INFORMES / f"presentacion_ejecutiva{extension}"

    literales = {"ruta_destino", "tema_presentacion", "contenido_diapositivas", "ruta", "destino"}
    p = Path(ruta)
    nombre = p.name
    if not nombre or nombre in literales:
        nombre = f"presentacion_ejecutiva{extension}"
    if not nombre.lower().endswith(extension):
        nombre += extension

    return _INFORMES / nombre


def _generar_css_marp(estilo_tema: str) -> str:
    """Genera directivas CSS embebidas para Marp según el estilo seleccionado."""
    if estilo_tema == "clean_modern":
        return """/* @theme clean_modern */
section {
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
  background-color: #FAFAFA;
  color: #0F172A;
  padding: 48px;
  font-size: 24px;
}
h1 { color: #0F172A; font-weight: 800; font-size: 46px; border-bottom: 3px solid #6366F1; padding-bottom: 12px; }
h2 { color: #334155; font-size: 34px; margin-bottom: 24px; }
ul { line-height: 1.6; }
strong { color: #4F46E5; }
.kpi-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
.columns { display: flex; gap: 32px; }
"""
    elif estilo_tema == "pitch_deck":
        return """/* @theme pitch_deck */
section {
  font-family: 'Plus Jakarta Sans', sans-serif;
  background-color: #030712;
  color: #F9FAFB;
  padding: 52px;
  font-size: 24px;
}
h1 { color: #FFFFFF; font-weight: 800; font-size: 48px; letter-spacing: -0.02em; }
h2 { color: #E5E7EB; font-size: 34px; }
strong { color: #10B981; }
.kpi-card { background: rgba(17, 24, 39, 0.8); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 16px; padding: 24px; }
.kpi-num { font-size: 48px; font-weight: 800; color: #10B981; display: block; }
.columns { display: flex; gap: 32px; }
"""
    else:  # dark_executive por defecto
        return """/* @theme dark_executive */
section {
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
  background-color: #0B0F19;
  color: #E2E8F0;
  padding: 50px;
  font-size: 24px;
}
h1 { color: #FFFFFF; font-weight: 800; font-size: 48px; border-bottom: 2px solid #6366F1; padding-bottom: 14px; }
h2 { color: #CBD5E1; font-size: 34px; margin-bottom: 20px; }
ul { line-height: 1.65; }
li { margin-bottom: 12px; }
strong { color: #818CF8; }
.kpi-card { background: #111827; border: 1px solid #1E293B; border-radius: 14px; padding: 20px; }
.columns { display: flex; gap: 32px; }
"""


def _marcar_a_html_simple(slide_md: str) -> str:
    """Convierte Markdown básico de diapositiva a HTML semántico seguro para el visor interactivo."""
    lineas = slide_md.strip().split("\n")
    html_out = []
    en_lista = False

    for linea in lineas:
        l = linea.strip()
        if not l:
            if en_lista:
                html_out.append("</ul>")
                en_lista = False
            continue

        # Encabezados
        if l.startswith("# "):
            if en_lista:
                html_out.append("</ul>")
                en_lista = False
            texto = escape(l[2:].strip())
            html_out.append(f'<h1 class="text-3xl md:text-5xl font-extrabold text-white tracking-tight border-b border-indigo-500/40 pb-4 mb-6">{texto}</h1>')
        elif l.startswith("## "):
            if en_lista:
                html_out.append("</ul>")
                en_lista = False
            texto = escape(l[3:].strip())
            html_out.append(f'<h2 class="text-2xl md:text-3xl font-bold text-slate-100 mb-5">{texto}</h2>')
        elif l.startswith("### "):
            if en_lista:
                html_out.append("</ul>")
                en_lista = False
            texto = escape(l[4:].strip())
            html_out.append(f'<h3 class="text-xl md:text-2xl font-semibold text-indigo-300 mb-4">{texto}</h3>')
        # Viñetas
        elif l.startswith("- ") or l.startswith("* "):
            if not en_lista:
                html_out.append('<ul class="space-y-4 my-4">')
                en_lista = True
            texto = l[2:].strip()
            # Formatear negritas
            texto_fmt = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-indigo-400 font-bold">\1</strong>', escape(texto))
            html_out.append(f'<li class="flex items-start gap-3 text-slate-300 text-lg md:text-xl leading-relaxed"><span class="w-2.5 h-2.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0"></span><span>{texto_fmt}</span></li>')
        # Párrafos normales
        else:
            if en_lista:
                html_out.append("</ul>")
                en_lista = False
            texto_fmt = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-indigo-400 font-bold">\1</strong>', escape(l))
            html_out.append(f'<p class="text-slate-300 text-lg md:text-xl leading-relaxed my-3">{texto_fmt}</p>')

    if en_lista:
        html_out.append("</ul>")

    return "\n".join(html_out)


def _generar_html_interactivo(
    tema_presentacion: str,
    contenido_diapositivas: List[str],
    estilo_tema: str = "dark_executive"
) -> str:
    """Genera un archivo HTML interactivo autocontenido para navegador con navegación por teclado."""
    slides_html = []
    total = len(contenido_diapositivas)

    for i, slide_md in enumerate(contenido_diapositivas):
        cuerpo_html = _marcar_a_html_simple(slide_md)
        num_str = f"{i + 1} / {total}"
        slide_card = f"""
        <!-- Slide {i + 1} -->
        <div class="slide absolute inset-0 p-8 md:p-14 flex flex-col justify-between transition-opacity duration-300 {'opacity-100 z-10' if i == 0 else 'opacity-0 pointer-events-none'}" data-slide="{i}">
          <div class="flex items-center justify-between pb-4 border-b border-slate-800/60 text-xs font-mono text-slate-400">
            <span class="px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">{escape(tema_presentacion)}</span>
            <span>DIAPOSITIVA {num_str}</span>
          </div>
          <div class="my-auto py-6">
            {cuerpo_html}
          </div>
          <div class="flex items-center justify-between pt-4 border-t border-slate-800/60 text-xs text-slate-500">
            <span>Subagente de Diseño • Presentaciones Ejecutivas</span>
            <span>Usa ⬅️ ➡️ o Espacio para navegar</span>
          </div>
        </div>
        """
        slides_html.append(slide_card)

    slides_bloque = "\n".join(slides_html)

    return f"""<!DOCTYPE html>
<html lang="es" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(tema_presentacion)} - Presentación Ejecutiva</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
    .aspect-16-9 {{ aspect-ratio: 16 / 9; }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col justify-between items-center p-4 md:p-8 select-none">
  <!-- Barra superior -->
  <header class="w-full max-w-6xl flex items-center justify-between py-3 mb-2">
    <div class="flex items-center gap-3">
      <div class="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow-md shadow-indigo-600/30">P</div>
      <h1 class="text-sm md:text-base font-bold text-white truncate max-w-xs md:max-w-md">{escape(tema_presentacion)}</h1>
    </div>
    <div class="flex items-center gap-2">
      <button id="btn-fullscreen" class="px-3 py-1.5 text-xs font-mono rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition">
        ⛶ Pantalla Completa [F]
      </button>
    </div>
  </header>

  <!-- Contenedor del Slide 16:9 -->
  <main class="w-full max-w-6xl flex-1 flex items-center justify-center">
    <div id="deck-container" class="w-full aspect-16-9 relative bg-slate-900/90 rounded-2xl border border-slate-800 shadow-2xl shadow-indigo-950/40 overflow-hidden">
      {slides_bloque}
    </div>
  </main>

  <!-- Controles y Barra de progreso inferior -->
  <footer class="w-full max-w-6xl flex items-center justify-between py-4 mt-2">
    <div class="flex items-center gap-3">
      <button id="btn-prev" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 shadow transition active:scale-95">
        ⬅ Anterior
      </button>
      <button id="btn-next" class="px-5 py-2 text-sm font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition active:scale-95">
        Siguiente ➡
      </button>
    </div>

    <!-- Indicador de Diapositiva -->
    <div class="text-sm font-mono text-slate-400">
      <span id="current-slide">1</span> / <span id="total-slides">{total}</span>
    </div>

    <!-- Barra de progreso -->
    <div class="w-32 md:w-48 h-2 rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
      <div id="progress-bar" class="h-full bg-indigo-500 transition-all duration-300" style="width: {(1 / max(total, 1)) * 100}%;"></div>
    </div>
  </footer>

  <!-- Script de Navegación -->
  <script>
    const slides = document.querySelectorAll('.slide');
    const totalSlides = slides.length;
    let currentIdx = 0;

    const currentSpan = document.getElementById('current-slide');
    const progressBar = document.getElementById('progress-bar');
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    const btnFs = document.getElementById('btn-fullscreen');
    const container = document.getElementById('deck-container');

    function updateSlide(newIdx) {{
      if (newIdx < 0 || newIdx >= totalSlides) return;
      slides[currentIdx].classList.remove('opacity-100', 'z-10');
      slides[currentIdx].classList.add('opacity-0', 'pointer-events-none');

      currentIdx = newIdx;
      slides[currentIdx].classList.remove('opacity-0', 'pointer-events-none');
      slides[currentIdx].classList.add('opacity-100', 'z-10');

      currentSpan.textContent = currentIdx + 1;
      progressBar.style.width = (((currentIdx + 1) / totalSlides) * 100) + '%';
    }}

    btnPrev.addEventListener('click', () => updateSlide(currentIdx - 1));
    btnNext.addEventListener('click', () => updateSlide(currentIdx + 1));

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {{
        e.preventDefault();
        updateSlide(currentIdx + 1);
      }} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
        e.preventDefault();
        updateSlide(currentIdx - 1);
      }} else if (e.key === 'Home') {{
        updateSlide(0);
      }} else if (e.key === 'End') {{
        updateSlide(totalSlides - 1);
      }} else if (e.key === 'f' || e.key === 'F') {{
        toggleFullscreen();
      }}
    }});

    function toggleFullscreen() {{
      if (!document.fullscreenElement) {{
        container.requestFullscreen().catch(err => alert(err.message));
      }} else {{
        document.exitFullscreen();
      }}
    }}
    btnFs.addEventListener('click', toggleFullscreen);
  </script>
</body>
</html>
"""


class MarpParams(BaseModel):
    tema_presentacion: str = Field(description="El tema central o título de la presentación ejecutiva.")
    contenido_diapositivas: List[str] = Field(description="Lista de diapositivas en Markdown (cada elemento es una lámina).")
    estilo_tema: str = Field(default="dark_executive", description="Estilo visual: 'dark_executive', 'clean_modern' o 'pitch_deck'.")
    generar_html_interactivo: bool = Field(default=True, description="Generar automáticamente visor HTML interactivo además del Markdown Marp.")
    ruta_destino: str = Field(default="presentacion_ejecutiva.md", description="Ruta o nombre del archivo .md de salida.")


@tool("generar_presentacion_marp", args_schema=MarpParams)
def generar_presentacion_marp(
    tema_presentacion: str,
    contenido_diapositivas: List[str],
    estilo_tema: str = "dark_executive",
    generar_html_interactivo: bool = True,
    ruta_destino: str = "presentacion_ejecutiva.md"
) -> str:
    """
    Genera una presentación ejecutiva profesional compilada en Markdown compatible con Marp Core
    con estilos CSS personalizados inyectados, y crea simultáneamente un visor HTML interactivo
    autocontenido listo para abrir y navegar con el teclado en cualquier navegador.
    """
    try:
        if not tema_presentacion or not isinstance(tema_presentacion, str) or tema_presentacion.strip() in ("tema_presentacion", ""):
            tema_presentacion = "Presentación Estratégica"

        if not contenido_diapositivas or not isinstance(contenido_diapositivas, list):
            contenido_diapositivas = [
                f"# {tema_presentacion}\n**Documento Estratégico Ejecutivo**\n\n- Fecha: {datetime.date.today().isoformat()}\n- Elaborado por: Subagente de Diseño",
                "## Resumen Ejecutivo y Tesis\n- **Oportunidad:** Crecimiento acelerado en el canal directo.\n- **Enfoque:** Alta conversión visual y optimización de recursos.\n- **Objetivo:** Retorno medible en el primer trimestre."
            ]
        else:
            _literales = {"contenido_diapositivas", "ruta_destino", "tema_presentacion", "ruta", "destino"}
            contenido_filtrado = [
                item for item in contenido_diapositivas
                if isinstance(item, str) and item.strip() and item.strip().lower() not in _literales
            ]
            contenido_diapositivas = contenido_filtrado if contenido_filtrado else [
                f"# {tema_presentacion}\n**Estrategia y Plan de Acción**",
                "## Pilares Estratégicos\n- Ejecución ágil y diseño de agencia."
            ]

        # Asegurar que la primera diapositiva sea de portada si no lo es
        if not contenido_diapositivas[0].strip().startswith("# "):
            contenido_diapositivas.insert(0, f"# {tema_presentacion}\n**Presentación Estratégica**\n\n*Subagente de Diseño • {datetime.date.today().isoformat()}*")

        # 1. Compilar Archivo Markdown Marp con CSS embebido
        destino_md = _transformar_ruta(ruta_destino, ".md")
        destino_md.parent.mkdir(parents=True, exist_ok=True)

        css_tema = _generar_css_marp(estilo_tema)

        with open(destino_md, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write("marp: true\n")
            f.write(f"theme: {estilo_tema}\n")
            f.write("paginate: true\n")
            f.write("size: 16:9\n")
            f.write(f"title: \"{tema_presentacion}\"\n")
            f.write("---\n\n")
            f.write(f"<style>\n{css_tema}\n</style>\n\n")

            for index, slide in enumerate(contenido_diapositivas):
                f.write(f"{slide}\n")
                if index < len(contenido_diapositivas) - 1:
                    f.write("\n---\n\n")

            f.write("\n\n---\n*Compilado por: [[Perfil_Subagente_Diseno]]*\n")

        tamano_md = destino_md.stat().st_size
        ruta_md_norm = str(destino_md).replace("\\", "/")

        # 2. Compilar Visor HTML Interactivo
        ruta_html_norm = None
        if generar_html_interactivo:
            destino_html = destino_md.with_suffix(".html")
            codigo_html = _generar_html_interactivo(
                tema_presentacion=tema_presentacion,
                contenido_diapositivas=contenido_diapositivas,
                estilo_tema=estilo_tema
            )
            with open(destino_html, "w", encoding="utf-8") as f:
                f.write(codigo_html)
            ruta_html_norm = str(destino_html).replace("\\", "/")

        # Metadatos Zero-Trust
        meta_dict = {
            "tema": tema_presentacion,
            "estilo_tema": estilo_tema,
            "diapositivas_totales": len(contenido_diapositivas),
            "archivo_marp_md": ruta_md_norm,
            "archivo_html_interactivo": ruta_html_norm,
            "timestamp": datetime.datetime.now().isoformat()
        }
        ruta_meta = destino_md.parent / f"{destino_md.stem}.verificacion.json"
        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, ensure_ascii=False, indent=2)

        return json.dumps({
            "status": "success",
            "tema": tema_presentacion,
            "estilo_aplicado": estilo_tema,
            "total_diapositivas": len(contenido_diapositivas),
            "ruta_markdown_marp": ruta_md_norm,
            "ruta_html_interactivo": ruta_html_norm,
            "metadatos_verificacion": str(ruta_meta).replace("\\", "/"),
            "mensaje": f"Presentación ejecutiva compilada con éxito. Archivo Marp: {ruta_md_norm}. Visor interactivo para navegador: {ruta_html_norm}."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al generar presentación ejecutiva: {str(e)}"}, ensure_ascii=False)


HERRAMIENTAS_PRESENTACIONES = [generar_presentacion_marp]
