"""
skill_reportes.py — Habilidades de Reportes de Vulnerabilidad y Remediación
===========================================================================
Herramientas para generar reportes formales de hallazgos de seguridad en Markdown
y registrar tickets de remediación atómicos en la Pizarra (Bitacora.md).

Herramientas disponibles:
  - generar_reporte_vulnerabilidades : Crear informe formal en reportes/
  - crear_ticket_seguridad           : Registrar ticket de remediación en Bitacora.md
  - leer_ultimo_reporte              : Consultar el último informe de seguridad emitido
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["robin", "subagente_ciberseguridad"] else _CURRENT.parents[2]
_AGENTE_DIR = _APP_ROOT / "Subagente_Ciberseguridad"
REPORTES_DIR = _AGENTE_DIR / "reportes"
REPORTES_DIR.mkdir(parents=True, exist_ok=True)

NIVELES_ORDEN = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3, "OK": 4}


def obtener_prompt_reportes() -> str:
    """
    Retorna el System Prompt especializado para la generación de reportes de seguridad.
    """
    return """[📋 DIRECTIVA OPERATIVA: MODO REPORTES DE SEGURIDAD Y REMEDIACIÓN]
Eres el Redactor de Inteligencia de Seguridad y Planes de Remediación de la tripulación.
Tu función es estructurar informes ejecutivos de vulnerabilidades y redactar tickets de mitigación accionables para los agentes de la flota.

PAUTAS CRÍTICAS DE REPORTE:
1. EVIDENCIA FÍSICA OBLIGATORIA (ZERO-TRUST):
   - Al concluir cualquier auditoría o escaneo, genera un reporte formal mediante `generar_reporte_vulnerabilidades` en `/app/Subagente_Ciberseguridad/reportes/reporte_XXX.md`.
   - La ruta absoluta a ese archivo DEBE ser tu `evidencia_hallazgo` para el Escudo JSON.
2. CLASIFICACIÓN DE SEVERIDAD RIGUROSA:
   - CRÍTICO: RCE, credenciales de producción o tokens de API en texto claro, bypass de autenticación.
   - ALTO: Webhooks n8n sin auth, librerías con CVEs explotables conocidas, .env expuesto fuera de .gitignore.
   - MEDIO: Permisos de archivo permisivos, puertos no esenciales abiertos, warnings de dependencias secundarias.
   - BAJO / OK: Mejoras de higiene, configuraciones preventivas o ausencia total de hallazgos.
3. REMEDIACIÓN PRECISA Y TICKETS EN PIZARRA:
   - Si detectas vulnerabilidades ALTO o CRÍTICO, crea el ticket de corrección en la Pizarra mediante `crear_ticket_seguridad` asignado al responsable correspondiente (`Subagente_Desarrollo` para código, `Agente_Orquestador` para decisiones estratégicas).
"""


def _nivel_a_emoji(nivel: str) -> str:
    return {
        "CRÍTICO": "🔴",
        "ALTO":    "🟠",
        "MEDIO":   "🟡",
        "BAJO":    "🟢",
        "OK":      "✅"
    }.get(nivel.upper(), "⚪")


# ══════════════════════════════════════════════════════════════════════════════
# Herramientas
# ══════════════════════════════════════════════════════════════════════════════

@tool
def generar_reporte_vulnerabilidades(
    titulo: str,
    area_auditada: str,
    hallazgos_json: str,
    nivel_global: str,
    recomendaciones_json: str = "[]"
) -> str:
    """
    Genera un reporte formal de vulnerabilidades en formato Markdown
    y lo almacena en /app/Subagente_Ciberseguridad/reportes/reporte_XXX.md.
    """
    try:
        REPORTES_DIR.mkdir(parents=True, exist_ok=True)

        hallazgos_raw = json.loads(hallazgos_json) if hallazgos_json else []
        recomendaciones_raw = json.loads(recomendaciones_json) if recomendaciones_json else []

        hallazgos = []
        for h in (hallazgos_raw if isinstance(hallazgos_raw, list) else [hallazgos_raw]):
            if isinstance(h, dict):
                hallazgos.append(h)
            elif isinstance(h, str):
                hallazgos.append({"tipo": "Hallazgo", "descripcion": h, "nivel": "BAJO"})

        recomendaciones = []
        for r in (recomendaciones_raw if isinstance(recomendaciones_raw, list) else [recomendaciones_raw]):
            if isinstance(r, dict):
                recomendaciones.append(r)
            elif isinstance(r, str):
                recomendaciones.append({"accion": r, "prioridad": "MEDIA", "responsable": "Subagente_Desarrollo"})

        hallazgos_ordenados = sorted(
            hallazgos,
            key=lambda h: NIVELES_ORDEN.get(h.get("nivel", "BAJO").upper(), 3)
        )

        timestamp = datetime.now()
        fecha_str = timestamp.strftime("%Y-%m-%d %H:%M")

        numero_reporte = 1
        for f in REPORTES_DIR.glob("reporte_*.md"):
            try:
                num = int(f.stem.split("_")[-1])
                if num >= numero_reporte:
                    numero_reporte = num + 1
            except ValueError:
                pass

        nombre_archivo = f"reporte_{numero_reporte:03d}.md"
        ruta_reporte = REPORTES_DIR / nombre_archivo

        emoji_global = _nivel_a_emoji(nivel_global)

        lineas = [
            f"# 🔐 Reporte de Seguridad — {titulo}",
            "",
            f"**Fecha:** {fecha_str}  ",
            f"**Área auditada:** `{area_auditada}`  ",
            f"**Nivel global:** {emoji_global} **{nivel_global}**  ",
            f"**Responsable:** Subagente_Ciberseguridad (Robin)  ",
            "",
            "---",
            "",
            "## 📋 Resumen Ejecutivo",
            "",
        ]

        conteo = {"CRÍTICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0, "OK": 0}
        for h in hallazgos:
            n = h.get("nivel", "BAJO").upper()
            if n in conteo:
                conteo[n] += 1

        lineas += [
            "| Nivel | Total Hallazgos |",
            "|:---|:---:|",
            f"| 🔴 CRÍTICO | {conteo['CRÍTICO']} |",
            f"| 🟠 ALTO    | {conteo['ALTO']} |",
            f"| 🟡 MEDIO   | {conteo['MEDIO']} |",
            f"| 🟢 BAJO    | {conteo['BAJO']} |",
            f"| ✅ OK      | {conteo['OK']} |",
            "",
            "---",
            "",
            "## 🔎 Hallazgos Detallados",
            "",
        ]

        if not hallazgos_ordenados:
            lineas.append("No se encontraron vulnerabilidades ni secretos. El área auditada se encuentra segura.")
        else:
            for i, hallazgo in enumerate(hallazgos_ordenados, 1):
                nivel_h = hallazgo.get("nivel", "BAJO").upper()
                emoji_h = _nivel_a_emoji(nivel_h)
                lineas += [
                    f"### {emoji_h} [{nivel_h}] Hallazgo #{i}: {hallazgo.get('id', f'SEC-{i:03}')}",
                    "",
                    f"- **Tipo:** {hallazgo.get('tipo', 'Vulnerabilidad')}  ",
                    f"- **Descripción:** {hallazgo.get('descripcion', 'Sin descripción')}  ",
                    f"- **Ubicación:** `{hallazgo.get('ubicacion', hallazgo.get('archivo', 'N/A'))}`  ",
                ]
                if "linea" in hallazgo:
                    lineas.append(f"- **Línea:** {hallazgo['linea']}  ")
                if "extracto" in hallazgo or "evidencia" in hallazgo:
                    ev = hallazgo.get("extracto") or hallazgo.get("evidencia")
                    lineas += ["", "```text", str(ev)[:500], "```"]
                lineas.append("")

        lineas += [
            "---",
            "",
            "## ✅ Recomendaciones y Plan de Remediación",
            "",
        ]

        if not recomendaciones:
            if nivel_global.upper() == "OK":
                lineas.append("No se requieren acciones de remediación inmediatas.")
            else:
                lineas.append("- Revisar las líneas señaladas y aplicar saneamiento según el protocolo.")
        else:
            for i, rec in enumerate(recomendaciones, 1):
                prioridad = rec.get("prioridad", "MEDIA")
                responsable = rec.get("responsable", "Subagente_Desarrollo")
                lineas += [
                    f"{i}. **[{prioridad}]** {rec.get('accion', '')}  ",
                    f"   - *Responsable sugerido:* `{responsable}`  ",
                    "",
                ]

        lineas += [
            "---",
            "",
            f"**Conexiones:** [[reportes/]] [[Perfil_Subagente_Ciberseguridad]]",
            "",
            f"*Reporte compilado automáticamente bajo el estándar Zero-Trust de la tripulación — {fecha_str}*",
        ]

        contenido_reporte = "\n".join(lineas)
        ruta_reporte.write_text(contenido_reporte, encoding="utf-8")

        return json.dumps({
            "status": "success",
            "reporte_guardado": str(ruta_reporte),
            "nombre_archivo": nombre_archivo,
            "nivel_global": nivel_global,
            "total_hallazgos": len(hallazgos),
            "conteo": conteo,
            "preview": contenido_reporte[:800]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def crear_ticket_seguridad(
    titulo: str,
    descripcion: str,
    nivel: str,
    area: str,
    acciones_requeridas_json: str,
    destinatario: str = "Subagente_Desarrollo"
) -> str:
    """
    Crea un ticket formal de remediación directamente en la Bitácora (Bitacora.md)
    para que el Agente Orquestador supervise la delegación técnica al subagente responsable.
    """
    try:
        bitacora_path = _APP_ROOT / "Bitacora.md"
        if not bitacora_path.exists():
            return json.dumps({"status": "error", "mensaje": "Bitacora.md no encontrada en la raíz."})

        acciones = json.loads(acciones_requeridas_json) if acciones_requeridas_json else []
        timestamp = datetime.now()
        ticket_id = f"SEC-{timestamp.strftime('%Y%m%d%H%M%S')}"

        ticket_md = f"\n\n## TKT-{ticket_id}: [REMEDIACIÓN] {titulo}\n"
        ticket_md += f"- **Tarea:** Remediación de seguridad: {titulo}\n"
        ticket_md += f"- **Responsable:** {destinatario}\n"
        ticket_md += f"- **Estado:** PENDIENTE\n"
        ticket_md += f"- **Fecha:** {timestamp.strftime('%Y-%m-%d %H:%M')}\n"
        ticket_md += f"- **Directrices:** Mitigar hallazgo de seguridad en `{area}`. Nivel: {nivel}. Aplicar saneamiento por código.\n"
        ticket_md += f"- **Evidencia_Esperada:** {area}\n"
        ticket_md += f"- **Contexto:** {descripcion}\n"
        if acciones:
            ticket_md += "- **Acciones Requeridas:**\n"
            for acc in acciones:
                ticket_md += f"  - {acc}\n"
        ticket_md += f"- **Historial:**\n"
        ticket_md += f"  - {timestamp.strftime('%Y-%m-%d %H:%M')} - Subagente_Ciberseguridad: Ticket de remediación generado tras auditoría física.\n"

        with open(bitacora_path, "a", encoding="utf-8") as f:
            f.write(ticket_md)

        return json.dumps({
            "status": "success",
            "ticket_id": f"TKT-{ticket_id}",
            "destinatario": destinatario,
            "mensaje": "Ticket de seguridad registrado formalmente en Bitacora.md."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def leer_ultimo_reporte() -> str:
    """
    Recupera el reporte de seguridad más reciente generado en /app/Subagente_Ciberseguridad/reportes/.
    Permite validar hallazgos previos y confirmar reauditorías.
    """
    try:
        if not REPORTES_DIR.exists():
            return json.dumps({"status": "info", "mensaje": "No hay reportes generados aún."})

        reportes = sorted(REPORTES_DIR.glob("reporte_*.md"), reverse=True)
        if not reportes:
            return json.dumps({"status": "info", "mensaje": "La carpeta de reportes está vacía."})

        ultimo = reportes[0]
        contenido = ultimo.read_text(encoding="utf-8", errors="replace")

        return json.dumps({
            "status": "success",
            "reporte_leido": ultimo.name,
            "ruta": str(ultimo),
            "contenido": contenido[:6000],
            "truncado": len(contenido) > 6000,
            "total_reportes": len(reportes)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_REPORTES = [
    generar_reporte_vulnerabilidades,
    crear_ticket_seguridad,
    leer_ultimo_reporte,
]
