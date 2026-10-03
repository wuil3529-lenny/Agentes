"""
Perfil_Subagente_Asistencia.py — Interfaz de Ejecución Canónica para Subagente de Asistencia
============================================================================================
Exporta e inicializa la funcionalidad completa de Subagente_Asistencia,
permitiendo la ejecución de ciclos de trabajo, tool calls y función de nodo LangGraph.
"""

from Subagente_Asistencia.subagente_asistencia_agent import (
    funcion_nodo_subagente_asistencia,
    ejecutar_ciclo,
    construir_system_prompt,
    cargar_prompt_asistencia,
    HERRAMIENTAS_ASISTENCIA,
    NOMBRE_AGENTE,
    NOMBRE_AGENTE_ALIAS,
    ARCHIVOS_TEMPORALES_PATH,
    ARCHIVOS_TEMPORALES_DOCKER,
    DOCUMENTOS_ASISTENCIA_PATH
)

# Compatibilidad de nodo
funcion_nodo_perfil_subagente_asistencia = funcion_nodo_subagente_asistencia

__all__ = [
    "funcion_nodo_subagente_asistencia",
    "funcion_nodo_perfil_subagente_asistencia",
    "ejecutar_ciclo",
    "construir_system_prompt",
    "cargar_prompt_asistencia",
    "HERRAMIENTAS_ASISTENCIA",
    "NOMBRE_AGENTE",
    "NOMBRE_AGENTE_ALIAS",
    "ARCHIVOS_TEMPORALES_PATH",
    "ARCHIVOS_TEMPORALES_DOCKER",
    "DOCUMENTOS_ASISTENCIA_PATH"
]

if __name__ == "__main__":
    import sys
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cuáles son tus habilidades operativas actuales?"
    print(ejecutar_ciclo(entrada))
