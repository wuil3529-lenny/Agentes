"""
Subagente_Desarrollo/skills/impeccable/__init__.py
==================================================
Punto de exportación de la habilidad Impeccable Design System de Paul Bakaus.
"""

from .skill_impeccable import (
    tool_impeccable_definir_superficie,
    tool_impeccable_auditar_diseno,
    tool_impeccable_harden_componente,
    tool_impeccable_distill_ui,
    obtener_prompt_impeccable,
    HERRAMIENTAS_IMPECCABLE,
)

PROMPT_HABILIDAD_IMPECCABLE = obtener_prompt_impeccable()

__all__ = [
    "tool_impeccable_definir_superficie",
    "tool_impeccable_auditar_diseno",
    "tool_impeccable_harden_componente",
    "tool_impeccable_distill_ui",
    "obtener_prompt_impeccable",
    "PROMPT_HABILIDAD_IMPECCABLE",
    "HERRAMIENTAS_IMPECCABLE",
]
