"""
skill_limpiar_workspace.py — Higiene y Limpieza Integral del Espacio de Trabajo
==============================================================================
Habilidad unificada del Agente Orquestador para mantener la higiene operativa
tanto de la raíz del proyecto como del directorio interno del agente, centralizando
archivos temporales en la raíz y eliminando cachés residuales.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Any
from langchain_core.tools import tool


def _obtener_raiz_proyecto() -> Path:
    """Encuentra la raíz del proyecto tanto en entorno local como en contenedor Docker."""
    actual = Path(__file__).resolve()
    for parent in actual.parents:
        if (parent / "Bitacora.md").exists() or (parent / "Agente_Orquestador").exists():
            return parent
    if Path("/app/Bitacora.md").exists():
        return Path("/app")
    return actual.parents[2]


CARPETAS_RAIZ_OFICIALES = {
    ".git",
    ".gemini",
    ".idea",
    ".vscode",
    ".obsidian",
    "Agente_Orquestador",
    "Archivos_temporales",
    "contexto",
    "dashboard",
    "logs",
    "memoria",
    "protocolo",
    "proyectos",
    "sistema",
    "Subagente_Asistencia",
    "Subagente_Ciberseguridad",
    "Subagente_Desarrollo",
    "Subagente_Diseno"
}

CARPETAS_LEGADAS_PERMITIDAS = {
    "Luffy",
    "Nami",
    "Robin",
    "Sanji",
    "Zoro"
}

ARCHIVOS_RAIZ_OFICIALES = {
    ".dockerignore",
    ".env",
    ".gitignore",
    "Bitacora.md",
    "Cerebro.md",
    "docker-compose.yml",
    "Dockerfile",
    "Perfil de wuil.md",
    "start.sh",
    "turno.json",
    "README.md",
    "INFORME_MIGRACION_Y_ESTADO_SISTEMA.md",
    "conector_remoto.py",
    "reiniciar_tripulacion.bat"
}

CARPETAS_AGENTE_OFICIALES = {
    ".agents",
    "_agents",
    ".agente",
    "data",
    "informes",
    "skills",
    "contexto"
}

ARCHIVOS_AGENTE_OFICIALES = {
    "requirements.txt",
    ".gitignore",
    "base_listener.py",
    "luffy_agent.py",
    "agente_orquestador_agent.py",
    "memory.py",
    "nim_client.py",
    "sync_cerebro.py",
    "costos_tracker.py",
    "telegram_bridge.py",
    "canal_usuario.json",
    "estado_tripulacion.json",
    "Perfil_Agente_Orquestador.md",
    "Memoria_Ejecucion_Agente_Orquestador.md",
    "Perfil_Luffy.md",
    "Memoria_Ejecucion_Luffy.md"
}


def obtener_prompt_limpiar_workspace() -> str:
    """
    System Prompt especializado y encapsulado para el modo de higiene
    y mantenimiento del espacio de trabajo.
    """
    return """[🛑 HARD-STOP: MODO HIGIENE Y LIMPIEZA DEL ESPACIO DE TRABAJO ACTIVO 🛑]
Eres el Administrador de Higiene Arquitectónica y Organización del Espacio de Trabajo.
Tu misión es mantener el repositorio y los directorios de los agentes en perfecto orden, sin archivos huérfanos, basura o cachés residuales.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CENTRALIZACIÓN DE ARCHIVOS TEMPORALES:
   - La carpeta `Archivos_temporales/` existe ÚNICAMENTE en la raíz del proyecto.
   - Jamás crees carpetas temporales internas dentro de los directorios de los agentes.
2. REUBICACIÓN INTELIGENTE (ZERO LOSS):
   - Archivos multimedia sueltos en la raíz (.png, .webp, .svg, etc.) se canalizan a `Subagente_Diseno/informes/`.
   - Módulos `skill_*.py` que queden sueltos en la raíz del agente se reubican en `skills/`.
   - Cualquier archivo o carpeta fuera de la lista oficial se traslada a `Archivos_temporales/` en la raíz.
3. ELIMINACIÓN DE CACHÉ:
   - Toda carpeta `__pycache__` se erradica recursivamente sin excepciones.
"""


@tool
def tool_limpiar_workspace() -> str:
    """
    Ejecuta una rutina integral de higiene y saneamiento del espacio de trabajo:
    1. Audita la raíz del proyecto, protegiendo archivos y carpetas oficiales y enviando basura a Archivos_temporales/.
    2. Audita la habitación del Agente Orquestador, moviendo skills sueltas a skills/ y elementos no autorizados a Archivos_temporales/ en la raíz.
    3. Elimina recursivamente todas las carpetas __pycache__ del sistema.
    """
    print("\n[Agente Orquestador] Ejecutando: tool_limpiar_workspace()...")

    raiz = _obtener_raiz_proyecto()
    dir_agente = raiz / "Agente_Orquestador" if (raiz / "Agente_Orquestador").exists() else raiz / "Luffy"

    # La única carpeta de temporales está en la raíz
    papelera_raiz = raiz / "Archivos_temporales"
    papelera_raiz.mkdir(parents=True, exist_ok=True)

    reporte: Dict[str, Any] = {
        "cache_eliminada": 0,
        "raiz_carpetas_creadas": [],
        "raiz_archivos_reubicados": 0,
        "raiz_carpetas_reubicadas": 0,
        "agente_skills_reubicadas": 0,
        "agente_elementos_reubicados": 0
    }

    # =========================================================================
    # FASE 1: HIGIENE DE LA RAÍZ DEL PROYECTO
    # =========================================================================
    for dir_oficial in CARPETAS_RAIZ_OFICIALES:
        carpeta_path = raiz / dir_oficial
        if not carpeta_path.exists():
            carpeta_path.mkdir(parents=True, exist_ok=True)
            reporte["raiz_carpetas_creadas"].append(dir_oficial)

    for item in list(raiz.iterdir()):
        nombre = item.name
        if nombre.startswith(".git") or nombre.startswith(".gemini") or nombre in CARPETAS_RAIZ_OFICIALES or nombre in CARPETAS_LEGADAS_PERMITIDAS or nombre in ARCHIVOS_RAIZ_OFICIALES or item.suffix.lower() in [".bat", ".sh"]:
            continue

        if item.is_dir():
            if nombre == "__pycache__":
                continue
            dest = papelera_raiz / nombre
            try:
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.move(str(item), str(dest))
                reporte["raiz_carpetas_reubicadas"] += 1
            except Exception as e:
                print(f"[Limpieza Raíz] Error moviendo directorio {nombre}: {e}")

        elif item.is_file():
            ext = item.suffix.lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".mov", ".svg", ".pdf", ".pptx", ".html", ".css"]:
                dest = raiz / "Subagente_Diseno" / "informes" / nombre
                dest.parent.mkdir(parents=True, exist_ok=True)
            else:
                dest = papelera_raiz / nombre

            try:
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
                reporte["raiz_archivos_reubicados"] += 1
            except Exception as e:
                print(f"[Limpieza Raíz] Error reubicando archivo {nombre}: {e}")

    # =========================================================================
    # FASE 2: HIGIENE DE LA HABITACIÓN DEL AGENTE ORQUESTADOR
    # =========================================================================
    if dir_agente.exists():
        for sub_oficial in ["data", "informes", "skills"]:
            (dir_agente / sub_oficial).mkdir(exist_ok=True)

        for item in list(dir_agente.iterdir()):
            nombre = item.name

            if item.is_dir():
                if nombre == "__pycache__":
                    continue
                if nombre not in CARPETAS_AGENTE_OFICIALES:
                    # Mover directorio no autorizado a la papelera central de la raíz
                    dest = papelera_raiz / f"Agente_Orquestador_{nombre}"
                    try:
                        if dest.exists():
                            shutil.rmtree(dest, ignore_errors=True)
                        shutil.move(str(item), str(dest))
                        reporte["agente_elementos_reubicados"] += 1
                    except Exception as e:
                        print(f"[Limpieza Agente] Error moviendo directorio {nombre}: {e}")

            elif item.is_file():
                if nombre in ARCHIVOS_AGENTE_OFICIALES:
                    continue

                # Si es una skill suelta en la raíz del agente, reubicarla a skills/
                if nombre.startswith("skill_") and nombre.endswith(".py"):
                    dest_skill = dir_agente / "skills" / nombre
                    try:
                        shutil.move(str(item), str(dest_skill))
                        reporte["agente_skills_reubicadas"] += 1
                    except Exception as e:
                        print(f"[Limpieza Agente] Error reubicando skill {nombre}: {e}")
                else:
                    # Mover archivo ajeno a Archivos_temporales/ de la raíz
                    dest_file = papelera_raiz / nombre
                    try:
                        if dest_file.exists():
                            dest_file.unlink()
                        shutil.move(str(item), str(dest_file))
                        reporte["agente_elementos_reubicados"] += 1
                    except Exception as e:
                        print(f"[Limpieza Agente] Error reubicando archivo {nombre}: {e}")

    # =========================================================================
    # FASE 3: BARRIDO DE CACHÉ (__pycache__)
    # =========================================================================
    for cache_dir in list(raiz.rglob("__pycache__")):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
                reporte["cache_eliminada"] += 1
            except Exception as e:
                pass

    # Generar resumen ejecutivo
    lineas = [
        "[HIGIENE Y LIMPIEZA INTEGRAL DEL ESPACIO DE TRABAJO]",
        "[OK] Estado: Espacio de trabajo saneado y ordenado.",
        f"- Carpetas de caché eliminadas (__pycache__): {reporte['cache_eliminada']}",
        f"- Archivos de la raíz reubicados a temporales: {reporte['raiz_archivos_reubicados']}",
        f"- Carpetas de la raíz reubicadas a temporales: {reporte['raiz_carpetas_reubicadas']}",
        f"- Skills de agente auto-organizadas en skills/: {reporte['agente_skills_reubicadas']}",
        f"- Elementos del agente movidos a temporales: {reporte['agente_elementos_reubicados']}"
    ]
    if reporte["raiz_carpetas_creadas"]:
        lineas.append(f"- Carpetas oficiales restauradas en raíz: {', '.join(reporte['raiz_carpetas_creadas'])}")

    return "\n".join(lineas)


if __name__ == "__main__":
    print(tool_limpiar_workspace.invoke({}))
