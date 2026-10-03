"""
skill_limpiar_pizarra.py — Limpieza y Archivado de la Pizarra (SSOT)
===================================================================
Habilidad del Agente Orquestador para extraer tickets completados, cerrados o
abortados de Bitacora.md, archivarlos en el histórico memoria/Tickets_Archivados.md
y registrar la solución en la memoria vectorial (ChromaDB).
"""

import re
import sys
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool


def _obtener_raiz_proyecto() -> Path:
    """Encuentra la raíz del proyecto tanto en entorno local como en contenedor Docker."""
    actual = Path(__file__).resolve()
    for parent in actual.parents:
        if (parent / "Bitacora.md").exists() or (parent / "Agente_Orquestador").exists():
            return parent
    if Path("/app/Bitacora.md").exists():
        return Path("/app")
    return actual.parents[2]


def obtener_prompt_limpiar_pizarra() -> str:
    """
    System Prompt especializado y encapsulado para el modo de limpieza
    y mantenimiento de la pizarra.
    """
    return """[🛑 HARD-STOP: MODO LIMPIEZA Y ARCHIVO DE PIZARRA ACTIVO 🛑]
Eres el Administrador de Higiene y Archivado Operativo del Agente Orquestador.
Tu misión es mantener la `Bitacora.md` libre de ruido y saturación, transfiriendo tickets finalizados al histórico permanente y preservando el conocimiento en la memoria vectorial.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. SOLO ESTADOS TERMINALES:
   - Únicamente tienes autorización para limpiar y archivar tickets con estado `COMPLETADO`, `CERRADO` o `ABORTADO`.
   - Queda terminantemente prohibido archivar tickets en estado `PENDIENTE`, `EN_PROGRESO` o `REVISION`.
2. VERIFICACIÓN DE EVIDENCIA:
   - Antes de limpiar un ticket `COMPLETADO`, asegúrate de que el Supervisor haya verificado la existencia física del entregable.
3. CONSERVACIÓN DEL HISTORIAL (ZERO LOSS):
   - Todo ticket retirado de la pizarra debe guardarse íntegramente en `memoria/Tickets_Archivados.md` y registrarse en la memoria vectorial como solución previa aprendida.
"""


@tool
def tool_limpiar_pizarra(id_ticket: str) -> str:
    """
    Extrae un ticket finalizado de la Bitacora.md, lo archiva en memoria/Tickets_Archivados.md
    y vectoriza la solución en ChromaDB.
    Solo se permite archivar tickets con estado COMPLETADO, CERRADO o ABORTADO.

    Args:
        id_ticket: Identificador del ticket (ej: 'TKT-DES-001' o 'TKT-SEC-015').
    """
    print(f"\n[Agente Orquestador] Ejecutando: tool_limpiar_pizarra(id_ticket='{id_ticket}')...")

    raiz = _obtener_raiz_proyecto()
    ruta_bitacora = raiz / "Bitacora.md"

    if not ruta_bitacora.exists():
        return "Error: Bitacora.md no existe en la raíz del proyecto."

    id_limpio = id_ticket.strip().replace("##", "").strip()

    try:
        texto = ruta_bitacora.read_text(encoding="utf-8")

        bloques = re.split(r"(?m)^##\s+", texto)
        if len(bloques) <= 1:
            return "No se encontraron tickets en la pizarra."

        header = bloques[0]
        tickets = bloques[1:]

        nuevos_tickets = []
        encontrado = False
        ticket_borrado_contenido = ""
        estado_ticket = "DESCONOCIDO"

        for bloque in tickets:
            lineas_bloque = bloque.splitlines()
            primera_linea = lineas_bloque[0].strip() if lineas_bloque else ""

            # Coincidencia con el ID del ticket
            if primera_linea.startswith(id_limpio) or f" {id_limpio}" in primera_linea:
                encontrado = True
                ticket_borrado_contenido = "## " + bloque

                # Extraer estado del ticket
                m_estado = re.search(r"\n(?:-?\s*\*\*|###\s*)Estado[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
                if m_estado:
                    estado_ticket = m_estado.group(1).split("\n")[0].strip().upper()
            else:
                nuevos_tickets.append("## " + bloque)

        if not encontrado:
            return f"No se encontró el ticket {id_limpio} en la pizarra."

        # Hard-Stop de Seguridad: Solo archivar estados terminales
        estados_terminales_permitidos = {"COMPLETADO", "CERRADO", "ABORTADO"}
        if estado_ticket not in estados_terminales_permitidos:
            return (
                f"RECHAZADO: El ticket {id_limpio} se encuentra en estado '{estado_ticket}'. "
                f"Solo está permitido limpiar y archivar tickets con estado: {', '.join(sorted(estados_terminales_permitidos))}."
            )

        # 1. Actualizar pizarra (Bitacora.md)
        nuevo_texto = header + "".join(nuevos_tickets)
        nuevo_texto = re.sub(r'\n{3,}', '\n\n', nuevo_texto)
        ruta_bitacora.write_text(nuevo_texto, encoding="utf-8")

        # 2. Archivar en memoria/Tickets_Archivados.md
        ruta_archivados = raiz / "memoria" / "Tickets_Archivados.md"
        ruta_archivados.parent.mkdir(parents=True, exist_ok=True)

        contenido_sin_links = re.sub(r'\[\[(.*?)\]\]', r'[\1]', ticket_borrado_contenido)
        with open(ruta_archivados, "a", encoding="utf-8") as f:
            f.write("\n\n" + contenido_sin_links.strip())

        # 3. Vectorizar solución en ChromaDB
        rag_msg = ""
        try:
            skills_dir = raiz / "Agente_Orquestador" / "skills"
            if str(skills_dir) not in sys.path:
                sys.path.insert(0, str(skills_dir))

            from memoria_vectorial.skill_memoria_vectorial import tool_guardar_solucion

            desc = f"Ticket archivado: {id_limpio}"
            m_desc = re.search(r'\*\*(?:Objetivo|Tarea):\*\*\s*(.+)', ticket_borrado_contenido)
            if m_desc:
                desc = m_desc.group(1).strip()

            # Extraer evidencia física
            m_ev = re.search(r'(?i)-\s*\*\*Evidencia_Fisica:\*\*\s*([^\n]+)', ticket_borrado_contenido)
            ev_val = re.sub(r'\s*\([^)]*\)', '', m_ev.group(1)).strip('`"\' ') if m_ev else "N/A"

            tool_guardar_solucion.invoke({
                "ticket_id": id_limpio,
                "descripcion": desc,
                "contenido": ticket_borrado_contenido,
                "evidencia_fisica": ev_val
            })
            rag_msg = " e indexado exitosamente en ChromaDB (RAG)"
        except Exception as e_rag:
            rag_msg = f" (aviso: indexación en ChromaDB omitida: {e_rag})"

        return f"Ticket {id_limpio} [Estado: {estado_ticket}] eliminado de la pizarra, archivado en memoria/Tickets_Archivados.md{rag_msg}."

    except Exception as e:
        return f"Error al limpiar la pizarra: {str(e)}"


if __name__ == "__main__":
    print(tool_limpiar_pizarra.invoke({"id_ticket": "TKT-TEST-999"}))
