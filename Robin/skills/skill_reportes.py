"""
skill_reportes.py — Habilidades de Reporte de Seguridad (Robin)
===============================================================
Herramientas para generar reportes formales de hallazgos de seguridad
y tickets de remediación que Luffy puede delegar a Zoro.

Herramientas disponibles:
  - generar_reporte_vulnerabilidades : Crear un reporte Markdown formal
  - crear_ticket_seguridad           : Crear un ticket de tarea para Zoro
  - leer_ultimo_reporte              : Leer el último reporte generado
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import json
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool


import os
_SKILLS_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
_ROBIN_DIR = _SKILLS_DIR.parent
REPORTES_DIR = _ROBIN_DIR / "reportes"

NIVELES_ORDEN = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3, "OK": 4}


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
    y lo guarda en la carpeta Robin/reportes/.
    El reporte está listo para ser leído por Luffy y presentado al usuario.

    Args:
        titulo: Título del reporte (ej: "Auditoría de Código Zoro - Sprint 1").
        area_auditada: Qué se auditó (ej: "Zoro/skill_web.py", "Nami/Nami_Workflow.json").
        hallazgos_json: JSON string con lista de hallazgos. Cada hallazgo:
                        [{"id": "...", "nivel": "ALTO", "descripcion": "...", "ubicacion": "..."}]
        nivel_global: Nivel de criticidad global: CRÍTICO | ALTO | MEDIO | BAJO | OK
        recomendaciones_json: JSON string con lista de recomendaciones.
                              [{"prioridad": "ALTA", "accion": "...", "responsable": "Zoro"}]
    """
    try:
        REPORTES_DIR.mkdir(parents=True, exist_ok=True)

        hallazgos = json.loads(hallazgos_json) if hallazgos_json else []
        recomendaciones = json.loads(recomendaciones_json) if recomendaciones_json else []

        # Ordenar hallazgos por severidad
        hallazgos_ordenados = sorted(
            hallazgos,
            key=lambda h: NIVELES_ORDEN.get(h.get("nivel", "BAJO"), 3)
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

        # Construir el contenido del reporte
        lineas = [
            f"# 🔐 Reporte de Seguridad — {titulo}",
            "",
            f"**Fecha:** {fecha_str}  ",
            f"**Área auditada:** `{area_auditada}`  ",
            f"**Nivel global:** {emoji_global} **{nivel_global}**  ",
            f"**Generado por:** Robin (Oficial de Ciberseguridad)  ",
            "",
            "---",
            "",
            "## 📋 Resumen Ejecutivo",
            "",
        ]

        # Conteo por nivel
        conteo = {"CRÍTICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0, "OK": 0}
        for h in hallazgos:
            nivel = h.get("nivel", "BAJO").upper()
            if nivel in conteo:
                conteo[nivel] += 1

        lineas += [
            f"| Nivel | Hallazgos |",
            f"|-------|-----------|",
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
            lineas.append("No se encontraron hallazgos. El área auditada está limpia.")
        else:
            for i, hallazgo in enumerate(hallazgos_ordenados, 1):
                nivel_h = hallazgo.get("nivel", "BAJO")
                emoji_h = _nivel_a_emoji(nivel_h)
                lineas += [
                    f"### {emoji_h} [{nivel_h}] Hallazgo #{i}: {hallazgo.get('id', f'H-{i:03}')}",
                    "",
                    f"**Descripción:** {hallazgo.get('descripcion', 'Sin descripción')}  ",
                    f"**Ubicación:** `{hallazgo.get('ubicacion', 'N/A')}`  ",
                ]
                if "detalle" in hallazgo:
                    lineas.append(f"**Detalle:** {hallazgo['detalle']}  ")
                if "evidencia" in hallazgo:
                    lineas += ["", "```", hallazgo["evidencia"][:500], "```"]
                lineas.append("")

        # Sección de recomendaciones
        lineas += [
            "---",
            "",
            "## ✅ Recomendaciones de Remediación",
            "",
        ]

        if not recomendaciones:
            if nivel_global == "OK":
                lineas.append("No se requieren acciones. El sistema está en buen estado de seguridad.")
            else:
                lineas.append("*Pendiente de definir acciones específicas.*")
        else:
            for i, rec in enumerate(recomendaciones, 1):
                prioridad = rec.get("prioridad", "MEDIA")
                responsable = rec.get("responsable", "Zoro")
                lineas += [
                    f"{i}. **[{prioridad}]** {rec.get('accion', '')}  ",
                    f"   *Responsable:* {responsable}  ",
                    "",
                ]

        lineas += [
            "---",
            "",
            "## 📌 Estado del Reporte",
            "",
            "- [ ] Revisado por Luffy",
            "- [ ] Acciones delegadas a Zoro",
            "- [ ] Vulnerabilidades corregidas",
            "- [ ] Reauditoría programada",
            "",
            f"*Reporte generado automáticamente por Robin — {fecha_str}*",
        ]

        contenido_reporte = "\n".join(lineas)
        ruta_reporte.write_text(contenido_reporte, encoding="utf-8")
        
        # Notificar a Luffy en la Pizarra si hay vulnerabilidades
        if nivel_global.upper() != "OK" and hallazgos:
            bitacora_path = _APP_ROOT / "Bitacora.md"
            if bitacora_path.exists():
                ticket_id = f"SEC-REV-{timestamp.strftime('%Y%m%d%H%M%S')}"
                ticket_md = f"\n\n## TKT-{ticket_id}\n"
                ticket_md += f"- **Tarea:** [REVISION_SEGURIDAD] Evaluar reporte de vulnerabilidades {nombre_archivo}\n"
                ticket_md += f"- **Responsable:** Luffy\n"
                ticket_md += f"- **Estado:** PENDIENTE_REVISION\n"
                ticket_md += f"- **Evidencia_Fisica:** {str(ruta_reporte)}\n"
                ticket_md += f"- **Contexto:** Auditoría completada en `{area_auditada}` con nivel {nivel_global}. Revisa el reporte en la carpeta de Robin y delega las correcciones al agente correspondiente (ej. Zoro).\n"
                ticket_md += f"- **Historial:**\n"
                ticket_md += f"  - [Robin - {fecha_str}]: Reporte {nombre_archivo} generado y ticket asignado al Capitán para verificación."
                
                with open(bitacora_path, "a", encoding="utf-8") as f:
                    f.write(ticket_md)

        return json.dumps({
            "status": "success",
            "reporte_guardado": str(ruta_reporte),
            "nombre_archivo": nombre_archivo,
            "nivel_global": nivel_global,
            "total_hallazgos": len(hallazgos),
            "resumen_conteo": conteo,
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
    destinatario: str = "Zoro"
) -> str:
    """
    Crea un ticket formal de seguridad directamente en la Pizarra Central (Bitacora.md)
    para que el orquestador lo delegue al agente responsable (generalmente Zoro).

    Args:
        titulo: Título corto del ticket (ej: "Eliminar token hardcodeado en skill_web.py").
        descripcion: Descripción completa del problema de seguridad.
        nivel: Criticidad: CRÍTICO | ALTO | MEDIO | BAJO
        area: Archivo o componente afectado.
        acciones_requeridas_json: JSON string con lista de acciones a tomar.
                                  ["Mover el token a .env", "Leer con os.getenv()"]
        destinatario: Agente que debe resolver el ticket (default: Zoro).
    """
    try:
        bitacora_path = _APP_ROOT / "Bitacora.md"
        if not bitacora_path.exists():
            return json.dumps({"status": "error", "mensaje": "Bitacora.md no encontrada en la raíz."})

        acciones = json.loads(acciones_requeridas_json) if acciones_requeridas_json else []
        timestamp = datetime.now()
        ticket_id = f"SEC-{timestamp.strftime('%Y%m%d%H%M%S')}"
        
        # Formatear el ticket en Markdown (Estructura de la Pizarra)
        ticket_md = f"\n\n## TKT-{ticket_id}\n"
        ticket_md += f"- **Tarea:** [SEGURIDAD] {titulo}\n"
        ticket_md += f"- **Responsable:** {destinatario}\n"
        ticket_md += f"- **Estado:** PENDIENTE_REVISION\n"
        ticket_md += f"- **Evidencia_Fisica:** {area}\n"
        ticket_md += f"- **Contexto:** {descripcion} | Nivel: {nivel}\n"
        ticket_md += f"- **Acciones Requeridas:**\n"
        for acc in acciones:
            ticket_md += f"  - {acc}\n"
        ticket_md += f"- **Historial:**\n"
        ticket_md += f"  - [Robin - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}]: Ticket de remediación creado por auditoría."

        # Añadir a la bitácora
        with open(bitacora_path, "a", encoding="utf-8") as f:
            f.write(ticket_md)

        return json.dumps({
            "status": "success",
            "ticket_id": f"TKT-{ticket_id}",
            "destinatario": destinatario,
            "mensaje": "Ticket de seguridad añadido exitosamente a la Pizarra (Bitacora.md)."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def leer_ultimo_reporte() -> str:
    """
    Lee el reporte de seguridad más reciente generado por Robin.
    Útil para que Luffy pueda consultar el estado de seguridad sin
    necesidad de lanzar una nueva auditoría.
    """
    try:
        if not REPORTES_DIR.exists():
            return json.dumps({
                "status": "info",
                "mensaje": "No hay reportes generados aún. Lanza una auditoría primero."
            })

        reportes = sorted(REPORTES_DIR.glob("*.md"), reverse=True)
        if not reportes:
            return json.dumps({
                "status": "info",
                "mensaje": "La carpeta de reportes existe pero está vacía."
            })

        ultimo = reportes[0]
        contenido = ultimo.read_text(encoding="utf-8", errors="replace")

        # Listar todos los reportes disponibles
        todos = [
            {"nombre": r.name, "tamaño": r.stat().st_size}
            for r in reportes[:10]
        ]

        return json.dumps({
            "status": "success",
            "reporte_leido": ultimo.name,
            "ruta": str(ultimo),
            "contenido": contenido[:5000],
            "truncado": len(contenido) > 5000,
            "todos_los_reportes": todos
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas exportadas
HERRAMIENTAS_REPORTES = [
    generar_reporte_vulnerabilidades,
    crear_ticket_seguridad,
    leer_ultimo_reporte,
]

