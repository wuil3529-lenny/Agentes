"""
smart_tv/__init__.py
====================
Paquete modular de la Habilidad: Control Remoto Virtual y Gestión de Smart TVs (Sanji).
"""

from .skill_smart_tv import (
    tool_controlar_smart_tv,
    tool_silenciar_smart_tv,
    tool_obtener_estado_smart_tv,
    obtener_prompt_smart_tv,
    HERRAMIENTAS_SMART_TV,
)

__all__ = [
    "tool_controlar_smart_tv",
    "tool_silenciar_smart_tv",
    "tool_obtener_estado_smart_tv",
    "obtener_prompt_smart_tv",
    "HERRAMIENTAS_SMART_TV",
]
