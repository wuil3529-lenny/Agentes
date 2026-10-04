"""
auto_aprendizaje/__init__.py
============================
Paquete modular de la Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks (Agente_Orquestador).
"""

from .skill_auto_aprendizaje import (
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    obtener_prompt_auto_aprendizaje,
    HERRAMIENTAS_AUTO_APRENDIZAJE
)

__all__ = [
    "tool_consultar_playbook_memoria",
    "tool_registrar_playbook_memoria",
    "obtener_prompt_auto_aprendizaje",
    "HERRAMIENTAS_AUTO_APRENDIZAJE"
]
