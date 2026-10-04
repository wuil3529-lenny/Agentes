"""
Subagente_Desarrollo/skills/taste/__init__.py
=============================================
Punto de exportación de la habilidad de Criterio de Diseño y Anti-Slop (Taste Skill).
"""

from .skill_taste import (
    tool_taste_inferir_brief,
    tool_taste_generar_tokens,
    tool_taste_auditar_anti_defaults,
    tool_taste_catalogo_estilos,
    obtener_prompt_taste,
    HERRAMIENTAS_TASTE,
    CATALOGO_ESTILOS_TASTE,
)

PROMPT_HABILIDAD_TASTE = obtener_prompt_taste()

__all__ = [
    "tool_taste_inferir_brief",
    "tool_taste_generar_tokens",
    "tool_taste_auditar_anti_defaults",
    "tool_taste_catalogo_estilos",
    "obtener_prompt_taste",
    "PROMPT_HABILIDAD_TASTE",
    "HERRAMIENTAS_TASTE",
    "CATALOGO_ESTILOS_TASTE",
]
