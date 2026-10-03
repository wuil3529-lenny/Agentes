"""
skill_limpiar_workspace.py — Rutina de Orden, Higiene y Limpieza del Workspace
=============================================================================
Habilidad del Subagente de Asistencia para mantener el orden, la limpieza y la
conformidad estructural de su espacio de trabajo:
- Carpetas Oficiales: .agents, _agents, data, informes, documentos_asistencia, documentos_sanji, skills
- Archivos en la Raíz: subagente_asistencia_agent.py, sanji_agent.py, Perfil_Subagente_Asistencia.md
- Archivos en _agents/.agents: agente.md (canónico), sanji_perfil.json, AGENTS.md
- Purga directorios temporales de caché (__pycache__)
- Reubica cualquier archivo basura o scratch a Archivos_temporales/
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"
_BASE_PATH = _APP_ROOT / _AGENTE

CARPETAS_OFICIALES = {
    ".agents",
    "_agents",
    "data",
    "informes",
    "documentos_asistencia",
    "documentos_sanji",
    "skills"
}

ARCHIVOS_RAIZ_OFICIALES = {
    "subagente_asistencia_agent.py",
    "sanji_agent.py",
    "Perfil_Subagente_Asistencia.md",
    "README.md"
}

ARCHIVOS_AGENTS_OFICIALES = {
    "agente.md",
    "AGENTS.md",
    "SANJI.md",
    "sanji_perfil.json"
}


def obtener_prompt_limpiar_workspace() -> str:
    """
    System Prompt especializado y encapsulado para el Oficial de Higiene y Orden del Workspace.
    """
    return """[🛑 HARD-STOP: MODO HIGIENE Y LIMPIEZA DE WORKSPACE ACTIVO 🛑]
Eres el Oficial de Higiene, Orden y Conformidad Estructural del Subagente de Asistencia.
Tu misión es auditar, purgar residuos temporales y preservar la arquitectura canónica de directorios del subagente con rigor técnico y determinismo.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. HIGIENE POST-EJECUCIÓN:
   - Al concluir una misión compleja o generación de múltiples borradores, ejecuta `tool_limpiar_workspace` para asegurar que ningún archivo temporal quede suelto en la raíz o carpetas de configuración.
2. REGLA ESTRICTA DE SCRATCH GLOBAL:
   - Todo archivo temporal, de pruebas intermedias o no categorizado debe residir exclusivamente en `/app/Archivos_temporales/` con prefijo `asistencia_` o `sanji_`.
3. CONFORMIDAD DE CARPETAS OFICIALES:
   - Las únicas carpetas permitidas en el espacio del subagente son: `informes`, `documentos_asistencia`, `data`, `skills` y `_agents` (o `.agents`). Cualquier carpeta extraña debe ser purgada o reubicada.
4. INTEGRIDAD DE LA MEMORIA:
   - Nunca intentes limpiar o alterar `Cerebro.md`, `Bitacora.md` ni `memoria/` mediante esta herramienta. Su alcance está estrictamente acotado a la habitación de trabajo del subagente.
"""


def limpiar_workspace(directorio_base: Path = None) -> Dict[str, Any]:
    """
    Ejecuta la rutina de inspección, purga de caché y reubicación de archivos extraños.
    """
    base_path = Path(directorio_base) if directorio_base else _BASE_PATH
    archivos_temporales_path = _APP_ROOT / "Archivos_temporales"
    archivos_temporales_path.mkdir(parents=True, exist_ok=True)

    reporte = {
        "agente": _AGENTE,
        "directorio_inspeccionado": str(base_path),
        "cache_eliminada": 0,
        "archivos_reubicados": 0,
        "carpetas_creadas": [],
        "carpetas_eliminadas": [],
        "detalles_reubicacion": []
    }

    if not base_path.exists():
        return reporte

    # 1. Asegurar existencia de las carpetas oficiales clave
    for dir_oficial in ["informes", "documentos_asistencia", "data", "skills"]:
        carpeta_path = base_path / dir_oficial
        if not carpeta_path.exists():
            carpeta_path.mkdir(parents=True, exist_ok=True)
            reporte["carpetas_creadas"].append(dir_oficial)

    # 2. Purgar carpetas __pycache__
    for cache_dir in list(base_path.rglob("__pycache__")):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                reporte["cache_eliminada"] += 1
            except Exception as e:
                print(f"[Asistencia Limpieza] Advertencia eliminando caché {cache_dir}: {e}")

    # 3. Limpiar carpeta de agentes (_agents o .agents)
    for nombre_ag in [".agents", "_agents"]:
        dir_agents = base_path / nombre_ag
        if dir_agents.exists() and dir_agents.is_dir():
            for item in list(dir_agents.iterdir()):
                if item.name not in ARCHIVOS_AGENTS_OFICIALES:
                    dest = archivos_temporales_path / f"asistencia_extra_{item.name}"
                    try:
                        shutil.move(str(item), str(dest))
                        reporte["archivos_reubicados"] += 1
                        reporte["detalles_reubicacion"].append(f"{nombre_ag}/{item.name} -> Archivos_temporales/")
                    except Exception as e:
                        print(f"[Asistencia Limpieza] Error reubicando archivo en {nombre_ag}: {e}")

    # 4. Inspeccionar raíz del agente
    for item in list(base_path.iterdir()):
        if item.name in CARPETAS_OFICIALES or item.name in ARCHIVOS_RAIZ_OFICIALES:
            continue

        if item.is_dir():
            if item.name != "__pycache__":
                dest = archivos_temporales_path / f"asistencia_dir_{item.name}"
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                    reporte["detalles_reubicacion"].append(f"{item.name}/ -> Archivos_temporales/")
                except Exception as e:
                    print(f"[Asistencia Limpieza] Error moviendo directorio extraño {item.name}: {e}")
        elif item.is_file():
            dest = archivos_temporales_path / f"asistencia_file_{item.name}"
            try:
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
                reporte["archivos_reubicados"] += 1
                reporte["detalles_reubicacion"].append(f"{item.name} -> Archivos_temporales/")
            except Exception as e:
                print(f"[Asistencia Limpieza] Error reubicando archivo {item.name}: {e}")

    return reporte


@tool
def tool_limpiar_workspace() -> str:
    """
    Ejecuta la rutina de orden, purga de caché y verificación estructural de carpetas
    en el espacio de trabajo del Subagente de Asistencia.
    Reubica archivos extraños a Archivos_temporales/ y asegura las carpetas oficiales.
    """
    try:
        res = limpiar_workspace()
        return json.dumps({
            "status": "success",
            "mensaje": "Rutina de higiene completada con éxito.",
            "reporte": res
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Fallo al ejecutar limpieza de workspace: {str(e)}"
        }, ensure_ascii=False)


# Alias de compatibilidad histórica
tool_limpiar_habitacion_sanji = tool_limpiar_workspace

__all__ = [
    "tool_limpiar_workspace",
    "tool_limpiar_habitacion_sanji",
    "limpiar_workspace",
    "obtener_prompt_limpiar_workspace",
]
