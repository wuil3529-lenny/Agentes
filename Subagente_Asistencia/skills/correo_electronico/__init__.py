from .skill_correo_electronico import (
    tool_correo_recibir_y_analizar,
    tool_correo_consultar_detalle,
    tool_correo_responder,
    tool_correo_notificar_usuario,
    tool_correo_seguimiento_pendientes,
    obtener_prompt_correo_electronico,
    HERRAMIENTAS_CORREO_ELECTRONICO,
)

PROMPT_HABILIDAD_CORREO_ELECTRONICO = obtener_prompt_correo_electronico()
PROMPT_HABILIDAD_CORREO = PROMPT_HABILIDAD_CORREO_ELECTRONICO
HERRAMIENTAS_CORREO = HERRAMIENTAS_CORREO_ELECTRONICO

__all__ = [
    "tool_correo_recibir_y_analizar",
    "tool_correo_consultar_detalle",
    "tool_correo_responder",
    "tool_correo_notificar_usuario",
    "tool_correo_seguimiento_pendientes",
    "obtener_prompt_correo_electronico",
    "PROMPT_HABILIDAD_CORREO_ELECTRONICO",
    "PROMPT_HABILIDAD_CORREO",
    "HERRAMIENTAS_CORREO_ELECTRONICO",
    "HERRAMIENTAS_CORREO",
]
