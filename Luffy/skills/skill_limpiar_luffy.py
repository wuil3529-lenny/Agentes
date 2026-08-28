import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]
import os
import shutil
from pathlib import Path


def limpiar_habitacion_luffy(dir_raiz: str = None) -> dict:
    """
    Limpia y organiza la habitación (directorio) de Luffy para garantizar que solo existan
    las carpetas oficiales (.agents, data, informes, skills) y exactamente los 6 archivos
    raíz permitidos (requirements.txt, .gitignore, y los 4 .py principales).
    """
    if dir_raiz is None:
        dir_raiz = Path(__file__).resolve().parent.parent
    else:
        dir_raiz = Path(dir_raiz)

    agente_nombre = dir_raiz.name
    print(f"[{agente_nombre}] Iniciando rutina 'Limpiar Habitación' en: {dir_raiz}")

    # 1. Rutas destino de papelera/archivos temporales
    papelera_base = (_APP_ROOT / "Archivos_temporales")
    papelera_agente = papelera_base / agente_nombre
    papelera_agente.mkdir(parents=True, exist_ok=True)

    # 2. Carpetas oficiales permitidas en la raíz de Luffy
    carpetas_permitidas = {".agents", ".agente", "data", "informes", "skills"}
    for carpeta in [".agents", "data", "informes", "skills"]:
        (dir_raiz / carpeta).mkdir(exist_ok=True)

    # 3. Archivos raíz permitidos exactamente (los 6 archivos oficiales)
    archivos_raiz_permitidos = {
        "requirements.txt",
        ".gitignore",
        "base_listener.py",
        "luffy_agent.py",
        "memory.py",
        "nim_client.py"
    }

    reporte = {
        "carpetas_eliminadas_cache": 0,
        "carpetas_movidas_temporal": 0,
        "archivos_movidos_skills": 0,
        "archivos_movidos_temporal": 0
    }

    # 4. Eliminar todas las carpetas __pycache__ de forma recursiva
    for p in list(dir_raiz.rglob("__pycache__")):
        if p.exists() and p.is_dir():
            print(f"  -> Eliminando caché temporal: {p.relative_to(dir_raiz)}")
            shutil.rmtree(p, ignore_errors=True)
            reporte["carpetas_eliminadas_cache"] += 1

    # 5. Revisar todos los elementos en la raíz del agente
    for item in list(dir_raiz.iterdir()):
        nombre = item.name

        # Si es un directorio
        if item.is_dir():
            if nombre == "__pycache__":
                continue  # Ya eliminado arriba
            if nombre not in carpetas_permitidas:
                print(f"  -> Carpeta no autorizada '{nombre}': moviendo a Archivos_temporales...")
                destino = papelera_agente / nombre
                if destino.exists():
                    shutil.rmtree(destino, ignore_errors=True)
                shutil.move(str(item), str(destino))
                reporte["carpetas_movidas_temporal"] += 1

        # Si es un archivo en la raíz
        elif item.is_file():
            if nombre in archivos_raiz_permitidos:
                continue

            # Si es una skill que quedó en la raíz
            if (nombre.startswith("skill_") and nombre.endswith(".py")) or nombre in {"telegram_bridge.py", "plantilla_agente.py"}:
                print(f"  -> Moviendo skill '{nombre}' a la carpeta skills/...")
                shutil.move(str(item), str(dir_raiz / "skills" / nombre))
                reporte["archivos_movidos_skills"] += 1
            else:
                print(f"  -> Archivo no autorizado en raíz '{nombre}': moviendo a Archivos_temporales...")
                destino_file = papelera_agente / nombre
                if destino_file.exists():
                    destino_file.unlink()
                shutil.move(str(item), str(destino_file))
                reporte["archivos_movidos_temporal"] += 1

    print(f"[{agente_nombre}] ¡Habitación limpia y ordenada según la norma de la tripulación!")
    print(f"  - Caché eliminada: {reporte['carpetas_eliminadas_cache']}")
    print(f"  - Carpetas temporales movidas: {reporte['carpetas_movidas_temporal']}")
    print(f"  - Skills reubicadas: {reporte['archivos_movidos_skills']}")
    print(f"  - Archivos basura/temporales movidos: {reporte['archivos_movidos_temporal']}")
    return reporte

# Alias para compatibilidad
limpiar_habitacion = limpiar_habitacion_luffy

if __name__ == "__main__":
    limpiar_habitacion_luffy()
