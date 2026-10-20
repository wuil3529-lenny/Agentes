"""
skill_solicitar_soporte_pizarra.py — Habilidad: Solicitud de Soporte, Pausa y Delegación en Pizarra
===================================================================================================
Permite al Subagente de Ciberseguridad pausar su ejecución y generar un ticket formal en la Pizarra
(Bitacora.md) asignado al Agente_Orquestador cuando necesite:
  1. Un insumo o entregable de OTRO SUBAGENTE (Desarrollo, Diseño, Asistencia).
  2. Asistencia o desbloqueo estratégico del AGENTE_ORQUESTADOR.
  3. Intervención o información directa del USUARIO (credenciales de producción, confirmación, decisiones).

Directiva de Oro: El subagente solo usa esta herramienta si necesita ayuda real para evitar bucles.
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_AGENTE_ORIGEN = "Subagente_Ciberseguridad"
_BITACORA_PATH = _APP_ROOT / "Bitacora.md"


def obtener_prompt_solicitar_soporte_pizarra() -> str:
    """
    System Prompt especializado para el protocolo de Pausa y Solicitud de Soporte en Pizarra.
    """
    return """[🛑 DIRECTIVA OPERATIVA: PAUSA Y SOLICITUD DE SOPORTE EN PIZARRA 🛑]
Eres el operador responsable de tu dominio técnico. Tienes la facultad y la OBLIGACIÓN de pausar tu ejecución y solicitar ayuda en la Pizarra (Bitacora.md) ÚNICAMENTE cuando exista un bloqueo real o una dependencia externa:

1. CUÁNDO USAR ESTA HABILIDAD (SOLO SI ES ESTRICTAMENTE NECESARIO):
   - Si necesitas un entregable o insumo de OTRO SUBAGENTE (ej: necesitas código o parches de Subagente_Desarrollo, credenciales o accesos ofimáticos de Subagente_Asistencia) para poder culminar tu tarea.
   - Si necesitas asistencia o decisiones estratégicas del AGENTE_ORQUESTADOR (ej: ambigüedad en los límites del escaneo o priorización de riesgos).
   - Si necesitas intervención directa del USUARIO (ej: autorización para escaneo intrusivo, credenciales de producción o decisión de impacto).

2. PROTOCOLO DE PAUSA OPERATIVA:
   - Invoca de inmediato `tool_solicitar_ayuda_pizarra(...)` detallando con precisión quirúrgica:
     * `destinatario_tipo`: 'otro_subagente', 'agente_orquestador', o 'usuario'.
     * `subagente_sugerido`: Nombre del subagente si aplica (ej. 'Subagente_Desarrollo', 'Subagente_Asistencia').
     * `motivo_bloqueo`: Razón exacta por la cual no puedes continuar autónomamente.
     * `tarea_requerida`: Qué acción concreta debe realizar el destinatario.
     * `contexto_actual`: Avance logrado hasta el momento y archivos preliminares generados.
     * `evidencia_previa`: Ruta de archivos creados o 'N/A'.

3. EFECTO INMEDIATO:
   - Se creará un ticket en la Pizarra (Bitacora.md) con Estado 'PENDIENTE' y Responsable 'Agente_Orquestador'.
   - El Agente_Orquestador leerá el ticket, analizará el destinatario y lo delegará al subagente correspondiente, te asistirá directamente o se comunicará con el usuario.
   - QUEDA PROHIBIDO inventar datos, suponer credenciales o caer en bucles repetitivos cuando falta un insumo externo. Pausa y crea el ticket.
"""


@tool
def tool_solicitar_ayuda_pizarra(
    tarea_requerida: str,
    destinatario_tipo: str,
    subagente_sugerido: str = "N/A",
    motivo_bloqueo: str = "",
    contexto_actual: str = "",
    evidencia_previa: str = "N/A"
) -> str:
    """
    Pausa la ejecución del subagente y crea un ticket de auxilio en la Pizarra (Bitacora.md)
    asignado al Agente_Orquestador para resolver un bloqueo.
    """
    print(f"\n[{_AGENTE_ORIGEN}] Solicitando auxilio en Pizarra...")
    try:
        dest_tipo_norm = destinatario_tipo.strip().lower()
        if dest_tipo_norm not in ["otro_subagente", "agente_orquestador", "usuario"]:
            dest_tipo_norm = "agente_orquestador"

        timestamp = datetime.now()
        fecha_str = timestamp.strftime("%Y-%m-%d %H:%M")
        id_sufijo = timestamp.strftime("%Y%m%d%H%M%S")
        ticket_id = f"TKT-HLP-{id_sufijo}"

        if not _BITACORA_PATH.exists():
            _BITACORA_PATH.write_text("# Bitácora de Operaciones\n\n", encoding="utf-8")

        ticket_md = f"\n\n## {ticket_id}: [SOLICITUD DE AYUDA] {tarea_requerida[:80]}\n"
        ticket_md += f"- **Tarea:** {tarea_requerida}\n"
        ticket_md += f"- **Responsable:** Agente_Orquestador\n"
        ticket_md += f"- **Estado:** PENDIENTE\n"
        ticket_md += f"- **Fecha:** {fecha_str}\n"
        ticket_md += f"- **Origen:** {_AGENTE_ORIGEN}\n"
        ticket_md += f"- **Destinatario_Tipo:** {dest_tipo_norm}\n"
        ticket_md += f"- **Subagente_Sugerido:** {subagente_sugerido}\n"
        ticket_md += f"- **Motivo_Bloqueo:** {motivo_bloqueo}\n"
        ticket_md += f"- **Contexto_Actual:** {contexto_actual}\n"
        ticket_md += f"- **Evidencia_Previa:** {evidencia_previa}\n"
        ticket_md += f"- **Historial:**\n"
        ticket_md += f"  - [{_AGENTE_ORIGEN} - {fecha_str}]: Solicitud de soporte creada. Ejecución pausada a la espera de resolución del Orquestador.\n"

        with open(_BITACORA_PATH, "a", encoding="utf-8") as f:
            f.write(ticket_md)

        return json.dumps({
            "status": "success",
            "ticket_creado": ticket_id,
            "asignado_a": "Agente_Orquestador",
            "destinatario_tipo": dest_tipo_norm,
            "subagente_sugerido": subagente_sugerido,
            "mensaje": f"Ticket {ticket_id} registrado en Bitacora.md. Pausa operativa concedida."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_consultar_estado_ticket_pizarra(ticket_id: str) -> str:
    """
    Consulta en Bitacora.md el estado y las novedades de un ticket de ayuda previo.
    """
    try:
        if not _BITACORA_PATH.exists():
            return json.dumps({"status": "error", "mensaje": "Bitacora.md no existe."})

        contenido = _BITACORA_PATH.read_text(encoding="utf-8", errors="replace")
        tkt_clean = ticket_id.replace("##", "").strip()

        if tkt_clean not in contenido:
            return json.dumps({"status": "error", "mensaje": f"Ticket '{ticket_id}' no encontrado en Bitacora.md."})

        bloque = ""
        capturando = False
        for linea in contenido.splitlines():
            if tkt_clean in linea and linea.startswith("##"):
                capturando = True
                bloque += linea + "\n"
                continue
            if capturando:
                if linea.startswith("## ") and tkt_clean not in linea:
                    break
                bloque += linea + "\n"

        return json.dumps({
            "status": "success",
            "ticket_id": tkt_clean,
            "contenido_ticket": bloque.strip()
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_SOPORTE_PIZARRA = [
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra,
]
