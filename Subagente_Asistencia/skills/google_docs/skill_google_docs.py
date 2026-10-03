"""
skill_google_docs.py — Generador y Gestor Profesional de Google Docs
===================================================================
Habilidad del Subagente de Asistencia para construir documentos ejecutivos en Google Docs
mediante la API nativa de Google Workspace, con soporte avanzado para:
  - Títulos centrados y jerarquía tipográfica (HEADING_1, HEADING_2, HEADING_3)
  - Párrafos formateados con negrita, cursiva, espaciados (space_above, space_below) y alineación
  - Control de paginación para evitar cortes de párrafo en mitad de hoja (avoidWidowAndOrphan, keepWithNext)
  - Tablas estructuradas con encabezados estilizados y fondo de color en RGB
  - Inserción y maquetación de imágenes con leyenda (captions)
  - Saltos de página y publicación continua reutilizando identificadores de documento

Herramientas disponibles:
  - tool_google_docs         : Genera o actualiza un documento en Google Docs y retorna su URL.
  - ProDocBuilder            : Constructor de documentos en memoria con reglas de estilo editorial.
  - DocManager               : Gestor de publicación, limpieza y reciclaje de identificadores.
  - obtener_prompt_google_docs : System Prompt especializado para inyección bajo demanda.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"

# Importar servicio oficial de Google Workspace
try:
    from Subagente_Asistencia.skills.google_workspace.skill_google import obtener_servicio
except ImportError:
    try:
        from skills.google_workspace.skill_google import obtener_servicio
    except ImportError:
        try:
            from skill_google_sanji import obtener_servicio
        except ImportError:
            obtener_servicio = None


def obtener_prompt_google_docs() -> str:
    """
    System Prompt especializado y encapsulado para el Redactor y Maquetador de Google Docs.
    """
    return """[🛑 HARD-STOP: MODO REDACCIÓN Y MAQUETACIÓN EDITORIAL EN GOOGLE DOCS ACTIVO 🛑]
Eres el Diseñador Editorial y Redactor de Documentos Ejecutivos del Subagente de Asistencia.
Tu misión es maquetar y publicar documentos en Google Docs con acabado corporativo de alta calidad visual, tipografía armónica, control estricto de paginación y tabulación profesional.

DIRECTIVAS OPERATIVAS EDITORIALES OBLIGATORIAS:
1. JERARQUÍA Y CENTRADO DE TÍTULOS:
   - Todo documento formal debe iniciar con un Título Principal (H1) CENTRADO (`align='CENTER'`), seguido de un subtítulo explicativo o metadatos de autoría y fecha.
2. ESPACIADO Y CONTROL DE PÁRRAFOS (CERO BLOQUES PEGADOS):
   - Cada párrafo debe contar con espaciado posterior (`space_below=8pt` a `10pt`) para garantizar legibilidad sin requerir dobles enters vacíos.
   - Aplica destacados en negrita exclusivamente para cifras clave, responsables o conceptos determinantes.
3. PREVENCIÓN DE CORTES Y CONTROL DE PAGINACIÓN:
   - Todo encabezado debe mantener la directiva `keepWithNext=True` para evitar que un título quede solo al final de una página (huérfano) y su contenido en la siguiente.
   - Aplica protección contra viudas y huérfanas (`avoidWidowAndOrphan=True`) en todos los párrafos.
   - Si una sección extensa o tabla comparativa grande inicia hacia el tercio inferior de una página, inserta un salto de página intencional (`page_break()`) para que comience limpia en la siguiente hoja.
4. UBICACIÓN ESTRATÉGICA DE IMÁGENES Y DIAGRAMAS:
   - Las imágenes o capturas deben ubicarse centradas, con un ancho estándar equilibrado (entre 350pt y 450pt) y acompañadas inmediatamente debajo de una leyenda explicativa en cursiva (`caption`). Nunca dejes una imagen aislada al fondo de una página.
5. TABLAS EJECUTIVAS:
   - Toda tabla debe poseer una fila de cabecera con fondo oscuro y texto en blanco/negrita, delimitando con claridad las columnas.
6. RECICLAJE DE DOCUMENTOS Y RETORNO DE URL:
   - Reutiliza el documento existente para reportes periódicos mediante `DocManager`. Devuelve siempre la URL pública o de edición directa al finalizar.
"""


class ProDocBuilder:
    """
    Construye un documento Google Docs en memoria como una secuencia de bloques estilizados
    con soporte para alineación, espaciados, control de saltos de página e imágenes.
    """

    def __init__(self):
        self._blocks = []

    def get_blocks(self) -> List[Dict[str, Any]]:
        return self._blocks

    def h1(self, text: str, align: str = "CENTER", space_above: float = 12.0, space_below: float = 8.0):
        """Título principal del documento (centrado por defecto)."""
        self._blocks.append({
            "type": "heading",
            "level": 1,
            "text": text,
            "align": align,
            "space_above": space_above,
            "space_below": space_below,
            "keep_with_next": True
        })

    def h2(self, text: str, align: str = "START", space_above: float = 14.0, space_below: float = 6.0):
        """Subtítulo de sección temático."""
        self._blocks.append({
            "type": "heading",
            "level": 2,
            "text": text,
            "align": align,
            "space_above": space_above,
            "space_below": space_below,
            "keep_with_next": True
        })

    def h3(self, text: str, align: str = "START", space_above: float = 10.0, space_below: float = 4.0):
        """Subtítulo de subsección."""
        self._blocks.append({
            "type": "heading",
            "level": 3,
            "text": text,
            "align": align,
            "space_above": space_above,
            "space_below": space_below,
            "keep_with_next": True
        })

    def para(self, text: str, bold: bool = False, italic: bool = False,
             font_size: float = None, align: str = "START",
             space_above: float = None, space_below: float = 8.0):
        """Párrafo de texto normal con estilos opcionales y espaciado inferior predeterminado."""
        self._blocks.append({
            "type": "para",
            "text": text,
            "bold": bold,
            "italic": italic,
            "font_size": font_size,
            "align": align,
            "space_above": space_above,
            "space_below": space_below,
            "avoid_widow_orphan": True
        })

    def bold(self, text: str, font_size: float = None, align: str = "START",
             space_above: float = None, space_below: float = 8.0):
        """Párrafo con texto en negrita."""
        self.para(text, bold=True, font_size=font_size, align=align,
                  space_above=space_above, space_below=space_below)

    def caption(self, text: str, align: str = "CENTER"):
        """Pie de imagen o leyenda descriptiva en cursiva y cuerpo reducido."""
        self.para(text, italic=True, font_size=9.0, align=align, space_above=2.0, space_below=12.0)

    def blank(self):
        """Inserta una línea en blanco."""
        self._blocks.append({"type": "blank"})

    def page_break(self):
        """Inserta un salto de página intencional para evitar cortes en mitad de hoja."""
        self._blocks.append({"type": "page_break"})

    def table(self, headers: List[str], rows: List[List[str]],
              header_bg: Tuple[float, float, float] = (0.18, 0.33, 0.58),
              header_fg: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        """Tabla con encabezados estilizados y filas de contenido."""
        self._blocks.append({
            "type": "table",
            "headers": headers,
            "rows": rows,
            "header_bg": header_bg,
            "header_fg": header_fg,
        })

    def image(self, uri: str, caption_text: str = "", width_pt: float = 400.0, height_pt: float = 240.0):
        """Inserta una imagen centrada con dimensiones controladas y leyenda opcional."""
        self._blocks.append({
            "type": "image",
            "uri": uri,
            "width": width_pt,
            "height": height_pt,
            "caption": caption_text
        })


class DocManager:
    """
    Gestiona la publicación, actualización y persistencia de identificadores de Google Docs.
    """

    def __init__(self, title: str = "Informe de Asistencia", id_file: Optional[str] = None):
        if obtener_servicio is None:
            raise RuntimeError("El cliente de Google Workspace no está disponible.")

        self.title = title
        self.docs_service = obtener_servicio('docs', 'v1')
        self.drive_service = obtener_servicio('drive', 'v3')

        if id_file:
            self.id_file = Path(id_file)
        else:
            data_dir = _APP_ROOT / _AGENTE / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.id_file = data_dir / "informe_asistencia_id.txt"
            archivo_legacy = data_dir / "informe_sanji_id.txt"
            if not self.id_file.exists() and archivo_legacy.exists():
                self.id_file = archivo_legacy

        self._doc_id = None

    def _get_or_create(self) -> str:
        """Obtiene el documento existente o crea uno nuevo."""
        if self.id_file.exists():
            saved_id = self.id_file.read_text(encoding='utf-8').strip()
            try:
                self.drive_service.files().get(fileId=saved_id).execute()
                self._doc_id = saved_id
                return self._doc_id
            except Exception:
                pass

        doc = self.docs_service.documents().create(body={'title': self.title}).execute()
        self._doc_id = doc.get('documentId')
        try:
            self.id_file.write_text(self._doc_id, encoding='utf-8')
        except Exception:
            pass
        return self._doc_id

    def _clear(self, doc_id: str):
        """Elimina contenido previo para refrescar el documento."""
        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            end_idx = content[-1].get('endIndex', 1) if content else 1
            if end_idx > 2:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': [{
                        'deleteContentRange': {
                            'range': {'startIndex': 1, 'endIndex': end_idx - 1}
                        }
                    }]}
                ).execute()
        except Exception as e:
            print(f"[DocManager] Advertencia al vaciar documento: {e}")

    def url(self) -> Optional[str]:
        if self._doc_id:
            return f"https://docs.google.com/document/d/{self._doc_id}/edit"
        return None

    def publicar(self, builder: ProDocBuilder) -> str:
        """Publica los bloques construidos en el documento y devuelve la URL."""
        doc_id = self._get_or_create()
        self._clear(doc_id)

        blocks = builder.get_blocks()
        if not blocks:
            return self.url()

        self._publicar_bloques(doc_id, blocks)
        return self.url()

    def _publicar_bloques(self, doc_id: str, blocks: List[Dict[str, Any]]):
        segments = []
        text_segment = []

        for block in blocks:
            btype = block.get("type")
            if btype in ("table", "page_break", "image"):
                if text_segment:
                    segments.append(("text", list(text_segment)))
                    text_segment = []
                segments.append((btype, block))
            else:
                text_segment.append(block)

        if text_segment:
            segments.append(("text", list(text_segment)))

        for seg_type, seg_data in segments:
            if seg_type == "text":
                full_text, positions = self._build_text(seg_data)
                if full_text:
                    req = [{"insertText": {"endOfSegmentLocation": {"segmentId": ""}, "text": full_text}}]
                    self.docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": req}).execute()

                    doc = self.docs_service.documents().get(documentId=doc_id).execute()
                    body_content = doc.get("body", {}).get("content", [])
                    self._apply_text_styles_at_end(doc_id, full_text, positions, body_content)

            elif seg_type == "page_break":
                req = [{"insertPageBreak": {"endOfSegmentLocation": {"segmentId": ""}}}]
                self.docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": req}).execute()

            elif seg_type == "image":
                img_data = seg_data
                uri = img_data.get("uri", "")
                if uri:
                    req = [{
                        "insertInlineImage": {
                            "endOfSegmentLocation": {"segmentId": ""},
                            "uri": uri,
                            "objectSize": {
                                "height": {"magnitude": img_data.get("height", 240.0), "unit": "PT"},
                                "width": {"magnitude": img_data.get("width", 400.0), "unit": "PT"}
                            }
                        }
                    }]
                    self.docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": req}).execute()

                caption = img_data.get("caption", "")
                if caption:
                    cap_text, cap_pos = self._build_text([{
                        "type": "para", "text": caption, "italic": True, "font_size": 9.0,
                        "align": "CENTER", "space_above": 3.0, "space_below": 12.0
                    }])
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={"requests": [{"insertText": {"endOfSegmentLocation": {"segmentId": ""}, "text": cap_text}}]}
                    ).execute()

            elif seg_type == "table":
                table_block = seg_data
                rows = 1 + len(table_block["rows"])
                cols = len(table_block["headers"])

                req = [{
                    "insertTable": {
                        "rows": rows,
                        "columns": cols,
                        "endOfSegmentLocation": {"segmentId": ""}
                    }
                }]
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": req}
                ).execute()

                doc = self.docs_service.documents().get(documentId=doc_id).execute()
                body_content = doc.get("body", {}).get("content", [])

                table_element = None
                for el in reversed(body_content):
                    if "table" in el:
                        table_element = el
                        break

                if table_element:
                    self._fill_table(doc_id, table_element, table_block)

    def _build_text(self, blocks: list) -> Tuple[str, list]:
        full_text = ""
        positions = []
        idx = 0

        for block in blocks:
            btype = block.get("type")
            if btype == "blank":
                text = "\n"
            elif btype in ("heading", "para"):
                text = block.get("text", "") + "\n"
            else:
                continue

            start = idx
            end = idx + len(text)
            style = f"HEADING_{block.get('level', 1)}" if btype == "heading" else None
            bold = block.get("bold", False) if btype == "para" else False
            italic = block.get("italic", False) if btype == "para" else False
            fsize = block.get("font_size")
            align = block.get("align", "START")
            sp_ab = block.get("space_above")
            sp_be = block.get("space_below")
            keep_next = block.get("keep_with_next", False)
            avoid_orphan = block.get("avoid_widow_orphan", True)

            positions.append((start, end, style, bold, italic, fsize, align, sp_ab, sp_be, keep_next, avoid_orphan))
            full_text += text
            idx = end

        return full_text, positions

    def _apply_text_styles_at_end(self, doc_id: str, inserted_text: str, positions: list, body_content: list):
        last_end = 1
        for el in body_content:
            ei = el.get("endIndex", 1)
            if ei > last_end:
                last_end = ei

        text_start = max(1, last_end - len(inserted_text) - 1)
        requests = []

        for rel_start, rel_end, style, bold, italic, fsize, align, sp_ab, sp_be, keep_next, avoid_orphan in positions:
            abs_start = text_start + rel_start
            abs_end = text_start + rel_end

            # Estilos de Párrafo (Alineación, espaciados y control de saltos de página)
            p_style = {}
            p_fields = []

            if style:
                p_style["namedStyleType"] = style
                p_fields.append("namedStyleType")

            if align:
                align_map = {"CENTER": "CENTER", "JUSTIFIED": "JUSTIFIED", "END": "END", "START": "START"}
                p_style["alignment"] = align_map.get(align.upper(), "START")
                p_fields.append("alignment")

            if keep_next:
                p_style["keepWithNext"] = True
                p_fields.append("keepWithNext")

            if avoid_orphan:
                p_style["avoidWidowAndOrphan"] = True
                p_fields.append("avoidWidowAndOrphan")

            if sp_ab is not None:
                p_style["spaceAbove"] = {"magnitude": sp_ab, "unit": "PT"}
                p_fields.append("spaceAbove")

            if sp_be is not None:
                p_style["spaceBelow"] = {"magnitude": sp_be, "unit": "PT"}
                p_fields.append("spaceBelow")

            if p_fields:
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": abs_start, "endIndex": abs_end},
                        "paragraphStyle": p_style,
                        "fields": ",".join(p_fields)
                    }
                })

            # Estilos de Texto (Negrita, Cursiva, Tamaño)
            tstyle = {}
            tfields = []
            if bold:
                tstyle["bold"] = True
                tfields.append("bold")
            if italic:
                tstyle["italic"] = True
                tfields.append("italic")
            if fsize:
                tstyle["fontSize"] = {"magnitude": fsize, "unit": "PT"}
                tfields.append("fontSize")

            if tfields:
                requests.append({
                    "updateTextStyle": {
                        "range": {"startIndex": abs_start, "endIndex": abs_end},
                        "textStyle": tstyle,
                        "fields": ",".join(tfields)
                    }
                })

        if requests:
            for i in range(0, len(requests), 500):
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests[i:i + 500]}
                ).execute()

    def _fill_table(self, doc_id: str, table_element: dict, table_block: dict):
        table_rows = table_element.get("table", {}).get("tableRows", [])
        if not table_rows:
            return

        all_rows_data = [table_block["headers"]] + table_block["rows"]
        insert_requests = []
        cell_locations = []

        for r_idx, row_el in enumerate(table_rows):
            if r_idx >= len(all_rows_data):
                break
            row_data = all_rows_data[r_idx]
            cells = row_el.get("tableCells", [])

            for c_idx, cell_el in enumerate(cells):
                if c_idx >= len(row_data):
                    break
                cell_content = cell_el.get("content", [])
                p_idx = 1
                if cell_content:
                    first_p = cell_content[0].get("paragraph", {})
                    p_elements = first_p.get("elements", [])
                    if p_elements:
                        p_idx = p_elements[0].get("startIndex", 1)

                val = str(row_data[c_idx])
                cell_locations.append((p_idx, val, r_idx == 0))

        for p_idx, val, is_header in reversed(cell_locations):
            insert_requests.append({
                "insertText": {
                    "location": {"index": p_idx},
                    "text": val
                }
            })

        if insert_requests:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": insert_requests}
            ).execute()

        # Estilo de encabezados
        hdr_bg = table_block.get("header_bg", (0.18, 0.33, 0.58))
        hdr_fg = table_block.get("header_fg", (1.0, 1.0, 1.0))
        style_requests = []

        doc_ref = self.docs_service.documents().get(documentId=doc_id).execute()
        b_content = doc_ref.get("body", {}).get("content", [])
        tbl_updated = None
        for el in reversed(b_content):
            if "table" in el:
                tbl_updated = el
                break

        if tbl_updated:
            t_rows = tbl_updated.get("table", {}).get("tableRows", [])
            if t_rows:
                first_row = t_rows[0]
                for cell in first_row.get("tableCells", []):
                    c_start = cell.get("startIndex", 1)
                    c_end = cell.get("endIndex", c_start + 1)

                    style_requests.append({
                        "updateTableCellStyle": {
                            "tableStartLocation": {"index": tbl_updated.get("startIndex", 1)},
                            "tableCellStyle": {
                                "backgroundColor": {
                                    "color": {
                                        "rgbColor": {"red": hdr_bg[0], "green": hdr_bg[1], "blue": hdr_bg[2]}
                                    }
                                }
                            },
                            "fields": "backgroundColor"
                        }
                    })

                    style_requests.append({
                        "updateTextStyle": {
                            "range": {"startIndex": c_start, "endIndex": c_end},
                            "textStyle": {
                                "bold": True,
                                "foregroundColor": {
                                    "color": {
                                        "rgbColor": {"red": hdr_fg[0], "green": hdr_fg[1], "blue": hdr_fg[2]}
                                    }
                                }
                            },
                            "fields": "bold,foregroundColor"
                        }
                    })

        if style_requests:
            for i in range(0, len(style_requests), 500):
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": style_requests[i:i + 500]}
                ).execute()


@tool
def tool_google_docs(title: str, content: str) -> str:
    """
    Crea o actualiza un documento ejecutivo en Google Docs con el título y contenido dados.
    Devuelve la URL oficial de Google Docs para visualización y edición directa.

    Args:
        title: Título principal del documento (se colocará centrado con H1).
        content: Contenido textual a incorporar (soporta encabezados ##, ###, párrafos y tablas).
    """
    if not title or not title.strip():
        return "Error: Se debe proporcionar un título válido para el documento en Google Docs."

    try:
        builder = ProDocBuilder()
        builder.h1(title.strip(), align="CENTER", space_above=12.0, space_below=10.0)

        for linea in (content or "").split("\n"):
            linea_limpia = linea.strip()
            if linea_limpia.startswith("## "):
                builder.h2(linea_limpia[3:], align="START", space_above=14.0, space_below=6.0)
            elif linea_limpia.startswith("### "):
                builder.h3(linea_limpia[4:], align="START", space_above=10.0, space_below=4.0)
            elif linea_limpia.startswith("---"):
                builder.page_break()
            elif linea_limpia:
                builder.para(linea_limpia, space_below=8.0)
            else:
                builder.blank()

        dm = DocManager(title=title.strip())
        url_doc = dm.publicar(builder)
        return f"Documento en Google Docs publicado exitosamente: {url_doc}"
    except Exception as e:
        return f"Error al generar documento en Google Docs: {str(e)}"


# Alias de retrocompatibilidad
tool_google_docs_sanji = tool_google_docs

__all__ = [
    "tool_google_docs",
    "tool_google_docs_sanji",
    "ProDocBuilder",
    "DocManager",
    "obtener_prompt_google_docs",
]
