"""
skill_leer_pdf.py — Habilidad de Extracción y Procesamiento de Documentos PDF
=============================================================================
Herramienta para inspeccionar, extraer texto plano y analizar metadatos de archivos PDF
usando la librería pypdf (o PyPDF2 de respaldo), con defensas activas contra path traversal,
consumo excesivo de memoria (archivos gigantes) y desbordamiento de contexto del LLM.

Utilidades disponibles:
  - tool_leer_pdf_texto     : Extrae el texto completo del PDF con protección de contexto.
  - tool_leer_pdf_pagina    : Extrae el contenido de una página específica (1-indexado).
  - tool_leer_pdf_metadatos : Obtiene metadatos del documento (título, autor, nº de páginas).
  - obtener_prompt_leer_pdf : System Prompt especializado para inyección bajo demanda.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

# Carga resiliente de librería PDF
try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"

# Mensajes seguros (no exponen rutas internas sensibles del sistema)
_MSG_LIBRERIA_NO_DISPONIBLE = (
    "No se pudo procesar el PDF: la librería de lectura (pypdf) no está instalada en el entorno."
)
_MSG_ARCHIVO_NO_ENCONTRADO = (
    "No se pudo procesar el PDF: el archivo indicado no existe o no es accesible."
)
_MSG_EXTENSION_INVALIDA = (
    "No se pudo procesar el PDF: el archivo no cuenta con extensión .pdf válida."
)
_MSG_ARCHIVO_DEMASIADO_GRANDE = (
    "No se pudo procesar el PDF: el archivo supera el límite máximo permitido de 50 MB."
)
_MSG_RUTA_NO_PERMITIDA = (
    "Acceso denegado: la ruta del archivo se encuentra fuera de los directorios permitidos del workspace."
)
_MSG_ERROR_GENERICO = (
    "Ocurrió un error inesperado al procesar el archivo PDF. Verifica el formato e intenta nuevamente."
)

# Límite máximo de tamaño en bytes: 50 MB
_TAMANO_MAXIMO_PDF_BYTES = 50 * 1024 * 1024

# Límite máximo de caracteres por llamada a tool_leer_pdf_texto para no saturar contexto
_MAX_CHARS_TEXTO_COMPLETO = 12000

# Directorios autorizados para lectura de PDFs (Soporta Docker /app y entorno local)
_DIRECTORIOS_PERMITIDOS = [
    (_APP_ROOT / _AGENTE / "data").resolve(),
    (_APP_ROOT / _AGENTE / "informes").resolve(),
    (_APP_ROOT / _AGENTE / "documentos_sanji").resolve(),
    (_APP_ROOT / _AGENTE / "skills").resolve(),
    (_APP_ROOT / "Archivos_temporales").resolve(),
    (_APP_ROOT / "proyectos").resolve(),
    (_APP_ROOT / "contexto").resolve(),
    Path("/app/Subagente_Asistencia/data").resolve(),
    Path("/app/Subagente_Asistencia/informes").resolve(),
    Path("/app/Subagente_Asistencia/documentos_sanji").resolve(),
    Path("/app/Archivos_temporales").resolve(),
]


def obtener_prompt_leer_pdf() -> str:
    """
    System Prompt especializado y encapsulado para el Especialista en Análisis de PDFs.
    """
    return """[🛑 HARD-STOP: MODO EXTRACCIÓN Y ANÁLISIS DE DOCUMENTOS PDF ACTIVO 🛑]
Eres el Especialista en Procesamiento e Ingesta de Documentos PDF del Subagente de Asistencia.
Tu misión es extraer texto, inspeccionar metadatos y analizar documentación en formato PDF con rigurosa precisión técnica, respetando la seguridad de rutas y protegiendo la ventana de contexto.

DIRECTIVAS OPERATIVAS:
1. EXPLORACIÓN METADATOS PREVIA:
   - Ante PDFs extensos o desconocidos, utiliza primero `tool_leer_pdf_metadatos` para conocer el número total de páginas, título y autor antes de extraer contenido completo.
2. EXTRACCIÓN FOCALIZADA:
   - Si el usuario o el flujo requiere una sección o página específica, utiliza `tool_leer_pdf_pagina` en lugar de volcar todo el documento.
3. PREVENCIÓN DE SATURACIÓN DE CONTEXTO:
   - Ten en cuenta que si el documento supera el límite de seguridad de caracteres, la respuesta se paginará. En tales casos, realiza lecturas por páginas específicas para extraer detalles específicos.
4. SANITIZACIÓN Y PRIVACIDAD:
   - Al sintetizar información de PDFs, no expongas datos personales, credenciales ni información confidencial sin anonimizar.
"""


def _validar_ruta_permitida(ruta: Path) -> None:
    """
    Verifica que la ruta del PDF resida dentro de los directorios autorizados del sistema.
    Previene vulnerabilidades de Path Traversal (CWE-22).
    """
    ruta_resuelta = ruta.resolve()
    for dir_permitido in _DIRECTORIOS_PERMITIDOS:
        try:
            ruta_resuelta.relative_to(dir_permitido)
            return
        except ValueError:
            continue
    raise PermissionError(_MSG_RUTA_NO_PERMITIDA)


def _obtener_reader(ruta_pdf: str) -> PdfReader:
    """
    Abre y valida el archivo PDF. Retorna una instancia de PdfReader.
    """
    if PdfReader is None:
        raise RuntimeError(_MSG_LIBRERIA_NO_DISPONIBLE)

    ruta = Path(ruta_pdf)
    if not ruta.is_file():
        raise FileNotFoundError(_MSG_ARCHIVO_NO_ENCONTRADO)

    if ruta.suffix.lower() != ".pdf":
        raise ValueError(_MSG_EXTENSION_INVALIDA)

    _validar_ruta_permitida(ruta)

    if ruta.stat().st_size > _TAMANO_MAXIMO_PDF_BYTES:
        raise ValueError(_MSG_ARCHIVO_DEMASIADO_GRANDE)

    return PdfReader(str(ruta.resolve()))


@tool
def tool_leer_pdf_texto(ruta_pdf: str) -> str:
    """
    Extrae el texto completo de un archivo PDF, iterando sobre todas sus páginas.
    Cuenta con paginación de seguridad para proteger el contexto del LLM.

    Args:
        ruta_pdf: Ruta absoluta o relativa del archivo PDF (ej: /app/Archivos_temporales/documento.pdf).

    Returns:
        Texto plano extraído delimitado por páginas, o mensaje estructurado de error.
    """
    try:
        reader = _obtener_reader(ruta_pdf)
        total_paginas = len(reader.pages)
        if total_paginas == 0:
            return "El PDF no contiene páginas."

        paginas = []
        caracteres_acumulados = 0
        truncado = False

        for i, pagina in enumerate(reader.pages, 1):
            texto_pag = (pagina.extract_text() or "").strip()
            bloque = f"--- Página {i} de {total_paginas} ---\n{texto_pag}"
            paginas.append(bloque)
            caracteres_acumulados += len(bloque)

            if caracteres_acumulados >= _MAX_CHARS_TEXTO_COMPLETO and i < total_paginas:
                truncado = True
                paginas.append(
                    f"\n[⚠️ AVISO DE CONTEXTO: Texto truncado tras procesar {i} de {total_paginas} páginas "
                    f"para proteger la memoria del modelo. Utiliza tool_leer_pdf_pagina para consultar las páginas restantes.]"
                )
                break

        return "\n\n".join(paginas)
    except PermissionError as pe:
        return f"Error de seguridad: {pe}"
    except (FileNotFoundError, ValueError) as ve:
        return f"Error de archivo: {ve}"
    except Exception as e:
        return f"{_MSG_ERROR_GENERICO} Detalle: {str(e)}"


@tool
def tool_leer_pdf_pagina(ruta_pdf: str, pagina: int) -> str:
    """
    Extrae el contenido de texto de una página específica del archivo PDF.

    Args:
        ruta_pdf: Ruta completa del archivo PDF.
        pagina: Número de página a consultar (comenzando en 1).

    Returns:
        Texto extraído de la página solicitada.
    """
    try:
        reader = _obtener_reader(ruta_pdf)
        total = len(reader.pages)
        if pagina < 1 or pagina > total:
            return f"Error: La página {pagina} está fuera de rango. El documento tiene un total de {total} páginas."

        texto = (reader.pages[pagina - 1].extract_text() or "").strip()
        return f"--- Página {pagina} de {total} ---\n{texto}"
    except PermissionError as pe:
        return f"Error de seguridad: {pe}"
    except (FileNotFoundError, ValueError) as ve:
        return f"Error de archivo: {ve}"
    except Exception as e:
        return f"{_MSG_ERROR_GENERICO} Detalle: {str(e)}"


@tool
def tool_leer_pdf_metadatos(ruta_pdf: str) -> str:
    """
    Inspecciona y devuelve los metadatos oficiales del archivo PDF.

    Args:
        ruta_pdf: Ruta del archivo PDF a examinar.

    Returns:
        Resumen estructurado con total de páginas, título, autor, software creador y fechas.
    """
    try:
        reader = _obtener_reader(ruta_pdf)
        meta = reader.metadata or {}
        info = {
            "archivo": str(Path(ruta_pdf).name),
            "total_paginas": len(reader.pages),
            "titulo": str(meta.get("/Title", "No especificado")),
            "autor": str(meta.get("/Author", "No especificado")),
            "creador": str(meta.get("/Creator", "No especificado")),
            "productor": str(meta.get("/Producer", "No especificado")),
            "fecha_creacion": str(meta.get("/CreationDate", "No especificada")),
        }
        lineas = [f"- **{k.replace('_', ' ').capitalize()}:** {v}" for k, v in info.items()]
        return "📋 **Metadatos del Documento PDF:**\n" + "\n".join(lineas)
    except PermissionError as pe:
        return f"Error de seguridad: {pe}"
    except (FileNotFoundError, ValueError) as ve:
        return f"Error de archivo: {ve}"
    except Exception as e:
        return f"{_MSG_ERROR_GENERICO} Detalle: {str(e)}"


# Alias de compatibilidad histórica
tool_leer_pdf_texto_sanji = tool_leer_pdf_texto
tool_leer_pdf_pagina_sanji = tool_leer_pdf_pagina
tool_leer_pdf_metadatos_sanji = tool_leer_pdf_metadatos

__all__ = [
    "tool_leer_pdf_texto",
    "tool_leer_pdf_pagina",
    "tool_leer_pdf_metadatos",
    "tool_leer_pdf_texto_sanji",
    "tool_leer_pdf_pagina_sanji",
    "tool_leer_pdf_metadatos_sanji",
    "obtener_prompt_leer_pdf",
]
