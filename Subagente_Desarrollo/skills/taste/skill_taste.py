"""
skill_taste.py — Habilidad: Criterio de Diseño Frontend y Anti-Slop (Taste Skill)
===================================================================================
Basada en la metodología de tasteskill.dev (Leonxlnx / taste-skill).
Inyecta juicio estético y toma de decisiones deliberadas al generar interfaces frontend,
combatiendo los vicios comunes de la IA (púrpura genérico, tarjetas idénticas, fuentes default):
  1. Inferencia del Brief ("Read the Room"): diagnostica la audiencia y vibra antes de programar.
  2. Disciplina Anti-Default: prohíbe plantillas repetitivas de IA.
  3. Generación de sistemas tipográficos y cromáticos con carácter e identidad de marca.
  4. Diales de diseño configurables: DESIGN_VARIANCE, DENSITY, TYPOGRAPHY_EXPRESSION.
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_taste() -> str:
    """
    System Prompt especializado y encapsulado para el modo de Criterio de Diseño (Taste Skill).
    """
    return """[🛑 HARD-STOP: MODO CRITERIO DE DISEÑO Y ANTI-SLOP (TASTE SKILL) ACTIVO 🛑]
Eres el Director de Arte y Curador de Diseño Frontend del Subagente de Desarrollo.
Tu misión es erradicar el diseño genérico de IA ("AI slop") e inyectar carácter, intención visual y jerarquía impecable en cada interfaz, dashboard o aplicación web.

DIRECTIVAS OPERATIVAS FUNDAMENTALES (METODOLOGÍA TASTESKILL):
1. INFERENCIA DEL BRIEF (READ THE ROOM PRIMERO):
   - Antes de escribir una sola línea de HTML o CSS, declara tu "Design Read":
     * "¿Para quién es este producto? ¿Cuál es el tono (Linear-clean, Awwwards-kinetic, Swiss-minimalist, Trust-first B2B, Modern-brutalist)?"
   - La audiencia y el objetivo del producto eligen la estética, no tu gusto por defecto.
2. DISCIPLINA ANTI-DEFAULT (PROHIBIDO POR DISEÑO):
   - Prohibido el degradado morado de IA sobre fondo oscuro con partículas flotantes.
   - Prohibido estructurar siempre en 3 tarjetas idénticas con el mismo icono genérico.
   - Prohibido recurrir por defecto a Inter + slate-900 en todo sin considerar alternativas con mayor personalidad (Geist, Instrument Serif, Plus Jakarta, Cabinet Grotesk).
   - Prohibido el glassmorphism saturado en todas las cajas si no aporta jerarquía.
3. JERARQUÍA TIPOGRÁFICA Y ESPACIAL:
   - Contraste deliberado entre titulares con intención y cuerpos de texto ultralegibles.
   - Espaciado rítmico: alternancia entre áreas de alta densidad de información (datos, métricas) y espacios generosos de respiro visual.
4. DIALES DE INTENCIÓN DE DISEÑO:
   - DENSITY: Alta para dashboards operativos; Baja y aireada para páginas de aterrizaje persuasivas.
   - DESIGN_VARIANCE: Controlado para herramientas de trabajo; Audaz para portafolios y experiencias de marca.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# FAMILIAS ESTÉTICAS Y SISTEMAS CROMÁTICOS DE AUTOR
# ═══════════════════════════════════════════════════════════════════════════════

CATALOGO_ESTILOS_TASTE = {
    "linear_minimalist": {
        "nombre": "Linear Modern Dark / SaaS Técnico",
        "audiencia": "Desarrolladores, equipos de producto, fundadores técnicos",
        "descripcion": "Estética oscura de precisión, bordes sutiles de 1px con destellos metálicos, tipografía neutra y jerarquía nítida.",
        "fuente_titular": "Geist Sans, -apple-system, sans-serif",
        "fuente_cuerpo": "Geist Sans, -apple-system, sans-serif",
        "paleta": {
            "fondo": "#09090b",
            "superficie": "#121215",
            "borde": "rgba(255, 255, 255, 0.08)",
            "texto_primario": "#f4f4f5",
            "texto_secundario": "#a1a1aa",
            "acento": "#5e6ad2"
        },
        "css_variables": """--bg-app: #09090b;
--bg-surface: #121215;
--border-subtle: rgba(255, 255, 255, 0.08);
--border-accent: rgba(94, 106, 210, 0.4);
--text-primary: #f4f4f5;
--text-muted: #a1a1aa;
--accent-primary: #5e6ad2;
--radius-card: 12px;"""
    },
    "swiss_editorial": {
        "nombre": "Swiss Graphic / Precision Editorial",
        "audiencia": "Marcas culturales, agencias creativas, publicaciones analíticas",
        "descripcion": "Retículas asimétricas rígidas, contraste tipográfico alto entre serifa editorial y sans monoespaciada, fondos claros y espacios vacíos deliberados.",
        "fuente_titular": "'Instrument Serif', Georgia, serif",
        "fuente_cuerpo": "'Plus Jakarta Sans', system-ui, sans-serif",
        "paleta": {
            "fondo": "#fbfbfb",
            "superficie": "#ffffff",
            "borde": "#e4e4e7",
            "texto_primario": "#18181b",
            "texto_secundario": "#71717a",
            "acento": "#e11d48"
        },
        "css_variables": """--bg-app: #fbfbfb;
--bg-surface: #ffffff;
--border-subtle: #e4e4e7;
--text-primary: #18181b;
--text-muted: #71717a;
--accent-primary: #e11d48;
--radius-card: 0px; /* Bordes rectos suizos */"""
    },
    "trust_b2b_executive": {
        "nombre": "Corporate Executive / Trust-First B2B",
        "audiencia": "Banca, finanzas, legal, enterprise dashboards",
        "descripcion": "Sobrio, confiable, accesible WCAG AAA, densidad informativa alta, azul marino profundo y grises cálidos.",
        "fuente_titular": "'Inter Display', -apple-system, sans-serif",
        "fuente_cuerpo": "Inter, system-ui, sans-serif",
        "paleta": {
            "fondo": "#f8fafc",
            "superficie": "#ffffff",
            "borde": "#cbd5e1",
            "texto_primario": "#0f172a",
            "texto_secundario": "#475569",
            "acento": "#0284c7"
        },
        "css_variables": """--bg-app: #f8fafc;
--bg-surface: #ffffff;
--border-subtle: #cbd5e1;
--text-primary: #0f172a;
--text-muted: #475569;
--accent-primary: #0284c7;
--radius-card: 8px;"""
    },
    "modern_brutalist": {
        "nombre": "Neo-Brutalist Digital",
        "audiencia": "Web3, arte digital, startups disruptivas",
        "descripcion": "Bordes negros gruesos (2-3px), sombras proyectadas rígidas sin desenfoque (hard shadows), colores vibrantes con fondo neutro y tipografía monoespaciada.",
        "fuente_titular": "'Cabinet Grotesk', system-ui, sans-serif",
        "fuente_cuerpo": "'JetBrains Mono', monospace",
        "paleta": {
            "fondo": "#f4f4f0",
            "superficie": "#ffffff",
            "borde": "#000000",
            "texto_primario": "#000000",
            "texto_secundario": "#3f3f46",
            "acento": "#facc15"
        },
        "css_variables": """--bg-app: #f4f4f0;
--bg-surface: #ffffff;
--border-subtle: #000000;
--border-width: 2px;
--shadow-hard: 4px 4px 0px #000000;
--text-primary: #000000;
--accent-primary: #facc15;
--radius-card: 4px;"""
    },
    "soft_humanist": {
        "nombre": "Soft Humanist / Calma Orgánica",
        "audiencia": "Salud, bienestar, herramientas de notas, meditación, apps de calma",
        "descripcion": "Tonos tierra suaves, esquinas redondeadas generosas, sombras difusas y sensación táctil cálida.",
        "fuente_titular": "'Fraunces', Georgia, serif",
        "fuente_cuerpo": "'Plus Jakarta Sans', system-ui, sans-serif",
        "paleta": {
            "fondo": "#faf8f5",
            "superficie": "#ffffff",
            "borde": "#e7e2da",
            "texto_primario": "#292524",
            "texto_secundario": "#78716c",
            "acento": "#d97706"
        },
        "css_variables": """--bg-app: #faf8f5;
--bg-surface: #ffffff;
--border-subtle: #e7e2da;
--text-primary: #292524;
--text-muted: #78716c;
--accent-primary: #d97706;
--radius-card: 20px;"""
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS TÉCNICAS DE TASTE
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tool_taste_inferir_brief(
    tipo_producto: str,
    publico_objetivo: str = "general",
    vibe_deseado: str = "moderno y limpio",
    restricciones: str = ""
) -> str:
    """
    Analiza el requerimiento de una interfaz y emite el 'Design Read' declarativo.
    Determina la familia estética, densidad de información y arquitectura visual
    apropiada antes de programar, evitando el diseño genérico de IA.

    Args:
        tipo_producto: Tipo de producto ('dashboard', 'landing_saas', 'app_movil', 'ecommerce', 'portfolio').
        publico_objetivo: A quién va dirigido (ej: 'ingenieros de software', 'ejecutivos B2B', 'diseñadores').
        vibe_deseado: Palabras clave de tono (ej: 'Linear dark', 'editorial minimalista', 'trust B2B', 'brutalista').
        restricciones: Restricciones específicas de marca o accesibilidad.
    """
    try:
        texto_busqueda = f"{tipo_producto} {publico_objetivo} {vibe_deseado}".lower()
        familia_seleccionada = "linear_minimalist"

        if "b2b" in texto_busqueda or "banco" in texto_busqueda or "empresa" in texto_busqueda or "corporativo" in texto_busqueda:
            familia_seleccionada = "trust_b2b_executive"
        elif "editorial" in texto_busqueda or "revista" in texto_busqueda or "cultural" in texto_busqueda or "suizo" in texto_busqueda:
            familia_seleccionada = "swiss_editorial"
        elif "brutalis" in texto_busqueda or "web3" in texto_busqueda or "disruptiv" in texto_busqueda:
            familia_seleccionada = "modern_brutalist"
        elif "calma" in texto_busqueda or "salud" in texto_busqueda or "humano" in texto_busqueda or "organico" in texto_busqueda:
            familia_seleccionada = "soft_humanist"

        datos_estilo = CATALOGO_ESTILOS_TASTE[familia_seleccionada]

        # Configuración de diales
        es_dashboard = "dashboard" in tipo_producto.lower() or "admin" in tipo_producto.lower()
        diales = {
            "DENSITY": "Alta (espacios compactos de 8px-12px, foco en métricas y tablas)" if es_dashboard else "Media/Baja (respiro generoso, secciones con padding de 48px-80px)",
            "DESIGN_VARIANCE": "Controlado (alta consistencia y predictibilidad de controles)",
            "TYPOGRAPHY_EXPRESSION": "Funcional y limpio" if es_dashboard else "Titulares expresivos con jerarquía visual notable"
        }

        read_declarativo = (
            f"Reading this as: {tipo_producto} para {publico_objetivo}, "
            f"con un lenguaje {vibe_deseado}, respaldado por la familia estética '{datos_estilo['nombre']}'."
        )

        return json.dumps({
            "status": "success",
            "design_read": read_declarativo,
            "familia_estetica": familia_seleccionada,
            "nombre_estilo": datos_estilo["nombre"],
            "diales_configurados": diales,
            "fuentes_recomendadas": {
                "titulares": datos_estilo["fuente_titular"],
                "cuerpo": datos_estilo["fuente_cuerpo"]
            },
            "paleta_sugerida": datos_estilo["paleta"],
            "directiva_anti_slop": "Prohibido usar gradientes morados genéricos, Inter plano sin jerarquía o 3 tarjetas idénticas."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al inferir brief de diseño: {str(e)}"})


@tool
def tool_taste_generar_tokens(
    familia_estetica: str = "linear_minimalist",
    modo_color: str = "dark"
) -> str:
    """
    Genera tokens de diseño listos para inyectar en CSS o Tailwind, incluyendo variables
    de color, tipografía de autor, radios de borde y espaciado intencional.

    Args:
        familia_estetica: Clave del estilo ('linear_minimalist', 'swiss_editorial', 'trust_b2b_executive', 'modern_brutalist', 'soft_humanist').
        modo_color: 'dark' o 'light'.
    """
    try:
        clave = familia_estetica.lower().replace("-", "_")
        estilo = CATALOGO_ESTILOS_TASTE.get(clave, CATALOGO_ESTILOS_TASTE["linear_minimalist"])

        tokens_css = f"""/* Tokens de Diseño Taste Skill — {estilo['nombre']} */
:root {{
  --font-heading: {estilo['fuente_titular']};
  --font-body: {estilo['fuente_cuerpo']};
{estilo['css_variables']}
}}
"""
        return json.dumps({
            "status": "success",
            "familia": estilo["nombre"],
            "descripcion": estilo["descripcion"],
            "codigo_tokens_css": tokens_css,
            "paleta": estilo["paleta"]
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al generar tokens de diseño: {str(e)}"})


@tool
def tool_taste_auditar_anti_defaults(codigo_html_o_css: str) -> str:
    """
    Auditor riguroso de diseño para erradicar el 'AI Slop' (malas prácticas visuales comunes en LLMs).
    Detecta patrones de diseño genéricos y recomienda alternativas de autor.

    Args:
        codigo_html_o_css: Código fuente de la interfaz a auditar.
    """
    vicios_detectados = []
    recomendaciones = []

    # 1. Púrpura de IA genérico (#8b5cf6, #7c3aed, purple-600, violet-500)
    if re.search(r"(#8b5cf6|#7c3aed|#6d28d9|purple-\d+|violet-\d+)", codigo_html_o_css, re.IGNORECASE):
        vicios_detectados.append("Detección de púrpura / violeta genérico de IA en gradientes o botones.")
        recomendaciones.append("Sustituye el púrpura por paletas intencionales: azul índigo sobrio (#5e6ad2), monocromo estricto con acento o tonos cálidos de autor.")

    # 2. Tres tarjetas de características idénticas
    if len(re.findall(r"grid-cols-3|grid-cols-1 md:grid-cols-3", codigo_html_o_css)) > 0:
        if codigo_html_o_css.count("<div") > 15 and "feature" in codigo_html_o_css.lower():
            vicios_detectados.append("Patrón repetitivo de 3 tarjetas idénticas de 'features'.")
            recomendaciones.append("Introduce asimetría deliberada: destaca una tarjeta principal (Bento Grid) con mayor tamaño, infografía o métrica interactiva.")

    # 3. Glassmorphism excesivo (backdrop-blur indiscriminado)
    conteo_blur = len(re.findall(r"backdrop-blur", codigo_html_o_css, re.IGNORECASE))
    if conteo_blur > 4:
        vicios_detectados.append(f"Uso excesivo de glassmorphism ({conteo_blur} elementos con backdrop-blur).")
        recomendaciones.append("Reserva el desenfoque de fondo exclusivamente para la barra de navegación o modales; los contenedores de contenido deben tener superficies sólidas opacas para evitar ruido.")

    # 4. Falta de jerarquía en textos (todos con font-medium o mismo color)
    if "text-slate-400" in codigo_html_o_css and "text-slate-900" in codigo_html_o_css and "font-" not in codigo_html_o_css:
        vicios_detectados.append("Bajo contraste tipográfico entre títulos y párrafos.")
        recomendaciones.append("Aplica contraste deliberado: h1 con tracking negativo (`tracking-tight`), peso bold o semi-bold y fuente de titular distinguible.")

    aprobado = len(vicios_detectados) == 0

    return json.dumps({
        "status": "success",
        "evaluacion_taste": "EXCELENTE — CERO SLOP" if aprobado else "REVISIÓN REQUERIDA",
        "vicios_detectados": vicios_detectados,
        "recomendaciones_de_autor": recomendaciones,
        "puntuacion_criterio": 10 if aprobado else max(4, 10 - len(vicios_detectados) * 2)
    }, ensure_ascii=False)


@tool
def tool_taste_catalogo_estilos() -> str:
    """
    Retorna el catálogo completo de estilos y familias estéticas disponibles en Taste Skill
    con sus casos de uso recomendados.
    """
    try:
        lista = []
        for clave, item in CATALOGO_ESTILOS_TASTE.items():
            lista.append({
                "id": clave,
                "nombre": item["nombre"],
                "audiencia_ideal": item["audiencia"],
                "descripcion": item["descripcion"],
                "fuentes": f"Titulares: {item['fuente_titular']} | Cuerpo: {item['fuente_cuerpo']}"
            })

        return json.dumps({
            "status": "success",
            "total_estilos": len(lista),
            "estilos": lista
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al consultar catálogo: {str(e)}"})


HERRAMIENTAS_TASTE = [
    tool_taste_inferir_brief,
    tool_taste_generar_tokens,
    tool_taste_auditar_anti_defaults,
    tool_taste_catalogo_estilos,
]
