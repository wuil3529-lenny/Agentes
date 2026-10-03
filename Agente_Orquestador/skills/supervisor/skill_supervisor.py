"""
skill_supervisor.py — Auditoría de Consistencia y Supervisión de la Pizarra (SSOT)
==================================================================================
Habilidad del Agente Orquestador para supervisar la integridad de Bitacora.md,
verificar la existencia física de evidencias de tareas terminadas y mantener
la verdad única del sistema libre de tickets huérfanos o inconsistentes.
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool


def _obtener_raiz_proyecto() -> Path:
    """Encuentra la raíz del proyecto tanto en entorno local como en contenedor."""
    actual = Path(__file__).resolve()
    for parent in actual.parents:
        if (parent / "Bitacora.md").exists() or (parent / "Agente_Orquestador").exists():
            return parent
    if Path("/app/Bitacora.md").exists():
        return Path("/app")
    return actual.parents[2]


def _resolver_ruta_evidencia(ruta_evidencia: str, raiz: Path) -> Path:
    """
    Resuelve la ruta de evidencia física de manera elástica,
    soportando tanto rutas absolutas dentro de Docker (/app/...) como rutas del host.
    """
    ruta_limpia = ruta_evidencia.strip().strip('`"\' ')
    p = Path(ruta_limpia)

    # Si existe directamente (ej. ruta local o dentro de Docker)
    if p.exists():
        return p

    # Si empieza con /app/ pero estamos en el host (Windows/Linux)
    if ruta_limpia.startswith("/app/"):
        relativa = ruta_limpia[5:]  # remover "/app/"
        p_host = raiz / relativa
        if p_host.exists():
            return p_host
        return p_host

    # Si es ruta relativa a la raíz
    p_rel = raiz / ruta_limpia
    return p_rel


def obtener_prompt_supervisor() -> str:
    """
    System Prompt especializado y encapsulado para el modo de supervisión
    y auditoría del SSOT (Pizarra / Bitácora).
    """
    return """[🛑 HARD-STOP: MODO SUPERVISIÓN Y AUDITORÍA DE CONSISTENCIA SSOT ACTIVO 🛑]
Eres el Supervisor de Integridad y Consistencia Operativa del Agente Orquestador.
Tu misión inquebrantable es auditar que la `Bitacora.md` represente la única y verdadera realidad (Single Source of Truth) del sistema multi-agente.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. LA PIZARRA ES EL ÚNICO SSOT:
   - La `Bitacora.md` es la única fuente de la verdad de las tareas en curso.
   - Ninguna tarea se considera finalizada verbalmente ni por mención; sólo existe lo registrado formalmente en la pizarra.
2. REGLA ESTRICTA DE EVIDENCIA FÍSICA (ZERO TRUST):
   - Todo ticket en estado `COMPLETADO` o `REVISION` DEBE contar obligatoriamente con el campo `- **Evidencia_Fisica:** <ruta>`.
   - Dicho archivo debe existir físicamente en el disco y tener contenido verificable.
   - Si la evidencia física no existe en el sistema de archivos, el ticket está INCONSISTENTE y debe ser rechazado inmediatamente.
3. CENTRALIZACIÓN DE DELEGACIÓN:
   - Los subagentes tienen prohibido delegarse tareas entre sí o crear tickets arbitrarios.
   - La delegación es responsabilidad exclusiva del Agente Orquestador (y del Agente de Ciberseguridad para reportes de seguridad).
4. HIGIENE Y TRANSICIÓN DE ESTADOS:
   - Audita que los estados sean estrictamente: PENDIENTE, EN_PROGRESO, REVISION, PENDIENTE_REVISION, COMPLETADO, CERRADO, ABORTADO.
   - No toleres tickets huérfanos, sin responsable o con estados contradictorios.
"""


def auditar_tickets_pizarra() -> Dict[str, Any]:
    """
    Analiza la Bitacora.md para auditar el estado y consistencia de todos los tickets.
    Verifica la existencia física de las evidencias reportadas.
    """
    raiz = _obtener_raiz_proyecto()
    bitacora_path = raiz / "Bitacora.md"

    resultado: Dict[str, Any] = {
        "existe_bitacora": False,
        "total_tickets": 0,
        "tickets_abiertos": [],
        "tickets_completados": [],
        "inconsistencias": [],
        "listos_para_archivar": []
    }

    if not bitacora_path.exists():
        resultado["inconsistencias"].append("El archivo Bitacora.md no existe en la raíz del proyecto.")
        return resultado

    resultado["existe_bitacora"] = True

    try:
        texto = bitacora_path.read_text(encoding="utf-8")
        bloques = re.split(r"(?=##\s+TKT-[A-Z0-9\-]+(?:[^\n]*)\n)", texto)

        estados_validos = {
            "PENDIENTE", "EN_PROGRESO", "REVISION", "PENDIENTE_REVISION",
            "COMPLETADO", "CERRADO", "ABORTADO"
        }

        for bloque in bloques:
            bloque = bloque.strip()
            if not bloque.startswith("## TKT-"):
                continue

            resultado["total_tickets"] += 1

            m_id = re.search(r"##\s+(TKT-[A-Z0-9\-]+)", bloque)
            m_tarea = re.search(r"\n(?:-?\s*\*\*|###\s*)(?:Tarea|Objetivo)[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            m_resp = re.search(r"\n(?:-?\s*\*\*|###\s*)Responsable[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            m_estado = re.search(r"\n(?:-?\s*\*\*|###\s*)Estado[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            m_evidencia = re.search(r"\n(?:-?\s*\*\*|###\s*)Evidencia_Fisica[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)

            t_id = m_id.group(1).strip() if m_id else "ID_DESCONOCIDO"
            tarea = m_tarea.group(1).strip() if m_tarea else "N/A"
            resp = m_resp.group(1).strip() if m_resp else "DESCONOCIDO"
            estado_raw = m_estado.group(1).split("\n")[0].strip() if m_estado else "DESCONOCIDO"
            estado = estado_raw.upper()
            evidencia = m_evidencia.group(1).split("\n")[0].strip() if m_evidencia else ""

            info_ticket = {
                "id": t_id,
                "tarea": tarea,
                "responsable": resp,
                "estado": estado,
                "evidencia": evidencia
            }

            # Validar estado
            if estado not in estados_validos:
                resultado["inconsistencias"].append(
                    f"Ticket {t_id}: Estado '{estado_raw}' no es un estado válido del sistema."
                )

            # Validar Responsable
            if resp == "DESCONOCIDO":
                resultado["inconsistencias"].append(
                    f"Ticket {t_id}: No tiene un Responsable formalmente asignado."
                )

            # Validar tickets que reclaman estar COMPLETADOS o en REVISION
            if estado in ["COMPLETADO", "REVISION", "PENDIENTE_REVISION"]:
                if not evidencia or evidencia.upper() in ["N/A", "NONE", "NULL"]:
                    resultado["inconsistencias"].append(
                        f"Ticket {t_id}: Marcado como '{estado}' pero carece del campo 'Evidencia_Fisica'."
                    )
                else:
                    ruta_ev = _resolver_ruta_evidencia(evidencia, raiz)
                    if not ruta_ev.exists():
                        resultado["inconsistencias"].append(
                            f"Ticket {t_id}: Evidencia física reportada '{evidencia}' NO existe físicamente en el disco."
                        )
                    else:
                        info_ticket["evidencia_verificada"] = True

                resultado["tickets_completados"].append(info_ticket)

                if estado == "COMPLETADO" and info_ticket.get("evidencia_verificada"):
                    resultado["listos_para_archivar"].append(t_id)

            elif estado in ["CERRADO", "ABORTADO"]:
                resultado["listos_para_archivar"].append(t_id)

            else:
                resultado["tickets_abiertos"].append(info_ticket)

        return resultado

    except Exception as e:
        resultado["inconsistencias"].append(f"Error procesando Bitacora.md: {str(e)}")
        return resultado


def sincronizar_grafo_obsidian() -> str:
    """
    Ejecuta el script oficial de sincronización del cerebro (sync_cerebro.py)
    para actualizar el grafo de conocimiento en Obsidian y ChromaDB.
    """
    raiz = _obtener_raiz_proyecto()
    script_sync = raiz / "Agente_Orquestador" / "sync_cerebro.py"

    if not script_sync.exists():
        return f"Error: No se encontró el script de sincronización en {script_sync}"

    try:
        res = subprocess.run(
            [sys.executable, str(script_sync)],
            capture_output=True,
            text=True,
            check=True
        )
        salida_resumida = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        return f"Sincronización de Cerebro completada con éxito. ({len(salida_resumida)} registros procesados)."
    except subprocess.CalledProcessError as e:
        return f"Fallo al ejecutar sync_cerebro.py: {e.stderr or e.stdout}"
    except Exception as e:
        return f"Error ejecutando sincronización: {str(e)}"


@tool
def tool_auditar_ssot(sincronizar_cerebro: bool = False) -> str:
    """
    Audita y supervisa la coherencia de la Pizarra oficial (Bitacora.md) como SSOT único.
    Verifica que cada ticket tenga un responsable válido, estados correctos y que
    la evidencia física de las tareas completadas exista realmente en el sistema de archivos.

    Args:
        sincronizar_cerebro: Si es True, ejecuta también la actualización del grafo de Obsidian y ChromaDB.
    """
    print(f"\n[Agente Orquestador] Ejecutando: tool_auditar_ssot(sincronizar_cerebro={sincronizar_cerebro})...")

    audit = auditar_tickets_pizarra()
    lineas = ["[SUPERVISIÓN DE PIZARRA Y AUDITORÍA SSOT]"]

    if not audit["existe_bitacora"]:
        return "ERROR CRÍTICO: Bitacora.md no existe en la raíz del proyecto."

    lineas.append(f"Total de tickets en tablero: {audit['total_tickets']}")
    lineas.append(f"Tickets abiertos / en progreso: {len(audit['tickets_abiertos'])}")
    lineas.append(f"Tickets completados / en revisión: {len(audit['tickets_completados'])}")

    if audit["tickets_abiertos"]:
        lineas.append("\n[TICKETS ACTIVOS]:")
        for t in audit["tickets_abiertos"]:
            lineas.append(f"  - [{t['id']}] Resp: {t['responsable']} | Estado: {t['estado']} | Tarea: {t['tarea'][:80]}")

    if audit["listos_para_archivar"]:
        lineas.append(f"\n[LISTOS PARA ARCHIVAR] ({len(audit['listos_para_archivar'])}):")
        for tid in audit["listos_para_archivar"]:
            lineas.append(f"  - {tid} (listo para `tool_limpiar_pizarra`)")

    if audit["inconsistencias"]:
        lineas.append("\n[INCONSISTENCIAS Y VIOLACIONES DE SSOT DETECTADAS]:")
        for inc in audit["inconsistencias"]:
            lineas.append(f"  - [FALLO] {inc}")
    else:
        lineas.append("\n[SSOT CONSISTENTE] No se detectaron inconsistencias ni anomalías en la pizarra.")

    if sincronizar_cerebro:
        lineas.append("\n[SINCRONIZACIÓN DE CEREBRO]:")
        res_sync = sincronizar_grafo_obsidian()
        lineas.append(f"  {res_sync}")

    return "\n".join(lineas)


def ejecutar_supervision(*args, **kwargs) -> str:
    """
    Función de compatibilidad para el daemon de escucha (base_listener.py).
    Ejecuta la auditoría y supervisión de consistencia del SSOT en la pizarra.
    """
    return tool_auditar_ssot.invoke({"sincronizar_cerebro": False}) if hasattr(tool_auditar_ssot, "invoke") else tool_auditar_ssot(sincronizar_cerebro=False)


if __name__ == "__main__":
    print(tool_auditar_ssot(sincronizar_cerebro=False))
