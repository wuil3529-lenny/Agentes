"""
auto_aprendizaje/__init__.py
============================
Paquete modular de la Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks (Agente_Orquestador).
"""

from .skill_auto_aprendizaje import (
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    tool_iniciar_aprendizaje_tarea,
    tool_registrar_paso_aprendizaje,
    tool_finalizar_aprendizaje_tarea,
    tool_guardar_procedimiento_aprendido,
    tool_ejecutar_tarea_aprendida,
    tool_listar_tareas_aprendidas,
    tool_eliminar_tarea_aprendida,
    obtener_prompt_auto_aprendizaje,
    HERRAMIENTAS_AUTO_APRENDIZAJE,
    HERRAMIENTAS_PROCEDIMIENTOS
)

__all__ = [
    "tool_consultar_playbook_memoria",
    "tool_registrar_playbook_memoria",
    "tool_iniciar_aprendizaje_tarea",
    "tool_registrar_paso_aprendizaje",
    "tool_finalizar_aprendizaje_tarea",
    "tool_guardar_procedimiento_aprendido",
    "tool_ejecutar_tarea_aprendida",
    "tool_listar_tareas_aprendidas",
    "tool_eliminar_tarea_aprendida",
    "obtener_prompt_auto_aprendizaje",
    "HERRAMIENTAS_AUTO_APRENDIZAJE",
    "HERRAMIENTAS_PROCEDIMIENTOS"
]

