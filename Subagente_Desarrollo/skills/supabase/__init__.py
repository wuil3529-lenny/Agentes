"""
Subagente_Desarrollo/skills/supabase/__init__.py
================================================
Módulo de inicialización para la habilidad de gestión completa de Supabase,
auditoría de seguridad RLS, ejecución SQL y conectores de base de datos.
"""

from .skill_supabase import (
    tool_supabase_ejecutar_sql,
    tool_supabase_auditar_seguridad_rls,
    tool_supabase_modificar_rls,
    tool_supabase_crear_politica_rls,
    tool_supabase_consultar_tabla,
    tool_supabase_insertar_registro,
    tool_supabase_listar_proyectos,
    obtener_prompt_supabase,
    HERRAMIENTAS_SUPABASE,
)

__all__ = [
    "tool_supabase_ejecutar_sql",
    "tool_supabase_auditar_seguridad_rls",
    "tool_supabase_modificar_rls",
    "tool_supabase_crear_politica_rls",
    "tool_supabase_consultar_tabla",
    "tool_supabase_insertar_registro",
    "tool_supabase_listar_proyectos",
    "obtener_prompt_supabase",
    "HERRAMIENTAS_SUPABASE",
]
