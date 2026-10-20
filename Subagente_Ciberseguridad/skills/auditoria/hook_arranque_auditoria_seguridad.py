#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hook_arranque_auditoria_seguridad.py
====================================
Hook de arranque de flota para Auditoría de Seguridad Preventiva (Robin / Subagente_Ciberseguridad).

Objetivo:
  Garantizar que CADA VEZ que se encienda o reinicie el ecosistema (contenedor Docker),
  se despache una auditoría de seguridad preventiva (SAST, detección de secretos expuestos,
  validación de blindaje en .gitignore y permisos de entorno) a cargo de Robin (Subagente_Ciberseguridad).

Acciones (idempotentes y tolerantes a fallos):
  1. Verificar si ya existe un ticket activo de seguridad en Bitacora.md para evitar duplicaciones.
  2. Inyectar el ticket formal TKT-SEC-BOOT-[timestamp] en Bitacora.md con Estado: PENDIENTE.
  3. Actualizar la fila REC-SEC-001 en el Registro de Tareas Programadas de Bitacora.md.

Garantías:
  - Nunca lanza excepción hacia el shell (siempre exit 0).
  - Idempotente: si ya hay un ticket de seguridad pendiente o en progreso, no inyecta otro.
  - El listener del Orquestador (Luffy) detecta el ticket e invoca a Robin en modo efímero (Spawn).
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Rutas canónicas ──────────────────────────────────────────────────────────
APP_ROOT = Path("/app")
if not APP_ROOT.exists():
    APP_ROOT = Path(__file__).resolve().parents[3]

BITACORA_FILE = APP_ROOT / "Bitacora.md"
LOG_FILE = APP_ROOT / "logs" / "hook_arranque_seguridad.log"
REPORTES_DIR = APP_ROOT / "Subagente_Ciberseguridad" / "reportes"
TAREA_ID = "REC-SEC-001"
RESPONSABLE = "Subagente_Ciberseguridad"


def _log(msg: str) -> None:
    """Registra en stdout y en el archivo de log dedicado."""
    linea = f"[hook-seguridad] {msg}"
    print(linea, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat()[:19]} {linea}\n")
    except Exception:
        pass


def verificar_ticket_seguridad_activo(texto_bitacora: str) -> bool:
    """Verifica si ya existe un ticket de seguridad pendiente o en progreso en Bitacora.md."""
    patron = r"##\s+TKT-SEC-[\w\-]+[\s\S]*?-\s*\*\*Estado:\*\*\s*(PENDIENTE|EN_PROGRESO|ESPERANDO_CORRECCION|PENDIENTE_REVISION)"
    return bool(re.search(patron, texto_bitacora, flags=re.IGNORECASE))


def actualizar_tabla_bitacora(ahora_str: str) -> None:
    """Actualiza la fecha de última ejecución en la tabla de tareas de Bitacora.md."""
    if not BITACORA_FILE.exists():
        return
    try:
        contenido = BITACORA_FILE.read_text(encoding="utf-8")
        if TAREA_ID not in contenido:
            return

        lineas = contenido.splitlines()
        nuevas_lineas = []
        modificado = False

        for linea in lineas:
            if f"`{TAREA_ID}`" in linea and linea.strip().startswith("|"):
                partes = [p.strip() for p in linea.strip().split("|")[1:-1]]
                if len(partes) >= 7:
                    partes[5] = "`ACTIVA`"
                    partes[6] = ahora_str
                    linea = f"| {' | '.join(partes)} |"
                    modificado = True
            nuevas_lineas.append(linea)

        if modificado:
            BITACORA_FILE.write_text("\n".join(nuevas_lineas) + "\n", encoding="utf-8")
            _log(f"Tabla de tareas en Bitacora.md actualizada para {TAREA_ID}.")
    except Exception as e:
        _log(f"ADVERTENCIA actualizando tabla de Bitacora: {e}")


def inyectar_ticket_auditoria_seguridad() -> str:
    """Inyecta el ticket formal de auditoría de seguridad en Bitacora.md."""
    ahora = datetime.now()
    fecha_str = ahora.strftime("%Y-%m-%d %H:%M")
    tag_tiempo = ahora.strftime("%Y%m%d%H%M%S")
    ticket_id = f"TKT-SEC-BOOT-{tag_tiempo}"
    evidencia_rel = f"Subagente_Ciberseguridad/reportes/auditoria_arranque_{tag_tiempo}.md"

    REPORTES_DIR.mkdir(parents=True, exist_ok=True)

    bloque_ticket = f"""

## {ticket_id}: Auditoría preventiva de seguridad en arranque de flota
- **Tarea:** Ejecutar inspección estática de código (SAST), escaneo de secretos en archivos críticos y .env, verificación de reglas en .gitignore y validación perimetral de seguridad tras el nuevo reinicio del sistema.
- **Responsable:** {RESPONSABLE}
- **Estado:** PENDIENTE
- **Fecha:** {fecha_str}
- **Directrices:** Ejecutar herramientas de SAST (detectar_secretos_expuestos, verificar_gitignore, listar_directorio_auditoria). Generar reporte formal de auditoría en `{evidencia_rel}`. Enmascarar siempre credenciales detectadas y emitir dictamen formal de seguridad (APROBADO / ALERTA / CRÍTICO).
- **Evidencia_Esperada:** {evidencia_rel}
- **Historial:**
  - {fecha_str} - Sistema: Disparo automático por Hook de Arranque tras nuevo reinicio de la flota.
"""

    texto_actual = BITACORA_FILE.read_text(encoding="utf-8") if BITACORA_FILE.exists() else "# 📃 Pizarra (Tablero de Tareas)\n\n"

    # Preservar marcador de conexiones de Obsidian si existe al final
    marca_conexiones = "<!-- CONEXIONES -->"
    if marca_conexiones in texto_actual:
        partes = texto_actual.split(marca_conexiones, 1)
        nuevo_texto = f"{partes[0].rstrip()}{bloque_ticket}\n\n{marca_conexiones}{partes[1]}"
    else:
        nuevo_texto = f"{texto_actual.rstrip()}{bloque_ticket}\n"

    BITACORA_FILE.write_text(nuevo_texto, encoding="utf-8")
    actualizar_tabla_bitacora(fecha_str)
    _log(f"Ticket {ticket_id} inyectado exitosamente en Bitacora.md para {RESPONSABLE}.")
    return ticket_id


def main():
    _log("=== Verificación de Auditoría de Seguridad al arranque de flota ===")
    try:
        if not BITACORA_FILE.exists():
            _log(f"ADVERTENCIA: no existe {BITACORA_FILE}. Se omite inyección.")
            return

        texto_bitacora = BITACORA_FILE.read_text(encoding="utf-8")

        if verificar_ticket_seguridad_activo(texto_bitacora):
            _log("Ya existe un ticket de seguridad ACTIVO (PENDIENTE/EN_PROGRESO) en Bitacora.md. Se omite duplicación.")
            return

        ticket_id = inyectar_ticket_auditoria_seguridad()
        _log(f"Auditoría preventiva programada con éxito: {ticket_id}")

    except Exception as e:
        _log(f"ADVERTENCIA inesperada en hook de seguridad ({e}). El arranque continúa normalmente.")


if __name__ == "__main__":
    main()
