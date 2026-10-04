"""
Subagente_Desarrollo/skills/animaciones/__init__.py
===================================================
Punto de exportación de la habilidad de Animaciones y Microinteracciones UI
inspirada en la filosofía de Emil Kowalski.
"""

from .skill_animaciones import (
    tool_generar_animacion_css,
    tool_generar_animacion_motion,
    tool_auditar_animaciones,
    tool_catalogo_recetas_animacion,
    obtener_prompt_animaciones,
    HERRAMIENTAS_ANIMACIONES,
    RECETAS_CATALOGO,
    TOKENS_CSS_BASE,
)

PROMPT_HABILIDAD_ANIMACIONES = obtener_prompt_animaciones()

__all__ = [
    "tool_generar_animacion_css",
    "tool_generar_animacion_motion",
    "tool_auditar_animaciones",
    "tool_catalogo_recetas_animacion",
    "obtener_prompt_animaciones",
    "PROMPT_HABILIDAD_ANIMACIONES",
    "HERRAMIENTAS_ANIMACIONES",
    "RECETAS_CATALOGO",
    "TOKENS_CSS_BASE",
]
