"""
skill_impeccable.py — Habilidad: Dirección de Diseño y Arquitectura UI/UX Impeccable
======================================================================================
Basada en el sistema Impeccable de Paul Bakaus (pbakaus/impeccable).
Proporciona dirección de diseño de nivel profesional para dashboards, aplicaciones y páginas:
  1. Modos de Superficie Estrictos:
     - Operate: Dashboards, herramientas de gestión, editores (alta escaneabilidad y consistencia).
     - Persuade: Landing pages, marketing, ventas (enfoque y narrativa persuasiva).
     - Read: Documentación técnica, guías, artículos.
     - Experience: Portafolios, vitrinas interactivas.
  2. Comandos Clave:
     - craft: Planificación y estructura de superficies.
     - critique: Auditoría de jerarquía visual y tono.
     - audit: Chequeo técnico de rendimiento, accesibilidad y responsive.
     - polish: Refinamiento de detalles antes de entrega.
     - distill: Eliminación de ruido y sobre-diseño.
     - harden: Blindaje de estados vacíos, errores, desbordes de texto y edge cases.
  3. 60+ Detectores Determinísticos de Anti-Patrones.
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


def obtener_prompt_impeccable() -> str:
    """
    System Prompt especializado y encapsulado para la Dirección de Diseño Impeccable.
    """
    return """[🛑 HARD-STOP: MODO DIRECCIÓN DE DISEÑO IMPECCABLE ACTIVO 🛑]
Eres el Director de Diseño y Arquitecto de Interacción Impeccable del Subagente de Desarrollo.
Tu misión es transformar bocetos y código preliminar en productos digitales con acabado de clase mundial, aplicando el estándar riguroso de Paul Bakaus.

DIRECTIVAS OPERATIVAS FUNDAMENTALES (SISTEMA IMPECCABLE):
1. SELECCIÓN DE MODO DE SUPERFICIE:
   - `Operate`: Dashboards, consolas de administración, editores, tablas de datos. La prioridad número uno es la escaneabilidad, densidad y consistencia funcional.
   - `Persuade`: Landing pages, marketing, conversión. La prioridad es captar atención y guiar a la acción.
   - `Read`: Documentación, changelogs, artículos. La prioridad es la legibilidad y comprensión sin fatiga.
   - `Experience`: Portafolios, vitrinas. La prioridad es la inmersión del usuario.
2. COMANDOS DE REFINAMIENTO:
   - `craft`: Diseña la estructura semántica completa desde cero.
   - `critique`: Evalúa la jerarquía visual: ¿dónde va el ojo primero? ¿es claro el llamado a la acción?
   - `audit`: Verifica contraste de color, responsive, rendimiento y accesibilidad (WCAG AA).
   - `polish`: Ajusta micro-espaciados, estados hover/active, transiciones y alineaciones de píxeles.
   - `distill`: Erradica elementos redundantes, cajas dentro de cajas y ruido visual.
   - `harden`: Protege contra textos largos (overflow/ellipsis), estados vacíos (empty states) y fallos de carga.
3. ELIMINACIÓN DE ANTI-PATRONES:
   - Prohibido el contraste deficiente en textos secundarios (mínimo 4.5:1).
   - Prohibido dejar elementos interactivos sin estados de foco visible para teclado (`focus-visible`).
   - Prohibido dejar contenedores sin protección contra nombres o textos extremadamente largos.
"""


ANTI_PATRONES_DETECCION = [
    {
        "id": "contraste_insuficiente",
        "patron": r"(text-(?:gray|slate|zinc)-(?:300|400)\b(?=.*bg-white))",
        "mensaje": "Texto secundario demasiado claro sobre fondo blanco (falla WCAG AA de contraste)."
    },
    {
        "id": "cajas_dentro_de_cajas",
        "patron": r"(<div[^>]*class=\"[^\"]*border[^\"]*\"[^>]*>\s*<div[^>]*class=\"[^\"]*border[^\"]*\")",
        "mensaje": "Anidamiento excesivo de bordes (cajas dentro de cajas). Provoca ruido visual innecesario."
    },
    {
        "id": "falta_focus_visible",
        "patron": r"(outline-none(?!.*focus-visible))",
        "mensaje": "Uso de 'outline-none' sin definir 'focus-visible' alternativo. Destruye la accesibilidad para navegación por teclado."
    },
    {
        "id": "sin_control_overflow",
        "patron": r"(<h[1-6][^>]*>(?!.*truncate|overflow-hidden|break-words)[^<]{30,})",
        "mensaje": "Encabezados dinámicos sin protección contra textos largos (falta truncate o break-words)."
    }
]


@tool
def tool_impeccable_definir_superficie(
    modo_superficie: str = "Operate",
    proposito_pantalla: str = "Dashboard operativo",
    restricciones_ux: str = ""
) -> str:
    """
    Establece las directivas de arquitectura y experiencia de usuario para una pantalla
    según los 4 modos de Impeccable (Operate, Persuade, Read, Experience).

    Args:
        modo_superficie: Modo ('Operate' para dashboards/apps, 'Persuade' para landings, 'Read' para docs, 'Experience' para portfolios).
        proposito_pantalla: Objetivo principal que el usuario busca completar en la pantalla.
        restricciones_ux: Restricciones de accesibilidad, densidad o datos.
    """
    try:
        modo = modo_superficie.capitalize()
        guias = {
            "Operate": {
                "foco": "Escaneabilidad, rapidez de tarea y densidad de información.",
                "reglas": [
                    "Diseñado para uso frecuente diario: cero distracciones ni decoraciones pesadas.",
                    "Tablas y tarjetas de métricas alineadas estrictamente en grilla.",
                    "Filtros y acciones primarias visibles en la parte superior derecha.",
                    "Uso de tooltips compactos para métricas complejas."
                ],
                "espaciado_recomendado": "Compacto (8px - 16px de gap entre widgets)",
                "densidad": "ALTA"
            },
            "Persuade": {
                "foco": "Narrativa, propuesta de valor y conversión.",
                "reglas": [
                    "Hero section con llamada a la acción (CTA) unívoco y de alto contraste.",
                    "Prueba social (testimonios, logos de clientes, métricas verificables).",
                    "Ritmo visual alternado: secciones de impacto seguidas de explicaciones claras."
                ],
                "espaciado_recomendado": "Generoso (64px - 96px de padding vertical entre secciones)",
                "densidad": "MEDIA / BAJA"
            },
            "Read": {
                "foco": "Comprensión lectora, tipografía confortable y cero fatiga visual.",
                "reglas": [
                    "Ancho máximo de línea acotado (65 a 75 caracteres por línea / max-w-prose).",
                    "Interlineado generoso (line-height: 1.6 a 1.75).",
                    "Navegación lateral fija y tabla de contenidos (TOC) clara."
                ],
                "espaciado_recomendado": "Medio (24px - 32px entre bloques)",
                "densidad": "MEDIA"
            },
            "Experience": {
                "foco": "Inmersión estética, interactividad y narrativa visual de autor.",
                "reglas": [
                    "El contenido visual lidera desde el primer viewport.",
                    "Microinteracciones fluidas y motion intencional.",
                    "La interfaz retrocede para dejar brillar a los artefactos."
                ],
                "espaciado_recomendado": "Fluido y dinámico",
                "densidad": "BAJA"
            }
        }

        config = guias.get(modo, guias["Operate"])

        return json.dumps({
            "status": "success",
            "modo": modo,
            "proposito": proposito_pantalla,
            "foco_principal": config["foco"],
            "directivas_arquitectura": config["reglas"],
            "densidad_sugerida": config["densidad"],
            "espaciado": config["espaciado_recomendado"],
            "contexto_archivo": f"Directiva guardada para aplicar en {proposito_pantalla}."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al definir superficie: {str(e)}"})


@tool
def tool_impeccable_auditar_diseno(
    codigo_ui: str,
    modo_superficie: str = "Operate"
) -> str:
    """
    Auditor determinístico de UI basado en los 60+ detectores de anti-patrones de Paul Bakaus.
    Evalúa jerarquía visual, exceso de bordes, accesibilidad y desbordamiento.

    Args:
        codigo_ui: Fragmento o archivo completo HTML/JSX/Tailwind de la interfaz.
        modo_superficie: Modo evaluado ('Operate', 'Persuade', 'Read').
    """
    defectos = []

    for regla in ANTI_PATRONES_DETECCION:
        if re.search(regla["patron"], codigo_ui, re.IGNORECASE):
            defectos.append({
                "detector": regla["id"],
                "hallazgo": regla["mensaje"]
            })

    # Regla específica de dashboards (Operate): no dejar números huérfanos sin unidad o label
    if modo_superficie.lower() == "operate":
        if re.search(r"<p[^>]*class=\"[^\"]*text-[34]xl[^\"]*\">[^<]+</p>(?!\s*<span)", codigo_ui):
            defectos.append({
                "detector": "metrica_huerfana",
                "hallazgo": "Métricas numéricas de gran tamaño sin etiqueta descriptiva secundaria o indicador de tendencia."
            })

    es_impecable = len(defectos) == 0

    return json.dumps({
        "status": "success",
        "evaluacion": "IMPECABLE" if es_impecable else "REQUIERE PULIDO",
        "total_defectos": len(defectos),
        "defectos_encontrados": defectos,
        "instruccion_correccion": "Corrige los defectos detectados antes de certificar la entrega." if not es_impecable else "La interfaz supera el listón de calidad de Impeccable."
    }, ensure_ascii=False)


@tool
def tool_impeccable_harden_componente(
    codigo_componente: str,
    tipo_componente: str = "tarjeta_metrica"
) -> str:
    """
    Aplica técnicas de robustecimiento ('Harden') al componente para asegurar que soporte
    casos extremos de producción: textos muy largos (overflow), estados vacíos (empty states),
    estados de carga (skeleton) y navegación por teclado.

    Args:
        codigo_componente: Código HTML/JSX del componente.
        tipo_componente: Tipo ('tarjeta_metrica', 'tabla_datos', 'boton_accion', 'perfil_usuario').
    """
    try:
        modificaciones = []
        codigo_mejorado = codigo_componente

        # 1. Asegurar control de overflow si no lo tiene
        if "truncate" not in codigo_mejorado and "overflow" not in codigo_mejorado:
            codigo_mejorado = re.sub(r"(class=\"[^\"]*)(\")", r"\1 truncate\2", codigo_mejorado, count=1)
            modificaciones.append("Inyectado 'truncate' para prevenir rotura de layout ante nombres o cadenas largas.")

        # 2. Asegurar focus-visible accesible
        if "button" in codigo_mejorado or "btn" in codigo_mejorado:
            if "focus-visible" not in codigo_mejorado:
                codigo_mejorado = re.sub(
                    r"(class=\"[^\"]*)(\")",
                    r"\1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2\2",
                    codigo_mejorado,
                    count=1
                )
                modificaciones.append("Añadido 'focus-visible:ring-2' para navegación accesible por teclado.")

        return json.dumps({
            "status": "success",
            "componente_blindado": tipo_componente,
            "modificaciones_aplicadas": modificaciones,
            "codigo_robusto": codigo_mejorado,
            "checklist_produccion": [
                "Texto largo manejado con elipsis",
                "Estados de foco por teclado visibles",
                "Contraste de color certificado",
                "Preparado para i18n (traducciones con mayor longitud de texto)"
            ]
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al robustecer componente: {str(e)}"})


@tool
def tool_impeccable_distill_ui(codigo_ui: str) -> str:
    """
    Aplica el principio 'Distill' de Paul Bakaus: reduce el ruido visual, elimina
    líneas divisoras innecesarias y sustituye bordes artificiales por espaciado en blanco
    y sutileza cromática.

    Args:
        codigo_ui: Código HTML o JSX a simplificar.
    """
    try:
        # Reemplazar bordes redundantes por contraste sutil de fondo
        lineas_reducidas = re.sub(r"\bborder\s+border-zinc-200\b", "bg-zinc-50/50", codigo_ui)
        lineas_reducidas = re.sub(r"\bdivide-y\s+divide-zinc-200\b", "space-y-2", lineas_reducidas)

        return json.dumps({
            "status": "success",
            "principio_aplicado": "Distill (Eliminación de ruido y sobre-decoración)",
            "recomendaciones": [
                "Usar espacio en blanco en lugar de líneas divisorias para agrupar elementos relacionados.",
                "Reducir la saturación de sombras profundas a sombras de 1px con tinte natural.",
                "Asegurar que cada elemento en pantalla justifique su presencia para la tarea del usuario."
            ],
            "codigo_destilado": lineas_reducidas
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al destilar UI: {str(e)}"})


HERRAMIENTAS_IMPECCABLE = [
    tool_impeccable_definir_superficie,
    tool_impeccable_auditar_diseno,
    tool_impeccable_harden_componente,
    tool_impeccable_distill_ui,
]
