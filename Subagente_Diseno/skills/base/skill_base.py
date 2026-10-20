"""
skill_base.py — Habilidades Base: Sistema de Archivos y Comandos de Shell Seguro
================================================================================
Herramientas fundamentales de entrada/salida (I/O) y ejecución de procesos
para el Subagente de Diseño (Nami).
Validación unificada: Firewall determinístico + Auto-enlazador Obsidian + Anti-alucinación.

Herramientas disponibles:
  - crear_archivo      : Crear/sobrescribir archivos con control de firewall
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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_AGENTE = "Subagente_Diseno"

# Directorios de trabajo y salida autorizados
_INFORMES = _APP_ROOT / _AGENTE / "informes"
_TEMP = _APP_ROOT / "Archivos_temporales"
_MEMORIA = _APP_ROOT / "memoria"

# Asegurar existencia de carpetas clave
_INFORMES.mkdir(parents=True, exist_ok=True)
_TEMP.mkdir(parents=True, exist_ok=True)


def obtener_prompt_base() -> str:
    """
    Retorna el System Prompt especializado para las operaciones base de sistema de archivos
    y ejecución de comandos de terminal del Subagente de Diseño.
    """
    return """[🛑 HARD-STOP: MODO OPERACIONES BASE Y ARCHIVOS SEGUROS ACTIVO 🛑]
Eres el Operador de Infraestructura y Gestión de Archivos del Subagente de Diseño.
Tu misión es gestionar lecturas, escrituras, prototipos visuales y ejecución de comandos con rigor técnico, respetando el firewall determinístico y garantizando que los entregables se almacenen en los directorios oficiales.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida su existencia o la de sus directorios contenedores usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y ZONAS SEGURAS:
   - Entregables, Prototipos HTML y Diseños: `/app/Subagente_Diseno/informes/`.
   - Archivos Temporales / Scratch: `/app/Archivos_temporales/` (obligatorio prefijo `diseno_` o `nami_`).
   - Bitácora de Tareas: `/app/Bitacora.md` (única fuente de verdad para actualizar estados y tickets).
   - Tienes terminantemente prohibido ejecutar comandos destructivos (`rm -rf`, `del /f`, `format`, `shutdown`, `drop table`, etc.).
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - NUNCA escribas manualmente en `Cerebro.md` ni en `memoria/`. El conocimiento procedural se registra a través de las herramientas de auto-aprendizaje autorizadas.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil correspondiente (`[[Perfil_Subagente_Diseno]]`).
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos extensos de código o diseño, el contenido se censura de metadatos de grafo y se pagina a un máximo de 12,000 caracteres para evitar desbordamiento de contexto.
"""


def _normalizar(ruta: str) -> str:
    return str(Path(ruta).resolve()).replace("\\", "/")


def _ruta_es_valida(ruta_str: str) -> tuple[bool, str]:
    try:
        p = Path(ruta_str).resolve()
        norm = str(p).replace("\\", "/")
        root_norm = str(_APP_ROOT.resolve()).replace("\\", "/")

        if not norm.startswith(root_norm) and not norm.startswith("/app"):
            return False, f"Ruta fuera del espacio de trabajo permitido: {ruta_str}"

        partes = [parte.lower() for parte in p.parts]
        for bloqueada in [".git", "venv", ".venv", "node_modules"]:
            if bloqueada in partes:
                return False, f"Acceso denegado a directorio protegido: {bloqueada}"

        return True, norm
    except Exception as e:
        return False, f"Error validando ruta: {str(e)}"


# SEC-H04: Lista blanca determinística de binarios permitidos
_BINARIOS_PERMITIDOS = [
    "python", "python3", "pip", "pip3", "node", "npm", "npx",
    "git", "docker", "ls", "dir", "cat", "type", "mkdir", "echo",
    "grep", "find", "rg", "findstr"
]


# ─── SEC-H04: Utilidades de saneamiento de comandos (shell=False) ─────────────
_OPERADORES_SHELL_PROHIBIDOS = (
    "&&", "||", ";", "|", "`", "$(", "${", ">", "<", "&>", ">>",
)


def _tokenizar_comando_seguro(comando: str, binarios_permitidos) -> list:
    """
    Tokeniza un comando en una lista de argumentos SIN invocar una shell.

    Raises:
        ValueError: si el comando contiene operadores de shell o un binario
                    fuera de la lista blanca.
    """
    import shlex

    if not isinstance(comando, str) or not comando.strip():
        raise ValueError("Comando vacío o inválido.")

    for op in _OPERADORES_SHELL_PROHIBIDOS:
        if op in comando:
            raise ValueError(
                f"Operador de shell '{op}' no permitido (ejecución sin shell intermedio). "
                "Emite un único comando por invocación."
            )

    try:
        argv = shlex.split(comando, posix=True)
    except ValueError as e:
        raise ValueError(f"Comando no tokenizable de forma segura: {e}")

    if not argv:
        raise ValueError("Comando vacío tras tokenizar.")

    binario = Path(argv[0]).name.lower()
    if binario.endswith(".exe"):
        binario = binario[:-4]

    permitidos = {str(b).lower() for b in binarios_permitidos}
    if binario not in permitidos:
        raise ValueError(
            f"Binario '{binario}' no autorizado. Permitidos: {', '.join(sorted(permitidos))}"
        )

    return argv


def _validar_directorio_trabajo(directorio, raiz) -> str:
    """Confina el directorio de trabajo a la raíz del proyecto."""
    raiz_p = Path(raiz).resolve()
    try:
        candidato = Path(directorio).resolve() if directorio else raiz_p
    except Exception:
        return str(raiz_p)
    try:
        candidato.relative_to(raiz_p)
    except ValueError:
        return str(raiz_p)
    return str(candidato) if candidato.is_dir() else str(raiz_p)
# ─────────────────────────────────────────────────────────────────────────────


@tool
def crear_archivo(ruta: str, contenido: str) -> str:
    """
    Crea o sobrescribe un archivo con control de firewall determinístico.
    Inyecta automáticamente enlaces bidireccionales de Obsidian si es Markdown.
    """
    try:
        # Redirigir si intenta escribir en la raíz del agente
        p_obj = Path(ruta)
        nombre_archivo = p_obj.name
        
        # Validación de ruta
        es_valida, ruta_norm = _ruta_es_valida(ruta)
        if not es_valida:
            # Fallback seguro a informes
            p_obj = _INFORMES / nombre_archivo
            ruta_norm = str(p_obj).replace("\\", "/")

        destino = Path(ruta_norm)
        destino.parent.mkdir(parents=True, exist_ok=True)

        # Enlazador Obsidian automático canónico para Markdown
        if destino.suffix.lower() == ".md":
            try:
                if str(_APP_ROOT / "Agente_Orquestador") not in sys.path:
                    sys.path.insert(0, str(_APP_ROOT / "Agente_Orquestador"))
                from sync_cerebro import formatear_md_canonico
                contenido = formatear_md_canonico(destino, contenido)
            except Exception:
                pass

        destino.write_text(contenido, encoding="utf-8")
        bytes_escritos = len(contenido.encode("utf-8"))
        return json.dumps({
            "status": "success",
            "mensaje": f"Archivo creado exitosamente en {ruta_norm}",
            "bytes": bytes_escritos,
            "ruta": ruta_norm
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al crear archivo: {str(e)}"}, ensure_ascii=False)


@tool
def leer_archivo(ruta: str, limite_caracteres: int = 12000) -> str:
    """
    Lee un archivo del sistema con censura anti-alucinación de enlaces Obsidian.
    Limita la lectura a 12,000 caracteres por defecto para evitar sobrecarga de contexto.
    """
    try:
        p = Path(ruta)
        if not p.is_absolute():
            # Buscar en informes o workspace
            if (_INFORMES / ruta).exists():
                p = _INFORMES / ruta
            elif (_APP_ROOT / ruta).exists():
                p = _APP_ROOT / ruta

        if not p.exists():
            return json.dumps({"status": "error", "mensaje": f"Archivo no encontrado: {ruta}"}, ensure_ascii=False)

        texto = p.read_text(encoding="utf-8", errors="replace")
        total_chars = len(texto)

        # Truncar si excede el límite
        truncado = False
        if total_chars > limite_caracteres:
            texto = texto[:limite_caracteres]
            truncado = True

        # Censura anti-alucinación de frontmatter complejo
        texto_limpio = re.sub(r"^---\n[\s\S]*?\n---\n", "", texto)

        return json.dumps({
            "status": "success",
            "ruta": str(p).replace("\\", "/"),
            "contenido": texto_limpio,
            "caracteres_totales": total_chars,
            "truncado": truncado
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al leer archivo: {str(e)}"}, ensure_ascii=False)


@tool
def listar_directorio(ruta: str = ".") -> str:
    """
    Explora la estructura de carpetas y archivos en una ruta dada.
    Retorna nombres, tamaños y tipo (archivo/directorio).
    """
    try:
        p = Path(ruta)
        if not p.is_absolute():
            if ruta in [".", "./"]:
                p = _APP_ROOT / _AGENTE
            else:
                p = _APP_ROOT / ruta

        if not p.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta}"}, ensure_ascii=False)

        elementos = []
        for item in sorted(p.iterdir()):
            if item.name in [".git", "__pycache__", "node_modules", ".venv", "venv"]:
                continue
            elementos.append({
                "nombre": item.name,
                "es_directorio": item.is_dir(),
                "tamano_bytes": item.stat().st_size if item.is_file() else None
            })

        return json.dumps({
            "status": "success",
            "directorio": str(p).replace("\\", "/"),
            "total_elementos": len(elementos),
            "elementos": elementos
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al listar directorio: {str(e)}"}, ensure_ascii=False)


@tool
def ejecutar_comando(comando: str) -> str:
    """
    Ejecuta un comando de consola con lista blanca de seguridad y timeout estricto de 45 segundos.
    Comandos bloqueados: operaciones de borrado masivo, formateo y manipulación no autorizada.
    """
    try:
        # Comandos prohibidos
        prohibidos = [
            "rm -rf", "del /f", "format", "mkfs", "shutdown", "reboot",
            "drop database", "drop table", "truncate", "git push --force"
        ]
        cmd_lower = comando.lower().strip()
        for p in prohibidos:
            if p in cmd_lower:
                return json.dumps({
                    "status": "bloqueado",
                    "mensaje": f"Comando bloqueado por firewall determinístico: contiene '{p}'."
                }, ensure_ascii=False)

        # SEC-H04: tokenización segura + ejecución SIN shell intermedio
        try:
            argv = _tokenizar_comando_seguro(comando, _BINARIOS_PERMITIDOS)
        except ValueError as e:
            return json.dumps({
                "status": "bloqueado",
                "mensaje": f"FIREWALL SEC-H04: {e}"
            }, ensure_ascii=False)

        resultado = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(_APP_ROOT / _AGENTE)
        )

        return json.dumps({
            "status": "success" if resultado.returncode == 0 else "error",
            "codigo_salida": resultado.returncode,
            "stdout": resultado.stdout.strip()[:4000],
            "stderr": resultado.stderr.strip()[:2000]
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "mensaje": "Comando excedió el tiempo límite de 45 segundos."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo ejecutando comando: {str(e)}"}, ensure_ascii=False)


HERRAMIENTAS_BASE = [
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando
]
