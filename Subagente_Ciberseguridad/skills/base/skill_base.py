"""
skill_base.py — Habilidades Base: Sistema de Archivos y Comandos de Shell Seguro
================================================================================
Herramientas fundamentales de entrada/salida (I/O) y ejecución de procesos
para el Subagente de Ciberseguridad.
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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["robin", "subagente_ciberseguridad"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Ciberseguridad"

# Directorios de trabajo y salida autorizados
_REPORTES = _APP_ROOT / _AGENTE / "reportes"
_INFORMES = _APP_ROOT / _AGENTE / "informes"
_TEMP = _APP_ROOT / "Archivos_temporales"
_MEMORIA = _APP_ROOT / "memoria"

# Asegurar existencia de carpetas clave
_REPORTES.mkdir(parents=True, exist_ok=True)
_INFORMES.mkdir(parents=True, exist_ok=True)
_TEMP.mkdir(parents=True, exist_ok=True)


def obtener_prompt_base() -> str:
    """
    System Prompt especializado y encapsulado para las operaciones base de sistema de archivos
    y ejecución de comandos de terminal del Subagente de Ciberseguridad.
    """
    return """[🛑 HARD-STOP: MODO OPERACIONES BASE Y ARCHIVOS SEGUROS ACTIVO 🛑]
Eres el Operador de Infraestructura y Acceso Seguro del Subagente de Ciberseguridad.
Tu misión es gestionar lecturas, escrituras, exploración de directorios y ejecución de procesos en el sistema operativo con rigor técnico absoluto, respetando el firewall determinístico y previniendo la corrupción de datos o la sobrecarga de contexto.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida su existencia o la de sus directorios contenedores usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y ZONAS SEGURAS:
   - Reportes e Informes de Seguridad: `/app/Subagente_Ciberseguridad/reportes/` o `/app/Subagente_Ciberseguridad/informes/`.
   - Archivos Temporales / Scratch: `/app/Archivos_temporales/` (obligatorio prefijo `ciberseguridad_` o `robin_`).
   - Bitácora de Tareas: `/app/Bitacora.md` (única fuente de verdad para actualizar estados y tickets).
   - Tienes terminantemente prohibido ejecutar comandos destructivos (`rm -rf`, `del /f`, `format`, `shutdown`, `drop table`, etc.).
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - NUNCA escribas manualmente en `Cerebro.md` ni en `memoria/`. El conocimiento procedural se registra a través de las herramientas RAG y de auto-aprendizaje autorizadas.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil correspondiente (`[[Perfil_Subagente_Ciberseguridad]]`).
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos para auditoría, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina a un máximo de seguridad para no desbordar la ventana de contexto.
"""


def _normalizar(ruta: str) -> str:
    return str(Path(ruta).resolve()).replace("\\", "/")


def _ruta_es_valida(ruta_str: str) -> tuple[bool, str]:
    """
    Verifica si la ruta es una zona de escritura autorizada para Ciberseguridad.
    Retorna (es_valida, ruta_corregida).
    """
    ruta = Path(ruta_str).resolve()
    ruta_norm = _normalizar(str(ruta))

    # Bitácora (SSOT)
    if ruta_norm.endswith("bitacora.md"):
        return True, str(_APP_ROOT / "Bitacora.md")

    # Rutas autorizadas de entregables
    zonas_validas = [
        _normalizar(str(_REPORTES)),
        _normalizar(str(_INFORMES)),
        _normalizar(str(_TEMP)),
    ]

    for zona in zonas_validas:
        if ruta_norm.startswith(zona):
            return True, str(ruta)

    # Si intenta escribir en la habitación del agente pero fuera de reportes/informes, redirigir a reportes
    habitacion = _normalizar(str(_APP_ROOT / _AGENTE))
    if ruta_norm.startswith(habitacion):
        archivo_nombre = ruta.name
        ruta_corregida = str(_REPORTES / archivo_nombre)
        print(f"[Ciberseguridad Firewall] Redirigiendo escritura interna a: {ruta_corregida}")
        return True, ruta_corregida

    # Si es un temporal suelto, redirigir a Archivos_temporales con prefijo
    nombre_archivo = ruta.name
    if not (nombre_archivo.startswith("ciberseguridad_") or nombre_archivo.startswith("robin_")):
        nombre_archivo = f"ciberseguridad_{nombre_archivo}"
    ruta_corregida = str(_TEMP / nombre_archivo)
    print(f"[Ciberseguridad Firewall] Redirigiendo escritura externa a Archivos_temporales: {ruta_corregida}")
    return True, ruta_corregida


def _inyectar_enlaces_obsidian(contenido: str, ruta_archivo: Path) -> str:
    """Inyecta enlaces limpios de Obsidian respetando la topología canónica."""
    if not str(ruta_archivo).endswith(".md"):
        return contenido
    try:
        if str(_APP_ROOT / "Agente_Orquestador") not in sys.path:
            sys.path.insert(0, str(_APP_ROOT / "Agente_Orquestador"))
        from sync_cerebro import formatear_md_canonico
        return formatear_md_canonico(ruta_archivo, contenido)
    except Exception:
        return contenido


def _limpiar_metadatos_obsidian(texto: str) -> str:
    """Elimina metadatos de Obsidian que confunden al LLM."""
    texto = re.sub(r"> 🔗 \*\*Nexo:\*\*.*?\n", "", texto)
    texto = re.sub(r"\n---\n\*\*Conexiones:\*\*.*?\n", "\n", texto)
    return texto


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS CANÓNICAS BASE
# ══════════════════════════════════════════════════════════════════════════════

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
    Crea o sobrescribe un archivo en el sistema validando permisos con el firewall.
    Ubicaciones autorizadas:
      - /app/Subagente_Ciberseguridad/reportes/
      - /app/Subagente_Ciberseguridad/informes/
      - /app/Archivos_temporales/ (prefijo ciberseguridad_ o robin_)
      - /app/Bitacora.md
    """
    try:
        valida, ruta_final = _ruta_es_valida(ruta)
        p = Path(ruta_final)
        p.parent.mkdir(parents=True, exist_ok=True)

        contenido_final = _inyectar_enlaces_obsidian(contenido, p)
        p.write_text(contenido_final, encoding="utf-8")

        return f"Archivo creado exitosamente en: {ruta_final} ({len(contenido_final)} caracteres)"
    except Exception as e:
        return f"Error al crear archivo {ruta}: {str(e)}"


@tool
def leer_archivo(ruta: str) -> str:
    """
    Lee el contenido de un archivo en texto plano con manejo robusto UTF-8.
    Censura metadatos de Obsidian y trunca archivos excesivamente grandes para proteger el contexto.
    """
    try:
        p = Path(ruta).resolve()
        if not p.exists():
            # Buscar en ubicaciones relativas a la raíz
            p_alt = _APP_ROOT / ruta.lstrip("/\\")
            if p_alt.exists():
                p = p_alt
            else:
                return f"Error: El archivo no existe en la ruta especificada: {ruta}"

        if p.is_dir():
            return f"Error: La ruta especificada es un directorio, no un archivo: {ruta}"

        contenido = p.read_text(encoding="utf-8", errors="replace")
        contenido_limpio = _limpiar_metadatos_obsidian(contenido)

        MAX_CHARS = 12000
        if len(contenido_limpio) > MAX_CHARS:
            resumen = f"\n\n[... CONTENIDO TRUNCADO POR TAMAÑO: Mostrando primeros {MAX_CHARS} de {len(contenido_limpio)} caracteres ...]"
            return contenido_limpio[:MAX_CHARS] + resumen

        return contenido_limpio
    except Exception as e:
        return f"Error al leer archivo {ruta}: {str(e)}"


@tool
def listar_directorio(ruta: str = ".") -> str:
    """
    Inspecciona la estructura de un directorio mostrando archivos y subcarpetas con sus tamaños.
    """
    try:
        p = Path(ruta).resolve()
        if not p.exists():
            p_alt = _APP_ROOT / ruta.lstrip("/\\")
            if p_alt.exists():
                p = p_alt
            else:
                return f"Error: El directorio no existe: {ruta}"

        if not p.is_dir():
            return f"Error: La ruta especificada no es un directorio: {ruta}"

        items = []
        for item in sorted(p.iterdir()):
            if item.name.startswith(".") and item.name not in [".agents", ".env"]:
                continue
            if item.name == "__pycache__":
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size_kb = item.stat().st_size / 1024
                items.append(f"📄 {item.name} ({size_kb:.1f} KB)")

        return f"Contenido de {p}:\n" + "\n".join(items) if items else f"El directorio {p} está vacío."
    except Exception as e:
        return f"Error al listar directorio {ruta}: {str(e)}"


@tool
def ejecutar_comando(comando: str) -> str:
    """
    Ejecuta comandos de shell en un entorno seguro y controlado.
    Comandos destructivos como 'rm -rf', 'del /f', 'format' están estrictamente bloqueados por firewall.
    """
    comandos_prohibidos = [
        "rm -rf", "del /f", "del /s", "format", "shutdown", "reboot",
        "drop database", "drop table", "mkfs", ":(){ :|:& };:"
    ]
    comando_lower = comando.lower()
    for prohibido in comandos_prohibidos:
        if prohibido in comando_lower:
            return f"Error de Seguridad [HS-01]: El comando '{comando}' contiene patrones destructivos bloqueados."

    # SEC-H04: tokenización segura + ejecución SIN shell intermedio
    try:
        argv = _tokenizar_comando_seguro(comando, _BINARIOS_PERMITIDOS)
    except ValueError as e:
        return f"Error de Seguridad [SEC-H04]: {e}"

    try:
        res = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(_APP_ROOT),
            encoding="utf-8",
            errors="replace"
        )
        salida = res.stdout.strip()
        errores = res.stderr.strip()

        resultado = f"Exit code: {res.returncode}\n"
        if salida:
            resultado += f"STDOUT:\n{salida[:3000]}\n"
        if errores:
            resultado += f"STDERR:\n{errores[:1500]}\n"

        return resultado.strip()
    except subprocess.TimeoutExpired:
        return "Error: El comando superó el tiempo límite de ejecución (45s)."
    except Exception as e:
        return f"Error al ejecutar comando: {str(e)}"
