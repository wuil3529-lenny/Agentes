"""
skill_solicitar_soporte_pizarra.py — Habilidad: Solicitud de Soporte, Pausa y Delegación en Pizarra
===================================================================================================
Permite al Subagente de Asistencia pausar su ejecución y generar un ticket formal en la Pizarra
(Bitacora.md) asignado al Agente_Orquestador cuando necesite:
  1. Un insumo o entregable de OTRO SUBAGENTE (Desarrollo, Diseño, Ciberseguridad).
  2. Asistencia o desbloqueo estratégico del AGENTE_ORQUESTADOR.
  3. Intervención o información directa del USUARIO (re-autenticación OAuth, confirmación, decisiones).

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
_AGENTE_ORIGEN = _CURRENT.parents[1].name  # Auto-detecta ej. Subagente_Asistencia
_BITACORA_PATH = _APP_ROOT / "Bitacora.md"

# Importar helper de mensajería interna si está disponible
try:
    if str(_APP_ROOT / "Agente_Orquestador") not in sys.path:
        sys.path.insert(0, str(_APP_ROOT / "Agente_Orquestador"))
    from memory import publicar_mensaje
except Exception:
    def publicar_mensaje(*args, **kwargs): return ""


def obtener_prompt_solicitar_soporte_pizarra() -> str:
    """
    System Prompt especializado para el protocolo de Pausa y Solicitud de Soporte en Pizarra.
    """
    return """[🛑 DIRECTIVA OPERATIVA: PAUSA Y SOLICITUD DE SOPORTE EN PIZARRA 🛑]
Eres el operador responsable de tu dominio técnico. Tienes la facultad y la OBLIGACIÓN de pausar tu ejecución y solicitar ayuda en la Pizarra (Bitacora.md) ÚNICAMENTE cuando exista un bloqueo real o una dependencia externa:

1. CUÁNDO USAR ESTA HABILIDAD (SOLO SI ES ESTRICTAMENTE NECESARIO):
   - Si necesitas un entregable o insumo de OTRO SUBAGENTE (ej: necesitas un script de backend de Subagente_Desarrollo, un diseño de Subagente_Diseno, o una auditoría de Subagente_Ciberseguridad) para poder culminar tu tarea.
   - Si necesitas asistencia o decisiones estratégicas del AGENTE_ORQUESTADOR (ej: ambigüedad en los requerimientos del plan o asignación de tareas).
   - Si necesitas intervención directa del USUARIO (ej: credenciales OAuth expiradas, confirmación de envío de correo masivo o decisión ejecutiva).

2. PROTOCOLO DE PAUSA OPERATIVA:
   - Invoca de inmediato `tool_solicitar_ayuda_pizarra(...)` detallando con precisión quirúrgica:
     * `destinatario_tipo`: 'otro_subagente', 'agente_orquestador', o 'usuario'.
     * `subagente_sugerido`: Nombre del subagente si aplica (ej. 'Subagente_Desarrollo', 'Subagente_Ciberseguridad').
     * `motivo_bloqueo`: Razón exacta por la cual no puedes continuar autónomamente.
     * `tarea_requerida`: Qué acción concreta debe realizar el destinatario.
     * `contexto_actual`: Avance logrado hasta el momento y archivos preliminares generados.
     * `evidencia_previa`: Ruta de archivos creados o 'N/A'.

3. EFECTO INMEDIATO:
   - Se creará un ticket en la Pizarra (Bitacora.md) con Estado 'PENDIENTE' y Responsable 'Agente_Orquestador'.
   - El Agente_Orquestador leerá el ticket, analizará el destinatario y lo delegará al subagente correspondiente, te asistirá directamente o se comunicará con el usuario.
   - QUEDA PROHIBIDO inventar datos, suponer tokens inexistentes o caer en bucles repetitivos cuando falta un insumo externo. Pausa y crea el ticket.
"""


@tool
def tool_solicitar_ayuda_pizarra(
    tarea_requerida: str,
    destinatario_tipo: str,
    subagente_sugerido: str = "",
    motivo_bloqueo: str = "",
    contexto_actual: str = "",
    evidencia_previa: str = "N/A"
) -> str:
    """
    Genera un ticket de solicitud de auxilio o pausa en la Pizarra (Bitacora.md)
    asignado al Agente_Orquestador cuando el subagente requiera la ayuda de otro
    subagente, del propio orquestador o del usuario para culminar su labor.

    Args:
        tarea_requerida: Descripción específica y concreta de la tarea o insumo que se necesita.
        destinatario_tipo: Quién debe intervenir. Valores válidos: 'otro_subagente', 'agente_orquestador', 'usuario'.
        subagente_sugerido: Nombre del subagente sugerido si destinatario_tipo es 'otro_subagente' (ej: 'Subagente_Desarrollo', 'Subagente_Ciberseguridad', 'Subagente_Diseno').
        motivo_bloqueo: Causa o justificación clara de por qué el subagente no puede continuar de forma autónoma.
        contexto_actual: Resumen del estado actual del trabajo, avances realizados y archivos involucrados.
        evidencia_previa: Rutas de archivos preliminares creados en disco hasta el momento, o 'N/A'.
    """
    try:
        # Validación de tipo de destinatario
        dest_norm = destinatario_tipo.strip().lower()
        if dest_norm not in ["otro_subagente", "agente_orquestador", "usuario"]:
            dest_norm = "agente_orquestador"

        # Generar identificador canónico de ticket
        timestamp_id = datetime.now().strftime("%Y%m%d%H%M%S")
        timestamp_humano = datetime.now().strftime("%Y-%m-%d %H:%M")
        ticket_id = f"TKT-REQ-{timestamp_id}"

        # Formatear el destinatario descriptivo
        destino_label = dest_norm.replace("_", " ").title()
        if dest_norm == "otro_subagente" and subagente_sugerido:
            destino_label = f"Otro Subagente ({subagente_sugerido})"

        # Bloque Markdown canónico de la Pizarra (Blackboard)
        bloque_ticket = f"""
---

## {ticket_id} — Solicitud de Soporte de {_AGENTE_ORIGEN}

- **Tarea:** [SOLICITUD DE AUXILIO / PAUSA]: {tarea_requerida} (Destinatario Requerido: {destino_label})
- **Contexto:** {contexto_actual if contexto_actual else 'Trabajo en progreso.'} | Motivo del Bloqueo: {motivo_bloqueo if motivo_bloqueo else 'Dependencia externa no resuelta.'}
- **Historial / Intentos Previos:**
  - [{_AGENTE_ORIGEN} - {timestamp_humano}]: PAUSA OPERATIVA. Tarea pausada a la espera de intervención externa. Insumo requerido: {tarea_requerida}.
- **Evidencia_Fisica:** {evidencia_previa if evidencia_previa else 'N/A'}
- **Estado:** PENDIENTE
- **Responsable:** Agente_Orquestador
"""

        # Escritura atómica en Bitacora.md
        if not _BITACORA_PATH.exists():
            _BITACORA_PATH.write_text("# Pizarra (Tablero de Tareas)\n\n", encoding="utf-8")

        with open(_BITACORA_PATH, "a", encoding="utf-8") as f:
            f.write(bloque_ticket)

        # Notificación en cola interna para el Agente_Orquestador
        try:
            publicar_mensaje(
                de=_AGENTE_ORIGEN,
                para="Agente_Orquestador",
                tipo="solicitud_soporte",
                contenido={
                    "ticket_id": ticket_id,
                    "destinatario_tipo": dest_norm,
                    "subagente_sugerido": subagente_sugerido,
                    "tarea_requerida": tarea_requerida,
                    "motivo_bloqueo": motivo_bloqueo
                },
                canal_tipo="interno"
            )
        except Exception:
            pass

        return json.dumps({
            "status": "success",
            "ticket_id": ticket_id,
            "origen": _AGENTE_ORIGEN,
            "destinatario_tipo": dest_norm,
            "subagente_sugerido": subagente_sugerido if subagente_sugerido else "N/A",
            "estado": "PENDIENTE",
            "responsable": "Agente_Orquestador",
            "mensaje": f"Ticket de auxilio/pausa {ticket_id} registrado exitosamente en la Pizarra (Bitacora.md). El Agente_Orquestador ha sido notificado para analizar si delega la tarea a {subagente_sugerido or 'un subagente'}, interviene directamente o consulta al usuario.",
            "evidencia_fisica": "/app/Bitacora.md"
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error al generar ticket de auxilio en la pizarra: {str(e)}"
        }, ensure_ascii=False)


@tool
def tool_consultar_estado_ticket_pizarra(ticket_id: str) -> str:
    """
    Consulta en la Pizarra (Bitacora.md) el estado actual de un ticket de soporte previamente creado,
    para verificar si el Agente_Orquestador, otro subagente o el usuario ya respondieron o lo completaron.

    Args:
        ticket_id: Identificador del ticket (ej: 'TKT-REQ-20261003203000').
    """
    try:
        if not _BITACORA_PATH.exists():
            return json.dumps({
                "status": "error",
                "mensaje": "El archivo Bitacora.md no existe en la raíz del proyecto."
            }, ensure_ascii=False)

        contenido = _BITACORA_PATH.read_text(encoding="utf-8", errors="replace")
        
        # Buscar el bloque del ticket
        patron = rf"##\s+{re.escape(ticket_id)}.*?(?=\n##\s+TKT-|\n---|#\s+Pizarra|$)"
        match = re.search(patron, contenido, re.DOTALL)

        if not match:
            return json.dumps({
                "status": "not_found",
                "ticket_id": ticket_id,
                "mensaje": f"No se encontró el ticket {ticket_id} en Bitacora.md."
            }, ensure_ascii=False)

        bloque = match.group(0).strip()
        
        # Extraer estado y responsable
        m_estado = re.search(r"-\s*\*\*Estado:\*\*\s*([^\n]+)", bloque)
        m_resp = re.search(r"-\s*\*\*Responsable:\*\*\s*([^\n]+)", bloque)
        m_ev = re.search(r"-\s*\*\*Evidencia_Fisica:\*\*\s*([^\n]+)", bloque)

        estado = m_estado.group(1).strip() if m_estado else "DESCONOCIDO"
        responsable = m_resp.group(1).strip() if m_resp else "DESCONOCIDO"
        evidencia = m_ev.group(1).strip() if m_ev else "N/A"

        return json.dumps({
            "status": "success",
            "ticket_id": ticket_id,
            "estado": estado,
            "responsable": responsable,
            "evidencia_fisica": evidencia,
            "contenido_bloque": bloque[:1500]
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error al consultar el ticket {ticket_id}: {str(e)}"
        }, ensure_ascii=False)


HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA = [
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra
]

__all__ = [
    "tool_solicitar_ayuda_pizarra",
    "tool_consultar_estado_ticket_pizarra",
    "obtener_prompt_solicitar_soporte_pizarra",
    "HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA"
]
