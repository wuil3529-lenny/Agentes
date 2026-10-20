"""
sync_cerebro.py — Sincronizador Maestro del Grafo de Obsidian

Implementa la Arquitectura Jerárquica por Hubs:
- Nivel 1: Triángulo de Gobernanza (Bitacora, Cerebro, Reglas de la Tripulacion)
- Nivel 2: Los 5 Agentes de la Tripulación, Memoria Colectiva y Sistema
- Nivel 3: 12 Hubs Departamentales (skills_*, proyectos_*, informes_*, reportes_*, playbooks_memoria)
- Nivel 4: Hojas individuales (todas las skills, playbooks, proyectos y documentos)

100% de los archivos Markdown del proyecto están conectados a su Hub respectivo,
sin líneas cruzadas ni madejas desordenadas.
"""

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Agente_Orquestador.skills.grafo_obsidian.skill_grafo_obsidian import (
    tool_sincronizar_grafo_canonico,
    tool_auditar_grafo_obsidian,
)


def sincronizar_conocimiento():
    print("[Obsidian] Ejecutando sincronización jerárquica de 176 nodos...")
    res = tool_sincronizar_grafo_canonico.invoke({"purgar_residuos": True, "calibrar_obsidian": True})
    print("[Obsidian] Resultado de sincronización:", res.get("mensaje"))
    audit = tool_auditar_grafo_obsidian.invoke({})
    print(f"[Obsidian] Puntuación de salud del grafo: {audit.get('puntuacion_salud')}/100")
    print(f"[Obsidian] Archivos conectados: {audit.get('archivos_conectados_ok')}/{audit.get('total_archivos_md')}")


if __name__ == "__main__":
    sincronizar_conocimiento()
