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
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - Nunca escribas manualmente en Cerebro.md. El conocimiento estructurado debe registrarse mediante las herramientas RAG oficiales.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil o carpeta correspondiente.
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina a un máximo de seguridad para no desbordar la ventana de contexto del modelo.
"""


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
        
        # --- AUTO-ENLAZADOR OBSIDIAN ---
        if ruta_str.endswith(".md"):
            # Limpiar cualquier intento de enlace doble a la Triada en el contenido
            contenido = re.sub(r'\[\[(Bitacora|Cerebro|Reglas de la Tripulacion|Memoria_Viva_Errores)\]\]', r'[\1]', contenido)
            
            # Determinar a donde pertenece segun la ruta (rutas canonicas y legadas)
            enlace_fuerte = None
            if "/Subagente_Diseno/informes" in ruta_str or "/Nami/informes" in ruta_str:
                enlace_fuerte = "[[informes]]"
            elif "/Subagente_Desarrollo/proyectos" in ruta_str or "/Zoro/proyectos" in ruta_str:
                enlace_fuerte = "[[proyectos]]"
            elif "/Subagente_Ciberseguridad/reportes" in ruta_str or "/Robin/reportes" in ruta_str:
                enlace_fuerte = "[[reportes]]"
            elif "/Subagente_Asistencia/documentos_sanji" in ruta_str or "/Sanji/documentos_sanji" in ruta_str:
                enlace_fuerte = "[[documentos_sanji]]"
            elif "/Archivos_temporales" in ruta_str:
                enlace_fuerte = "[[archivos_temporales]]"
            elif "/skills/" in ruta_str:
                match = re.search(r'/Agentes/([^/]+)/skills', ruta_str)
                if match:
                    enlace_fuerte = f"[[Perfil_{match.group(1)}]]"
            
            if enlace_fuerte and enlace_fuerte not in contenido:
                if "**Pertenece a:**" in contenido:
                    contenido = re.sub(r'\*\*Pertenece a:\*\*.*', f'**Pertenece a:** {enlace_fuerte}', contenido)
                else:
                    contenido += f"\n\n---\n**Pertenece a:** {enlace_fuerte}\n"
        # -------------------------------

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
    # Auto-corregir Archivos_temporales relativo -> global
    if 'Archivos_temporales' in ruta_absoluta:
        ruta_norm = ruta_absoluta.replace('\\', '/')
        if '/app/Archivos_temporales' not in ruta_norm:
            ruta_absoluta = str(_APP_ROOT / 'Archivos_temporales')
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta_absoluta}"})
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
def ejecutar_comando(command: str, directorio: str) -> str:
    """
    Ejecuta un comando de shell en el directorio especificado.
    Soporta: npm, npx, pip, python, node, flutter, git, docker, etc.
    Timeout máximo: 120 segundos.

    Args:
        command: Comando a ejecutar (ej: "npm install", "pip install fastapi")
        directorio: Directorio de trabajo absoluto donde se ejecuta el comando
    """
    try:
        # FIREWALL DETERMINÍSTICO
        cmd_lower = command.lower()
        
        # 1. Hard Blocks (Denegación estricta de comandos destructivos)
        bloqueos = ["rm -rf", "del /f", "del /s", "del /q", "chmod -r 777", "mkfs", "format", "shutdown", "reboot"]
        if any(b in cmd_lower for b in bloqueos):
            return json.dumps({"status": "error", "mensaje": "FIREWALL: Ejecución denegada. Comando destructivo detectado."})

        # 2. Lista Blanca de comandos base permitidos
        binarios_permitidos = ["npm ", "npx ", "pip ", "python ", "python3 ", "node ", "flutter ", "git ", "docker ", "ls", "dir", "cd ", "echo ", "cat ", "type ", "mkdir ", "touch ", "grep ", "find ", "findstr ", "rg "]
        base_cmd = command.strip().split(" ")[0] + " "
        if base_cmd.strip() not in [b.strip() for b in binarios_permitidos] and not any(command.strip().startswith(b) for b in binarios_permitidos):
            return json.dumps({"status": "error", "mensaje": f"FIREWALL: Binario '{base_cmd.strip()}' no está en la lista blanca de permitidos."})

        resultado = subprocess.run(
            command,
            shell=True,
            cwd=directorio,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace"
        )
        return json.dumps({
            "status": "success" if resultado.returncode == 0 else "warning",
            "codigo_retorno": resultado.returncode,
            "stdout": resultado.stdout[:3000] if resultado.stdout else "",
            "stderr": resultado.stderr[:1500] if resultado.stderr else ""
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "mensaje": "Timeout: el comando superó los 120 segundos."})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas fundamentales de I/O y sistema
HERRAMIENTAS_BASE = [crear_archivo, leer_archivo, listar_directorio, ejecutar_comando]