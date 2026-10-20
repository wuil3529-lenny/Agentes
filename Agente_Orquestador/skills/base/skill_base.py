"""
skill_base.py — Habilidades Base: Sistema de Archivos y Comandos de Shell
==========================================================================
Herramientas fundamentales de entrada/salida (I/O) y ejecución de procesos
para el Agente Orquestador y los subagentes del ecosistema.

Herramientas disponibles:
  - crear_archivo      : Crear/sobreescribir cualquier archivo con control de firewall
  - leer_archivo       : Leer contenido con censura de metadatos Obsidian (anti-alucinación)
  - listar_directorio  : Explorar la estructura de carpetas y tamaños de archivos
  - ejecutar_comando   : Ejecutar comandos de shell con lista blanca y timeout seguro

SEC-H04 (Remediación): `ejecutar_comando` ya NO usa `shell=True`. El comando se
tokeniza con `shlex.split()` y se ejecuta con `shell=False` sobre una lista de
argumentos, eliminando la superficie de inyección de comandos (RCE) por
interpolación de variables. Se conserva el firewall determinístico de lista
blanca y bloqueo de comandos destructivos.
"""

import os
import sys
import re
import json
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["luffy", "agente_orquestador"] else _CURRENT.parents[2]


def obtener_prompt_base() -> str:
    """
    System Prompt especializado y encapsulado para las operaciones base de sistema de archivos
    y ejecución de comandos de terminal.
    """
    return """[🛑 HARD-STOP: MODO OPERACIONES BASE DE SISTEMA Y COMANDOS ACTIVO 🛑]
Eres el Operador de Infraestructura y Sistema de Archivos de la tripulación de agentes.
Tu misión es gestionar lecturas, escrituras, exploración de directorios y ejecución de procesos en el sistema operativo con rigor técnico, respetando el firewall determinístico y previniendo la corrupción de datos o la saturación de contexto.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida su existencia o la de sus directorios contenedores usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y REGLAS DE SEGURIDAD:
   - Tienes terminantemente prohibido ejecutar comandos destructivos de sistema (rm -rf, del /f, format, mkfs, shutdown, etc.).
   - Solo ejecuta comandos en la lista blanca de herramientas autorizadas (npm, pip, python, git, docker, ls, cat, etc.).
   - Respeta el timeout máximo de 120 segundos por comando.
   - SEC-H04: La ejecución es SIN shell intermedio (`shell=False`). No uses operadores de shell
     (`&&`, `||`, `;`, `|`, `>`, `$()`, backticks). Emite UN comando por invocación.
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - Nunca escribas manualmente en Cerebro.md. El conocimiento estructurado debe registrarse mediante las herramientas RAG oficiales.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil o carpeta correspondiente.
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina a un máximo de seguridad para no desbordar la ventana de contexto del modelo.
"""


# ─── SEC-H04: Utilidades de saneamiento de comandos ────────────────────────────
# Operadores de shell que solo tienen sentido con shell=True. Su presencia es
# señal de intento de encadenamiento/inyección y se rechaza explícitamente.
_OPERADORES_SHELL_PROHIBIDOS = (
    "&&", "||", ";", "|", "`", "$(", "${", ">", "<", "&>", ">>",
)

# Binarios permitidos (lista blanca determinística)
_BINARIOS_PERMITIDOS = {
    "npm", "npx", "pip", "pip3", "python", "python3", "node", "flutter",
    "git", "docker", "ls", "dir", "cd", "echo", "cat", "type", "mkdir",
    "touch", "grep", "find", "findstr", "rg",
}

# Patrones destructivos (bloqueo duro, HS-01)
_PATRONES_DESTRUCTIVOS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\bdel\s+/[fsq]\b",
    r"\bchmod\s+-r\s+777\b",
    r"\bmkfs\b",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{\s*:\|:&\s*\};:",
]


def _tokenizar_comando_seguro(command: str) -> List[str]:
    """
    Tokeniza un comando en una lista de argumentos SIN invocar una shell.

    Raises:
        ValueError: si el comando contiene operadores de shell, metacaracteres
                    de expansión o no puede tokenizarse de forma segura.
    """
    if not isinstance(command, str) or not command.strip():
        raise ValueError("Comando vacío o inválido.")

    # 1. Rechazo de operadores de encadenamiento / redirección / sustitución
    for op in _OPERADORES_SHELL_PROHIBIDOS:
        if op in command:
            raise ValueError(
                f"Operador de shell '{op}' no permitido (ejecución sin shell intermedio). "
                "Emite un único comando por invocación."
            )

    # 2. Tokenización POSIX sin interpretación de shell
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as e:
        raise ValueError(f"Comando no tokenizable de forma segura: {e}")

    if not argv:
        raise ValueError("Comando vacío tras tokenizar.")

    # 3. Validación del binario base contra la lista blanca
    binario = Path(argv[0]).name.lower()
    if binario.endswith(".exe"):
        binario = binario[:-4]
    if binario not in _BINARIOS_PERMITIDOS:
        raise ValueError(
            f"Binario '{binario}' no está en la lista blanca de permitidos: "
            f"{', '.join(sorted(_BINARIOS_PERMITIDOS))}"
        )

    return argv


def _validar_directorio_trabajo(directorio: str) -> str:
    """
    Valida y normaliza el directorio de trabajo, confinándolo a la raíz del proyecto.
    """
    raiz = Path(_APP_ROOT).resolve()
    try:
        candidato = Path(directorio).resolve() if directorio else raiz
    except Exception:
        return str(raiz)

    # Confinamiento: el cwd debe estar dentro de la raíz del proyecto
    try:
        candidato.relative_to(raiz)
    except ValueError:
        return str(raiz)

    return str(candidato) if candidato.is_dir() else str(raiz)


@tool
def crear_archivo(ruta_absoluta: str, contenido: str) -> str:
    """
    Crea o sobreescribe un archivo con el contenido dado.
    Crea automáticamente los directorios padres si no existen.

    Args:
        ruta_absoluta: Ruta completa del archivo (ej: /app/proyectos/index.html)
        contenido: Contenido completo a escribir en el archivo
    """
    # Limpiar links relativos que contaminan el grafo de Obsidian
    contenido = re.sub(r'\[([^\]]+)\]\((?:\.\./|\./)[^)]+\)', r'\1', contenido)
    ruta_str = str(ruta_absoluta).replace(chr(92), '/')
    
    # Orquestador — tiene acceso de escritura amplio (Bitacora, memoria, etc.)
    # No aplica el firewall restrictivo de los subagentes
    rutas_permitidas = [
        str(_APP_ROOT / "Subagente_Desarrollo" / "proyectos").replace('\\', '/'),
        str(_APP_ROOT / "Subagente_Asistencia" / "documentos_sanji").replace('\\', '/'),
        str(_APP_ROOT / "Subagente_Ciberseguridad" / "reportes").replace('\\', '/'),
        str(_APP_ROOT / "Subagente_Diseno" / "informes").replace('\\', '/'),
        str(_APP_ROOT / "Agente_Orquestador" / "skills").replace('\\', '/'),
        str(_APP_ROOT / "Zoro" / "proyectos").replace('\\', '/'),
        str(_APP_ROOT / "Sanji" / "documentos_sanji").replace('\\', '/'),
        str(_APP_ROOT / "Robin" / "reportes").replace('\\', '/'),
        str(_APP_ROOT / "Nami" / "informes").replace('\\', '/'),
        str(_APP_ROOT / "Luffy" / "skills").replace('\\', '/'),
        str(_APP_ROOT / "Archivos_temporales").replace('\\', '/'),
        str(_APP_ROOT / "memoria").replace('\\', '/'),
        str(_APP_ROOT / "Bitacora.md").replace('\\', '/'),
        str(_APP_ROOT).replace('\\', '/'),  # Permite Bitacora.md y otros archivos raiz
        "/app/Bitacora.md",
        "/app/Archivos_temporales",
        "/app/memoria",
        "/app",
    ]
    
    es_valida = any(ruta_str.startswith(rp) for rp in rutas_permitidas)
    
    if "Cerebro.md" in ruta_str:
        raise Exception("PROHIBIDO escribir manualmente en Cerebro.md. Usa la herramienta 'tool_guardar_solucion' para registrar conocimiento.")

    if not es_valida:
        # Forzar a Archivos_temporales si intenta escribir fuera de zonas conocidas
        ruta_absoluta = os.path.join(str(_APP_ROOT / "Archivos_temporales"), os.path.basename(ruta_absoluta))
        
    try:
        ruta = Path(ruta_absoluta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        
        # --- AUTO-ENLAZADOR OBSIDIAN CANÓNICO ---
        if ruta_str.endswith(".md"):
            try:
                if str(_APP_ROOT / "Agente_Orquestador") not in sys.path:
                    sys.path.insert(0, str(_APP_ROOT / "Agente_Orquestador"))
                from sync_cerebro import formatear_md_canonico
                contenido = formatear_md_canonico(ruta, contenido)
            except Exception:
                pass
        # ----------------------------------------

        ruta.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "archivo": str(ruta),
            "bytes_escritos": len(contenido.encode("utf-8"))
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def leer_archivo(ruta_absoluta: str) -> str:
    """
    Lee y retorna el contenido completo de un archivo existente.

    Args:
        ruta_absoluta: Ruta completa del archivo a leer
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            # Fallback para reglas de la tripulación o protocolos
            nombre_archivo = ruta.name
            rutas_posibles = [
                _APP_ROOT / "protocolo" / nombre_archivo,
                _APP_ROOT / "memoria" / nombre_archivo,
                Path("/app/protocolo") / nombre_archivo,
                Path("/app/memoria") / nombre_archivo
            ]
            encontrado = False
            for rp in rutas_posibles:
                if rp.exists():
                    ruta = rp
                    encontrado = True
                    break
            if not encontrado:
                return json.dumps({"status": "error", "mensaje": f"Archivo no encontrado: {ruta_absoluta}"})
        
        contenido = ruta.read_text(encoding="utf-8")
        
        # --- CENSURA DE METADATA OBSIDIAN (Anti-Alucinacion) ---
        # Ocultamos los enlaces fisicos del grafo a los LLM para que no intenten parsearlos ni replicarlos erroneamente
        contenido = re.sub(r'(?m)^> \*\*Conexiones Core:\*\*.*\n?', '', contenido)
        contenido = re.sub(r'(?m)^\*\*Pertenece a:\*\*.*\n?', '', contenido)
        contenido = re.sub(r'(?m)^\*\*Conexiones:\*\*.*\n?', '', contenido)
        # -------------------------------------------------------
        return json.dumps({
            "status": "success",
            "archivo": str(ruta),
            "contenido": contenido[:8000],  # limit to prevent token blowup
            "lineas": contenido.count("\n") + 1
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def listar_directorio(ruta_absoluta: str) -> str:
    """
    Lista el contenido de un directorio mostrando archivos y carpetas con sus tamaños.

    Args:
        ruta_absoluta: Ruta del directorio a explorar
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta_absoluta}"})
        if not ruta.is_dir():
            return json.dumps({"status": "error", "mensaje": f"La ruta no es un directorio: {ruta_absoluta}"})

        items = []
        for item in sorted(ruta.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                if item.is_dir():
                    items.append({"nombre": item.name, "tipo": "carpeta", "tamano": "-"})
                else:
                    tam = item.stat().st_size
                    items.append({"nombre": item.name, "tipo": "archivo", "tamano": f"{tam} bytes"})
            except Exception:
                items.append({"nombre": item.name, "tipo": "desconocido", "tamano": "-"})

        return json.dumps({
            "status": "success",
            "directorio": str(ruta),
            "total": len(items),
            "contenido": items
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def ejecutar_comando(command: str, directorio: str) -> str:
    """
    Ejecuta un comando de shell en el directorio especificado.
    Soporta: npm, npx, pip, python, node, flutter, git, docker, etc.
    Timeout máximo: 120 segundos.

    SEC-H04: Ejecución SIN shell intermedio (`shell=False`) sobre una lista de
    argumentos tokenizada con `shlex.split()`. Los operadores de shell
    (`&&`, `||`, `;`, `|`, `>`, `$()`, backticks) son rechazados.

    Args:
        command: Comando a ejecutar (ej: "npm install", "pip install fastapi")
        directorio: Directorio de trabajo absoluto donde se ejecuta el comando
    """
    try:
        # 1. Hard Blocks (Denegación estricta de comandos destructivos)
        for patron in _PATRONES_DESTRUCTIVOS:
            if re.search(patron, command, re.IGNORECASE):
                return json.dumps({
                    "status": "error",
                    "mensaje": "FIREWALL: Ejecución denegada. Comando destructivo detectado."
                }, ensure_ascii=False)

        # 2. Tokenización segura + lista blanca de binarios (sin shell)
        try:
            argv = _tokenizar_comando_seguro(command)
        except ValueError as e:
            return json.dumps({
                "status": "error",
                "mensaje": f"FIREWALL: {e}"
            }, ensure_ascii=False)

        # 3. Confinamiento del directorio de trabajo a la raíz del proyecto
        cwd = _validar_directorio_trabajo(directorio)

        # 4. Ejecución sin shell intermedio
        resultado = subprocess.run(
            argv,
            shell=False,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace"
        )
        return json.dumps({
            "status": "success" if resultado.returncode == 0 else "warning",
            "codigo_retorno": resultado.returncode,
            "stdout": (resultado.stdout or "")[:6000],
            "stderr": (resultado.stderr or "")[:3000],
            "comando_ejecutado": argv,
            "directorio": cwd
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "mensaje": "Timeout: el comando excedió el límite de 120 segundos."
        }, ensure_ascii=False)
    except FileNotFoundError as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Binario no encontrado en el sistema: {e}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)
