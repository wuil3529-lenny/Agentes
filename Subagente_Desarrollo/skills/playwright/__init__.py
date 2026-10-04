"""
Subagente_Desarrollo/skills/playwright/__init__.py
=================================================
Punto de exportación de la habilidad Playwright MCP y Verificación en Navegador.
"""

from .skill_playwright import (
    tool_playwright_generar_test,
    tool_playwright_verificar_responsive,
    tool_playwright_inspeccionar_accesibilidad,
    tool_playwright_configurar_mcp,
    obtener_prompt_playwright,
    HERRAMIENTAS_PLAYWRIGHT,
)

PROMPT_HABILIDAD_PLAYWRIGHT = obtener_prompt_playwright()

__all__ = [
    "tool_playwright_generar_test",
    "tool_playwright_verificar_responsive",
    "tool_playwright_inspeccionar_accesibilidad",
    "tool_playwright_configurar_mcp",
    "obtener_prompt_playwright",
    "PROMPT_HABILIDAD_PLAYWRIGHT",
    "HERRAMIENTAS_PLAYWRIGHT",
]
