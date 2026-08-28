"""
skill_limpiar_habitacion.py — Rutina de Orden y Limpieza para Zoro
==================================================================
Estructura oficial estricta de Zoro (C:\\Users\\admin\\Documents\\Agentes\\Zoro):
- Carpetas Oficiales: .agents, skills, n8n-mcp-skills, proyectos
- Archivos en .agents: ZORO.md, zoro_perfil.json, Zoro_Skills.md (si corresponde)
- Archivos en la Raíz: zoro_agent.py
- Cualquier archivo temporal o no oficial se traslada a C:\\Users\\admin\\Documents\\Agentes\\Archivos_temporales.
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import os
import shutil
from pathlib import Path
from langchain_core.tools import tool

CARPETAS_OFICIALES = {".agents", "skills", "n8n-mcp-skills", "proyectos"}
ARCHIVOS_RAIZ_OFICIALES = {"zoro_agent.py"}
ARCHIVOS_AGENTS_OFICIALES = {"AGENTS.md", "ZORO.md", "zoro_perfil.json", "Zoro_Skills.md"}


def limpiar_habitacion_zoro(directorio_base: str = str(Path(__file__).resolve().parents[1])) -> dict:
    base_path = Path(directorio_base)
    archivos_temporales_path = (_APP_ROOT / "Archivos_temporales")
    archivos_temporales_path.mkdir(parents=True, exist_ok=True)
    
    reporte = {
        "cache_eliminada": 0,
        "archivos_reubicados": 0,
        "carpetas_creadas": [],
        "carpetas_eliminadas": []
    }
    
    # 1. Asegurar existencia de las carpetas oficiales
    for dir_oficial in CARPETAS_OFICIALES:
        carpeta_path = base_path / dir_oficial
        if not carpeta_path.exists():
            carpeta_path.mkdir(parents=True, exist_ok=True)
            reporte["carpetas_creadas"].append(dir_oficial)
            
    # 2. Eliminar __pycache__ en raíz y subcarpetas
    for cache_dir in base_path.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                reporte["cache_eliminada"] += 1
            except Exception as e:
                print(f"[Zoro Limpieza] Error eliminando caché {cache_dir}: {e}")

    # 3. Asegurar que en .agents SOLO estén los archivos oficiales
    dir_agents = base_path / ".agents"
    if dir_agents.exists() and dir_agents.is_dir():
        for item in dir_agents.iterdir():
            if item.name not in ARCHIVOS_AGENTS_OFICIALES:
                dest = archivos_temporales_path / item.name
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                except Exception as e:
                    print(f"[Zoro Limpieza] Error sacando archivo no oficial de .agents: {e}")

    # 4. Revisar archivos y directorios en la raíz de Zoro
    for item in base_path.iterdir():
        if item.name in CARPETAS_OFICIALES or item.name in ARCHIVOS_RAIZ_OFICIALES:
            continue
            
        if item.is_dir():
            if item.name != "__pycache__":
                dest = archivos_temporales_path / item.name
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                except Exception as e:
                    print(f"[Zoro Limpieza] Error moviendo directorio no oficial {item.name}: {e}")
        elif item.is_file():
            dest = archivos_temporales_path / item.name
            try:
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
                reporte["archivos_reubicados"] += 1
            except Exception as e:
                print(f"[Zoro Limpieza] Error reubicando archivo {item.name}: {e}")
                
    return reporte

@tool
def tool_limpiar_habitacion_zoro() -> str:
    """Ejecuta la rutina de orden y limpieza para mantener solo las carpetas oficiales en Zoro."""
    try:
        res = limpiar_habitacion_zoro()
        import json
        return json.dumps({"status": "success", "reporte": res})
    except Exception as e:
        import json
        return json.dumps({"status": "error", "mensaje": str(e)})

if __name__ == "__main__":
    res = limpiar_habitacion_zoro()
    print(f"[Zoro] Rutina 'Limpiar Habitación' ejecutada con éxito: {res}")
