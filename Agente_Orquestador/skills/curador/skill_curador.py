"""
skill_curador.py — Sistema de Autocuración y Parcheo en Caliente (Self-Healing)
==============================================================================
Habilidad de emergencia del Agente Orquestador para interceptar excepciones fatales,
leer el código fuente con precisión de línea y aplicar parches quirúrgicos en caliente (hot-patching).
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]


def obtener_prompt_curador() -> str:
    """
    System Prompt especializado y encapsulado para el modo de autocuración y
    parcheo quirúrgico de código en caliente.
    """
    return """[🛑 HARD-STOP: MODO AUTOCURACIÓN Y PARCHEO EN CALIENTE (HOT-PATCHING) ACTIVO 🛑]
Eres el Ingeniero de Confiabilidad y Curador de Código en Caliente (SRE & Hot-Patching Lead).
Ha ocurrido un error crítico o excepción no controlada en la ejecución de un agente del sistema. Tu misión exclusiva es diagnosticar la causa raíz del fallo y reparar el archivo directamente en disco mediante un parche quirúrgico exacto.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. INSPECCIÓN PRECISA DEL CÓDIGO:
   - Utiliza `tool_leer_archivo` sobre la ruta indicada en el traceback de error para examinar el código circundante y los números de línea exactos.
2. PARCHEO QUIRÚRGICO EXACTO:
   - Utiliza `tool_parchear_archivo` proporcionando en `buscar` el bloque EXACTO de código defectuoso (respetando espacios, saltos de línea e indentación) y en `reemplazar` el código corregido.
   - Aplica el principio de mínimo cambio: modifica únicamente las líneas necesarias para corregir la excepción sin alterar la lógica de negocio ni refactorizar código ajeno al error.
3. PREVENCIÓN DE EFECTOS COLATERALES:
   - Asegúrate de que las importaciones requeridas estén presentes y que la sintaxis sea 100% válida.
   - No crees archivos nuevos si el objetivo es reparar un módulo existente.
4. CONFIRMACIÓN Y CIERRE:
   - Una vez aplicado el parche con éxito, reporta el diagnóstico, el archivo modificado y la solución aplicada para que el listener reanude la ejecución del agente.
"""


def _resolver_ruta_segura(ruta_str: str) -> Path:
    """
    Resuelve la ruta normalizada manejando entornos Docker (/app/...) y entornos locales en host.
    """
    limpia = ruta_str.strip().strip("'\"")
    # Si viene con prefijo /app en entorno host donde no existe /app
    if limpia.startswith("/app/") and not Path("/app").exists():
        relativa = limpia[len("/app/"):]
        return _APP_ROOT / relativa
    
    p = Path(limpia)
    if not p.is_absolute():
        p = _APP_ROOT / p
    return p


@tool
def tool_leer_archivo(ruta: str) -> str:
    """
    Lee y devuelve el contenido completo de un archivo de código fuente con números de línea.
    Útil para inspeccionar el contexto exacto donde ocurrió una excepción o fallo.
    
    Args:
        ruta: Ruta absoluta o relativa del archivo a inspeccionar (ej: /app/Agente_Orquestador/base_listener.py).
    """
    try:
        p = _resolver_ruta_segura(ruta)
        if not p.exists():
            return f"Error: El archivo '{ruta}' no existe en el sistema."
            
        contenido = p.read_text(encoding="utf-8", errors="replace")
        lineas = contenido.splitlines()
        contenido_numerado = "\n".join([f"{i+1:4d}: {linea}" for i, linea in enumerate(lineas)])
        return f"--- Contenido numerado de {p.name} ({len(lineas)} líneas) ---\n{contenido_numerado}\n--- Fin de archivo ---"
    except Exception as e:
        return f"Error al leer el archivo '{ruta}': {str(e)}"


@tool
def tool_parchear_archivo(ruta: str, buscar: str, reemplazar: str) -> str:
    """
    Reemplaza un bloque EXACTO de código en un archivo por otro bloque (hot-patching).
    El texto en 'buscar' debe coincidir carácter por carácter (incluyendo indentación) con el contenido original.
    Devuelve un mensaje de éxito o el error si no se encuentra el bloque.
    
    Args:
        ruta: Ruta del archivo de código a reparar.
        buscar: Bloque exacto de código defectuoso a reemplazar.
        reemplazar: Nuevo bloque de código corregido que sustituirá a 'buscar'.
    """
    try:
        p = _resolver_ruta_segura(ruta)
        if not p.exists():
            return f"Error de Parcheo: El archivo '{ruta}' no existe en el sistema."
            
        contenido = p.read_text(encoding="utf-8", errors="replace")
        
        # Normalizar finales de línea para evitar desajustes CRLF vs LF
        buscar_norm = buscar.replace("\r\n", "\n")
        contenido_norm = contenido.replace("\r\n", "\n")
        
        if buscar_norm not in contenido_norm:
            return (
                "Error de Parcheo: El bloque de texto especificado en 'buscar' no se encuentra exactamente en el archivo. "
                "Asegúrate de copiar el bloque idéntico (incluyendo espacios de indentación y saltos de línea)."
            )
            
        nuevo_contenido = contenido_norm.replace(buscar_norm, reemplazar.replace("\r\n", "\n"), 1)
        p.write_text(nuevo_contenido, encoding="utf-8")
        
        return f"¡Hot-Patch exitoso en {p.name}! Archivo reparado correctamente en disco."
    except Exception as e:
        return f"Error al aplicar el parche en '{ruta}': {str(e)}"


HERRAMIENTAS_CURADOR = [
    tool_leer_archivo,
    tool_parchear_archivo
]
