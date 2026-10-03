"""
luffy_agent.py — Shim de compatibilidad canónica (Alias de Luffy / Agente_Orquestador)
=====================================================================================
Este módulo existe para preservar la compatibilidad de importación histórica de la
flota. Múltiples subagentes (Zoro, Sanji, Robin, Nami) importan `crear_llm` desde
`luffy_agent`, pero la implementación canónica reside en `agente_orquestador_agent.py`.

En lugar de duplicar la lógica (violando DRY) o reescribir cada subagente, este shim
re-exporta la fábrica de LLM canónica. Así, `from luffy_agent import crear_llm`
sigue funcionando de forma transparente.

NOTA: El Agente Orquestador es la entidad formal; "Luffy" es su identidad asignada
por el usuario. Este alias refleja esa dualidad de identidad.
"""

from agente_orquestador_agent import crear_llm

__all__ = ["crear_llm"]
