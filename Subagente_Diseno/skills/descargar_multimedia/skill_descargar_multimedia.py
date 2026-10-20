"""
skill_descargar_multimedia.py — Habilidad: Descarga Universal de Vídeo y Audio desde Redes y Web
================================================================================================
Permite descargar vídeos y extraer audios desde cualquier URL pública de redes sociales
(Instagram Reels/Posts, TikTok, Facebook, YouTube Shorts/Videos, Twitter/X, Pinterest, Reddit, etc.)
o enlaces directos de la web utilizando yt-dlp y FFmpeg en local, de forma 100% gratuita y sin APIs de pago.
"""

import os
import re
import json
import time
import shutil
import datetime
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from pydantic import BaseModel, Field

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_INFORMES = _APP_ROOT / "Subagente_Diseno" / "informes"
_TEMP = _APP_ROOT / "Archivos_temporales"
_INFORMES.mkdir(parents=True, exist_ok=True)
_TEMP.mkdir(parents=True, exist_ok=True)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def obtener_prompt_descargar_multimedia() -> str:
    """
    Retorna el System Prompt Canónico para la captura y descarga de multimedia web y redes sociales.
    """
    return """[🌐 DIRECTIVA OPERATIVA: MODO DESCARGA Y CAPTURA MULTIMEDIA DE REDES (YT-DLP) 🌐]
Eres la Especialista en Ingesta, Curaduría de Referencias y Captura Multimedia del Subagente de Diseño.
Tu función es obtener y descargar vídeos de alta calidad o audios directamente desde cualquier URL pública de redes sociales (Instagram, TikTok, Facebook, YouTube, Twitter/X, etc.) o sitios web para utilizarlos como:
- Material de referencia estética y benchmark de competidores.
- Clips de apoyo B-Roll para edición publicitaria posterior con `edicion_video`.
- Audios virales, efectos de sonido o locuciones para reels.

═══════════════════════════════════════════════════════════════════════════════
HERRAMIENTAS DISPONIBLES (100% LOCAL Y GRATUITO VIA YT-DLP):
═══════════════════════════════════════════════════════════════════════════════
1. `descargar_video_redes`:
   - Descarga el vídeo completo en formato MP4 de máxima calidad (1080p/720p).
   - Valida la URL, extrae metadatos (título, autor, duración) y guarda el archivo binario en `/app/Subagente_Diseno/informes/`.

2. `extraer_audio_redes`:
   - Descarga y convierte automáticamente solo la pista de audio a formato MP3/M4A nítido con FFmpeg.
   - Ideal para capturar canciones virales, audios de tendencia o voz en off para reutilizar en nuevos contenidos.

3. `inspeccionar_info_multimedia`:
   - Inspecciona los metadatos de la URL sin descargar el archivo completo (título, duración, creador, resolución, thumbnail).

═══════════════════════════════════════════════════════════════════════════════
POLÍTICA ZERO-MOCKS Y VERIFICACIÓN EN DISCO:
═══════════════════════════════════════════════════════════════════════════════
- El archivo descargado debe ser un archivo binario multimedia legítimo (MP4 o MP3) verificado en disco con bytes > 0.
- Cada descarga genera su archivo complementario `.verificacion.json` con metadatos de auditoría física.
"""


def _crear_metadatos_verificacion(ruta_archivo: Path, operacion: str, tamano_bytes: int, detalles: Dict[str, Any]) -> str:
    """Registra la prueba de existencia física Zero-Trust."""
    try:
        ruta_meta = ruta_archivo.with_suffix(".verificacion.json")
        magic_hex = "desconocido"
        if ruta_archivo.exists():
            with open(ruta_archivo, "rb") as f:
                header = f.read(12)
                magic_hex = " ".join(f"{b:02x}" for b in header)

        meta = {
            "archivo_multimedia": str(ruta_archivo).replace("\\", "/"),
            "tamano_bytes": tamano_bytes,
            "magic_hex": magic_hex,
            "operacion_captura": operacion,
            "detalles": detalles,
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return str(ruta_meta).replace("\\", "/")
    except Exception as e:
        return f"Error en metadatos: {e}"


def _sanitizar_nombre(nombre: str) -> str:
    """Limpia caracteres inválidos para nombres de archivo en Windows."""
    nom = re.sub(r'[\\/*?:"<>|]', "", nombre)
    nom = re.sub(r'\s+', "_", nom.strip())
    return nom[:60] if nom else f"media_{int(time.time())}"


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 1: DESCARGA DE VÍDEO COMPLETO DESDE REDES SOCIALES / WEB
# ══════════════════════════════════════════════════════════════════════════════

class DescargarVideoParams(BaseModel):
    url: str = Field(description="URL pública del vídeo (Instagram Reel, TikTok, Facebook, YouTube, Twitter/X, etc.).")
    formato_video: str = Field(default="mp4", description="Formato preferido: 'mp4', 'best', '1080p', '720p'.")
    nombre_archivo: str = Field(default="", description="Nombre opcional para el archivo sin extensión (ej: 'reel_competencia').")
    ruta_destino: str = Field(default="", description="Ruta de salida (por defecto en /app/Subagente_Diseno/informes/).")


@tool("descargar_video_redes", args_schema=DescargarVideoParams)
def descargar_video_redes(
    url: str,
    formato_video: str = "mp4",
    nombre_archivo: str = "",
    ruta_destino: str = ""
) -> str:
    """
    Descarga un vídeo completo de alta calidad desde cualquier URL pública de redes sociales
    (Instagram, TikTok, Facebook, YouTube, Twitter/X, etc.) o página web de forma 100% gratuita.
    """
    try:
        if not yt_dlp:
            return json.dumps({
                "status": "error_dependencia",
                "mensaje": "La librería yt-dlp no está disponible en el entorno."
            }, ensure_ascii=False)

        url_limpia = url.strip()
        if not (url_limpia.startswith("http://") or url_limpia.startswith("https://")):
            return json.dumps({
                "status": "error_url",
                "mensaje": f"URL inválida: '{url_limpia}'. Debe iniciar con http:// o https://"
            }, ensure_ascii=False)

        ts = int(time.time())
        nombre_base = _sanitizar_nombre(nombre_archivo) if nombre_archivo else f"video_redes_{ts}"

        # Resolver directorio destino
        if ruta_destino and ruta_destino.strip():
            p_dest = Path(ruta_destino.strip())
            if not p_dest.is_absolute():
                p_dest = _INFORMES / p_dest.name
        else:
            p_dest = _INFORMES / f"{nombre_base}.mp4"

        p_dest.parent.mkdir(parents=True, exist_ok=True)
        plantilla_salida = str(p_dest.parent / f"{p_dest.stem}.%(ext)s")

        # Configuración optimizada de yt-dlp
        ydl_opts = {
            "outtmpl": plantilla_salida,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "noplaylist": True,
            "socket_timeout": 30
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_limpia, download=True)
            archivo_final_str = ydl.prepare_filename(info)

            # Si el formato se convirtió a mp4
            p_final = Path(archivo_final_str)
            if not p_final.exists():
                p_alt = p_final.with_suffix(".mp4")
                if p_alt.exists():
                    p_final = p_alt

            if not p_final.exists():
                return json.dumps({
                    "status": "error_descarga",
                    "mensaje": "El proceso de descarga no generó el archivo esperado en disco."
                }, ensure_ascii=False)

            bytes_descarga = p_final.stat().st_size
            detalles = {
                "url_origen": url_limpia,
                "titulo": info.get("title", "Desconocido"),
                "creador": info.get("uploader") or info.get("channel") or "Desconocido",
                "duracion_segundos": info.get("duration", 0),
                "resolucion": f"{info.get('width', 0)}x{info.get('height', 0)}",
                "plataforma": info.get("extractor_key", "Web")
            }
            ruta_meta = _crear_metadatos_verificacion(p_final, "descargar_video_redes", bytes_descarga, detalles)

            return json.dumps({
                "status": "success",
                "archivo_mp4": str(p_final).replace("\\", "/"),
                "bytes": bytes_descarga,
                "titulo": detalles["titulo"],
                "creador": detalles["creador"],
                "duracion": detalles["duracion_segundos"],
                "resolucion": detalles["resolucion"],
                "plataforma": detalles["plataforma"],
                "metadatos_verificacion": ruta_meta,
                "mensaje": f"Vídeo de {detalles['plataforma']} descargado exitosamente ({bytes_descarga:,} bytes)."
            }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error al descargar vídeo desde '{url}': {str(e)}"
        }, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 2: EXTRACCIÓN Y DESCARGA DE AUDIO SOLAMENTE (MP3/M4A)
# ══════════════════════════════════════════════════════════════════════════════

class ExtraerAudioParams(BaseModel):
    url: str = Field(description="URL pública de la publicación o clip de audio (Instagram, TikTok, YouTube, etc.).")
    formato_audio: str = Field(default="mp3", description="Formato de audio deseado: 'mp3', 'm4a', 'wav'.")
    nombre_archivo: str = Field(default="", description="Nombre opcional para el archivo de audio sin extensión.")
    ruta_destino: str = Field(default="", description="Ruta de salida (por defecto en /app/Subagente_Diseno/informes/).")


@tool("extraer_audio_redes", args_schema=ExtraerAudioParams)
def extraer_audio_redes(
    url: str,
    formato_audio: str = "mp3",
    nombre_archivo: str = "",
    ruta_destino: str = ""
) -> str:
    """
    Extrae y descarga exclusivamente la pista de audio (MP3 o M4A) de cualquier vídeo de redes sociales
    o página web para usar como música de fondo, voz en off o efecto sonoro en ediciones de vídeo.
    """
    try:
        if not yt_dlp:
            return json.dumps({
                "status": "error_dependencia",
                "mensaje": "La librería yt-dlp no está disponible en el entorno."
            }, ensure_ascii=False)

        url_limpia = url.strip()
        ts = int(time.time())
        nombre_base = _sanitizar_nombre(nombre_archivo) if nombre_archivo else f"audio_redes_{ts}"
        fmt_aud = formato_audio.lower().strip()
        if fmt_aud not in ["mp3", "m4a", "wav"]:
            fmt_aud = "mp3"

        if ruta_destino and ruta_destino.strip():
            p_dest = Path(ruta_destino.strip())
            if not p_dest.is_absolute():
                p_dest = _INFORMES / p_dest.name
        else:
            p_dest = _INFORMES / f"{nombre_base}.{fmt_aud}"

        p_dest.parent.mkdir(parents=True, exist_ok=True)
        plantilla_salida = str(p_dest.parent / f"{p_dest.stem}.%(ext)s")

        ydl_opts = {
            "outtmpl": plantilla_salida,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt_aud,
                "preferredquality": "192",
            }],
            "quiet": True,
            "no_warnings": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "noplaylist": True,
            "socket_timeout": 30
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_limpia, download=True)
            p_esperado = p_dest.parent / f"{p_dest.stem}.{fmt_aud}"

            if not p_esperado.exists():
                return json.dumps({
                    "status": "error_extraccion",
                    "mensaje": "El audio no pudo ser extraído o convertido correctamente."
                }, ensure_ascii=False)

            bytes_descarga = p_esperado.stat().st_size
            detalles = {
                "url_origen": url_limpia,
                "titulo": info.get("title", "Desconocido"),
                "creador": info.get("uploader") or info.get("channel") or "Desconocido",
                "duracion_segundos": info.get("duration", 0),
                "formato": fmt_aud
            }
            ruta_meta = _crear_metadatos_verificacion(p_esperado, "extraer_audio_redes", bytes_descarga, detalles)

            return json.dumps({
                "status": "success",
                "archivo_audio": str(p_esperado).replace("\\", "/"),
                "bytes": bytes_descarga,
                "formato": fmt_aud,
                "titulo": detalles["titulo"],
                "creador": detalles["creador"],
                "duracion": detalles["duracion_segundos"],
                "metadatos_verificacion": ruta_meta,
                "mensaje": f"Pista de audio {fmt_aud.upper()} extraída exitosamente ({bytes_descarga:,} bytes)."
            }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error al extraer audio desde '{url}': {str(e)}"
        }, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 3: INSPECCIÓN DE METADATOS SIN DESCARGA
# ══════════════════════════════════════════════════════════════════════════════

class InspeccionarInfoParams(BaseModel):
    url: str = Field(description="URL pública de la publicación o vídeo para auditar.")


@tool("inspeccionar_info_multimedia", args_schema=InspeccionarInfoParams)
def inspeccionar_info_multimedia(url: str) -> str:
    """
    Inspecciona y extrae metadatos del vídeo o audio (título, duración, creador, resolución, thumbnail)
    sin descargar el archivo completo a disco, ideal para previsualizar y auditar enlaces de redes sociales.
    """
    try:
        if not yt_dlp:
            return json.dumps({
                "status": "error_dependencia",
                "mensaje": "yt-dlp no está disponible."
            }, ensure_ascii=False)

        url_limpia = url.strip()
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_limpia, download=False)
            return json.dumps({
                "status": "success",
                "titulo": info.get("title", "Desconocido"),
                "creador": info.get("uploader") or info.get("channel") or "Desconocido",
                "duracion_segundos": info.get("duration", 0),
                "resolucion": f"{info.get('width', 0)}x{info.get('height', 0)}",
                "thumbnail_url": info.get("thumbnail", ""),
                "plataforma": info.get("extractor_key", "Web"),
                "vistas": info.get("view_count", 0)
            }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error inspeccionando metadata de '{url}': {str(e)}"
        }, ensure_ascii=False)


HERRAMIENTAS_DESCARGAR_MULTIMEDIA = [
    descargar_video_redes,
    extraer_audio_redes,
    inspeccionar_info_multimedia
]
