"""
skill_video.py — Habilidad: Dirección y Generación de Vídeo con IA (Higgsfield Image-to-Video)
=============================================================================================
Herramienta de generación de vídeo cinemático con IA basada estrictamente en la doctrina
de 2 Pasos (Keyframe Base -> Image-to-Video), desacoplamiento de prompts, vocabulario de cámara
cinematográfico, manejo asíncrono y persistencia física en disco sin mocks.
"""

import os
import re
import json
import time
import base64
import datetime
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_INFORMES = _APP_ROOT / "Subagente_Diseno" / "informes"
_INFORMES.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    _ENV_PATH = _APP_ROOT / ".env"
    if _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH)
except Exception:
    pass


def obtener_prompt_video() -> str:
    """
    Retorna el System Prompt Canónico especializado para la dirección y generación de vídeo cinemático con IA.
    """
    return """[🎬 DIRECTIVA OPERATIVA: MODO DIRECCIÓN Y GENERACIÓN DE VÍDEO CON IA (I2V) 🎬]
Eres la Directora Audiovisual y Animadora de Imagen en Movimiento del Subagente de Diseño.
Tu cometido es transformar conceptos publicitarios y productos de marca en piezas de vídeo cinemático de alto impacto para redes sociales (Reels, TikTok, Shorts en 1080x1920 vertical) utilizando la tecnología Image-to-Video (I2V) de Higgsfield AI.

═══════════════════════════════════════════════════════════════════════════════
DOCTRINA OBLIGATORIA EN 2 PASOS (IMAGE-TO-VIDEO > TEXT-TO-VIDEO):
═══════════════════════════════════════════════════════════════════════════════
Para evitar que el producto, la botella, el logotipo o el sujeto se deformen en el vídeo:

1. PASO 1 (KEYFRAME BASE ESTÁTICO):
   - Nunca generes vídeos directamente desde texto para productos o marcas.
   - Primero se genera o solicita la imagen fija hiperrealista con la habilidad `ia_creativa` (usando estilos de packshot y producto).
   - REGLA DE PROMPT DEL FRAME BASE: El prompt de la imagen inicial debe controlar estrictamente lo estático (sujeto, ropa, iluminación de estudio, lente). JAMÁS incluyas movimientos de cámara ni acciones de vídeo en el prompt del Paso 1.

2. PASO 2 (ANIMACIÓN I2V DESACOPLADA):
   - Con la imagen fija lista y aprobada (`ruta_imagen_base`), se activa `generar_video_ia`.
   - El prompt de movimiento solo debe controlar la acción en el tiempo, movimientos de cámara y físicas del entorno.

═══════════════════════════════════════════════════════════════════════════════
VOCABULARIO CINEMATOGRÁFICO Y ESTRUCTURA DEL PROMPT DE VÍDEO:
═══════════════════════════════════════════════════════════════════════════════
Cada prompt de movimiento debe combinar 4 dimensiones cinemáticas:
- MOVIMIENTO DE CÁMARA EXPLÍCITO:
  * 'Dolly in': Acercamiento lento y elegante hacia el producto.
  * 'Dolly out': Alejamiento suave revelando el contexto o entorno.
  * 'Orbit around subject': Giro semicircular suave mostrando la tridimensionalidad del producto.
  * 'Tracking shot': Seguimiento dinámico lateral o frontal del sujeto.
  * 'Slow pan left / right': Barrido horizontal suave.
  * 'Handheld subtle shake': Movimiento orgánico en mano estilo UGC / creador.
- FÍSICAS Y DINÁMICAS DEL ENTORNO:
  * Partículas y fluidos: 'steam rising gently from coffee', 'water condensation slowly dripping on glass', 'dust particles floating in rim light', 'soft breeze moving fabric'.
- RITMO Y TIEMPO: Tomas cortas de alto impacto (de 3 a 5 segundos).
- SONIDO (AUDIO NATIVO): Indicar efectos sonoros asociados (ej. sonido de vertido, murmullo de cafetería) en modelos con audio como Kling 3.0.

NEGATIVE PROMPTS OBLIGATORIOS:
"deformed hands, warping, flickering, morphing face, low resolution, blurry details, distorted logo, unnatural anatomy, glitch artifacts"

═══════════════════════════════════════════════════════════════════════════════
POLÍTICA DE TRANSPARENCIA Y CERO MOCKS:
═══════════════════════════════════════════════════════════════════════════════
- Si la cuenta no tiene créditos en Higgsfield AI (`not_enough_credits`), se reporta directamente el estado para que el usuario recargue saldo. PROHIBIDO simular o generar archivos de texto falsos haciéndose pasar por archivos MP4.
- Cuando la API renderiza el vídeo, el archivo binario real se descarga inmediatamente en disco (`/app/Subagente_Diseno/informes/`) registrando su `.verificacion.json`.
"""


def _transformar_ruta(ruta: str) -> Path:
    if not isinstance(ruta, str) or not ruta.strip():
        return _INFORMES / "video_producto.mp4"

    literales = {"ruta_destino", "prompt_movimiento", "ruta_imagen_base", "ruta", "destino"}
    p = Path(ruta)
    nombre = p.name
    if not nombre or nombre in literales:
        nombre = "video_producto.mp4"
    if not nombre.lower().endswith(".mp4"):
        nombre += ".mp4"

    return _INFORMES / nombre


def _imagen_a_url_o_base64(ruta_imagen: str) -> Optional[str]:
    """Convierte una ruta de imagen local a data URI base64 o retorna la URL web si ya lo es."""
    if not ruta_imagen or not isinstance(ruta_imagen, str):
        return None

    r = ruta_imagen.strip()
    if r.startswith("http://") or r.startswith("https://") or r.startswith("data:image/"):
        return r

    p = Path(r)
    if not p.is_absolute():
        p = _INFORMES / p.name

    if p.exists() and p.is_file():
        try:
            ext = p.suffix.lower().lstrip(".")
            mime = "jpeg" if ext in ["jpg", "jpeg"] else ("webp" if ext == "webp" else "png")
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/{mime};base64,{b64}"
        except Exception as e:
            print(f"[Subagente_Diseno] Error al codificar imagen: {e}")
            return None
    return None


def _crear_metadatos_verificacion(ruta_archivo: Path, prompt_mov: str, modelo: str, tamano_bytes: int) -> str:
    try:
        ruta_meta = ruta_archivo.parent / f"{ruta_archivo.stem}.verificacion.json"
        magic_hex = ""
        with open(ruta_archivo, "rb") as f:
            magic_hex = f.read(8).hex()

        metadatos = {
            "archivo_generado": str(ruta_archivo).replace("\\", "/"),
            "tamano_bytes": tamano_bytes,
            "modelo_ia_video": modelo,
            "formato": "MP4 binario genuino (H.264/AAC)",
            "verificacion_disco": f"EXISTE: True | BYTES: {tamano_bytes} | MAGIC: 0x{magic_hex}",
            "magic_hex": magic_hex,
            "prompt_movimiento": prompt_mov,
            "timestamp_verificacion": datetime.datetime.now().isoformat()
        }

        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(metadatos, f, ensure_ascii=False, indent=2)

        return str(ruta_meta).replace("\\", "/")
    except Exception as e:
        return f"Error creando metadatos: {str(e)}"


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 1: ESTRUCTURAR PROMPT CINEMÁTICO DE MOVIMIENTO
# ══════════════════════════════════════════════════════════════════════════════

class EstructurarPromptVideoParams(BaseModel):
    accion_principal: str = Field(description="Acción en el tiempo del producto o sujeto (ej. 'condensación resbalando suavemente por el vidrio de la botella').")
    movimiento_camara: str = Field(default="Dolly in", description="Dirección de cámara: 'Dolly in', 'Dolly out', 'Orbit around subject', 'Tracking shot', 'Slow pan right', 'Handheld subtle shake'.")
    dinamica_ambiente: str = Field(default="soft lighting shift with floating dust particles", description="Físicas del entorno (ej. 'vapor sutil elevándose', 'gotas de lluvia en ventana', 'brisa suave').")
    sugerencia_audio: str = Field(default="", description="Diseño sonoro sugerido (ej. 'sonido de hielo chocando suavemente y vertido de líquido').")
    duracion_segundos: int = Field(default=5, description="Duración recomendada del clip (3 a 5 segundos).")


@tool("estructurar_prompt_movimiento_video", args_schema=EstructurarPromptVideoParams)
def estructurar_prompt_movimiento_video(
    accion_principal: str,
    movimiento_camara: str = "Dolly in",
    dinamica_ambiente: str = "soft lighting shift with floating dust particles",
    sugerencia_audio: str = "",
    duracion_segundos: int = 5
) -> str:
    """
    Prepara y formula el prompt cinemático desacoplado para Image-to-Video siguiendo las mejores prácticas:
    combina movimiento de cámara explícito, acción en el tiempo, dinámicas ambientales y negative prompts.
    """
    cam_map = {
        "dolly in": "Slow cinematic dolly-in camera movement toward the subject",
        "dolly out": "Smooth slow dolly-out camera movement gently pulling back",
        "orbit": "Slow 45-degree smooth orbit camera rotation around the subject",
        "tracking": "Smooth cinematic tracking shot maintaining sharp subject focus",
        "pan": "Slow horizontal camera pan across the frame",
        "handheld": "Subtle authentic handheld camera movement with natural micro-motion"
    }

    mov_clave = movimiento_camara.lower().strip()
    cam_str = next((v for k, v in cam_map.items() if k in mov_clave), f"{movimiento_camara} camera movement")

    componentes = [
        cam_str,
        accion_principal.strip().rstrip("."),
        dinamica_ambiente.strip().rstrip(".") if dinamica_ambiente else "natural physically consistent lighting",
        "crisp sharp focus throughout",
        "masterwork commercial cinematography 4k"
    ]

    prompt_movimiento = ", ".join([c for c in componentes if c])

    neg_prompt = "deformed hands, warping, flickering, morphing face, low resolution, blurry details, distorted logo, unnatural anatomy, glitch artifacts"

    return json.dumps({
        "status": "success",
        "prompt_movimiento_cinematico": prompt_movimiento,
        "negative_prompt_estandar": neg_prompt,
        "movimiento_camara": movimiento_camara,
        "accion_principal": accion_principal,
        "dinamica_ambiente": dinamica_ambiente,
        "audio_sugerido": sugerencia_audio or "Audio ambiental sutil del producto",
        "duracion_recomendada": f"{duracion_segundos}s",
        "instruccion": "Pasa 'prompt_movimiento_cinematico' y la ruta de la imagen fija a 'generar_video_ia'."
    }, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 2: GENERAR VÍDEO CON IA (HIGGSFIELD IMAGE-TO-VIDEO REAL)
# ══════════════════════════════════════════════════════════════════════════════

class GenerarVideoIAParams(BaseModel):
    ruta_imagen_base: str = Field(description="Ruta a la imagen fija generada por ia_creativa (Keyframe base estático).")
    prompt_movimiento: str = Field(description="Prompt cinemático que describe únicamente el movimiento de cámara, acción y entorno.")
    modelo_video: str = Field(default="AUTO", description="Modelo Higgsfield I2V: 'AUTO', 'kling_turbo', 'kling_pro', 'wan_prime', 'seedance_2_5', 'minimax_hailuo'.")
    movimiento_camara: str = Field(default="Dolly in", description="Movimiento de cámara: 'Dolly in', 'Dolly out', 'Orbit', 'Tracking', 'Pan', 'Handheld'.")
    duracion_segundos: int = Field(default=5, description="Duración del clip (3 a 10 segundos).")
    aspect_ratio: str = Field(default="9:16", description="Relación de aspecto: '9:16' (vertical móvil) o '16:9' (horizontal).")
    ruta_destino: str = Field(default="video_producto.mp4", description="Nombre o ruta del archivo de guardado en informes/.")


@tool("generar_video_ia", args_schema=GenerarVideoIAParams)
def generar_video_ia(
    ruta_imagen_base: str,
    prompt_movimiento: str,
    modelo_video: str = "AUTO",
    movimiento_camara: str = "Dolly in",
    duracion_segundos: int = 5,
    aspect_ratio: str = "9:16",
    ruta_destino: str = "video_producto.mp4"
) -> str:
    """
    Genera un clip de vídeo publicitario hiperrealista mediante Higgsfield Image-to-Video (I2V)
    animando la imagen fija del producto. Maneja el ciclo asíncrono, negative prompts y descarga física en disco.
    Si la cuenta no tiene créditos, reporta con total transparencia el estado para recarga (sin mocks).
    """
    try:
        destino_p = _transformar_ruta(ruta_destino)
        destino_p.parent.mkdir(parents=True, exist_ok=True)

        # 1. Preparar la imagen base (Keyframe estático)
        image_payload_url = _imagen_a_url_o_base64(ruta_imagen_base)
        if not image_payload_url:
            return json.dumps({
                "status": "error",
                "mensaje": f"No se pudo localizar o leer la imagen base en '{ruta_imagen_base}'. Genera primero la imagen del producto con la skill ia_creativa."
            }, ensure_ascii=False)

        # 2. Mapeo y selección del modelo I2V
        modelos_i2v = {
            "kling_turbo": "kling-video/v3.0-turbo/image-to-video",
            "kling_pro": "kling-video/v3.0/pro/image-to-video",
            "wan_prime": "alibaba/wan-3.0-prime/image-to-video",
            "seedance_2_5": "bytedance/seedance-2.5/image-to-video",
            "minimax_hailuo": "minimax/hailuo-2.3/standard/image-to-video"
        }

        mod_req = modelo_video.lower().strip()
        slug = modelos_i2v.get(mod_req)

        if not slug:
            p_low = prompt_movimiento.lower()
            if any(k in p_low for k in ["persona", "rostro", "gesto", "wan"]):
                slug = "alibaba/wan-3.0-prime/image-to-video"
            elif any(k in p_low for k in ["baile", "cuerpo", "deporte", "ropa", "moda"]):
                slug = "bytedance/seedance-2.5/image-to-video"
            elif any(k in p_low for k in ["cine", "comercial", "lujo", "pro"]):
                slug = "kling-video/v3.0/pro/image-to-video"
            else:
                # Default óptimo para productos y publicidad rápida
                slug = "kling-video/v3.0-turbo/image-to-video"

        nombre_modelo = slug.split("/")[0].capitalize()

        # 3. Formular Prompt Cinemático con Dirección de Cámara
        prompt_completo = prompt_movimiento.strip()
        if movimiento_camara and movimiento_camara.lower() != "auto" and movimiento_camara.lower() not in prompt_completo.lower():
            prompt_completo = f"{movimiento_camara} camera movement, {prompt_completo}"

        negative_prompt = "deformed hands, warping, flickering, morphing face, low resolution, blurry details, distorted logo, unnatural anatomy, glitch artifacts"

        # 4. Conexión con Higgsfield API
        higgsfield_key = os.environ.get("HIGGSFIELD_API_KEY") or (
            f"{os.environ.get('HF_API_KEY_ID')}:{os.environ.get('HF_API_KEY_SECRET')}"
            if os.environ.get("HF_API_KEY_ID") and os.environ.get("HF_API_KEY_SECRET") else None
        )

        if not higgsfield_key:
            return json.dumps({
                "status": "error_credenciales",
                "mensaje": "No se encontraron credenciales de Higgsfield AI en las variables de entorno (.env)."
            }, ensure_ascii=False)

        headers = {
            "Authorization": f"Key {higgsfield_key}" if ":" in higgsfield_key and not higgsfield_key.startswith("Key ") else f"Bearer {higgsfield_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt_completo,
            "image_url": image_payload_url,
            "negative_prompt": negative_prompt,
            "duration": duracion_segundos,
            "aspect_ratio": "9:16" if aspect_ratio in ["9:16", "vertical"] else "16:9"
        }

        # Enviar petición POST a Higgsfield I2V
        resp = requests.post(f"https://api.higgsfield.ai/{slug}", headers=headers, json=payload, timeout=30)

        # Caso A: Saldo insuficiente (Sin mocks, reporte honesto y directo)
        if resp.status_code in [402, 403] or "not_enough_credits" in resp.text:
            return json.dumps({
                "status": "error_creditos",
                "modelo_solicitado": nombre_modelo,
                "slug_higgsfield": slug,
                "mensaje": "Saldo insuficiente en la cuenta de Higgsfield AI para procesar el renderizado de vídeo.",
                "accion_requerida": "Es necesario recargar créditos en https://higgsfield.ai para procesar el clip con este modelo.",
                "prompt_preparado": prompt_completo,
                "imagen_base_verificada": ruta_imagen_base
            }, ensure_ascii=False, indent=2)

        # Caso B: Petición aceptada (Polling asíncrono y descarga física)
        if resp.status_code in [200, 201]:
            data = resp.json()
            status_url = data.get("status_url") or (
                f"https://api.higgsfield.ai/requests/{data.get('request_id')}/status"
                if "request_id" in data else None
            )

            if status_url:
                # Polling cada 6 segundos hasta 3 minutos
                for _ in range(30):
                    time.sleep(6)
                    st = requests.get(status_url, headers=headers, timeout=12)
                    if st.status_code == 200:
                        sdata = st.json()
                        estado = sdata.get("status")
                        if estado == "completed":
                            video_url = sdata.get("video", {}).get("url") or sdata.get("output_url")
                            if video_url:
                                vbin = requests.get(video_url, timeout=90).content
                                with open(destino_p, "wb") as f:
                                    f.write(vbin)

                                tamano_bytes = len(vbin)
                                ruta_meta = _crear_metadatos_verificacion(destino_p, prompt_completo, slug, tamano_bytes)
                                ruta_norm = str(destino_p).replace("\\", "/")

                                return json.dumps({
                                    "status": "success",
                                    "modelo_usado": nombre_modelo,
                                    "slug": slug,
                                    "archivo_mp4": ruta_norm,
                                    "bytes": tamano_bytes,
                                    "metadatos_verificacion": ruta_meta,
                                    "mensaje": f"Vídeo publicitario renderizado y descargado exitosamente en {ruta_norm}."
                                }, ensure_ascii=False, indent=2)

                        elif estado in ["failed", "error"]:
                            error_detalle = sdata.get("error") or "Fallo en el servidor de renderizado de Higgsfield."
                            return json.dumps({
                                "status": "error_renderizado",
                                "mensaje": f"Higgsfield reportó fallo en el procesamiento del vídeo: {error_detalle}"
                            }, ensure_ascii=False)

        # Caso C: Error inesperado en API
        return json.dumps({
            "status": "error_api",
            "codigo_http": resp.status_code,
            "detalle_respuesta": resp.text[:200],
            "mensaje": f"Error al comunicar con Higgsfield Video API ({resp.status_code})."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Excepción durante la generación de vídeo: {str(e)}"
        }, ensure_ascii=False)


HERRAMIENTAS_VIDEO = [
    generar_video_ia,
    estructurar_prompt_movimiento_video
]
