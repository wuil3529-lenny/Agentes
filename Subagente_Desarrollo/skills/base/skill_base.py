"""
skill_base.py — Habilidades Base: Sistema de Archivos y Comandos de Shell
==========================================================================
Herramientas fundamentales de entrada/salida (I/O) y ejecución de procesos
para el Subagente de Desarrollo.
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
from typing import Optional, Dict, Any, List, Tuple
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"

# Directorios de trabajo y salida
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"
_SKILLS = _APP_ROOT / _AGENTE / "skills"
_TEMP = _APP_ROOT / "Archivos_temporales"
_MEMORIA = _APP_ROOT / "memoria"

# Asegurar existencia de carpetas clave
_PROYECTOS.mkdir(parents=True, exist_ok=True)
_SKILLS.mkdir(parents=True, exist_ok=True)
_TEMP.mkdir(parents=True, exist_ok=True)


def obtener_prompt_base() -> str:
    """
    System Prompt especializado y encapsulado para las operaciones base de sistema de archivos
    y ejecución de comandos de terminal del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO OPERACIONES BASE DE SISTEMA Y ARCHIVOS ACTIVO 🛑]
Eres el Operador de Infraestructura y Sistema de Archivos del Subagente de Desarrollo.
Tu misión es gestionar lecturas, escrituras de código, exploración de directorios y ejecución de procesos en el sistema operativo con máxima precisión técnica, respetando el firewall determinístico y garantizando que todo código y proyecto generado sea funcional y persistente.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida la existencia del directorio contenedor usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y ZONAS SEGURAS DE DESARROLLO:
   - Proyectos de Software y Código: `/app/Subagente_Desarrollo/proyectos/` (directorio canónico de desarrollo).
   - Habilidades y Herramientas: `/app/Subagente_Desarrollo/skills/` (únicamente para mantenimiento y extensión autorizada de skills).
   - Archivos Temporales / Scratch / Compilaciones intermedias: `/app/Archivos_temporales/` (obligatorio prefijo `desarrollo_`).
   - Bitácora de Tareas: `/app/Bitacora.md` (actualización de estados de tickets asignados).
   - Tienes terminantemente prohibido ejecutar comandos destructivos (`rm -rf`, `del /f`, `format`, `shutdown`, `drop database`, etc.).
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - NUNCA escribas manualmente en `Cerebro.md` ni en `memoria/`. El conocimiento se registra a través de las herramientas de aprendizaje autorizadas.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil correspondiente (`[[proyectos]]` o `[[Perfil_Subagente_Desarrollo]]`).
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos de código fuente grandes, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina para evitar saturar la ventana de contexto.
"""


def _normalizar(ruta: str) -> str:
    return str(Path(ruta).resolve()).replace("\\", "/")


def _ruta_es_valida(ruta_str: str) -> Tuple[bool, str]:
    """
    Verifica si la ruta es una zona de escritura autorizada para Subagente_Desarrollo.
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

    # Compatibilidad con alias legacy 'Zoro'
    raiz_legacy = _normalizar(str(_APP_ROOT / "Zoro"))
    if ruta_norm.startswith(raiz_legacy):
        ruta_corregida = ruta_norm.replace(raiz_legacy, raiz_agente)
        return _ruta_es_valida(ruta_corregida)

    # Zonas válidas directas
    zonas_validas = [
        _normalizar(str(_PROYECTOS)),
        _normalizar(str(_SKILLS)),
        temp_global,
        _normalizar(str(_APP_ROOT / "Bitacora.md")),
    ]
    for zona in zonas_validas:
        if ruta_norm.startswith(zona):
            return True, ruta_str

    # Zona raíz del agente: solo permitida si es una subcarpeta autorizada
    if ruta_norm.startswith(raiz_agente):
        subcarpetas_ok = ["proyectos", "skills", ".agents", "_agents"]
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
        f"  /app/{_AGENTE}/proyectos/  → proyectos de desarrollo y entregables\n"
        f"  /app/{_AGENTE}/skills/     → mantenimiento de herramientas y skills\n"
        f"  /app/Archivos_temporales/  → archivos temporales (usa prefijo desarrollo_)\n"
        f"  /app/Bitacora.md           → actualizar estado de tickets asignados\n"
    )


@tool
def crear_archivo(ruta_absoluta: str, contenido: str) -> str:
    """
    Crea o sobreescribe un archivo en disco con el contenido dado.
    Solo puede escribir en las rutas autorizadas del Subagente de Desarrollo.

    Args:
        ruta_absoluta: Ruta completa del archivo a crear (ej: /app/Subagente_Desarrollo/proyectos/mi_app/main.py).
        contenido: Contenido completo del archivo.
    """
    try:
        # Limpiar links relativos que contaminan el grafo de Obsidian
        contenido_limpio = re.sub(r"\[([^\]]+)\]\((?:\.\./|\./)(?:[^)]+)\)", r"\1", contenido)

        # BLINDAJE: Cerebro.md solo via herramientas RAG autorizadas
        if "Cerebro.md" in ruta_absoluta or "/memoria/" in ruta_absoluta.replace("\\", "/"):
            return json.dumps({
                "status": "error",
                "mensaje": "PROHIBIDO escribir manualmente en Cerebro.md o memoria/. Utiliza las herramientas autorizadas de aprendizaje."
            })

        es_valida, ruta_corregida = _ruta_es_valida(ruta_absoluta)
        if not es_valida:
            return json.dumps({
                "status": "error",
                "mensaje": _msg_hard_stop(ruta_absoluta)
            })

        ruta_final = ruta_corregida or ruta_absoluta
        ruta = Path(ruta_final)
        ruta.parent.mkdir(parents=True, exist_ok=True)

        # AUTO-ENLAZADOR OBSIDIAN para archivos Markdown
        ruta_str = str(ruta_final).replace("\\", "/")
        if ruta_str.endswith(".md"):
            contenido_limpio = re.sub(r"(?im)^\s*\*\*(Pertenece a|Conexiones):\*\*.*\n?", "", contenido_limpio).strip()
            enlace_fuerte = None
            if "/Archivos_temporales/" in ruta_str or ruta_str.endswith("/Archivos_temporales"):
                enlace_fuerte = "[[archivos_temporales]]"
            elif f"/{_AGENTE}/proyectos/" in ruta_str or ruta_str.endswith(f"/{_AGENTE}/proyectos"):
                enlace_fuerte = "[[proyectos]]"

            if enlace_fuerte:
                contenido_limpio += f"\n\n---\n**Pertenece a:** {enlace_fuerte}\n"

        ruta.write_text(contenido_limpio, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "archivo": str(ruta),
            "bytes_escritos": len(contenido_limpio.encode("utf-8"))
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def leer_archivo(ruta_absoluta: str) -> str:
    """
    Lee y retorna el contenido de un archivo en disco en codificación UTF-8.
    Filtra metadatos de Obsidian para evitar alucinaciones y desbordamiento de contexto.

    Args:
        ruta_absoluta: Ruta completa del archivo a leer.
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({
                "status": "error",
                "mensaje": f"Archivo no encontrado en disco: {ruta_absoluta}"
            })

        if ruta.is_dir():
            return json.dumps({
                "status": "error",
                "mensaje": f"La ruta especificada es un directorio, no un archivo: {ruta_absoluta}. Usa listar_directorio en su lugar."
            })

        contenido = ruta.read_text(encoding="utf-8", errors="replace")

        # Censura de metadatos de Obsidian para evitar confusión en el LLM
        contenido_filtrado = re.sub(r"(?m)^> \*\*Conexiones Core:\*\*.*\n?", "", contenido)
        contenido_filtrado = re.sub(r"(?m)^\*\*Pertenece a:\*\*.*\n?", "", contenido_filtrado)
        contenido_filtrado = re.sub(r"(?m)^\*\*Conexiones:\*\*.*\n?", "", contenido_filtrado)

        total_lineas = contenido_filtrado.count("\n") + 1
        return json.dumps({
            "status": "success",
            "archivo": str(ruta),
            "contenido": contenido_filtrado[:12000],
            "lineas": total_lineas,
            "truncado": len(contenido_filtrado) > 12000
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def listar_directorio(ruta_absoluta: str) -> str:
    """
    Explora y lista el contenido de un directorio en disco (archivos, subdirectorios y tamaños).

    Args:
        ruta_absoluta: Ruta completa del directorio a explorar.
    """
    try:
        # Auto-corrección: Archivos_temporales local -> global
        if "Archivos_temporales" in ruta_absoluta:
            temp_local = str(_APP_ROOT / _AGENTE / "Archivos_temporales")
            if _normalizar(ruta_absoluta).startswith(_normalizar(temp_local)):
                ruta_absoluta = str(_TEMP)

        # Compatibilidad con alias legacy 'Zoro'
        if "/Zoro" in ruta_absoluta.replace("\\", "/"):
            ruta_absoluta = ruta_absoluta.replace("/Zoro", f"/{_AGENTE}").replace("\\Zoro", f"\\{_AGENTE}")

        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({
                "status": "error",
                "mensaje": f"Directorio no encontrado: {ruta_absoluta}"
            })

        if not ruta.is_dir():
            return json.dumps({
                "status": "error",
                "mensaje": f"La ruta indicada es un archivo, no un directorio: {ruta_absoluta}. Usa leer_archivo."
            })

        items = []
        for item in sorted(ruta.iterdir()):
            items.append({
                "nombre": item.name,
                "tipo": "directorio" if item.is_dir() else "archivo",
                "bytes": item.stat().st_size if item.is_file() else None
            })

        return json.dumps({
            "status": "success",
            "ruta": str(ruta),
            "total": len(items),
            "items": items
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def ejecutar_comando(comando: str, directorio: str) -> str:
    """
    Ejecuta un comando de shell o proceso en el directorio de trabajo especificado.
    Incorpora firewall preventivo contra comandos destructivos y control de timeout.

    Args:
        comando: Comando a ejecutar (ej: 'python -m pytest', 'git status', 'npm test').
        directorio: Directorio de trabajo donde se ejecutará el comando.
    """
    try:
        # Firewall contra comandos destructivos
        comandos_prohibidos = [
            "rm -rf /", "rm -rf /*", "del /f /s /q c:\\", "format ", "mkfs",
            ":(){ :|:& };:", "shutdown", "reboot", "drop database"
        ]
        cmd_lower = comando.lower().strip()
        for prohibido in comandos_prohibidos:
            if prohibido in cmd_lower:
                return json.dumps({
                    "status": "error",
                    "mensaje": f"Comando bloqueado por el firewall de seguridad del sistema: '{prohibido}' no está permitido."
                })

        dir_path = Path(directorio)
        if not dir_path.exists():
            return json.dumps({
                "status": "error",
                "mensaje": f"El directorio de ejecución no existe: {directorio}"
            })

        resultado = subprocess.run(
            comando,
            shell=True,
            cwd=str(dir_path),
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace"
        )

        return json.dumps({
            "status": "success" if resultado.returncode == 0 else "warning",
            "codigo_retorno": resultado.returncode,
            "stdout": resultado.stdout[:4000],
            "stderr": resultado.stderr[:2000]
        })
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "mensaje": "Timeout: el comando superó los 300 segundos de ejecución. Divide la tarea o ejecuta con parámetros no interactivos."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_BASE = [
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando
]
