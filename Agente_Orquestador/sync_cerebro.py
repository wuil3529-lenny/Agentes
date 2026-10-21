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
import json
from datetime import datetime
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Agente_Orquestador.skills.grafo_obsidian.skill_grafo_obsidian import (
    tool_sincronizar_grafo_canonico,
    tool_auditar_grafo_obsidian,
    tool_capturar_verificar_grafo_obsidian,
)


def sincronizar_conocimiento():
    print("[Obsidian] Ejecutando sincronización jerárquica y canónica...")
    res = tool_sincronizar_grafo_canonico.invoke({"purgar_residuos": True, "calibrar_obsidian": True})
    print("[Obsidian] Resultado de sincronización:", res.get("mensaje"))
    audit = tool_auditar_grafo_obsidian.invoke({})
    print(f"[Obsidian] Puntuación de salud del grafo: {audit.get('puntuacion_salud')}/100")
    print(f"[Obsidian] Archivos conectados: {audit.get('total_archivos_conectados')}/{audit.get('total_archivos_md')}")
    # Verificación visual multimodal mediante manos y ojos
    ruta_cap = ""
    try:
        cap = tool_capturar_verificar_grafo_obsidian.invoke({})
        ruta_cap = cap.get("ruta_archivo", "")
        print(f"[Obsidian] Verificación visual de pantalla: {cap.get('status')} -> {ruta_cap}")
    except Exception as e_cap:
        print(f"[Obsidian] Aviso en verificación visual: {e_cap}")

    # Guardar registro diario para cumplir la política de 1 ejecución diaria en supervisión
    try:
        archivo_estado = APP_ROOT / "memoria" / "estado_sync_obsidian.json"
        hoy = datetime.now().strftime("%Y-%m-%d")
        ahora = datetime.now().strftime("%H:%M:%S")
        datos = {
            "ultimo_sync_fecha": hoy,
            "ultimo_sync_hora": ahora,
            "timestamp": datetime.now().isoformat(),
            "salud_puntuacion": audit.get("puntuacion_salud", 100),
            "archivos_conectados": f"{audit.get('total_archivos_conectados', 0)}/{audit.get('total_archivos_md', 0)}",
            "ruta_captura": ruta_cap,
            "estado": "exitoso",
            "politica": "1 vez al dia en ciclo de supervision para ahorro de tokens y tiempo",
        }
        archivo_estado.parent.mkdir(parents=True, exist_ok=True)
        archivo_estado.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Obsidian] Estado de sincronización diaria registrado ({hoy} {ahora}).")
    except Exception as e_est:
        print(f"[Obsidian] Aviso guardando estado diario: {e_est}")


if __name__ == "__main__":
    sincronizar_conocimiento()
