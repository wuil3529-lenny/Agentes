import os
import re
from pathlib import Path
from langchain.tools import tool
from pydantic import BaseModel, Field

_APP_ROOT = Path(__file__).resolve().parents[2]

def _transformar_ruta_linux(ruta: str) -> str:
    """
    Asegura que la ruta de destino sea Linux y dentro del contenedor /app/.
    Maneja rutas vacías, literales de parámetro, rutas Windows y rutas relativas.
    """
    # Ruta por defecto si viene vacía, None, o es un literal de nombre de parámetro
    if not isinstance(ruta, str) or not ruta.strip():
        return str(_APP_ROOT / "Nami" / "informes" / "presentacion_marp.md")
    
    # Detectar si el valor es un literal de nombre de parámetro
    literales_parametro = {"ruta_destino", "tema_presentacion", "contenido_diapositivas", "ruta", "destino"}
    if ruta.strip().lower() in literales_parametro:
        return str(_APP_ROOT / "Nami" / "informes" / "presentacion_marp.md")
    
    # Si la ruta no tiene separadores de directorio ni extensión de archivo, es inválida
    if not os.path.sep in ruta and "/" not in ruta and "\\" not in ruta:
        if not ruta.endswith(".md"):
            ruta = ruta + ".md"
        return str(_APP_ROOT / "Nami" / "informes" / ruta)
    
    # Convertir rutas Windows a Linux
    patron = r"[Cc]:[/\\]+Users[/\\]+admin[/\\]+Documents[/\\]+Agentes[/\\]*"
    ruta_tr = re.sub(patron, "/app/", ruta, flags=re.IGNORECASE)
    ruta_tr = ruta_tr.replace("\\", "/")
    
    # También manejar rutas Windows sin el prefijo Agentes
    if ruta_tr.startswith("C:") or ruta_tr.startswith("c:"):
        nombre_archivo = os.path.basename(ruta_tr)
        if not nombre_archivo:
            nombre_archivo = "presentacion_marp.md"
        if not nombre_archivo.endswith(".md"):
            nombre_archivo = nombre_archivo + ".md"
        return str(_APP_ROOT / "Nami" / "informes" / nombre_archivo)
    
    # Si después de la transformación la ruta no empieza con /app/, forzar a informes/
    if not ruta_tr.startswith("/app/"):
        nombre_archivo = os.path.basename(ruta_tr)
        if not nombre_archivo:
            nombre_archivo = "presentacion_marp.md"
        if not nombre_archivo.endswith(".md"):
            nombre_archivo = nombre_archivo + ".md"
        return str(_APP_ROOT / "Nami" / "informes" / nombre_archivo)
    
    return ruta_tr

class MarpParams(BaseModel):
    tema_presentacion: str = Field(description="El tema o título de la presentación.")
    contenido_diapositivas: list[str] = Field(description="Lista de strings, cada uno representa el texto/bullet points de una diapositiva.")
    ruta_destino: str = Field(description="Ruta donde se guardará el archivo .md compatible con Marp.")

@tool("generar_presentacion_marp", args_schema=MarpParams)
def generar_presentacion_marp(tema_presentacion: str, contenido_diapositivas: list[str], ruta_destino: str) -> str:
    """Genera un archivo markdown estructurado para ser renderizado como presentación por Marp."""
    try:
        # Validar tema
        if not tema_presentacion or not isinstance(tema_presentacion, str) or tema_presentacion.strip() in ("tema_presentacion", ""):
            tema_presentacion = "Presentación"
        
        # Validar contenido: filtrar strings vacíos y literales de parámetro
        if not contenido_diapositivas or not isinstance(contenido_diapositivas, list):
            contenido_diapositivas = ["Diapositiva de contenido"]
        else:
            # Filtrar elementos vacíos o literales de nombre de parámetro
            _literales = {"contenido_diapositivas", "ruta_destino", "tema_presentacion", "ruta", "destino"}
            contenido_filtrado = [
                item for item in contenido_diapositivas
                if isinstance(item, str) and item.strip() and item.strip().lower() not in _literales
            ]
            if contenido_filtrado:
                contenido_diapositivas = contenido_filtrado
            else:
                contenido_diapositivas = ["Diapositiva de contenido"]
        
        ruta_limpia = _transformar_ruta_linux(ruta_destino)
        dir_destino = os.path.dirname(ruta_limpia)
        if not dir_destino:
            dir_destino = str(_APP_ROOT / "Nami" / "informes")
            ruta_limpia = os.path.join(dir_destino, "presentacion_marp.md")
        os.makedirs(dir_destino, exist_ok=True)
        
        with open(ruta_limpia, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write("marp: true\n")
            f.write("theme: default\n")
            f.write("paginate: true\n")
            f.write("---\n\n")
            
            f.write(f"# {tema_presentacion}\n")
            f.write("---\n\n")
            
            for index, slide_content in enumerate(contenido_diapositivas):
                f.write(f"{slide_content}\n")
                if index < len(contenido_diapositivas) - 1:
                    f.write("---\n\n")
                    
        return f"Éxito: Presentación Marp generada en {ruta_limpia}."
    except Exception as e:
        return f"Error: {str(e)}"

HERRAMIENTAS_PRESENTACIONES = [generar_presentacion_marp]
