"""
Perfil_Subagente_Desarrollo.py — Interfaz de Ejecución Canónica para Subagente de Desarrollo
=============================================================================================
Exporta e inicializa la funcionalidad completa de Subagente_Desarrollo,
permitiendo la ejecución de ciclos de trabajo, tool calls y función de nodo LangGraph.
"""

from Subagente_Desarrollo.subagente_desarrollo_agent import (
    funcion_nodo_subagente_desarrollo,
    funcion_nodo_zoro,
    ejecutar_ciclo,
    construir_system_prompt,
    cargar_prompt_desarrollo,
    HERRAMIENTAS_AGENTE,
    HERRAMIENTAS_DESARROLLO,
    NOMBRE_AGENTE,
    NOMBRE_AGENTE_ALIAS,
    ARCHIVOS_TEMPORALES_PATH,
    ARCHIVOS_TEMPORALES_DOCKER,
    PROYECTOS_PATH
)

# Compatibilidad de nodo
funcion_nodo_perfil_subagente_desarrollo = funcion_nodo_subagente_desarrollo

__all__ = [
    "funcion_nodo_subagente_desarrollo",
    "funcion_nodo_perfil_subagente_desarrollo",
    "funcion_nodo_zoro",
    "ejecutar_ciclo",
    "construir_system_prompt",
    "cargar_prompt_desarrollo",
    "HERRAMIENTAS_AGENTE",
    "HERRAMIENTAS_DESARROLLO",
    "NOMBRE_AGENTE",
    "NOMBRE_AGENTE_ALIAS",
    "ARCHIVOS_TEMPORALES_PATH",
    "ARCHIVOS_TEMPORALES_DOCKER",
    "PROYECTOS_PATH"
]

if __name__ == "__main__":
    import sys
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cuáles son tus habilidades operativas actuales?"
    print(ejecutar_ciclo(entrada))
