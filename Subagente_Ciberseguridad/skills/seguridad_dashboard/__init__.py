"""
Módulo de Habilidad: Seguridad y Monitoreo del Dashboard (SOC Defensivo)
========================================================================
Provee herramientas para auditar incidentes de intrusión, verificar el estado
de la alarma perimetral del Dashboard, gestionar alertas y evaluar la postura
de seguridad y autenticación de la consola central.
"""

from .skill_seguridad_dashboard import (
    tool_consultar_incidentes_dashboard,
    tool_verificar_estado_alarma_dashboard,
    tool_gestionar_alarma_dashboard,
    tool_auditar_postura_dashboard,
    tool_bloquear_ip_dashboard,
    obtener_prompt_seguridad_dashboard
)

__all__ = [
    "tool_consultar_incidentes_dashboard",
    "tool_verificar_estado_alarma_dashboard",
    "tool_gestionar_alarma_dashboard",
    "tool_auditar_postura_dashboard",
    "tool_bloquear_ip_dashboard",
    "obtener_prompt_seguridad_dashboard"
]
