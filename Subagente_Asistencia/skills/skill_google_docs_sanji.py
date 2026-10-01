"""
skill_google_docs_sanji.py — Habilidad de Creación de Documentos Profesionales
================================================================================
Utilidades para construir documentos de alta calidad en Google Docs usando
la API nativa, con soporte para:
  - Títulos y subtítulos (HEADING_1, HEADING_2, HEADING_3)
  - Párrafos con texto normal, negrita e itálica
  - Tablas con encabezados y estilos de celda
  - Listas con viñetas y numeradas
  - Color de fondo en celdas
  - Gestión de documentos: crear, limpiar, reutilizar por ID

Patrón de uso:
    from skill_google_docs_sanji import ProDocBuilder, DocManager

    dm  = DocManager(docs_service, drive_service, id_file="mi_doc_id.txt")
    doc = ProDocBuilder()
    doc.h1("Mi Informe")
    doc.para("Contenido del informe...")
    doc.table(headers=["Columna A", "Columna B"], rows=[["val1", "val2"]])
    dm.publicar(doc)
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from skill_google_sanji import obtener_servicio


# ═══════════════════════════════════════════════════════════════════════════════
# Clase ProDocBuilder — Construye un documento en memoria
# ═══════════════════════════════════════════════════════════════════════════════

class ProDocBuilder:
    """
    Construye un documento Google Docs en memoria como una secuencia de bloques.
    Soporta texto, tablas y estilos nativos de Docs.

    Uso:
        doc = ProDocBuilder()
        doc.h1("Título")
        doc.h2("Sección")
        doc.para("Contenido normal")
        doc.bold("Texto en negrita")
        doc.blank()
        doc.table(
            headers=["Columna 1", "Columna 2"],
            rows=[["A", "1"], ["B", "2"]]
        )
    """

    def __init__(self):
        self._blocks = []  # Lista de bloques en orden

    # ── Bloques de texto ──────────────────────────────────────────────────────

    def h1(self, text: str, space_above: float = None, space_below: float = None):
        """Título principal del documento."""
        self._blocks.append({"type": "heading", "level": 1, "text": text,
                             "space_above": space_above, "space_below": space_below})

    def h2(self, text: str, space_above: float = None, space_below: float = None):
        """Subtítulo de sección."""
        self._blocks.append({"type": "heading", "level": 2, "text": text,
                             "space_above": space_above, "space_below": space_below})

    def h3(self, text: str, space_above: float = None, space_below: float = None):
        """Subtítulo de subsección."""
        self._blocks.append({"type": "heading", "level": 3, "text": text,
                             "space_above": space_above, "space_below": space_below})

    def para(self, text: str, bold: bool = False, italic: bool = False,
             font_size: float = None, space_above: float = None, space_below: float = None):
        """Párrafo de texto normal."""
        self._blocks.append({
            "type": "para", "text": text, "bold": bold, "italic": italic,
            "font_size": font_size, "space_above": space_above, "space_below": space_below
        })

    def bold(self, text: str, font_size: float = None, space_above: float = None, space_below: float = None):
        """Párrafo con texto en negrita."""
        self.para(text, bold=True, font_size=font_size, space_above=space_above, space_below=space_below)

    def blank(self):
        """Línea en blanco."""
        self._blocks.append({"type": "blank"})

    def page_break(self):
        """Salto de página."""
        self._blocks.append({"type": "page_break"})

    # ── Bloques de tabla ──────────────────────────────────────────────────────

    def table(self, headers: list[str], rows: list[list[str]],
              header_bg: tuple = (0.18, 0.33, 0.58),
              header_fg: tuple = (1.0, 1.0, 1.0)):
        """
        Tabla con encabezados y filas de datos.

        Args:
            headers:    Lista de títulos de columna.
            rows:       Lista de filas, cada fila es una lista de strings.
            header_bg:  Color de fondo del encabezado en RGB 0-1 (default: azul oscuro).
            header_fg:  Color del texto del encabezado en RGB 0-1 (default: blanco).
        """
        self._blocks.append({
            "type": "table",
            "headers": headers,
            "rows": rows,
            "header_bg": header_bg,
            "header_fg": header_fg,
        })

    # ── Obtener bloques ───────────────────────────────────────────────────────

    def get_blocks(self) -> list:
        return self._blocks


# ═══════════════════════════════════════════════════════════════════════════════
# Clase DocManager — Publica el documento en Google Docs
# ═══════════════════════════════════════════════════════════════════════════════

class DocManager:
    """
    Gestiona el ciclo de vida de un documento Google Docs:
    - Crea el documento si no existe.
    - Reutiliza el mismo documento en publicaciones posteriores.
    - Limpia el contenido anterior antes de publicar.
    """

    def __init__(self, title: str, id_file: str,
                 docs_service=None, drive_service=None):
        self.title        = title
        self.id_file      = Path(id_file)
        self.docs_service = docs_service or obtener_servicio('docs', 'v1')
        self.drive_service= drive_service or obtener_servicio('drive', 'v3')
        self._doc_id      = None

    def _get_or_create(self) -> str:
        """Retorna el ID del documento, creándolo si no existe."""
        if self._doc_id:
            return self._doc_id

        if self.id_file.exists():
            saved_id = self.id_file.read_text(encoding='utf-8').strip()
            try:
                self.drive_service.files().get(fileId=saved_id).execute()
                self._doc_id = saved_id
                print(f"[DocManager] Documento existente: {self._doc_id}")
                return self._doc_id
            except Exception:
                print("[DocManager] Documento anterior no encontrado. Creando uno nuevo.")

        doc = self.docs_service.documents().create(
            body={'title': self.title}
        ).execute()
        self._doc_id = doc.get('documentId')
        self.id_file.write_text(self._doc_id, encoding='utf-8')
        print(f"[DocManager] Nuevo documento creado: {self._doc_id}")
        return self._doc_id

    def _clear(self, doc_id: str):
        """Elimina todo el contenido del documento (solo si tiene contenido real)."""
        doc = self.docs_service.documents().get(documentId=doc_id).execute()
        content = doc.get('body', {}).get('content', [])
        end_idx = content[-1].get('endIndex', 1) if content else 1
        # Un doc nuevo solo tiene el párrafo vacío inicial (endIndex=1).
        # Solo borramos si hay contenido real (endIndex > 2).
        if end_idx > 2:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': [{
                    'deleteContentRange': {
                        'range': {'startIndex': 1, 'endIndex': end_idx - 1}
                    }
                }]}
            ).execute()

    def url(self) -> Optional[str]:
        """Retorna la URL del documento si existe."""
        if self._doc_id:
            return f"https://docs.google.com/document/d/{self._doc_id}/edit"
        return None

    def publicar(self, builder: ProDocBuilder) -> str:
        """
        Publica el documento en Google Docs.
        Limpia el contenido anterior si el documento ya existía.
        Retorna la URL del documento.
        """
        doc_id = self._get_or_create()
        self._clear(doc_id)

        blocks = builder.get_blocks()
        if not blocks:
            return self.url()

        # ── Separar bloques en texto y tablas ─────────────────────────────────
        # Estrategia: insertar texto y tablas en secuencia.
        # Las tablas se insertan vacías y luego se rellenan.

        text_blocks  = []  # bloques de texto en orden
        table_blocks = []  # (posición_en_secuencia, tabla_dict)

        for i, block in enumerate(blocks):
            if block["type"] == "table":
                table_blocks.append((i, block))
            else:
                text_blocks.append((i, block))

        if not table_blocks:
            # Sin tablas: insertar todo de una vez
            self._insert_text_blocks(doc_id, [b for _, b in sorted(text_blocks)])
        else:
            # Con tablas: publicar en fases
            self._publicar_con_tablas(doc_id, blocks)

        print(f"[DocManager] Documento publicado: {self.url()}")
        return self.url()

    # ── Publicación sin tablas ────────────────────────────────────────────────

    def _insert_text_blocks(self, doc_id: str, blocks: list):
        """Inserta una secuencia de bloques de texto delegando a _publicar_con_tablas."""
        self._publicar_con_tablas(doc_id, blocks)

    # ── Publicación con tablas ────────────────────────────────────────────────

    def _publicar_con_tablas(self, doc_id: str, blocks: list):
        """
        Publica un documento que contiene tablas y/o saltos de página.
        Inserta bloques en secuencia.
        """
        segments = []
        text_segment = []

        for block in blocks:
            if block["type"] == "table" or block["type"] == "page_break":
                if text_segment:
                    segments.append(("text", list(text_segment)))
                    text_segment = []
                segments.append((block["type"], block))
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

            elif seg_type == "table":
                table_block = seg_data
                rows   = 1 + len(table_block["rows"])  # header + data rows
                cols   = len(table_block["headers"])

                # Insertar tabla vacía al final
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

                # Obtener documento para encontrar la tabla recién insertada
                doc = self.docs_service.documents().get(documentId=doc_id).execute()
                body_content = doc.get("body", {}).get("content", [])

                # La tabla está al final
                table_element = None
                for el in reversed(body_content):
                    if "table" in el:
                        table_element = el
                        break

                if table_element:
                    self._fill_table(doc_id, table_element, table_block)

    def _build_text(self, blocks: list) -> tuple:
        """Construye el texto completo y lista de posiciones relativas."""
        full_text = ""
        positions = []
        idx = 0  # relativo

        for block in blocks:
            btype = block.get("type")
            if btype == "blank":
                text = "\n"
            elif btype == "heading":
                text = block["text"] + "\n"
            elif btype == "para":
                text = block["text"] + "\n"
            else:
                continue

            start  = idx
            end    = idx + len(text)
            style  = None
            bold   = block.get("bold", False) if btype == "para" else False
            italic = block.get("italic", False) if btype == "para" else False
            fsize  = block.get("font_size")
            sp_ab  = block.get("space_above")
            sp_be  = block.get("space_below")

            if btype == "heading":
                style = f"HEADING_{block.get('level', 1)}"

            positions.append((start, end, style, bold, italic, fsize, sp_ab, sp_be))
            full_text += text
            idx = end

        return full_text, positions

    def _apply_text_styles_at_end(self, doc_id: str, inserted_text: str,
                                   positions: list, body_content: list):
        """Aplica estilos al texto recién insertado al final del documento."""
        last_end = 1
        for el in body_content:
            ei = el.get("endIndex", 1)
            if ei > last_end:
                last_end = ei

        text_start = last_end - len(inserted_text) - 1
        if text_start < 1:
            text_start = 1

        requests = []
        for rel_start, rel_end, style, bold, italic, fsize, sp_ab, sp_be in positions:
            abs_start = text_start + rel_start
            abs_end   = text_start + rel_end

            # Estilos de párrafo
            p_style = {}
            fields_p = []
            if style:
                p_style["namedStyleType"] = style
                fields_p.append("namedStyleType")
            if sp_ab is not None:
                p_style["spaceAbove"] = {"magnitude": sp_ab, "unit": "PT"}
                fields_p.append("spaceAbove")
            if sp_be is not None:
                p_style["spaceBelow"] = {"magnitude": sp_be, "unit": "PT"}
                fields_p.append("spaceBelow")

            if p_style:
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": abs_start, "endIndex": abs_end},
                        "paragraphStyle": p_style,
                        "fields": ",".join(fields_p)
                    }
                })

            # Estilos de texto
            t_style = {}
            fields_t = []
            if bold:
                t_style["bold"] = True
                fields_t.append("bold")
            if italic:
                t_style["italic"] = True
                fields_t.append("italic")
            if fsize is not None:
                t_style["fontSize"] = {"magnitude": fsize, "unit": "PT"}
                fields_t.append("fontSize")

            if t_style and abs_end - 1 > abs_start:
                requests.append({
                    "updateTextStyle": {
                        "range": {"startIndex": abs_start, "endIndex": abs_end - 1},
                        "textStyle": t_style,
                        "fields": ",".join(fields_t)
                    }
                })

        if requests:
            for i in range(0, len(requests), 500):
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests[i:i+500]}
                ).execute()

    def _fill_table(self, doc_id: str, table_element: dict, table_block: dict):
        """Rellena las celdas de una tabla y aplica estilos de encabezado."""
        all_rows = [table_block["headers"]] + table_block["rows"]
        table_rows = table_element.get("table", {}).get("tableRows", [])

        # Recopilar (cell_index, text, is_header) en orden inverso
        cell_jobs = []

        for row_i, (trow, data_row) in enumerate(zip(table_rows, all_rows)):
            is_header = (row_i == 0)
            for col_i, (tcell, cell_text) in enumerate(
                zip(trow.get("tableCells", []), data_row)
            ):
                cell_content = tcell.get("content", [])
                if cell_content:
                    # startIndex es el inicio del párrafo vacío dentro de la celda.
                    # Insertamos en ese índice (dentro de los límites del párrafo).
                    cell_start = cell_content[0].get("startIndex", 0)
                    cell_jobs.append((cell_start, str(cell_text), is_header))

        # Ordenar en reversa para que los índices no se desplacen
        cell_jobs.sort(key=lambda x: x[0], reverse=True)

        insert_requests = []
        for cell_idx, text, is_header in cell_jobs:
            insert_requests.append({
                "insertText": {
                    "location": {"index": cell_idx},   # startIndex del párrafo, sin +1
                    "text": text
                }
            })

        # Insertar texto en celdas
        if insert_requests:
            for i in range(0, len(insert_requests), 500):
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": insert_requests[i:i+500]}
                ).execute()

        # Aplicar estilos al encabezado (fondo de color + texto blanco + negrita)
        hdr_bg = table_block.get("header_bg", (0.18, 0.33, 0.58))
        hdr_fg = table_block.get("header_fg", (1.0, 1.0, 1.0))

        doc = self.docs_service.documents().get(documentId=doc_id).execute()
        body_content = doc.get("body", {}).get("content", [])

        # Encontrar la tabla actualizada
        for el in reversed(body_content):
            if "table" in el:
                updated_table = el
                break
        else:
            return

        header_row = updated_table.get("table", {}).get("tableRows", [])[0]
        style_requests = []

        for tcell in header_row.get("tableCells", []):
            # Fondo de celda
            tc_start = tcell.get("startIndex", 0)
            tc_end   = tcell.get("endIndex", 0)
            style_requests.append({
                "updateTableCellStyle": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": updated_table.get("startIndex")},
                            "rowIndex": 0,
                            "columnIndex": header_row.get("tableCells", []).index(tcell)
                        },
                        "rowSpan": 1,
                        "columnSpan": 1
                    },
                    "tableCellStyle": {
                        "backgroundColor": {
                            "color": {
                                "rgbColor": {
                                    "red": hdr_bg[0],
                                    "green": hdr_bg[1],
                                    "blue": hdr_bg[2]
                                }
                            }
                        }
                    },
                    "fields": "backgroundColor"
                }
            })
            # Texto blanco y negrita
            for para in tcell.get("content", []):
                for el_run in para.get("paragraph", {}).get("elements", []):
                    run_start = el_run.get("startIndex", 0)
                    run_end   = el_run.get("endIndex", 0)
                    if run_end > run_start:
                        style_requests.append({
                            "updateTextStyle": {
                                "range": {"startIndex": run_start, "endIndex": run_end},
                                "textStyle": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "color": {
                                            "rgbColor": {
                                                "red": hdr_fg[0],
                                                "green": hdr_fg[1],
                                                "blue": hdr_fg[2]
                                            }
                                        }
                                    }
                                },
                                "fields": "bold,foregroundColor"
                            }
                        })

        if style_requests:
            for i in range(0, len(style_requests), 500):
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": style_requests[i:i+500]}
                ).execute()


from langchain_core.tools import tool

@tool
def tool_google_docs(title: str, content: str) -> str:
    """
    Crea un nuevo documento en Google Docs con el título especificado y escribe el contenido.
    Devuelve la URL del documento creado.
    """
    try:
        doc = ProDocBuilder()
        doc.h1(title)
        for para in content.split('\n'):
            if para.strip():
                doc.para(para.strip())
        
        id_file = str(Path(__file__).resolve().parents[1] / "data" / "informe_sanji_id.txt")
        dm = DocManager(title=title, id_file=id_file)
        url = dm.publicar(doc)
        return f"Documento creado exitosamente: {url}"
    except Exception as e:
        return f"Error al crear documento: {str(e)}"

# ═══════════════════════════════════════════════════════════════════════════════
# Ejemplo de uso directo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Probando ProDocBuilder + DocManager...")

    doc = ProDocBuilder()
    doc.h1("Documento de Prueba")
    doc.para("Este es un párrafo de texto normal.")
    doc.blank()
    doc.h2("Sección con tabla")
    doc.para("A continuación un resumen en formato de tabla:")
    doc.blank()
    doc.table(
        headers=["Categoría", "Valor"],
        rows=[
            ["Elemento A", "100"],
            ["Elemento B", "200"],
            ["Elemento C", "300"],
        ]
    )
    doc.blank()
    doc.h2("Conclusión")
    doc.para("Todo funcionando correctamente.")

    BASE_DIR = Path(__file__).parent
    dm = DocManager(
        title="Documento de Prueba — Sanji",
        id_file=str(BASE_DIR / "test_doc_id.txt")
    )
    url = dm.publicar(doc)
    print(f"Documento disponible en: {url}")
