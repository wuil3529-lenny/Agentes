"""
skill_voz.py — Sistema Integral de Voz Bidireccional del Agente Orquestador
===========================================================================
Dota al Agente_Orquestador de capacidades completas de voz en 3 modalidades:
  1. Micrófono de la Computadora (STT): Escucha al usuario por el micrófono físico de la PC
     (`sounddevice` + `scipy` con detección de silencio VAD) y transcribe a texto (`SpeechRecognition`
     Google STT gratuito y/o OpenAI Whisper).
  2. Cornetas / Altavoces de la Computadora (TTS Local/Neural): Habla directamente por las cornetas
     de la PC usando voz neural (`edge-tts` + `pygame.mixer`, con fallback a `gTTS` y `pyttsx3` SAPI5).
  3. Notas de Voz (Consola y Telegram): Genera archivos de audio (`.mp3` y `.ogg` Opus con `ffmpeg`)
     y los envía como notas de voz reproducibles tanto en el chat de la Consola como en Telegram
     (`sendVoice`), además de transcribir notas de voz entrantes del usuario.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]
_NOTAS_VOZ_DIR = _APP_ROOT / "dashboard" / "static" / "notas_voz"
_ESTADO_VOZ_FILE = _APP_ROOT / "dashboard" / "estado_voz.json"

# Voz neural masculina en español por defecto para el Agente Orquestador
DEFAULT_EDGE_VOICE = os.getenv("VOICE_ORQUESTADOR", "es-MX-JorgeNeural")

# Candado para evitar superposición de audios en las cornetas de la PC
_SPEAKER_LOCK = threading.Lock()


def _es_entorno_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("AGENTES_ROOT") == "/app"


def _llamar_puente_host(endpoint: str, payload: dict, timeout: int = 35) -> Optional[dict]:
    """Llama a la Consola Web en el host Windows (host.docker.internal:8000) cuando el agente corre en Docker."""
    import urllib.request
    host_base = os.getenv("CONSOLE_HOST_URL", "http://host.docker.internal:8000").rstrip("/")
    url = f"{host_base}{endpoint}"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[Puente Audio Host] Advertencia contactando {url}: {e}")
        return None


def _asegurar_directorios() -> None:
    _NOTAS_VOZ_DIR.mkdir(parents=True, exist_ok=True)


def obtener_estado_voz() -> dict:
    """Lee la configuración persistente de voz (cornetas activas, auto-nota de voz, etc.)."""
    if _ESTADO_VOZ_FILE.exists():
        try:
            return json.loads(_ESTADO_VOZ_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"cornetas_activas": False, "auto_nota_voz": False, "voz_neural": DEFAULT_EDGE_VOICE}


def guardar_estado_voz(cornetas_activas: Optional[bool] = None, auto_nota_voz: Optional[bool] = None) -> dict:
    estado = obtener_estado_voz()
    if cornetas_activas is not None:
        estado["cornetas_activas"] = bool(cornetas_activas)
    if auto_nota_voz is not None:
        estado["auto_nota_voz"] = bool(auto_nota_voz)
    try:
        _ESTADO_VOZ_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ESTADO_VOZ_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return estado


def limpiar_texto_para_voz(texto: str) -> str:
    """
    Limpia bloques de código, tablas Markdown, enlaces, símbolos de formato y caracteres técnicos
    para que la síntesis de voz suene natural, ejecutiva y concisa (~25-30 segundos).
    """
    if not texto:
        return ""
    limpio = str(texto)
    # Eliminar bloques de código largos
    limpio = re.sub(r"```[\s\S]*?```", " ", limpio)
    # Convertir tablas Markdown a pausas legibles
    limpio = re.sub(r"[|\-]+", " ", limpio)
    # Eliminar prefijos de ruteo interno
    limpio = re.sub(r"^\[[^\]]+->[^\]]+\]:\s*", "", limpio)
    # Convertir enlaces [texto](url) -> texto
    limpio = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", limpio)
    # Convertir wikilinks [[nodo|alias]] -> alias
    limpio = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", limpio)
    # Quitar encabezados, negritas, backticks
    limpio = re.sub(r"[#*_`~>]+", " ", limpio)
    # Quitar emojis excesivos o caracteres no pronunciables manteniendo puntuación española
    limpio = re.sub(r"[^\w\s.,;:¡!¿?áéíóúÁÉÍÓÚñÑüÜ()\-/%$]", " ", limpio)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    # Permitir locución completa y exhaustiva sin cortes artificiales (hasta 4000 caracteres)
    if len(limpio) > 4000:
        limpio = limpio[:3990].rsplit(".", 1)[0] + "."
    return limpio


# ══════════════════════════════════════════════════════════════════════════════
# 1. SÍNTESIS DE VOZ (TTS) Y GENERACIÓN DE NOTAS DE VOZ (.MP3 / .OGG)
# ══════════════════════════════════════════════════════════════════════════════

# Voces gratuitas (Premade) de ElevenLabs compatibles con el Plan Gratuito + Español (Multilingual v2 / Flash v2.5)
VOCES_ELEVENLABS_GRATIS = {
    "brian": "nPczCjzI2devNBz1zQrb",    # Masculina — Profunda, resonante y reconfortante (Por defecto)
    "george": "JBFqnCBsd6RMkjVDRZzb",   # Masculina — Cálida, narrador cautivador
    "daniel": "onwK4e9ZLuTAKqWW03F9",   # Masculina — Locutor firme y autoritativo
    "adam": "pNInz6obpgDQGcFmaJgB",     # Masculina — Dominante y firme
    "bill": "pqHfZKP75CvOlQylNhV4",     # Masculina — Sabia, madura y equilibrada
    "eric": "cjVigY5qzO86Huf0OWal",     # Masculina — Suave y confiable
    "chris": "iP95p4xoKVk53GoZ742B",    # Masculina — Cercana y natural
    "roger": "CwhRBWXzGAHq8TQ4Fs17",    # Masculina — Relajada, casual y resonante
    "charlie": "IKne3meq5aSn9XLyUdCD",  # Masculina — Profunda, confiada y enérgica
    "callum": "N2lVS1w4EtoT3dr4eOWO",   # Masculina — Rasgada y con carácter
    "harry": "SOYHLrjzK2X1ezoPC6cr",    # Masculina — Guerrero intenso
    "liam": "TX3LPaxmHKxFdv7VOQHJ",     # Masculina — Joven y energética
    "will": "bIHbv24MWmeRgasZH58o",     # Masculina — Relajada y optimista
    "river": "SAz9YHcvj6GT2YYXdXww",    # Neutra — Relajada, neutral e informativa
    "sarah": "EXAVITQu4vr4xnSDxMaL",    # Femenina — Madura, segura y confiada
    "matilda": "XrExE9yKIg1WjnnlVkGX",  # Femenina — Profesional y ejecutiva
    "bella": "hpp4J3VqNfWAUOO0d1Us",    # Femenina — Profesional, brillante y cálida
    "alice": "Xb7hH8MSUJpSbSDYk0k2",    # Femenina — Clara y didáctica
    "jessica": "cgSgspJ2msm6clMCkdW9",  # Femenina — Brillante y cálida
    "laura": "FGY2WhTYpPnrIDTdsKH5",    # Femenina — Entusiasta y expresiva
    "lily": "pFZP5JQG7iQjIQuC4Bku",     # Femenina — Aterciopelada y actoral
}
DEFAULT_ELEVENLABS_VOICE_ID = "nPczCjzI2devNBz1zQrb"  # Brian (Premade Free)
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"


def _leer_env_valor(clave: str, default: str = "") -> str:
    """Lee una variable desde os.environ o en caliente desde el archivo .env en la raíz."""
    val = os.getenv(clave, "").strip()
    if val:
        return val
    env_file = _APP_ROOT / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == clave:
                    return v.strip().strip('"').strip("'")
        except Exception:
            pass
    return default


async def _edge_tts_guardar(texto: str, ruta_mp3: Path, voz: str) -> bool:
    import edge_tts
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(str(ruta_mp3))
    return ruta_mp3.exists() and ruta_mp3.stat().st_size > 0


def _elevenlabs_tts_guardar(texto: str, ruta_mp3: Path, voice_id: Optional[str] = None) -> bool:
    """
    Sintetiza voz usando la API de ElevenLabs con voces Premade gratuitas.
    Intenta primero el modelo configurado (`eleven_multilingual_v2` o `eleven_flash_v2_5`)
    y hace fallback automático si el modelo o voz requiere ajuste.
    """
    import urllib.request
    import urllib.error

    api_key = _leer_env_valor("ELEVENLABS_API_KEY")
    if not api_key:
        return False

    estado = obtener_estado_voz()
    vid = (
        voice_id
        or estado.get("elevenlabs_voice_id")
        or _leer_env_valor("ELEVENLABS_VOICE_ID")
        or DEFAULT_ELEVENLABS_VOICE_ID
    )
    # Permitir pasar el nombre corto ("brian", "george", "daniel", etc.)
    vid = VOCES_ELEVENLABS_GRATIS.get(vid.lower(), vid)

    modelo_preferido = _leer_env_valor("ELEVENLABS_MODEL_ID", DEFAULT_ELEVENLABS_MODEL_ID)
    modelos_a_probar = [modelo_preferido]
    if "eleven_flash_v2_5" not in modelos_a_probar:
        modelos_a_probar.append("eleven_flash_v2_5")
    if "eleven_multilingual_v2" not in modelos_a_probar:
        modelos_a_probar.append("eleven_multilingual_v2")

    for model_id in modelos_a_probar:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128"
        payload = {
            "text": texto,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.78,
                "style": 0.15,
                "use_speaker_boost": True,
            },
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                audio_bytes = resp.read()
                if audio_bytes and len(audio_bytes) > 200:
                    ruta_mp3.write_bytes(audio_bytes)
                    return True
        except urllib.error.HTTPError as he:
            err_body = ""
            try:
                err_body = he.read().decode("utf-8", errors="ignore")[:250]
            except Exception:
                pass
            print(f"[ElevenLabs TTS] HTTP {he.code} con modelo {model_id} (voz {vid}): {err_body}")
        except Exception as e_el:
            print(f"[ElevenLabs TTS] Error con modelo {model_id}: {e_el}")

    return False


def generar_audio_voz(
    texto: str,
    formato: str = "mp3",
    nombre_archivo: Optional[str] = None,
    voz: Optional[str] = None,
) -> Optional[Path]:
    """
    Sintetiza el `texto` en un archivo de audio (`.mp3` o `.ogg` Opus para Telegram)
    dentro de `dashboard/static/notas_voz/`.
    Usa `ElevenLabs` (voces gratuitas Premade en español) como motor primario,
    con fallback a `gTTS`, `edge-tts` y `pyttsx3` (SAPI5 offline de Windows).
    """
    _asegurar_directorios()
    texto_hablado = limpiar_texto_para_voz(texto)
    if not texto_hablado:
        return None

    voz_usar = voz or os.getenv("VOICE_ORQUESTADOR", DEFAULT_EDGE_VOICE)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    base_name = nombre_archivo or f"voz_orquestador_{ts}"
    ruta_mp3 = _NOTAS_VOZ_DIR / f"{base_name}.mp3"
    ruta_ogg = _NOTAS_VOZ_DIR / f"{base_name}.ogg"

    generado_ok = False

    # Intento 1: ElevenLabs (Voz Ultra-Realista Gratuita Premade)
    if _leer_env_valor("ELEVENLABS_API_KEY"):
        try:
            generado_ok = _elevenlabs_tts_guardar(texto_hablado, ruta_mp3, voice_id=voz)
        except Exception as e_eleven:
            print(f"[Voz Orquestador] Advertencia ElevenLabs ({e_eleven}), probando fallback...")

    # Intento 2: Edge-TTS (Voz Neural de Microsoft de Alta Calidad - Gratuita e Ilimitada)
    if not generado_ok:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                err_holder = []

                def _runner():
                    try:
                        asyncio.run(_edge_tts_guardar(texto_hablado, ruta_mp3, voz_usar))
                    except Exception as ex:
                        err_holder.append(ex)

                t = threading.Thread(target=_runner)
                t.start()
                t.join(timeout=15)
                generado_ok = ruta_mp3.exists() and ruta_mp3.stat().st_size > 0
            else:
                generado_ok = asyncio.run(_edge_tts_guardar(texto_hablado, ruta_mp3, voz_usar))
        except Exception as e_edge:
            print(f"[Voz Orquestador] Advertencia edge-tts ({e_edge}), probando fallback gTTS...")

    # Intento 3: gTTS (Fallback secundario si Edge-TTS fallara)
    if not generado_ok:
        try:
            from gtts import gTTS
            tts = gTTS(text=texto_hablado, lang="es", slow=False)
            tts.save(str(ruta_mp3))
            generado_ok = ruta_mp3.exists() and ruta_mp3.stat().st_size > 0
        except Exception as e_gtts:
            print(f"[Voz Orquestador] Advertencia gTTS ({e_gtts}), probando fallback pyttsx3...")

    # Intento 3: pyttsx3 (Windows SAPI5 100% Offline)
    if not generado_ok and not _es_entorno_docker():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            ruta_wav = _NOTAS_VOZ_DIR / f"{base_name}.wav"
            engine.save_to_file(texto_hablado, str(ruta_wav))
            engine.runAndWait()
            if ruta_wav.exists() and ruta_wav.stat().st_size > 0:
                if shutil.which("ffmpeg"):
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(ruta_wav), "-codec:a", "libmp3lame", "-qscale:a", "2", str(ruta_mp3)],
                        capture_output=True,
                        timeout=15,
                    )
                    ruta_wav.unlink(missing_ok=True)
                    generado_ok = ruta_mp3.exists() and ruta_mp3.stat().st_size > 0
                else:
                    return ruta_wav
        except Exception as e_pyttsx:
            print(f"[Voz Orquestador] Error en síntesis offline pyttsx3: {e_pyttsx}")

    if not generado_ok or not ruta_mp3.exists():
        return None

    # Si se solicitó .ogg (para nota de voz nativa en Telegram con onda de audio)
    if formato.lower() == "ogg" and shutil.which("ffmpeg"):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(ruta_mp3), "-c:a", "libopus", "-b:a", "48k", "-vbr", "on", str(ruta_ogg)],
                capture_output=True,
                timeout=20,
            )
            if ruta_ogg.exists() and ruta_ogg.stat().st_size > 0:
                return ruta_ogg
        except Exception:
            pass

    return ruta_mp3


# ══════════════════════════════════════════════════════════════════════════════
# 2. REPRODUCCIÓN POR LAS CORNETAS / ALTAVOCES DE LA COMPUTADORA
# ══════════════════════════════════════════════════════════════════════════════

def actualizar_estado_procesando(procesando: bool) -> None:
    """Actualiza en `estado_voz.json` si el Agente Orquestador está procesando/pensando para apagar el micrófono en la consola."""
    try:
        estado = obtener_estado_voz()
        estado["agente_procesando"] = bool(procesando)
        if procesando:
            estado["inicio_proceso_ts"] = time.time()
        else:
            estado["fin_proceso_ts"] = time.time()
        _ESTADO_VOZ_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ESTADO_VOZ_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _marcar_cornetas_hablando(activo: bool) -> None:
    """Actualiza en `estado_voz.json` si las cornetas físicas están reproduciendo audio para silenciar el micrófono (Half-Duplex Anti-Eco)."""
    try:
        estado = obtener_estado_voz()
        estado["hablando_en_cornetas"] = bool(activo)
        if activo:
            estado["inicio_cornetas_ts"] = time.time()
        else:
            estado["fin_cornetas_ts"] = time.time()
        _ESTADO_VOZ_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ESTADO_VOZ_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def detener_cornetas_pc() -> bool:
    """Detiene inmediatamente cualquier audio reproduciéndose en las cornetas físicas de la PC."""
    try:
        import pygame
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass
    _marcar_cornetas_hablando(False)
    return True


def reproducir_archivo_en_cornetas(ruta_audio: Path, bloquear: bool = True) -> bool:
    """
    Reproduce un archivo de audio (.mp3, .wav, .ogg) directamente a través de las
    cornetas/altavoces físicos de la computadora usando `pygame.mixer` (o cola compartida si corre en Docker).
    """
    if not ruta_audio or not Path(ruta_audio).exists():
        return False

    if _es_entorno_docker():
        try:
            estado = obtener_estado_voz()
            now_ts = time.time()
            estado["hablando_en_cornetas"] = True
            estado["inicio_cornetas_ts"] = now_ts
            estado["cola_cornetas"] = {
                "id": f"play_{int(now_ts * 1000)}",
                "archivo": Path(ruta_audio).name,
                "timestamp": now_ts,
            }
            _ESTADO_VOZ_FILE.parent.mkdir(parents=True, exist_ok=True)
            _ESTADO_VOZ_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception as e_q:
            print(f"[Voz Orquestador] Error encolando audio para cornetas del host: {e_q}")
            return False

    def _play():
        with _SPEAKER_LOCK:
            _marcar_cornetas_hablando(True)
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(str(ruta_audio))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.music.unload()
                return True
            except Exception as e_pg:
                print(f"[Voz Orquestador] Advertencia pygame.mixer ({e_pg}), usando fallback SAPI5...")
                return False
            finally:
                _marcar_cornetas_hablando(False)

    if bloquear:
        return _play()
    else:
        t = threading.Thread(target=_play, daemon=True)
        t.start()
        return True


def hablar_por_cornetas_pc(texto: str, bloquear: bool = True) -> dict:
    """
    Sintetiza el texto con la voz del Agente Orquestador y lo reproduce por las
    cornetas (altavoces) de la computadora. Retorna también la ruta y URL del audio generado.
    """
    texto_limpio = limpiar_texto_para_voz(texto)
    if not texto_limpio:
        return {"status": "error", "mensaje": "Texto vacío para hablar."}

    ruta_mp3 = generar_audio_voz(texto_limpio, formato="mp3")
    if ruta_mp3 and ruta_mp3.exists():
        ok = reproducir_archivo_en_cornetas(ruta_mp3, bloquear=bloquear)
        if not ok:
            # Fallback directo con pyttsx3 SAPI5
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.say(texto_limpio)
                engine.runAndWait()
                ok = True
            except Exception as e:
                return {"status": "error", "mensaje": f"No se pudo reproducir en cornetas: {e}"}

        audio_url = f"/static/notas_voz/{ruta_mp3.name}"
        return {
            "status": "success",
            "mensaje": "Respuesta reproducida por las cornetas de la computadora.",
            "ruta_audio": str(ruta_mp3),
            "audio_url": audio_url,
        }

    # Si no se pudo generar MP3, hablar directo con pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.say(texto_limpio)
        engine.runAndWait()
        return {"status": "success", "mensaje": "Respuesta reproducida por cornetas (SAPI5 local)."}
    except Exception as e:
        return {"status": "error", "mensaje": f"Error al hablar por las cornetas: {e}"}


# ══════════════════════════════════════════════════════════════════════════════
# 3. ESCUCHA POR MICRÓFONO DE LA PC Y TRANSCRIPCIÓN DE AUDIO (STT)
# ══════════════════════════════════════════════════════════════════════════════

def transcribir_archivo_audio(ruta_audio: str | Path, idioma: str = "es-ES") -> dict:
    """
    Convierte cualquier archivo de audio (.ogg, .mp3, .webm, .wav, .m4a) a WAV PCM 16kHz mono
    usando `ffmpeg` y lo transcribe a texto en español.
    Soporta:
      1. Google Speech Recognition (gratuito vía `speech_recognition`, 0 costo de API).
      2. OpenAI Whisper / Groq Whisper API si se requiere fallback.
    """
    origen = Path(ruta_audio)
    if not origen.exists() or origen.stat().st_size == 0:
        return {"status": "error", "texto": "", "mensaje": f"El archivo de audio '{origen}' no existe o está vacío."}

    tmp_wav = None
    try:
        # Convertir siempre a WAV PCM 16-bit 16kHz mono para compatibilidad universal
        if origen.suffix.lower() != ".wav" or shutil.which("ffmpeg"):
            fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="stt_")
            os.close(fd)
            tmp_wav = Path(tmp_path)
            if shutil.which("ffmpeg"):
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(origen), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp_wav)],
                    capture_output=True,
                    timeout=20,
                )
                wav_a_usar = tmp_wav if (tmp_wav.exists() and tmp_wav.stat().st_size > 44) else origen
            else:
                wav_a_usar = origen
        else:
            wav_a_usar = origen

        # 1. Transcripción con SpeechRecognition (Google STT gratuito)
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(wav_a_usar)) as source:
            audio_data = recognizer.record(source)

        try:
            texto = recognizer.recognize_google(audio_data, language=idioma)
            if texto and texto.strip():
                return {"status": "success", "texto": texto.strip(), "motor": "google_stt"}
        except sr.UnknownValueError:
            return {"status": "error", "texto": "", "mensaje": "No se detectó voz clara en el audio."}
        except Exception as e_goog:
            print(f"[STT Orquestador] Advertencia Google STT ({e_goog}), intentando Whisper API...")

        # 2. Fallback a OpenAI Whisper API si existe OPENAI_API_KEY
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            with open(wav_a_usar, "rb") as f_aud:
                tr = client.audio.transcriptions.create(model="whisper-1", file=f_aud, language="es")
            if tr and tr.text:
                return {"status": "success", "texto": tr.text.strip(), "motor": "openai_whisper"}

        return {"status": "error", "texto": "", "mensaje": "No fue posible transcribir el audio."}
    except Exception as e:
        return {"status": "error", "texto": "", "mensaje": f"Error transcribiendo audio: {e}"}
    finally:
        if tmp_wav and tmp_wav.exists():
            try:
                tmp_wav.unlink()
            except Exception:
                pass


def escuchar_microfono_pc(
    duracion_max_segundos: int = 12,
    umbral_silencio_segundos: float = 1.8,
    idioma: str = "es-ES",
) -> dict:
    """
    Accede al micrófono físico de la computadora usando `sounddevice`, graba la voz del usuario
    hasta detectar silencio (VAD automático por energía RMS) o alcanzar `duracion_max_segundos`,
    guarda la nota de voz y devuelve el texto transcrito.
    """
    _asegurar_directorios()
    if _es_entorno_docker():
        res_host = _llamar_puente_host(
            "/api/voz/microfono-host",
            {
                "duracion_max_segundos": duracion_max_segundos,
                "umbral_silencio_segundos": umbral_silencio_segundos,
                "idioma": idioma,
            },
            timeout=duracion_max_segundos + 15,
        )
        if res_host:
            return res_host
    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io import wavfile
    except Exception as e:
        return {"status": "error", "texto": "", "mensaje": f"Librerías de micrófono no disponibles: {e}"}

    samplerate = 16000
    bloque_seg = 0.2
    bloque_frames = int(samplerate * bloque_seg)
    max_bloques = max(5, int(duracion_max_segundos / bloque_seg))
    bloques_silencio_corte = max(4, int(umbral_silencio_segundos / bloque_seg))

    frames_grabados = []
    empezo_a_hablar = False
    bloques_silencio = 0
    umbral_rms = 0.012  # Sensibilidad de detección de voz

    print("\n🎙️ [Micrófono PC] Escuchando... Habla ahora (se detendrá automáticamente al terminar de hablar).")
    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype="float32") as stream:
            # Calibrar ruido ambiente rápido (0.4s)
            ruido_base = []
            for _ in range(2):
                chunk, _ = stream.read(bloque_frames)
                ruido_base.append(float(np.sqrt(np.mean(chunk**2))))
            umbral_dinamico = max(umbral_rms, (sum(ruido_base) / len(ruido_base)) * 1.8)

            for _ in range(max_bloques):
                chunk, _ = stream.read(bloque_frames)
                frames_grabados.append(chunk.copy())
                rms = float(np.sqrt(np.mean(chunk**2)))

                if rms > umbral_dinamico:
                    empezo_a_hablar = True
                    bloques_silencio = 0
                else:
                    if empezo_a_hablar:
                        bloques_silencio += 1
                        if bloques_silencio >= bloques_silencio_corte:
                            break

        if not frames_grabados or not empezo_a_hablar:
            return {"status": "empty", "texto": "", "mensaje": "No se detectó voz en el micrófono."}

        audio_np = np.concatenate(frames_grabados, axis=0)
        audio_int16 = np.int16(np.clip(audio_np, -1.0, 1.0) * 32767)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_wav = _NOTAS_VOZ_DIR / f"mic_usuario_{ts}.wav"
        wavfile.write(str(ruta_wav), samplerate, audio_int16)

        res_stt = transcribir_archivo_audio(ruta_wav, idioma=idioma)
        res_stt["ruta_audio_usuario"] = str(ruta_wav)
        res_stt["audio_url_usuario"] = f"/static/notas_voz/{ruta_wav.name}"
        if res_stt.get("status") == "success":
            print(f"📝 [Micrófono PC Transcrito]: \"{res_stt.get('texto')}\"")
        return res_stt
    except Exception as e:
        return {"status": "error", "texto": "", "mensaje": f"Error al acceder al micrófono de la PC: {e}"}


# ══════════════════════════════════════════════════════════════════════════════
# 4. HERRAMIENTAS LANGCHAIN (@tool) PARA EL AGENTE ORQUESTADOR
# ══════════════════════════════════════════════════════════════════════════════

@tool
def tool_hablar_por_cornetas(mensaje: str) -> str:
    """
    Habla directamente al usuario a través de las cornetas (altavoces) de la computadora
    convirtiendo el texto en voz neural del Agente Orquestador.
    Úsala cuando el usuario esté conversando por voz en la consola o pida que le hables
    por las cornetas/altavoces de la PC.
    """
    print(f"\n🔊 [Agente_Orquestador] Hablando por las cornetas de la PC: '{mensaje[:80]}...'")
    res = hablar_por_cornetas_pc(mensaje, bloquear=True)
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_escuchar_microfono(duracion_max_segundos: int = 12) -> str:
    """
    Escucha al usuario a través del micrófono físico de la computadora y transcribe su voz a texto.
    Úsala cuando se requiera capturar una respuesta hablada directa desde el micrófono de la PC.
    """
    res = escuchar_microfono_pc(duracion_max_segundos=duracion_max_segundos)
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_enviar_nota_voz(
    mensaje_a_hablar: str,
    destino: str = "ambos",
    reproducir_en_cornetas: bool = False,
) -> str:
    """
    Genera una nota de voz con la voz del Agente Orquestador y la envía al usuario a través
    de la Consola (Dashboard), a través de Telegram (`sendVoice`), o por ambos canales.
    Opcionalmente también la reproduce por las cornetas de la computadora.

    Args:
        mensaje_a_hablar: El texto que el Agente Orquestador dirá en la nota de voz.
        destino: 'telegram' (envía nota de voz a Telegram), 'consola' (publica nota de voz en la consola), o 'ambos' (por defecto).
        reproducir_en_cornetas: Si es True, además de enviar la nota de voz, la reproduce por los altavoces de la PC.
    """
    print(f"\n🎙️ [Agente_Orquestador] Generando y enviando nota de voz (destino={destino})...")
    try:
        dest = (destino or "ambos").strip().lower()
        ruta_mp3 = generar_audio_voz(mensaje_a_hablar, formato="mp3")
        if not ruta_mp3 or not ruta_mp3.exists():
            return json.dumps({"status": "error", "mensaje": "No se pudo sintetizar el archivo de audio."}, ensure_ascii=False)

        audio_url = f"/static/notas_voz/{ruta_mp3.name}"
        resultados = {"audio_url": audio_url, "ruta_local": str(ruta_mp3)}

        if reproducir_en_cornetas:
            reproducir_archivo_en_cornetas(ruta_mp3, bloquear=False)
            resultados["cornetas"] = "Reproduciendo en cornetas de la PC"

        if dest in ("telegram", "ambos"):
            from telegram_bridge import enviar_nota_voz_telegram
            res_tg = enviar_nota_voz_telegram(
                texto_o_ruta_audio=str(ruta_mp3),
                caption=mensaje_a_hablar[:900],
                remitente="Agente_Orquestador",
                espejear_en_consola=(dest == "ambos" or dest == "telegram"),
            )
            resultados["telegram"] = res_tg
        elif dest == "consola":
            from memory import publicar_mensaje
            publicar_mensaje(
                de="Agente_Orquestador",
                para="usuario",
                tipo="nota_voz_dashboard",
                contenido={
                    "texto": mensaje_a_hablar,
                    "audio_url": audio_url,
                    "es_nota_voz": True,
                },
                canal_tipo="usuario",
            )
            resultados["consola"] = "Nota de voz publicada en la consola."

        return json.dumps({"status": "success", "resultados": resultados}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error enviando nota de voz: {e}"}, ensure_ascii=False)


def obtener_prompt_voz() -> str:
    """System Prompt especializado para interacción por voz, micrófono, cornetas y notas de voz."""
    return """[🎙️ DIRECTIVA DE SISTEMA DE VOZ, CORNETAS Y NOTAS DE VOZ]
Cuentas con un sistema de voz bidireccional completo (`skills/voz/`):
1. Si el usuario te pide que le envíes un audio o una nota de voz (por Telegram o por la Consola), o si te envió una nota de voz y deseas responderle con voz, invoca `tool_enviar_nota_voz(mensaje_a_hablar=..., destino='ambos')`.
2. Si el usuario te pide que hables directamente por las cornetas / altavoces de la computadora, invoca `tool_hablar_por_cornetas(mensaje=...)`.
3. Cuando redactes respuestas destinadas a ser habladas por voz o notas de voz, usa un tono natural, fluido, claro y ejecutivo, evitando leer código fuente o rutas largas.
"""


HERRAMIENTAS_VOZ = [
    tool_enviar_nota_voz,
    tool_hablar_por_cornetas,
    tool_escuchar_microfono,
]
