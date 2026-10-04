"""
solicitar_soporte_pizarra/__init__.py
====================================
Paquete modular de la Habilidad: Solicitud de Soporte, Pausa y Delegación en Pizarra.
"""

from .skill_solicitar_soporte_pizarra import (
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra,
    obtener_prompt_solicitar_soporte_pizarra,
    HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA
)

__all__ = [
    "tool_solicitar_ayuda_pizarra",
    "tool_consultar_estado_ticket_pizarra",
    "obtener_prompt_solicitar_soporte_pizarra",
    "HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA"
]
