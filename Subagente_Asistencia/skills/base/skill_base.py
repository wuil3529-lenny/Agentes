"""
skill_base.py — Habilidades Base: Sistema de Archivos y Comandos de Shell
==========================================================================
Herramientas fundamentales de entrada/salida (I/O) y ejecución de procesos
para el Subagente de Asistencia.
Validación unificada: Hard Stop + Auto-enlazador Obsidian + Anti-alucinación.

Herramientas disponibles:
  - crear_archivo      : Crear/sobreescribir cualquier archivo con control de firewall
  - leer_archivo       : Leer contenido con censura de metadatos Obsidian (anti-alucinación)
  - listar_directorio  : Explorar la estructura de carpetas y tamaños de archivos
  - ejecutar_comando   : Ejecutar comandos de shell con lista blanca y timeout seguro
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"

# Directorios de trabajo y salida
_INFORMES = _APP_ROOT / _AGENTE / "informes"
_DOCUMENTOS_ASISTENCIA = _APP_ROOT / _AGENTE / "documentos_asistencia"
_DOCUMENTOS = _APP_ROOT / _AGENTE / "documentos_sanji"
_DATA = _APP_ROOT / _AGENTE / "data"
_TEMP = _APP_ROOT / "Archivos_temporales"
_MEMORIA = _APP_ROOT / "memoria"

# Asegurar existencia de carpetas clave
_INFORMES.mkdir(parents=True, exist_ok=True)
_DOCUMENTOS_ASISTENCIA.mkdir(parents=True, exist_ok=True)
_TEMP.mkdir(parents=True, exist_ok=True)


def obtener_prompt_base() -> str:
    """
    System Prompt especializado y encapsulado para las operaciones base de sistema de archivos
    y ejecución de comandos de terminal del Subagente de Asistencia.
    """
    return """[🛑 HARD-STOP: MODO OPERACIONES BASE DE SISTEMA Y ARCHIVOS ACTIVO 🛑]
Eres el Operador de Infraestructura y Gestión de Archivos del Subagente de Asistencia.
Tu misión es gestionar lecturas, escrituras, exploración de directorios y ejecución de procesos en el sistema operativo con rigor técnico, respetando el firewall determinístico y previniendo la corrupción de datos o la sobrecarga de contexto.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida su existencia o la de sus directorios contenedores usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y ZONAS SEGURAS:
   - Entregables e Informes de Asistencia: `/app/Subagente_Asistencia/informes/`, `/app/Subagente_Asistencia/documentos_asistencia/` o `/app/Subagente_Asistencia/documentos_sanji/`.
   - Archivos Temporales / Scratch: `/app/Archivos_temporales/` (obligatorio prefijo `asistencia_` o `sanji_`).
   - Bitácora de Tareas: `/app/Bitacora.md` (única fuente de verdad).
   - Tienes terminantemente prohibido ejecutar comandos destructivos (rm -rf, del /f, format, shutdown, etc.).
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - NUNCA escribas manualmente en Cerebro.md ni en memoria/. El conocimiento se registra a través de las herramientas RAG autorizadas.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil correspondiente.
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina a un máximo de seguridad para no desbordar la ventana de contexto.
"""


def _normalizar(ruta: str) -> str:
    return str(Path(ruta).resolve()).replace("\\", "/")


def _ruta_es_valida(ruta_str: str) -> tuple[bool, str]:
    """
    Verifica si la ruta es una zona de escritura autorizada.
    Retorna (es_valida, ruta_corregida).
    """
    ruta_norm = _normalizar(ruta_str)
    raiz_agente = _normalizar(str(_APP_ROOT / _AGENTE))
    temp_global = _normalizar(str(_TEMP))
    temp_local = _normalizar(str(_APP_ROOT / _AGENTE / "Archivos_temporales"))

    # AUTO-CORRECCIÓN: si apunta a la Archivos_temporales local del agente -> redirigir a global
    if ruta_norm.startswith(temp_local):
        ruta_corregida = ruta_norm.replace(temp_local, temp_global)
        return True, ruta_corregida

    # Zonas válidas
    zonas_validas = [
        _normalizar(str(_INFORMES)),
        _normalizar(str(_DOCUMENTOS_ASISTENCIA)),
        _normalizar(str(_DOCUMENTOS)),
        _normalizar(str(_DATA)),
        temp_global,
        _normalizar(str(_MEMORIA)),
        _normalizar(str(_APP_ROOT / "Bitacora.md")),
    ]
    for zona in zonas_validas:
        if ruta_norm.startswith(zona):
            return True, ruta_str

    # Zona raíz del agente: solo permitida si es una subcarpeta conocida
    if ruta_norm.startswith(raiz_agente):
        subcarpetas_ok = ["informes", "documentos_asistencia", "documentos_sanji", "data", "skills", ".agents", "_agents"]
        sub = ruta_norm[len(raiz_agente):].lstrip("/")
        primera = sub.split("/")[0] if "/" in sub else sub
        if primera in subcarpetas_ok:
            return True, ruta_str
        return False, ""

    return False, ""


def _msg_hard_stop(ruta: str) -> str:
    return (
        f"HARD STOP — Escritura bloqueada en ruta no autorizada: {ruta}\n"
        f"Rutas de escritura permitidas para {_AGENTE}:\n"
        f"  /app/{_AGENTE}/informes/                  → entregables e informes de asistencia\n"
        f"  /app/{_AGENTE}/documentos_asistencia/      → documentos e informes oficiales de asistencia\n"
        f"  /app/{_AGENTE}/documentos_sanji/          → documentos generados (compatibilidad)\n"
        f"  /app/Archivos_temporales/                 → archivos temporales (usa prefijo asistencia_ o sanji_)\n"
        f"  /app/Bitacora.md                          → actualizar estado de tickets\n"
    )


@tool
def crear_archivo(ruta_absoluta: str, contenido: str) -> str:
    """
    Crea o sobreescribe un archivo con el contenido dado.
    Solo puede escribir en las rutas autorizadas del agente.
    """
    # Limpiar links relativos que contaminan el grafo de Obsidian
    contenido = re.sub(r"\[([^\]]+)\]\((?:\.\./|\./)(?:[^)]+)\)", r"\1", contenido)

    # BLINDAJE: Cerebro.md solo via herramienta oficial
    if "Cerebro.md" in ruta_absoluta:
        return json.dumps({
            "status": "error",
            "mensaje": "PROHIBIDO escribir manualmente en Cerebro.md. Usa tool_guardar_solucion para registrar conocimiento."
        }, ensure_ascii=False)

    es_valida, ruta_corregida = _ruta_es_valida(ruta_absoluta)
    if not es_valida:
        return json.dumps({
            "status": "error",
            "mensaje": _msg_hard_stop(ruta_absoluta)
        }, ensure_ascii=False)

    ruta_final = ruta_corregida or ruta_absoluta

    try:
        p = Path(ruta_final)
        p.parent.mkdir(parents=True, exist_ok=True)

        # Auto-enlace a Obsidian si es markdown y no lo tiene
        if p.suffix == ".md" and "**Pertenece a:**" not in contenido:
            # Enlazar a perfil canónico
            conexion = f"\n\n---\n**Pertenece a:** [[Perfil_{_AGENTE}]]\n"
            contenido = contenido.rstrip() + conexion

        p.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "mensaje": f"Archivo creado exitosamente en {ruta_final}",
            "ruta": str(p),
            "bytes_escritos": len(contenido.encode("utf-8"))
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def leer_archivo(ruta_absoluta: str) -> str:
    """
    Lee y devuelve el contenido de un archivo en texto plano.
    Aplica censura de metadatos de grafo para evitar alucinaciones.
    """
    try:
        p = Path(ruta_absoluta)
        if not p.is_file():
            return json.dumps({"status": "error", "mensaje": f"El archivo '{ruta_absoluta}' no existe."}, ensure_ascii=False)

        texto = p.read_text(encoding="utf-8", errors="replace")

        # Censura anti-alucinación: remover líneas de metadatos de grafo
        lineas_limpias = []
        for linea in texto.splitlines():
            if re.match(r"^\s*-\s*\[\[.+\]\]", linea) or re.match(r"^\s*\*\*Conexiones:\*\*", linea):
                continue
            lineas_limpias.append(linea)

        texto_limpio = "\n".join(lineas_limpias)

        # Paginación de seguridad para proteger contexto
        max_chars = 8000
        if len(texto_limpio) > max_chars:
            texto_limpio = texto_limpio[:max_chars] + f"\n\n[... Truncado a {max_chars} caracteres para proteger contexto ...]"

        return json.dumps({
            "status": "success",
            "ruta": str(p),
            "total_lineas": len(lineas_limpias),
            "contenido": texto_limpio
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def listar_directorio(ruta_absoluta: str) -> str:
    """
    Lista el contenido de un directorio con indicación de tipo y tamaño.
    """
    try:
        p = Path(ruta_absoluta)
        if not p.is_dir():
            return json.dumps({"status": "error", "mensaje": f"'{ruta_absoluta}' no es un directorio válido."}, ensure_ascii=False)

        items = []
        for item in sorted(p.iterdir()):
            tipo = "directorio" if item.is_dir() else "archivo"
            tamano = item.stat().st_size if item.is_file() else None
            items.append({"nombre": item.name, "tipo": tipo, "bytes": tamano})

        return json.dumps({
            "status": "success",
            "directorio": str(p),
            "total_elementos": len(items),
            "elementos": items
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


_COMANDOS_BLOQUEADOS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\bformat\b",
    r"\bmkfs\b",
    r"\bdel\s+/[fq]\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bdd\b"
]

_COMANDOS_AUTORIZADOS = [
    "python", "python3", "pip", "pip3", "node", "npm", "npx",
    "git", "docker", "ls", "dir", "cat", "type", "mkdir", "echo"
]


@tool
def ejecutar_comando(comando: str, directorio: Optional[str] = None) -> str:
    """
    Ejecuta un comando en la shell del sistema con validación de seguridad y timeout.
    Solo permite comandos dentro de la lista blanca autorizada.
    """
    # 1. Comprobar comandos destructivos
    for patron in _COMANDOS_BLOQUEADOS:
        if re.search(patron, comando, re.IGNORECASE):
            return json.dumps({
                "status": "error",
                "mensaje": f"FIREWALL CRÍTICO: Comando bloqueado por regla de seguridad destructiva: {comando}"
            }, ensure_ascii=False)

    # 2. Comprobar binario en lista blanca
    binario = comando.strip().split()[0].lower() if comando.strip() else ""
    binario_limpio = Path(binario).stem.lower()

    if binario_limpio not in _COMANDOS_AUTORIZADOS and binario not in _COMANDOS_AUTORIZADOS:
        return json.dumps({
            "status": "error",
            "mensaje": f"FIREWALL: Binario '{binario}' no autorizado. Binarios permitidos: {', '.join(_COMANDOS_AUTORIZADOS)}"
        }, ensure_ascii=False)

    cwd = directorio if directorio and Path(directorio).is_dir() else str(_APP_ROOT)

    try:
        proc = subprocess.run(
            comando,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace"
        )
        return json.dumps({
            "status": "success",
            "codigo_retorno": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "mensaje": "Timeout: El comando superó el límite de 120 segundos."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


__all__ = ["crear_archivo", "leer_archivo", "listar_directorio", "ejecutar_comando", "obtener_prompt_base"]
