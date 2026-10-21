#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hook_arranque_revision_correos.py
=================================
Hook de arranque de flota (TKT-DEV-20261014002).

Objetivo:
  Garantizar que CADA VEZ que se encienda el ecosistema (contenedor Docker),
  se ejecute UNA SOLA VEZ una revision de correos de valor en el buzon
  configurado por entorno (EMAIL_REMITENTE), de forma ZERO-TOKEN (sin polling LLM).

Acciones (idempotentes y tolerantes a fallos):
  1. REANUDAR la tarea REC-VIGILANTED-003 si quedo PAUSADA tras el reinicio.
  2. Ejecutar el sensor Python puro v2.1 (sensor_correo_imap_prioridad_v2.py)
     en modo lectura. Si `disparar == true`, inyectar el ticket en Bitacora.md
     para Subagente_Asistencia con los datos reales del evento.

Garantias:
  - NUNCA lanza excepcion hacia el shell (siempre exit 0). El arranque de la
    flota NO debe colgarse ni abortar si el sensor o IMAP fallan.
  - Idempotente: re-ejecutarlo no duplica tickets ni corrompe el estado.
  - Timeout duro interno para no bloquear el arranque si la red cuelga.

Uso:
  python3 hook_arranque_revision_correos.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Rutas canonicas ──────────────────────────────────────────────────────────
APP_ROOT = Path("/app")
if not APP_ROOT.exists():
    APP_ROOT = Path(__file__).resolve().parents[2]

TAREAS_FILE = APP_ROOT / "Agente_Orquestador" / "data" / "tareas_programadas.json"
SENSOR_V2 = APP_ROOT / "Agente_Orquestador" / "data" / "sensores" / "sensor_correo_imap_prioridad_v2.py"
BITACORA_FILE = APP_ROOT / "Bitacora.md"
LOG_FILE = APP_ROOT / "logs" / "hook_arranque_correos.log"

TAREA_ID = "REC-VIGILANTED-003"
RESPONSABLE = "Subagente_Asistencia"
TIMEOUT_SENSOR = 45  # segundos: no bloquear el arranque si IMAP cuelga
EMAIL_OBJETIVO = os.getenv("EMAIL_REMITENTE", os.getenv("EMAIL_IMAP_USER", "usuario_flota@dominio.com"))


def _log(msg: str) -> None:
    """Log a stdout (capturado por docker logs) y a archivo de log."""
    linea = f"[hook-correos] {msg}"
    print(linea, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat()[:19]} {linea}\n")
    except Exception:
        pass


# ── Paso 1: Reanudar la tarea si esta PAUSADA ────────────────────────────────
def reanudar_tarea_si_pausada() -> bool:
    """
    Lee tareas_programadas.json y, si REC-VIGILANTED-003 esta PAUSADA,
    la marca como ACTIVA y recalcula proxima_verificacion.
    Retorna True si la tarea quedo ACTIVA (ya lo estaba o se reanudo).
    """
    try:
        if not TAREAS_FILE.exists():
            _log(f"ADVERTENCIA: no existe {TAREAS_FILE}. Se omite reanudacion.")
            return False

        data = json.loads(TAREAS_FILE.read_text(encoding="utf-8"))
        tareas = data.get("tareas", [])
        encontrada = False

        for t in tareas:
            if str(t.get("id_tarea", "")).upper() != TAREA_ID.upper():
                continue
            encontrada = True
            estado_previo = str(t.get("estado", "")).upper()

            from datetime import timedelta
            try:
                intervalo = max(10, int(t.get("intervalo_segundos_sensor", 60) or 60))
            except Exception:
                intervalo = 60

            if estado_previo == "PAUSADA":
                t["estado"] = "ACTIVA"
                t["proxima_verificacion"] = (datetime.now() + timedelta(seconds=intervalo)).isoformat()[:19]
                TAREAS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                _log(f"Tarea {TAREA_ID} estaba PAUSADA -> REANUDADA (ACTIVA).")
            else:
                # Asegurar que la próxima verificación no haya quedado varada en fecha lejana
                t["proxima_verificacion"] = datetime.now().isoformat()[:19]
                TAREAS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                _log(f"Tarea {TAREA_ID} activa y sincronizada para monitoreo continuo inmediato.")
            break

        if not encontrada:
            _log(f"ADVERTENCIA: no se encontro la tarea {TAREA_ID} en el registro.")
            return False
        return True

    except Exception as e:
        _log(f"ADVERTENCIA: fallo al reanudar la tarea ({e}). Se continua el arranque.")
        return False


# ── Paso 2: Ejecutar el sensor v2.1 (Zero-Token, Python puro) ────────────────
def ejecutar_sensor_v2() -> dict:
    """
    Ejecuta el sensor v2.1 en modo lectura y parsea su salida JSON.
    Retorna el dict del payload o {} si falla (nunca lanza excepcion).
    """
    if not SENSOR_V2.exists():
        _log(f"ADVERTENCIA: no existe el sensor {SENSOR_V2}. Se omite revision.")
        return {}

    try:
        proc = subprocess.run(
            [sys.executable, str(SENSOR_V2)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SENSOR,
            cwd=str(APP_ROOT),
        )
        salida = (proc.stdout or "").strip()
        if proc.returncode != 0:
            _log(f"ADVERTENCIA: sensor v2.1 retorno codigo {proc.returncode}. "
                 f"stderr={ (proc.stderr or '').strip()[:300] }")
        if not salida:
            _log("ADVERTENCIA: sensor v2.1 no produjo salida. Se asume sin novedades.")
            return {}

        # El sensor imprime una unica linea JSON.
        ultima_linea = salida.splitlines()[-1].strip()
        payload = json.loads(ultima_linea)
        return payload if isinstance(payload, dict) else {}

    except subprocess.TimeoutExpired:
        _log(f"ADVERTENCIA: sensor v2.1 excedio el timeout de {TIMEOUT_SENSOR}s "
             f"(posible red/IMAP lento). Se continua el arranque.")
        return {}
    except json.JSONDecodeError as e:
        _log(f"ADVERTENCIA: salida del sensor no es JSON valido ({e}). Se continua.")
        return {}
    except Exception as e:
        _log(f"ADVERTENCIA: fallo inesperado al ejecutar el sensor ({e}). Se continua.")
        return {}


# ── Paso 3: Inyectar ticket en Bitacora.md si hay correos de valor ───────────
def inyectar_ticket_bitacora(payload: dict) -> str:
    """
    Inyecta un ticket en Bitacora.md para Subagente_Asistencia con los datos
    reales del evento capturado por el sensor. Retorna el ticket_id generado.
    """
    datos = payload.get("datos_evento", {}) or {}
    correos = datos.get("correos", []) or []
    total_importantes = datos.get("total_importantes", len(correos))
    total_silenciados = datos.get("total_silenciados", 0)

    # Resumen compacto de correos para el ticket (sin volcar cuerpos completos).
    resumen_correos = []
    for c in correos[:20]:
        resumen_correos.append(
            f"    - [{c.get('categoria','?')}] {c.get('remitente','?')} — "
            f"{c.get('asunto','(sin asunto)')} (uid={c.get('uid','?')})"
        )
    bloque_correos = "\n".join(resumen_correos) if resumen_correos else "    - (sin detalle)"

    ahora = datetime.now()
    ticket_id = f"TKT-{TAREA_ID}-BOOT-{ahora.strftime('%Y%m%d%H%M%S')}"

    bloque_ticket = (
        f"\n\n## {ticket_id}\n"
        f"- **Tarea:** [REVISION DE CORREOS AL ARRANQUE DE FLOTA] Se detectaron "
        f"{total_importantes} correo(s) NUEVO(S) de VALOR (prioridad ALTA) en el buzon "
        f"{EMAIL_OBJETIVO} durante el arranque del ecosistema. El sensor v2.1 ya filtro "
        f"el ruido ({total_silenciados} silenciados).\n"
        f"  - **Correos_Detectados:**\n{bloque_correos}\n"
        f"  - **Datos_Evento_Capturado_Por_Gatillo:** `{json.dumps(datos, ensure_ascii=False)[:1800]}`\n"
        f"- **Responsable:** {RESPONSABLE}\n"
        f"- **Estado:** PENDIENTE\n"
        f"- **Evidencia_Fisica:** Subagente_Asistencia/informes/reporte_vigilante_de_correos_zero_token_v2_.md\n"
        f"- **Contexto:** Disparo por `hook_arranque_flota` (Zero-Token Trigger, revision unica al encender). "
        f"Notificacion: siempre.\n"
        f"- **Historial:**\n"
        f"  - [Hook_Arranque - {ahora.strftime('%Y-%m-%d %H:%M:%S')}]: Revision de correos al arranque "
        f"ejecutada por el sensor v2.1. Ticket asignado a {RESPONSABLE}.\n"
    )

    try:
        texto_actual = BITACORA_FILE.read_text(encoding="utf-8") if BITACORA_FILE.exists() \
            else "# 📓 Pizarra (Tablero de Tareas)\n\n"
    except Exception:
        texto_actual = "# 📓 Pizarra (Tablero de Tareas)\n\n"

    marca_conexiones = "\n---\n**Conexiones:** [[Cerebro]] [[Reglas de la Tripulacion]]"
    if "**Conexiones:**" in texto_actual:
        texto_sin_pie = re.sub(
            r"\n*---\n\*\*Conexiones:\*\*.*$", "", texto_actual, flags=re.DOTALL
        ).rstrip()
        nuevo_texto = f"{texto_sin_pie}{bloque_ticket}\n{marca_conexiones}\n"
    else:
        nuevo_texto = f"{texto_actual.rstrip()}{bloque_ticket}\n{marca_conexiones}\n"

    BITACORA_FILE.write_text(nuevo_texto, encoding="utf-8")
    return ticket_id


# ── Orquestacion del hook ────────────────────────────────────────────────────
def main() -> int:
    _log("=== Revision de correos al arranque de flota (Zero-Token) ===")

    # Paso 1: reanudar vigilante si quedo pausado.
    reanudar_tarea_si_pausada()

    # Paso 2: ejecutar sensor v2.1 (lectura pura, 0 tokens LLM).
    payload = ejecutar_sensor_v2()

    if not payload:
        _log("Sin payload del sensor (fallo o sin datos). Arranque continua normalmente.")
        return 0

    disparar = bool(payload.get("disparar", False))
    if not disparar:
        if payload.get("error"):
            _log(f"ALERTA: Sensor v2.1 reportó error de conexión/autenticación: {payload.get('error')}")
        else:
            _log("Sensor v2.1: sin correos nuevos de valor. Nada que notificar.")
        return 0

    # Paso 3: hay correos de valor -> inyectar ticket para Asistencia.
    try:
        ticket_id = inyectar_ticket_bitacora(payload)
        _log(f"Correos de valor detectados. Ticket inyectado en Bitacora.md: {ticket_id}")
    except Exception as e:
        _log(f"ADVERTENCIA: fallo al inyectar el ticket en Bitacora.md ({e}). Se continua.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Blindaje final: jamas propagar error al shell de arranque.
        _log(f"ADVERTENCIA CRITICA capturada en el hook ({e}). Arranque continua.")
        sys.exit(0)
