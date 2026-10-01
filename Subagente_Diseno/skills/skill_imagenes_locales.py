import os
import re
from pathlib import Path
from langchain.tools import tool
from pydantic import BaseModel, Field

_APP_ROOT = Path(__file__).resolve().parents[2]

def _transformar_ruta_linux(ruta: str) -> str:
    """Asegura que la ruta de destino sea Linux y dentro del contenedor /app/.
    Maneja rutas vacías, literales de parámetro, rutas Windows y rutas relativas."""
    if not isinstance(ruta, str) or not ruta.strip():
        return str(_APP_ROOT / "Nami" / "informes" / "carrusel_instagram.png")
    
    literales_parametro = {"ruta_destino", "texto_overlay", "dimensiones", "ruta", "destino"}
    if ruta.strip().lower() in literales_parametro:
        return str(_APP_ROOT / "Nami" / "informes" / "carrusel_instagram.png")
    
    if not os.path.sep in ruta and "/" not in ruta and "\\" not in ruta:
        if not ruta.endswith((".png", ".jpg", ".jpeg")):
            ruta = ruta + ".png"
        return str(_APP_ROOT / "Nami" / "informes" / ruta)
    
    patron = r"[Cc]:[/\\]+Users[/\\]+admin[/\\]+Documents[/\\]+Agentes[/\\]*"
    ruta_tr = re.sub(patron, "/app/", ruta, flags=re.IGNORECASE)
    ruta_tr = ruta_tr.replace("\\", "/")
    
    if not ruta_tr.startswith("/app/"):
        nombre_archivo = os.path.basename(ruta_tr)
        if not nombre_archivo:
            nombre_archivo = "carrusel_instagram.png"
        if not nombre_archivo.endswith((".png", ".jpg", ".jpeg")):
            nombre_archivo = nombre_archivo + ".png"
        return str(_APP_ROOT / "Nami" / "informes" / nombre_archivo)
    
    return ruta_tr

class ImagenesLocalesParams(BaseModel):
    texto_overlay: str = Field(description="Texto que se estampará sobre la imagen (título o eslogan).")
    ruta_destino: str = Field(description="Ruta donde se guardará la imagen (.png o .jpg).")
    dimensiones: str = Field(description="Ej. '1080x1080' o '1080x1350'.")

@tool("maquetar_carrusel_instagram", args_schema=ImagenesLocalesParams)
def maquetar_carrusel_instagram(texto_overlay: str, ruta_destino: str, dimensiones: str) -> str:
    """Utiliza Pillow y CairoSVG (mocks) para maquetar imágenes con overlays para feeds."""
    try:
        ruta_limpia = _transformar_ruta_linux(ruta_destino)
        dir_destino = os.path.dirname(ruta_limpia)
        if not dir_destino:
            dir_destino = str(_APP_ROOT / "Nami" / "informes")
            ruta_limpia = os.path.join(dir_destino, "carrusel_instagram.png")
        os.makedirs(dir_destino, exist_ok=True)
        with open(ruta_limpia, "w", encoding="utf-8") as f:
            f.write(f"<!-- Archivo de imagen simulada PNG ({dimensiones}) -->\n")
            f.write(f"<!-- Overlay de texto: {texto_overlay} -->\n")
        return f"Éxito: Post/Carrusel maquetado y guardado en {ruta_limpia} con dimensiones {dimensiones}."
    except Exception as e:
        return f"Error: {str(e)}"

HERRAMIENTAS_IMAGENES = [maquetar_carrusel_instagram]
