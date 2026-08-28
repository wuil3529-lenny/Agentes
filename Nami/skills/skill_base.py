"""
skill_base.py - Habilidades Base: Sistema de Archivos y Comandos de Shell
==========================================================================
Herramientas fundamentales de I/O y ejecucion de procesos.
Validacion unificada: Hard Stop + Auto-enlazador Obsidian + Anti-alucinacion.

Rutas de escritura permitidas para Nami:
  - /app/Nami/informes/    (entregables)
  - /app/Archivos_temporales/           (scratch compartido)
  - /app/Bitacora.md                    (tickets)
  - /app/Cerebro.md                     (conocimiento — solo via tool_guardar_solucion)
  - /app/memoria/                       (informes de conocimiento)
"""
import re
import os
import json
import subprocess
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[2]
_AGENTE   = "Nami"
_TRABAJO  = _APP_ROOT / _AGENTE / "informes"
_TEMP     = _APP_ROOT / "Archivos_temporales"
_MEMORIA  = _APP_ROOT / "memoria"


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
    temp_local  = _normalizar(str(_APP_ROOT / _AGENTE / "Archivos_temporales"))

    # AUTO-CORRECCIÓN: si apunta a la Archivos_temporales local del agente -> redirigir a global
    if ruta_norm.startswith(temp_local):
        ruta_corregida = ruta_norm.replace(temp_local, temp_global)
        return True, ruta_corregida

    # Zonas válidas
    zonas_validas = [
        _normalizar(str(_TRABAJO)),
        temp_global,
        _normalizar(str(_MEMORIA)),
        _normalizar(str(_APP_ROOT / "Bitacora.md")),
        _normalizar(str(_APP_ROOT / "Cerebro.md")),
    ]
    for zona in zonas_validas:
        if ruta_norm.startswith(zona):
            return True, ruta_str

    # Zona raíz del agente: solo permitida si es una subcarpeta conocida
    if ruta_norm.startswith(raiz_agente):
        # Subcarpetas permitidas dentro de /app/Nami/
        subcarpetas_ok = ["informes", "skills", ".agents"]
        sub = ruta_norm[len(raiz_agente):].lstrip("/")
        primera = sub.split("/")[0] if "/" in sub else sub
        if primera in subcarpetas_ok:
            return True, ruta_str
        # Cualquier otra subcarpeta inventada -> HARD STOP
        return False, ""

    return False, ""

def _msg_hard_stop(ruta: str) -> str:
    return (
        f"HARD STOP — Escritura bloqueada en ruta no autorizada: {{ruta}}\n"
        f"Rutas de escritura permitidas para {_AGENTE}:\n"
        f"  /app/{_AGENTE}/{"informes"}/  → entregables de trabajo\n"
        f"  /app/Archivos_temporales/             → archivos temporales (usa prefijo {_AGENTE.lower()}_)\n"
        f"  /app/Bitacora.md                      → actualizar estado de tickets\n"
        f"  /app/Cerebro.md                       → SOLO via tool_guardar_solucion\n"
        f"  /app/memoria/                         → SOLO via tool_guardar_solucion\n"
    )


@tool
def crear_archivo(ruta_absoluta: str, contenido: str) -> str:
    """
    Crea o sobreescribe un archivo con el contenido dado.
    Solo puede escribir en las rutas autorizadas del agente.
    """
    # Limpiar links relativos que contaminan el grafo de Obsidian
    contenido = re.sub(r"\[([^\]]+)\]\((?:\.\./|\./)(?:[^)]+)\)", r"\1", contenido)

    # BLINDAJE: Cerebro.md solo via herramienta
    if "Cerebro.md" in ruta_absoluta:
        raise Exception("PROHIBIDO escribir manualmente en Cerebro.md. Usa la herramienta 'tool_guardar_solucion' para registrar conocimiento.")

    es_valida, ruta_corregida = _ruta_es_valida(ruta_absoluta)
    if not es_valida:
        raise Exception(_msg_hard_stop(ruta_absoluta))

    ruta_final = ruta_corregida or ruta_absoluta

    try:
        ruta = Path(ruta_final)
        ruta.parent.mkdir(parents=True, exist_ok=True)

        # --- AUTO-ENLAZADOR OBSIDIAN ---
        ruta_str = str(ruta_final).replace("\\", "/")
        if ruta_str.endswith(".md"):
            # Limpiar cualquier intento manual del agente de crear conexiones incorrectas
            contenido = re.sub(r"(?im)^\s*\*\*(Pertenece a|Conexiones):\*\*.*\n?", "", contenido)
            contenido = contenido.strip()
            
            enlace_fuerte = None
            if "/Archivos_temporales/" in ruta_str or ruta_str.endswith("/Archivos_temporales"):
                enlace_fuerte = "[[archivos_temporales]]"
            elif f"/{_AGENTE}/{"informes"}/" in ruta_str or ruta_str.endswith(f"/{_AGENTE}/{"informes"}"):
                enlace_fuerte = "[[informes]]"
            elif "/memoria/" in ruta_str or ruta_str.endswith("/memoria"):
                enlace_fuerte = "[[memoria]]"

            if enlace_fuerte:
                contenido += f"\n\n---\n**Pertenece a:** {{enlace_fuerte}}\n"
        # ----------------------------

        ruta.write_text(contenido, encoding="utf-8")
        return json.dumps({{"status": "success", "archivo": str(ruta), "bytes_escritos": len(contenido.encode("utf-8"))}})
    except Exception as e:
        return json.dumps({{"status": "error", "mensaje": str(e)}})


@tool
def leer_archivo(ruta_absoluta: str) -> str:
    """
    Lee y retorna el contenido de un archivo. Filtra metadatos de Obsidian para evitar alucinaciones.
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({{"status": "error", "mensaje": f"Archivo no encontrado: {{ruta_absoluta}}"}})

        contenido = ruta.read_text(encoding="utf-8")

        # --- CENSURA DE METADATA OBSIDIAN (Anti-Alucinacion) ---
        contenido = re.sub(r"(?m)^> \*\*Conexiones Core:\*\*.*\n?", "", contenido)
        contenido = re.sub(r"(?m)^\*\*Pertenece a:\*\*.*\n?", "", contenido)
        contenido = re.sub(r"(?m)^\*\*Conexiones:\*\*.*\n?", "", contenido)
        # -------------------------------------------------------

        return json.dumps({{"status": "success", "archivo": str(ruta), "contenido": contenido[:8000], "lineas": contenido.count("\n") + 1}})
    except Exception as e:
        return json.dumps({{"status": "error", "mensaje": str(e)}})


@tool
def listar_directorio(ruta_absoluta: str) -> str:
    """
    Lista el contenido de un directorio. Auto-corrige rutas relativas de Archivos_temporales.
    """
    # Auto-corrección: Archivos_temporales local -> global
    if "Archivos_temporales" in ruta_absoluta:
        temp_local = str(_APP_ROOT / _AGENTE / "Archivos_temporales")
        if _normalizar(ruta_absoluta).startswith(_normalizar(temp_local)):
            ruta_absoluta = str(_TEMP)

    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({{"status": "error", "mensaje": f"Directorio no encontrado: {{ruta_absoluta}}"}})
        items = []
        for item in sorted(ruta.iterdir()):
            items.append({{"nombre": item.name, "tipo": "directorio" if item.is_dir() else "archivo", "bytes": item.stat().st_size if item.is_file() else None}})
        return json.dumps({{"status": "success", "ruta": str(ruta), "total": len(items), "items": items}})
    except Exception as e:
        return json.dumps({{"status": "error", "mensaje": str(e)}})


@tool
def ejecutar_comando(comando: str, directorio: str) -> str:
    """
    Ejecuta un comando de shell en el directorio especificado.
    Solo puede ejecutar dentro del territorio del agente.
    """
    try:
        caracteres_peligrosos = ["&", "|", ";", ">", "<", "$", "`"]
        if any(c in comando for c in caracteres_peligrosos):
            return json.dumps({{"status": "error", "mensaje": "Violacion de seguridad: inyeccion de comandos detectada."}})

        resultado = subprocess.run(comando, shell=True, cwd=directorio, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        return json.dumps({{"status": "success" if resultado.returncode == 0 else "warning", "codigo_retorno": resultado.returncode, "stdout": resultado.stdout[:3000], "stderr": resultado.stderr[:1500]}})
    except subprocess.TimeoutExpired:
        return json.dumps({{"status": "error", "mensaje": "Timeout: el comando supero los 120 segundos."}})
    except Exception as e:
        return json.dumps({{"status": "error", "mensaje": str(e)}})


@tool
def buscar_web_duckduckgo(query: str) -> str:
    """Busca informacion en la web utilizando DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        resultados = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                resultados.append(r)
        return json.dumps({{"status": "success", "resultados": resultados}})
    except ImportError:
        return json.dumps({{"status": "warning", "mensaje": "La libreria duckduckgo_search no esta instalada."}})
    except Exception as e:
        return json.dumps({{"status": "error", "mensaje": str(e)}})


HERRAMIENTAS_BASE = [crear_archivo, leer_archivo, listar_directorio, ejecutar_comando, buscar_web_duckduckgo]
