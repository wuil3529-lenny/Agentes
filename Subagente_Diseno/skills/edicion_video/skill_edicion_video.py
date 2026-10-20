"""
skill_edicion_video.py — Habilidad: Edición Dinámica de Vídeo y Motion Graphics
================================================================================
Postproducción programática para vídeo corto (Reels, TikTok, Shorts 1080x1920).
Cubre:
  1. Pop-up Motion Graphics / Animated Overlays (stickers, íconos, alertas).
  2. Auto B-Roll Integration (cutaway a pantalla completa o Picture-in-Picture).
  3. Kinetic Typography / Dynamic Captions (estilo Alex Hormozi / subtítulos virales).
  4. Lower Thirds (Terceros Inferiores) y Callouts explicativos.
  5. Ensamblado Completo de Edición Audiovisual.

Operación con FFmpeg 8.1 real en local (sin mocks) y verificación física en disco.
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
from PIL import Image, ImageDraw, ImageFont
from langchain_core.tools import tool
from pydantic import BaseModel, Field

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_INFORMES = _APP_ROOT / "Subagente_Diseno" / "informes"
_TEMP = _APP_ROOT / "Archivos_temporales"
_INFORMES.mkdir(parents=True, exist_ok=True)
_TEMP.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    _ENV_PATH = _APP_ROOT / ".env"
    if _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH)
except Exception:
    pass


def obtener_prompt_edicion_video() -> str:
    """
    Retorna el System Prompt Canónico para la edición dinámica y postproducción de vídeo.
    """
    return """[🎬 DIRECTIVA OPERATIVA: MODO EDICIÓN DINÁMICA DE VÍDEO Y MOTION GRAPHICS 🎬]
Eres la Editora de Postproducción y Diseñadora de Motion Graphics del Subagente de Diseño.
Tu misión es llevar vídeos crudos o clips publicitarios al estándar viral de alta retención para redes sociales (Reels, TikTok, YouTube Shorts en formato vertical 1080x1920).

═══════════════════════════════════════════════════════════════════════════════
LAS 4 TÉCNICAS NUCLEARES DE POSTPRODUCCIÓN Y RETENCIÓN VISUAL:
═══════════════════════════════════════════════════════════════════════════════
1. POP-UP MOTION GRAPHICS / ANIMATED OVERLAYS (`superponer_motion_overlay`):
   - Stickers, alertas, métricas e íconos flotantes que aparecen junto al hablante o producto en momentos clave.
   - Refuerzan visualmente la idea (ej. '🚀 +10X CRECIMIENTO', '⚡ RÁPIDO', '⚠️ ALERTA', '💡 TIP').
   - Regla de timing: Duración corta (2 a 3 segundos) con entrada precisa.

2. AUTO B-ROLL INTEGRATION (`insertar_broll`):
   - Inserción de material visual secundario (packshots generados con `ia_creativa`, clips de soporte o demostraciones).
   - Dos modalidades de visualización:
     * 'recuadro_pip': Picture-in-Picture elegante con marco y sombra flotando en una esquina mientras el hablante continúa.
     * 'pantalla_completa': Corte directo (cutaway) que cubre la pantalla durante 2-4 segundos para ilustrar lo narrado.

3. KINETIC TYPOGRAPHY / DYNAMIC CAPTIONS (`generar_subtitulos_dinamicos`):
   - Subtítulos dinámicos de alto impacto estilo Alex Hormozi o Reels virales.
   - Mayúsculas gruesas (Arial Bold / Impact), contraste máximo, borde exterior negro grueso (stroke) y sombra profunda.
   - Palabras clave destacadas en color vibrante (Amarillo neón #FFE600, Verde eléctrico #00FF66, Cian #00E5FF) sobre texto blanco.

4. LOWER THIRDS Y CALLOUTS EXPLICATIVOS (`generar_lower_third_callout`):
   - Banners y tarjetas en el tercio inferior o esquinas de la pantalla.
   - 'lower_third': Nombre del orador + cargo/handle en un banner de vidrio esmerilado con acento de color.
   - 'callout_tarjeta': Ficha flotante con datos, estadísticas o puntos clave enumerados.
   - 'stat_badge': Cifra destacada en grande con etiqueta descriptiva.

═══════════════════════════════════════════════════════════════════════════════
REGLAS TÉCNICAS Y ZERO-MOCKS:
═══════════════════════════════════════════════════════════════════════════════
- Renderizado 100% físico mediante FFmpeg y composiciones RGBA de Pillow.
- Prohibido crear archivos simulados de texto. Todo archivo .mp4 generado debe ser un binario legítimo verificado con bytes > 0 y ftyp magic hex en disco.
- Resolución vertical nativa: 1080x1920 (9:16).
- Si no se proporciona un vídeo base, el sistema crea un lienzo base vertical elegante a partir de imágenes previas o fondos de estudio para verificar la edición en One-Shot.
"""


def _obtener_fuente(tamano: int = 36, negrita: bool = True) -> ImageFont.ImageFont:
    """Carga una fuente TTF del sistema o usa default si falla."""
    candidatas = [
        "C:/Windows/Fonts/impact.ttf" if negrita else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if negrita else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if negrita else "C:/Windows/Fonts/segoeui.ttf",
        "arialbd.ttf",
        "arial.ttf"
    ]
    for c in candidatas:
        try:
            return ImageFont.truetype(c, tamano)
        except Exception:
            continue
    return ImageFont.load_default()


def _crear_metadatos_verificacion(ruta_mp4: Path, operacion: str, tamano_bytes: int, detalles: Dict[str, Any]) -> str:
    """Registra la prueba de existencia física Zero-Trust."""
    try:
        ruta_meta = ruta_mp4.with_suffix(".verificacion.json")
        magic_hex = "desconocido"
        if ruta_mp4.exists():
            with open(ruta_mp4, "rb") as f:
                header = f.read(12)
                magic_hex = " ".join(f"{b:02x}" for b in header)

        meta = {
            "archivo_mp4": str(ruta_mp4).replace("\\", "/"),
            "tamano_bytes": tamano_bytes,
            "magic_hex": magic_hex,
            "operacion_edicion": operacion,
            "detalles": detalles,
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return str(ruta_meta).replace("\\", "/")
    except Exception as e:
        return f"Error en metadatos: {e}"


def _asegurar_video_base(ruta: str, duracion_s: float = 5.0) -> str:
    """
    Garantiza un vídeo base MP4 1080x1920 válido.
    Si la ruta ya es un MP4 existente, la retorna.
    Si es una imagen estática existente, la convierte a un MP4 en bucle de duracion_s.
    Si está vacía o no existe, crea un clip vertical elegante de estudio 1080x1920.
    """
    if ruta and isinstance(ruta, str):
        p = Path(ruta.strip())
        if not p.is_absolute():
            p_inf = _INFORMES / p.name
            if p_inf.exists():
                p = p_inf
            else:
                p_tmp = _TEMP / p.name
                if p_tmp.exists():
                    p = p_tmp

        if p.exists() and p.is_file():
            if p.suffix.lower() == ".mp4":
                return str(p).replace("\\", "/")
            elif p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                # Convertir imagen fija a clip vertical de vídeo
                clip_generado = _TEMP / f"clip_base_{p.stem}.mp4"
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(p),
                    "-c:v", "libx264", "-t", str(duracion_s),
                    "-pix_fmt", "yuv420p",
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#0f172a",
                    str(clip_generado)
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                return str(clip_generado).replace("\\", "/")

    # Caso por defecto: Generar un lienzo de estudio vertical elegante
    lienzo_img_p = _TEMP / "canvas_estudio_vertical.png"
    img = Image.new("RGB", (1080, 1920), color=(15, 23, 42)) # Slate 900
    draw = ImageDraw.Draw(img)
    # Dibujar iluminación de estudio sutil en el fondo
    for r in range(400, 0, -20):
        alpha_color = (25 + int((400 - r) * 0.05), 35 + int((400 - r) * 0.05), 55 + int((400 - r) * 0.08))
        draw.ellipse([(540 - r, 800 - r), (540 + r, 800 + r)], fill=alpha_color)
    draw.text((380, 1750), "SUBAGENTE DE DISEÑO — ESTUDIO", fill=(100, 116, 139))
    img.save(lienzo_img_p)

    clip_canvas = _TEMP / "lienzo_base_default.mp4"
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(lienzo_img_p),
        "-c:v", "libx264", "-t", str(duracion_s),
        "-pix_fmt", "yuv420p",
        str(clip_canvas)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return str(clip_canvas).replace("\\", "/")


def _resolver_ruta_salida(ruta_destino: str, prefijo: str) -> Path:
    """Normaliza la ruta destino en informes."""
    if not ruta_destino or not isinstance(ruta_destino, str) or not ruta_destino.strip():
        ts = int(time.time())
        return _INFORMES / f"{prefijo}_{ts}.mp4"
    p = Path(ruta_destino.strip())
    nom = p.name
    if not nom.lower().endswith(".mp4"):
        nom += ".mp4"
    return _INFORMES / nom


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 1: POP-UP MOTION GRAPHICS / ANIMATED OVERLAYS
# ══════════════════════════════════════════════════════════════════════════════

class MotionOverlayParams(BaseModel):
    video_base: str = Field(default="", description="Ruta del clip de vídeo .mp4 (o imagen de producto para crear base).")
    texto_o_etiqueta: str = Field(default="🚀 +10X CRECIMIENTO", description="Texto o concepto visual del badge (ej. '🚀 +10X CRECIMIENTO', '⚠️ ATENCIÓN', '💡 TIP DE ORO', '⚡ 100% AUTOMATIZADO').")
    tipo_overlay: str = Field(default="sticker", description="Tipo de elemento: 'sticker', 'icono', 'alerta', 'metrica', 'emoji'.")
    posicion: str = Field(default="arriba_derecha", description="Ubicación: 'arriba_derecha', 'arriba_izquierda', 'centro_derecha', 'centro_izquierda', 'abajo_derecha'.")
    tiempo_inicio: float = Field(default=1.0, description="Segundo exacto en el que aparece el gráfico flotante.")
    duracion: float = Field(default=2.5, description="Tiempo de permanencia en pantalla en segundos (típico 2 a 3.5s).")
    ruta_destino: str = Field(default="", description="Ruta de salida del vídeo final .mp4.")


@tool("superponer_motion_overlay", args_schema=MotionOverlayParams)
def superponer_motion_overlay(
    video_base: str = "",
    texto_o_etiqueta: str = "🚀 +10X CRECIMIENTO",
    tipo_overlay: str = "sticker",
    posicion: str = "arriba_derecha",
    tiempo_inicio: float = 1.0,
    duracion: float = 2.5,
    ruta_destino: str = ""
) -> str:
    """
    Inserta un Pop-up Motion Graphic / Overlay animado (sticker, ícono o badge flotante)
    al lado del hablante o producto en pantalla para reforzar visualmente el concepto clave.
    """
    try:
        vid_in = _asegurar_video_base(video_base, duracion_s=max(5.0, tiempo_inicio + duracion + 1.5))
        vid_out_p = _resolver_ruta_salida(ruta_destino, "video_motion_overlay")

        # 1. Crear el Badge Gráfico RGBA con Pillow
        w_badge, h_badge = 520, 130
        badge_img = Image.new("RGBA", (w_badge, h_badge), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge_img)

        # Paleta según tipo
        paletas = {
            "alerta": {"bg": (220, 38, 38, 235), "border": (254, 202, 202, 255), "txt": (255, 255, 255)},
            "metrica": {"bg": (15, 23, 42, 240), "border": (34, 197, 94, 255), "txt": (74, 222, 128)},
            "icono": {"bg": (30, 41, 59, 240), "border": (56, 189, 248, 255), "txt": (240, 249, 255)},
            "sticker": {"bg": (24, 24, 27, 245), "border": (250, 204, 21, 255), "txt": (254, 240, 138)}
        }
        pal = paletas.get(tipo_overlay.lower(), paletas["sticker"])

        # Fondo con esquinas redondeadas y borde brillante
        draw.rounded_rectangle([(4, 4), (w_badge - 4, h_badge - 4)], radius=28, fill=pal["bg"], outline=pal["border"], width=4)

        # Texto centrado y nítido
        font = _obtener_fuente(tamano=34, negrita=True)
        bbox = draw.textbbox((0, 0), texto_o_etiqueta, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (w_badge - tw) // 2
        ty = (h_badge - th) // 2 - 4
        draw.text((tx, ty), texto_o_etiqueta, fill=pal["txt"], font=font)

        badge_path = _TEMP / f"temp_overlay_{int(time.time() * 1000)}.png"
        badge_img.save(badge_path)

        # 2. Calcular coordenadas en formato 1080x1920
        coords = {
            "arriba_derecha": (520, 240),
            "arriba_izquierda": (60, 240),
            "centro_derecha": (520, 800),
            "centro_izquierda": (60, 800),
            "abajo_derecha": (520, 1450)
        }
        x_pos, y_pos = coords.get(posicion.lower(), (520, 240))
        t_fin = tiempo_inicio + duracion

        # 3. Invocar FFmpeg con filtro de superposición temporizada
        filtro = f"[0:v][1:v]overlay=x={x_pos}:y={y_pos}:enable='between(t,{tiempo_inicio:.2f},{t_fin:.2f})'[v]"
        cmd = [
            "ffmpeg", "-y",
            "-i", vid_in,
            "-i", str(badge_path),
            "-filter_complex", filtro,
            "-map", "[v]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(vid_out_p)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return json.dumps({
                "status": "error_ffmpeg",
                "detalle": res.stderr[-400:],
                "mensaje": "Fallo al procesar el filtro de overlay con FFmpeg."
            }, ensure_ascii=False)

        bytes_salida = vid_out_p.stat().st_size
        detalles = {
            "texto": texto_o_etiqueta,
            "tipo": tipo_overlay,
            "posicion": posicion,
            "intervalo": f"{tiempo_inicio}s - {t_fin}s",
            "coordenadas": f"x={x_pos}, y={y_pos}"
        }
        ruta_meta = _crear_metadatos_verificacion(vid_out_p, "superponer_motion_overlay", bytes_salida, detalles)

        return json.dumps({
            "status": "success",
            "archivo_mp4": str(vid_out_p).replace("\\", "/"),
            "bytes": bytes_salida,
            "metadatos_verificacion": ruta_meta,
            "mensaje": f"Pop-up motion overlay superpuesto exitosamente en [{tiempo_inicio}s a {t_fin}s]."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en superponer_motion_overlay: {str(e)}"}, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 2: AUTO B-ROLL INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

class AutoBRollParams(BaseModel):
    video_base: str = Field(default="", description="Ruta del vídeo principal del orador/escena.")
    medio_broll: str = Field(default="", description="Ruta de la imagen o clip de soporte (packshot, gráfico, vídeo secundario). Si se omite, se genera un mockup de producto automático.")
    modo: str = Field(default="recuadro_pip", description="Modalidad de inserción: 'recuadro_pip' (Picture-in-Picture flotante) o 'pantalla_completa' (corte completo de apoyo).")
    posicion_pip: str = Field(default="arriba_derecha", description="Posición en modo PiP: 'arriba_derecha', 'arriba_izquierda', 'abajo_derecha', 'abajo_izquierda'.")
    tiempo_inicio: float = Field(default=1.5, description="Segundo donde comienza la inserción del B-Roll.")
    duracion: float = Field(default=3.0, description="Duración del B-Roll en segundos (típico 2 a 4s).")
    ruta_destino: str = Field(default="", description="Ruta de salida del archivo .mp4.")


@tool("insertar_broll", args_schema=AutoBRollParams)
def insertar_broll(
    video_base: str = "",
    medio_broll: str = "",
    modo: str = "recuadro_pip",
    posicion_pip: str = "arriba_derecha",
    tiempo_inicio: float = 1.5,
    duracion: float = 3.0,
    ruta_destino: str = ""
) -> str:
    """
    Inserta contenido de soporte (B-Roll) dentro del vídeo principal,
    ya sea como un recuadro Picture-in-Picture (PiP) flotante o como un corte de apoyo a pantalla completa.
    """
    try:
        t_fin = tiempo_inicio + duracion
        vid_in = _asegurar_video_base(video_base, duracion_s=max(6.0, t_fin + 1.5))
        vid_out_p = _resolver_ruta_salida(ruta_destino, "video_broll_integrado")

        # Verificar medio b-roll
        broll_p = None
        if medio_broll and isinstance(medio_broll, str) and medio_broll.strip():
            candidato = Path(medio_broll.strip())
            if candidato.is_file():
                broll_p = candidato
            elif (_INFORMES / candidato.name).is_file():
                broll_p = _INFORMES / candidato.name
            elif (_TEMP / candidato.name).is_file():
                broll_p = _TEMP / candidato.name

        if not broll_p or not broll_p.is_file():
            # Si no existe, crear un asset de B-Roll de producto ilustrativo
            broll_p = _TEMP / "demo_broll_product_card.png"
            bimg = Image.new("RGB", (640, 640), color=(30, 41, 59))
            bdraw = ImageDraw.Draw(bimg)
            bdraw.rounded_rectangle([(10, 10), (630, 630)], radius=32, fill=(15, 23, 42), outline=(56, 189, 248), width=6)
            bdraw.text((120, 260), "B-ROLL: PRODUCTO", fill=(255, 255, 255), font=_obtener_fuente(36, True))
            bdraw.text((160, 320), "Vista de Detalle 4K", fill=(148, 163, 184), font=_obtener_fuente(28, False))
            bimg.save(broll_p)

        es_imagen = broll_p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]

        # Configurar filtros según el modo
        if modo.lower() == "pantalla_completa":
            filtro = f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[broll_crop];[0:v][broll_crop]overlay=x=0:y=0:enable='between(t,{tiempo_inicio:.2f},{t_fin:.2f})'[v]"
        else:
            # Recuadro PiP (480x480 con borde y posición)
            coords_pip = {
                "arriba_derecha": (540, 220),
                "arriba_izquierda": (60, 220),
                "abajo_derecha": (540, 1150),
                "abajo_izquierda": (60, 1150)
            }
            px, py = coords_pip.get(posicion_pip.lower(), (540, 220))
            filtro = (
                f"[1:v]scale=480:480:force_original_aspect_ratio=increase,crop=480:480,"
                f"pad=496:496:8:8:color=#38bdf8[broll_pip];"
                f"[0:v][broll_pip]overlay=x={px}:y={py}:enable='between(t,{tiempo_inicio:.2f},{t_fin:.2f})'[v]"
            )

        cmd = ["ffmpeg", "-y", "-i", vid_in]
        if es_imagen:
            cmd.extend(["-loop", "1", "-t", str(t_fin + 1.0), "-i", str(broll_p)])
        else:
            cmd.extend(["-i", str(broll_p)])

        cmd.extend([
            "-filter_complex", filtro,
            "-map", "[v]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(vid_out_p)
        ])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return json.dumps({
                "status": "error_ffmpeg",
                "detalle": res.stderr[-400:],
                "mensaje": "Fallo al insertar B-Roll con FFmpeg."
            }, ensure_ascii=False)

        bytes_salida = vid_out_p.stat().st_size
        detalles = {
            "medio_broll": str(broll_p).replace("\\", "/"),
            "modo": modo,
            "posicion_pip": posicion_pip if modo == "recuadro_pip" else "n/a",
            "intervalo": f"{tiempo_inicio}s - {t_fin}s"
        }
        ruta_meta = _crear_metadatos_verificacion(vid_out_p, "insertar_broll", bytes_salida, detalles)

        return json.dumps({
            "status": "success",
            "archivo_mp4": str(vid_out_p).replace("\\", "/"),
            "bytes": bytes_salida,
            "metadatos_verificacion": ruta_meta,
            "mensaje": f"B-Roll insertado exitosamente en modalidad '{modo}' de {tiempo_inicio}s a {t_fin}s."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en insertar_broll: {str(e)}"}, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 3: KINETIC TYPOGRAPHY / DYNAMIC CAPTIONS (ESTILO HORMOZI)
# ══════════════════════════════════════════════════════════════════════════════

class SubtitulosDinamicosParams(BaseModel):
    video_base: str = Field(default="", description="Ruta del clip de vídeo .mp4.")
    lineas_subtitulos: str = Field(
        default='[{"inicio":0.5,"fin":2.0,"texto":"ESTA ESTRATEGIA CAMBIÓ TODO","palabra_clave":"ESTRATEGIA"}]',
        description="JSON de frases con tiempos (ej: '[{\"inicio\":0.5,\"fin\":2.0,\"texto\":\"ESTA ESTRATEGIA CAMBIÓ TODO\",\"palabra_clave\":\"ESTRATEGIA\"}]') o texto separado por comas."
    )
    estilo: str = Field(default="hormozi", description="Paleta y estilo: 'hormozi' (amarillo y blanco sobre negro), 'neon_green' (verde neón y blanco), 'cyber_cyan' (cian eléctrico y blanco).")
    posicion_vertical: str = Field(default="tercio_medio", description="Ubicación vertical: 'centro', 'tercio_medio' (óptimo para Reels) o 'tercio_inferior'.")
    ruta_destino: str = Field(default="", description="Ruta de salida del vídeo final .mp4.")


@tool("generar_subtitulos_dinamicos", args_schema=SubtitulosDinamicosParams)
def generar_subtitulos_dinamicos(
    video_base: str = "",
    lineas_subtitulos: str = '[{"inicio":0.5,"fin":2.0,"texto":"ESTA ESTRATEGIA CAMBIÓ TODO","palabra_clave":"ESTRATEGIA"}]',
    estilo: str = "hormozi",
    posicion_vertical: str = "tercio_medio",
    ruta_destino: str = ""
) -> str:
    """
    Incrusta subtítulos cinemáticos dinámicos de alto impacto (estilo Alex Hormozi o Reels virales)
    con tipografía bold en mayúsculas, contorno negro grueso y resaltado de palabras clave.
    """
    try:
        # 1. Parsear las líneas
        frases = []
        try:
            frases = json.loads(lineas_subtitulos)
        except Exception:
            # Si se pasa texto plano separado por líneas o comas
            partes = [p.strip() for p in lineas_subtitulos.split("\n") if p.strip()] or [lineas_subtitulos]
            t_actual = 0.5
            for p in partes:
                palabras = p.split()
                kw = palabras[-1] if palabras else ""
                frases.append({"inicio": t_actual, "fin": t_actual + 1.8, "texto": p.upper(), "palabra_clave": kw.upper()})
                t_actual += 2.0

        dur_max = max(f.get("fin", 4.0) for f in frases) if frases else 4.0
        vid_in = _asegurar_video_base(video_base, duracion_s=dur_max + 1.0)
        vid_out_p = _resolver_ruta_salida(ruta_destino, "video_subtitulado_hormozi")

        # 2. Paletas de color en formato ASS (&HAABBGGRR)
        estilos_color = {
            "hormozi": {"primary": "&H00FFFFFF", "highlight": "&H0000FFFF"},    # Blanco con amarillo (#FFFF00)
            "neon_green": {"primary": "&H00FFFFFF", "highlight": "&H0000FF00"}, # Blanco con verde (#00FF00)
            "cyber_cyan": {"primary": "&H00FFFFFF", "highlight": "&H00FFFF00"}   # Blanco con cian (#00FFFF)
        }
        pal = estilos_color.get(estilo.lower(), estilos_color["hormozi"])

        # Margen vertical según posición
        margin_v = 400 if posicion_vertical == "tercio_inferior" else (850 if posicion_vertical == "tercio_medio" else 960)

        # 3. Construir el archivo .ass
        ass_path = _TEMP / f"subtitulos_{int(time.time() * 1000)}.ass"
        lineas_eventos = []

        for f in frases:
            t_ini = float(f.get("inicio", 0.0))
            t_end = float(f.get("fin", t_ini + 1.5))
            texto = str(f.get("texto", "")).upper()
            palabra_kw = str(f.get("palabra_clave", "")).upper().strip()

            def _seg_a_ass(s):
                h = int(s // 3600)
                m = int((s % 3600) // 60)
                sec = s % 60
                return f"{h:01d}:{m:02d}:{sec:05.2f}"

            t_ini_str = _seg_a_ass(t_ini)
            t_end_str = _seg_a_ass(t_end)

            if palabra_kw and palabra_kw in texto:
                # Resaltar la palabra clave con color highlight
                reemplazo = f"{{\\c{pal['highlight']}}}{palabra_kw}{{\\c{pal['primary']}}}"
                texto_formateado = texto.replace(palabra_kw, reemplazo, 1)
            else:
                texto_formateado = texto

            lineas_eventos.append(
                f"Dialogue: 0,{t_ini_str},{t_end_str},HormoziStyle,,0,0,0,,{texto_formateado}"
            )

        eventos_ass = "\n".join(lineas_eventos)
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HormoziStyle,Arial,68,{pal['primary']},{pal['highlight']},&H00000000,&H80000000,1,0,0,0,100,100,2,0,1,7,3,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{eventos_ass}
"""
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_header)

        # 4. Renderizar con FFmpeg usando el filtro libass relativo
        # Se usa ruta relativa con barras normales para compatibilidad multiplataforma
        rel_ass = os.path.relpath(ass_path, _APP_ROOT).replace("\\", "/")
        cmd = [
            "ffmpeg", "-y",
            "-i", vid_in,
            "-vf", f"ass={rel_ass}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(vid_out_p)
        ]
        res = subprocess.run(cmd, cwd=str(_APP_ROOT), capture_output=True, text=True)
        if res.returncode != 0:
            return json.dumps({
                "status": "error_ffmpeg",
                "detalle": res.stderr[-400:],
                "mensaje": "Fallo al incrustar subtítulos dinámicos con libass en FFmpeg."
            }, ensure_ascii=False)

        bytes_salida = vid_out_p.stat().st_size
        detalles = {
            "estilo": estilo,
            "frases_procesadas": len(frases),
            "posicion_vertical": posicion_vertical,
            "ass_script": str(ass_path).replace("\\", "/")
        }
        ruta_meta = _crear_metadatos_verificacion(vid_out_p, "generar_subtitulos_dinamicos", bytes_salida, detalles)

        return json.dumps({
            "status": "success",
            "archivo_mp4": str(vid_out_p).replace("\\", "/"),
            "bytes": bytes_salida,
            "metadatos_verificacion": ruta_meta,
            "mensaje": f"Subtítulos dinámicos estilo '{estilo}' incrustados exitosamente con {len(frases)} bloques temporales."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en generar_subtitulos_dinamicos: {str(e)}"}, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 4: LOWER THIRDS Y CALLOUTS EXPLICATIVOS
# ══════════════════════════════════════════════════════════════════════════════

class LowerThirdParams(BaseModel):
    video_base: str = Field(default="", description="Ruta del clip de vídeo .mp4.")
    titulo: str = Field(default="DIRECTOR CREATIVO", description="Texto principal del rótulo (ej. 'CARLOS MÉNDEZ' o 'TASA DE CONVERSIÓN').")
    subtitulo: str = Field(default="", description="Línea secundaria descriptiva (ej. 'Lead Architect & Founder' o '+140% en 30 días').")
    tipo: str = Field(default="lower_third", description="Formato del rótulo: 'lower_third' (banner horizontal inferior), 'callout_tarjeta' (ficha flotante en esquina), 'stat_badge' (cifra destacada).")
    posicion: str = Field(default="inferior_izquierda", description="Ubicación: 'inferior_izquierda', 'inferior_derecha', 'superior_izquierda', 'superior_derecha'.")
    tiempo_inicio: float = Field(default=0.8, description="Segundo de entrada del rótulo.")
    duracion: float = Field(default=3.5, description="Tiempo visible en pantalla en segundos.")
    ruta_destino: str = Field(default="", description="Ruta de salida del vídeo final .mp4.")


@tool("generar_lower_third_callout", args_schema=LowerThirdParams)
def generar_lower_third_callout(
    video_base: str = "",
    titulo: str = "DIRECTOR CREATIVO",
    subtitulo: str = "Agentes Autónomos & IA",
    tipo: str = "lower_third",
    posicion: str = "inferior_izquierda",
    tiempo_inicio: float = 0.8,
    duracion: float = 3.5,
    ruta_destino: str = ""
) -> str:
    """
    Genera y superpone un Lower Third (Tercero Inferior) o Callout explicativo
    para mostrar nombres, cargos, citas, datos clave o resúmenes en las esquinas o bordes del vídeo.
    """
    try:
        t_fin = tiempo_inicio + duracion
        vid_in = _asegurar_video_base(video_base, duracion_s=max(5.0, t_fin + 1.2))
        vid_out_p = _resolver_ruta_salida(ruta_destino, "video_lower_third")

        # 1. Crear el Banner Gráfico con Pillow
        w_card, h_card = 640, 160
        card_img = Image.new("RGBA", (w_card, h_card), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card_img)

        # Estilo Dark Neo-Bento con acento azul/cian
        draw.rounded_rectangle([(0, 0), (w_card, h_card)], radius=20, fill=(15, 23, 42, 235), outline=(51, 65, 85, 255), width=2)
        # Barra lateral de acento de marca (accent bar)
        draw.rounded_rectangle([(6, 12), (18, h_card - 12)], radius=6, fill=(56, 189, 248, 255))

        # Tipografía y jerarquía
        font_tit = _obtener_fuente(tamano=34, negrita=True)
        font_sub = _obtener_fuente(tamano=24, negrita=False)

        draw.text((36, 32), titulo.upper(), fill=(255, 255, 255), font=font_tit)
        if subtitulo:
            draw.text((36, 85), subtitulo, fill=(148, 163, 184), font=font_sub)

        card_path = _TEMP / f"temp_lt_{int(time.time() * 1000)}.png"
        card_img.save(card_path)

        # 2. Coordenadas según posición (márgenes seguros de Reels)
        coords = {
            "inferior_izquierda": (70, 1500),
            "inferior_derecha": (370, 1500),
            "superior_izquierda": (70, 200),
            "superior_derecha": (370, 200)
        }
        x_pos, y_pos = coords.get(posicion.lower(), (70, 1500))

        # 3. Superponer mediante FFmpeg
        filtro = f"[0:v][1:v]overlay=x={x_pos}:y={y_pos}:enable='between(t,{tiempo_inicio:.2f},{t_fin:.2f})'[v]"
        cmd = [
            "ffmpeg", "-y",
            "-i", vid_in,
            "-i", str(card_path),
            "-filter_complex", filtro,
            "-map", "[v]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(vid_out_p)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return json.dumps({
                "status": "error_ffmpeg",
                "detalle": res.stderr[-400:],
                "mensaje": "Fallo al generar lower third con FFmpeg."
            }, ensure_ascii=False)

        bytes_salida = vid_out_p.stat().st_size
        detalles = {
            "titulo": titulo,
            "subtitulo": subtitulo,
            "tipo": tipo,
            "posicion": posicion,
            "intervalo": f"{tiempo_inicio}s - {t_fin}s"
        }
        ruta_meta = _crear_metadatos_verificacion(vid_out_p, "generar_lower_third_callout", bytes_salida, detalles)

        return json.dumps({
            "status": "success",
            "archivo_mp4": str(vid_out_p).replace("\\", "/"),
            "bytes": bytes_salida,
            "metadatos_verificacion": ruta_meta,
            "mensaje": f"Lower third / Callout '{titulo}' integrado exitosamente en {posicion} de {tiempo_inicio}s a {t_fin}s."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en generar_lower_third_callout: {str(e)}"}, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 5: ENSAMBLADO COMPLETO DE EDICIÓN MULTI-CAPA
# ══════════════════════════════════════════════════════════════════════════════

class EnsambladoEdicionParams(BaseModel):
    video_base: str = Field(default="", description="Ruta del clip de vídeo .mp4.")
    titulo_lower_third: str = Field(default="", description="Texto para lower third o nombre de orador.")
    subtitulo_lower_third: str = Field(default="", description="Subtítulo o cargo del lower third.")
    sticker_overlay: str = Field(default="", description="Texto de sticker/alerta motion (ej. '🚀 +10X CRECIMIENTO').")
    medio_broll: str = Field(default="", description="Ruta de asset o imagen para B-roll PiP.")
    lineas_subtitulos: str = Field(default="", description="Subtítulos dinámicos en formato JSON o texto.")
    ruta_destino: str = Field(default="", description="Ruta final del archivo renderizado .mp4.")


@tool("ensamblar_edicion_video_completa", args_schema=EnsambladoEdicionParams)
def ensamblar_edicion_video_completa(
    video_base: str = "",
    titulo_lower_third: str = "",
    subtitulo_lower_third: str = "",
    sticker_overlay: str = "",
    medio_broll: str = "",
    lineas_subtitulos: str = "",
    ruta_destino: str = ""
) -> str:
    """
    Ejecuta el pipeline integral de postproducción encadenando las capas solicitadas
    (Lower Thirds, Pop-up Overlays, B-Roll PiP y Subtítulos Dinámicos) en un único entregable final verificado.
    """
    try:
        vid_actual = _asegurar_video_base(video_base, duracion_s=6.0)
        pasos_ejecutados = []

        # Paso 1: Lower Third
        if titulo_lower_third:
            res_lt = json.loads(generar_lower_third_callout.invoke({
                "video_base": vid_actual,
                "titulo": titulo_lower_third,
                "subtitulo": subtitulo_lower_third,
                "tiempo_inicio": 0.5,
                "duracion": 3.0
            }))
            if res_lt.get("status") == "success":
                vid_actual = res_lt["archivo_mp4"]
                pasos_ejecutados.append("lower_third")

        # Paso 2: Motion Overlay
        if sticker_overlay:
            res_ov = json.loads(superponer_motion_overlay.invoke({
                "video_base": vid_actual,
                "texto_o_etiqueta": sticker_overlay,
                "tiempo_inicio": 2.0,
                "duracion": 2.5
            }))
            if res_ov.get("status") == "success":
                vid_actual = res_ov["archivo_mp4"]
                pasos_ejecutados.append("motion_overlay")

        # Paso 3: B-Roll PiP
        if medio_broll:
            res_br = json.loads(insertar_broll.invoke({
                "video_base": vid_actual,
                "medio_broll": medio_broll,
                "modo": "recuadro_pip",
                "tiempo_inicio": 2.5,
                "duracion": 2.8
            }))
            if res_br.get("status") == "success":
                vid_actual = res_br["archivo_mp4"]
                pasos_ejecutados.append("broll_pip")

        # Paso 4: Subtítulos Dinámicos
        if lineas_subtitulos:
            res_sub = json.loads(generar_subtitulos_dinamicos.invoke({
                "video_base": vid_actual,
                "lineas_subtitulos": lineas_subtitulos,
                "estilo": "hormozi"
            }))
            if res_sub.get("status") == "success":
                vid_actual = res_sub["archivo_mp4"]
                pasos_ejecutados.append("subtitulos_dinamicos")

        # Mover a destino final si se especificó
        salida_final_p = _resolver_ruta_salida(ruta_destino, "reel_postproducido_completo")
        if str(salida_final_p) != vid_actual:
            shutil.copy2(vid_actual, salida_final_p)
            vid_actual = str(salida_final_p).replace("\\", "/")

        bytes_final = Path(vid_actual).stat().st_size
        ruta_meta = _crear_metadatos_verificacion(Path(vid_actual), "ensamblar_edicion_video_completa", bytes_final, {"capas": pasos_ejecutados})

        return json.dumps({
            "status": "success",
            "archivo_mp4": vid_actual,
            "bytes": bytes_final,
            "capas_aplicadas": pasos_ejecutados,
            "metadatos_verificacion": ruta_meta,
            "mensaje": f"Vídeo ensamblado con éxito incorporando {len(pasos_ejecutados)} técnicas de postproducción."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en ensamblado completo: {str(e)}"}, ensure_ascii=False)


HERRAMIENTAS_EDICION_VIDEO = [
    superponer_motion_overlay,
    insertar_broll,
    generar_subtitulos_dinamicos,
    generar_lower_third_callout,
    ensamblar_edicion_video_completa
]
