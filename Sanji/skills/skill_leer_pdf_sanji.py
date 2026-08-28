"""
skill_leer_pdf_sanji.py — Habilidad de Extracción de Texto de PDFs (Sanji)
==========================================================================
Herramienta para extraer texto plano de archivos PDF usando la librería pypdf.

Utilidades disponibles:
  - tool_leer_pdf_texto : Extrae el texto completo de un PDF (todas las páginas)
  - tool_leer_pdf_pagina: Extrae el texto de una página específica del PDF
  - tool_leer_pdf_metadatos: Obtiene metadatos del PDF (título, autor, nº páginas)

Patrón de uso:
    from skill_leer_pdf_sanji import tool_leer_pdf_texto, tool_leer_pdf_pagina, tool_leer_pdf_metadatos

    texto = tool_leer_pdf_texto("ruta/al/archivo.pdf")
    pagina = tool_leer_pdf_pagina("ruta/al/archivo.pdf", pagina=2)
    meta = tool_leer_pdf_metadatos("ruta/al/archivo.pdf")
"""

from pathlib import Path
from langchain_core.tools import tool

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

# Mensajes de error genéricos y seguros (no exponen rutas absolutas ni stack traces)
_MSG_LIBRERIA_NO_DISPONIBLE = (
    "No se pudo procesar el PDF: la librería de lectura no está disponible. "
    "Contacta al administrador del sistema."
)
_MSG_ARCHIVO_NO_ENCONTRADO = (
    "No se pudo procesar el PDF: el archivo indicado no existe o no es accesible."
)
_MSG_EXTENSION_INVALIDA = (
    "No se pudo procesar el PDF: el archivo no tiene una extensión .pdf válida."
)
_MSG_ARCHIVO_DEMASIADO_GRANDE = (
    "No se pudo procesar el PDF: el archivo supera el tamaño máximo permitido de 50 MB."
)
_MSG_RUTA_NO_PERMITIDA = (
    "No se pudo procesar el PDF: la ruta del archivo no está dentro de un directorio permitido."
)
_MSG_ERROR_GENERICO = (
    "No se pudo procesar el PDF. Ocurrió un error inesperado. "
    "Inténtalo de nuevo o contacta al administrador del sistema."
)

# Tamaño máximo permitido para archivos PDF (en bytes): 50 MB
_TAMANO_MAXIMO_PDF_BYTES = 50 * 1024 * 1024  # 52,428,800 bytes

# Directorios permitidos para la lectura de PDFs (Hallazgo PDF-03)
# Previene path traversal: solo se permite leer PDFs dentro de estos directorios.
_DIRECTORIOS_PERMITIDOS = [
    Path("/app/Sanji/data").resolve(),
    Path("/app/Sanji/documentos_sanji").resolve(),
    Path("/app/Sanji/skills").resolve(),
]


def _validar_ruta_permitida(ruta: Path) -> None:
    """
    Valida que la ruta del PDF esté dentro de un directorio permitido.
    Previene ataques de path traversal (Hallazgo PDF-03).

    Args:
        ruta: Ruta absoluta resuelta del archivo PDF.

    Raises:
        PermissionError: Si la ruta no está dentro de un directorio permitido.
    """
    ruta_resuelta = ruta.resolve()
    for dir_permitido in _DIRECTORIOS_PERMITIDOS:
        try:
            # Verifica si la ruta está dentro del directorio permitido
            ruta_resuelta.relative_to(dir_permitido)
            return
        except ValueError:
            # No está dentro de este directorio, probar el siguiente
            continue
    # No se encontró ningún directorio permitido que contenga la ruta
    raise PermissionError(_MSG_RUTA_NO_PERMITIDA)


def _obtener_reader(ruta_pdf: str) -> PdfReader:
    """Abre el PDF y devuelve un objeto PdfReader. Lanza excepción si no es válido."""
    if PdfReader is None:
        raise RuntimeError(_MSG_LIBRERIA_NO_DISPONIBLE)
    ruta = Path(ruta_pdf)
    if not ruta.exists():
        raise FileNotFoundError(_MSG_ARCHIVO_NO_ENCONTRADO)
    if ruta.suffix.lower() != ".pdf":
        raise ValueError(_MSG_EXTENSION_INVALIDA)
    # Validación de ruta permitida (Hallazgo PDF-03)
    # Previene path traversal: solo se permite leer PDFs dentro de directorios permitidos
    _validar_ruta_permitida(ruta)
    # Validación de tamaño máximo del archivo PDF (50 MB)
    # Previene agotamiento de memoria por PDFs extremadamente grandes (Hallazgo PDF-02)
    tamano_bytes = ruta.stat().st_size
    if tamano_bytes > _TAMANO_MAXIMO_PDF_BYTES:
        raise ValueError(_MSG_ARCHIVO_DEMASIADO_GRANDE)
    return PdfReader(str(ruta))


@tool
def tool_leer_pdf_texto(ruta_pdf: str) -> str:
    """
    Extrae el texto completo de un archivo PDF, página por página.

    Args:
        ruta_pdf: Ruta completa del archivo PDF a leer.

    Returns:
        El texto extraído de todas las páginas del PDF, o un mensaje de error.
    """
    try:
        reader = _obtener_reader(ruta_pdf)
        paginas = []
        for i, pagina in enumerate(reader.pages, 1):
            texto = pagina.extract_text() or ""
            paginas.append(f"--- Página {i} ---\n{texto.strip()}")
        if not paginas:
            return "El PDF no contiene páginas."
        return "\n\n".join(paginas)
    except Exception:
        return _MSG_ERROR_GENERICO


@tool
def tool_leer_pdf_pagina(ruta_pdf: str, pagina: int) -> str:
    """
    Extrae el texto de una página específica de un archivo PDF.

    Args:
        ruta_pdf: Ruta completa del archivo PDF a leer.
        pagina: Número de página (1-indexado) a extraer.

    Returns:
        El texto de la página solicitada, o un mensaje de error.
    """
    try:
        reader = _obtener_reader(ruta_pdf)
        total = len(reader.pages)
        if pagina < 1 or pagina > total:
            return f"Página {pagina} fuera de rango. El PDF tiene {total} páginas."
        texto = reader.pages[pagina - 1].extract_text() or ""
        return f"--- Página {pagina} de {total} ---\n{texto.strip()}"
    except Exception:
        return _MSG_ERROR_GENERICO


@tool
def tool_leer_pdf_metadatos(ruta_pdf: str) -> str:
    """
    Obtiene los metadatos de un archivo PDF (título, autor, nº de páginas, etc.).

    Args:
        ruta_pdf: Ruta completa del archivo PDF a inspeccionar.

    Returns:
        Un resumen con los metadatos del PDF, o un mensaje de error.
    """
    try:
        reader = _obtener_reader(ruta_pdf)
        meta = reader.metadata or {}
        info = {
            "archivo": ruta_pdf,
            "total_paginas": len(reader.pages),
            "titulo": meta.get("/Title", "Desconocido"),
            "autor": meta.get("/Author", "Desconocido"),
            "creador": meta.get("/Creator", "Desconocido"),
            "productor": meta.get("/Producer", "Desconocido"),
            "fecha_creacion": meta.get("/CreationDate", "Desconocido"),
        }
        lineas = [f"{k}: {v}" for k, v in info.items()]
        return "\n".join(lineas)
    except Exception:
        return _MSG_ERROR_GENERICO
