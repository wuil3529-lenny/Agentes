"""
Subagente_Desarrollo/skills/conectores_mcp_api/__init__.py
==========================================================
Punto de exportación de la habilidad de Conectores Universales MCP y APIs con Ciberseguridad.
"""

from .skill_conectores_mcp_api import (
    tool_solicitar_auditoria_ciberseguridad,
    tool_conectar_api_rest,
    tool_conectar_servidor_mcp,
    tool_probar_conexion_segura,
    obtener_prompt_conectores_mcp_api,
    HERRAMIENTAS_CONECTORES_MCP_API,
)

PROMPT_HABILIDAD_CONECTORES_MCP_API = obtener_prompt_conectores_mcp_api()

__all__ = [
    "tool_solicitar_auditoria_ciberseguridad",
    "tool_conectar_api_rest",
    "tool_conectar_servidor_mcp",
    "tool_probar_conexion_segura",
    "obtener_prompt_conectores_mcp_api",
    "PROMPT_HABILIDAD_CONECTORES_MCP_API",
    "HERRAMIENTAS_CONECTORES_MCP_API",
]
