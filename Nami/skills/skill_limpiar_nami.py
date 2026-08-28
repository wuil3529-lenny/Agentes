"""
skill_limpiar_habitacion.py — Rutina de Orden y Limpieza para Nami
==================================================================
Estructura oficial estricta de Nami (C:\\Users\\admin\\Documents\\Agentes\\Nami):
- 3 Carpetas Oficiales: .agents, informes, skills
- 3 Archivos en .agents: AGENTS.md, NAMI.md, nami_perfil.json
- 2 Archivos en la Raíz: nami_agent.py, requirements.txt
- La carpeta 'data' se elimina por completo (las creaciones van a 'informes').
- Cualquier archivo temporal o no oficial se traslada a C:\\Users\\admin\\Documents\\Agentes\\Archivos_temporales.
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import os
import shutil
from pathlib import Path

CARPETAS_OFICIALES = {".agents", "informes", "skills"}
ARCHIVOS_RAIZ_OFICIALES = {"nami_agent.py", "requirements.txt"}
ARCHIVOS_AGENTS_OFICIALES = {"AGENTS.md", "NAMI.md", "nami_perfil.json"}


def limpiar_habitacion_nami(directorio_base: str = str(Path(__file__).resolve().parents[1])) -> dict:
    base_path = Path(directorio_base)
    archivos_temporales_path = (_APP_ROOT / "Archivos_temporales")
    archivos_temporales_path.mkdir(parents=True, exist_ok=True)
    
    reporte = {
        "cache_eliminada": 0,
        "archivos_reubicados": 0,
        "carpetas_creadas": [],
        "carpetas_eliminadas": []
    }
    
    # 1. Asegurar existencia de las 3 carpetas oficiales (.agents, informes, skills)
    for dir_oficial in CARPETAS_OFICIALES:
        carpeta_path = base_path / dir_oficial
        if not carpeta_path.exists():
            carpeta_path.mkdir(parents=True, exist_ok=True)
            reporte["carpetas_creadas"].append(dir_oficial)
            
    # 2. Eliminar la carpeta 'data' si existe (moviendo creaciones a 'informes' primero)
    carpeta_data = base_path / "data"
    if carpeta_data.exists() and carpeta_data.is_dir():
        for item in carpeta_data.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".mov", ".svg", ".pdf", ".pptx", ".html", ".css", ".js"]:
                    dest = base_path / "informes" / item.name
                else:
                    dest = archivos_temporales_path / item.name
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                except Exception:
                    pass
        try:
            shutil.rmtree(carpeta_data)
            reporte["carpetas_eliminadas"].append("data")
        except Exception as e:
            print(f"[Nami Limpieza] Error eliminando carpeta data: {e}")

    # 3. Eliminar __pycache__ en raíz y subcarpetas
    for cache_dir in base_path.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                reporte["cache_eliminada"] += 1
            except Exception as e:
                print(f"[Nami Limpieza] Error eliminando caché {cache_dir}: {e}")

    # 4. Asegurar que en .agents SOLO estén los 3 archivos oficiales
    dir_agents = base_path / ".agents"
    if dir_agents.exists() and dir_agents.is_dir():
        for item in dir_agents.iterdir():
            if item.name not in ARCHIVOS_AGENTS_OFICIALES:
                dest = archivos_temporales_path / item.name
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                except Exception as e:
                    print(f"[Nami Limpieza] Error sacando archivo no oficial de .agents: {e}")

    # 5. Revisar archivos y directorios en la raíz de Nami
    for item in base_path.iterdir():
        if item.name in CARPETAS_OFICIALES or item.name in ARCHIVOS_RAIZ_OFICIALES:
            continue
            
        if item.is_dir():
            # Si es un directorio no oficial (no es .agents, informes ni skills), mover a Archivos_temporales
            if item.name != "__pycache__":
                dest = archivos_temporales_path / item.name
                try:
                    shutil.move(str(item), str(dest))
                    reporte["archivos_reubicados"] += 1
                except Exception as e:
                    print(f"[Nami Limpieza] Error moviendo directorio no oficial {item.name}: {e}")
        elif item.is_file():
            # Si hay creaciones perdidas en la raíz, enviarlas a informes; cualquier otro archivo a Archivos_temporales
            ext = item.suffix.lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".mov", ".svg", ".pdf", ".pptx", ".html", ".css", ".js"]:
                dest = base_path / "informes" / item.name
            else:
                dest = archivos_temporales_path / item.name
                
            try:
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
                reporte["archivos_reubicados"] += 1
            except Exception as e:
                print(f"[Nami Limpieza] Error reubicando archivo {item.name}: {e}")
                
    return reporte

if __name__ == "__main__":
    res = limpiar_habitacion_nami()
    print(f"[Nami] Rutina 'Limpiar Habitación' ejecutada con éxito: {res}")
