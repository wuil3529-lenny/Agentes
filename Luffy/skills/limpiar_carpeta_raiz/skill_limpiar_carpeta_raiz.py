"""
skill_limpiar_carpeta_raiz.py — Skill de Limpieza de Carpeta Raíz para Luffy
=============================================================================
Organiza y mantiene impecable la carpeta raíz del proyecto (C:\\Users\\admin\\Documents\\Agentes):
- 10 Carpetas Oficiales:
  .obsidian, Archivos_temporales, Luffy, memoria, Nami, protocolo, Robin, sistema, Sanji, Zoro
- 9 Archivos Sueltos Oficiales:
  .dockerignore, .env, .gitignore, Bitacora.md, Cerebro.md, docker-compose.yml, Dockerfile, Perfil de wuil.md, start.sh
- Elimina carpetas temporales (__pycache__).
- Reubica cualquier archivo no autorizado a Archivos_temporales/ (o las creaciones a informes/ de Nami si fuera el caso).
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import os
import shutil
from pathlib import Path

CARPETAS_RAIZ_OFICIALES = {
    ".obsidian",
    "Archivos_temporales",
    "logs",
    "Luffy",
    "memoria",
    "Nami",
    "protocolo",
    "Robin",
    "sistema",
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
    "start.sh",
    "turno.json"
}


def limpiar_carpeta_raiz_luffy(directorio_base: str = str(_APP_ROOT)) -> dict:
    base_path = Path(directorio_base)
    archivos_temporales_path = base_path / "Archivos_temporales"
    archivos_temporales_path.mkdir(parents=True, exist_ok=True)
    
    reporte = {
        "cache_eliminada": 0,
        "archivos_reubicados": 0,
        "carpetas_reubicadas": 0,
        "carpetas_creadas": []
    }
    
    # 1. Asegurar la existencia de las 10 carpetas oficiales
    for dir_oficial in CARPETAS_RAIZ_OFICIALES:
        carpeta_path = base_path / dir_oficial
        if not carpeta_path.exists():
            carpeta_path.mkdir(parents=True, exist_ok=True)
            reporte["carpetas_creadas"].append(dir_oficial)
            
    # 2. Eliminar carpetas __pycache__ en la raíz o en carpetas de agentes
    for cache_dir in base_path.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
                reporte["cache_eliminada"] += 1
            except Exception as e:
                print(f"[Luffy Limpieza Raíz] Error eliminando caché {cache_dir}: {e}")

    # 3. Revisar elementos en la raíz /app
    for item in base_path.iterdir():
        if item.name in CARPETAS_RAIZ_OFICIALES or item.name in ARCHIVOS_RAIZ_OFICIALES:
            continue
            
        if item.is_dir():
            if item.name != "__pycache__":
                dest = archivos_temporales_path / item.name
                try:
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.move(str(item), str(dest))
                    reporte["carpetas_reubicadas"] += 1
                except Exception as e:
                    print(f"[Luffy Limpieza Raíz] Error moviendo directorio {item.name}: {e}")
        elif item.is_file():
            # Si es una creación multimedia extraviada, la mandamos a Nami/informes/
            ext = item.suffix.lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".mov", ".svg", ".pdf", ".pptx", ".html", ".css", ".js"]:
                dest = base_path / "Nami" / "informes" / item.name
                dest.parent.mkdir(parents=True, exist_ok=True)
            else:
                dest = archivos_temporales_path / item.name
                
            try:
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
                reporte["archivos_reubicados"] += 1
            except Exception as e:
                print(f"[Luffy Limpieza Raíz] Error reubicando archivo {item.name}: {e}")
                
    return reporte

if __name__ == "__main__":
    res = limpiar_carpeta_raiz_luffy()
    print(f"[Luffy] Rutina 'Limpiar Carpeta Raíz' ejecutada con éxito: {res}")
