"""
Módulo de Habilidad: Triaje y Monitoreo de Nuevos Correos (Gmail) para Subagente de Asistencia
"""

from .skill_inbox import (
    tool_inbox_analizar_nuevos_correos,
    tool_inbox_clasificar_correo,
    tool_inbox_resumen_estado,
    tool_inbox_gmail,
    obtener_prompt_inbox,
)

__all__ = [
    "tool_inbox_analizar_nuevos_correos",
    "tool_inbox_clasificar_correo",
    "tool_inbox_resumen_estado",
    "tool_inbox_gmail",
    "obtener_prompt_inbox",
]
