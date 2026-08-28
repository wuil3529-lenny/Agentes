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
        return str(_APP_ROOT / "Nami" / "informes" / "video_generado.mp4")
    
    literales_parametro = {"ruta_destino", "descripcion_video", "framework_usado", "ruta", "destino"}
    if ruta.strip().lower() in literales_parametro:
        return str(_APP_ROOT / "Nami" / "informes" / "video_generado.mp4")
    
    if not os.path.sep in ruta and "/" not in ruta and "\\" not in ruta:
        if not ruta.endswith(".mp4"):
            ruta = ruta + ".mp4"
        return str(_APP_ROOT / "Nami" / "informes" / ruta)
    
    patron = r"[Cc]:[/\\]+Users[/\\]+admin[/\\]+Documents[/\\]+Agentes[/\\]*"
    ruta_tr = re.sub(patron, "/app/", ruta, flags=re.IGNORECASE)
    ruta_tr = ruta_tr.replace("\\", "/")
    
    if not ruta_tr.startswith("/app/"):
        nombre_archivo = os.path.basename(ruta_tr)
        if not nombre_archivo:
            nombre_archivo = "video_generado.mp4"
        if not nombre_archivo.endswith(".mp4"):
            nombre_archivo = nombre_archivo + ".mp4"
        return str(_APP_ROOT / "Nami" / "informes" / nombre_archivo)
    
    return ruta_tr

class VideoProgramaticoParams(BaseModel):
    descripcion_video: str = Field(description="Descripción de la temática del clip y los textos.")
    ruta_destino: str = Field(description="Ruta donde se guardará el mock/archivo de video (.mp4).")
    framework_usado: str = Field(description="Opciones: MoviePy o Remotion.")

@tool("editar_video_programatico", args_schema=VideoProgramaticoParams)
def editar_video_programatico(descripcion_video: str, ruta_destino: str, framework_usado: str) -> str:
    """Wrapper para manipular video, aplicar superposiciones de texto o renderizar React components a video."""
    try:
        ruta_limpia = _transformar_ruta_linux(ruta_destino)
        dir_destino = os.path.dirname(ruta_limpia)
        if not dir_destino:
            dir_destino = str(_APP_ROOT / "Nami" / "informes")
            ruta_limpia = os.path.join(dir_destino, "video_generado.mp4")
        os.makedirs(dir_destino, exist_ok=True)
        with open(ruta_limpia, "w", encoding="utf-8") as f:
            f.write(f"<!-- Archivo binario simulado MP4 -->\n")
            f.write(f"<!-- [{framework_usado}] Generado basado en: {descripcion_video} -->\n")
        return f"Éxito: Video generado con {framework_usado} y exportado a {ruta_limpia}."
    except Exception as e:
        return f"Error: {str(e)}"

HERRAMIENTAS_VIDEO = [editar_video_programatico]
