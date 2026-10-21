import os
import sys
import time
from datetime import datetime
from pathlib import Path
import requests

_THIS_DIR = Path(__file__).resolve().parent
_APP_ROOT = _THIS_DIR.parent
_SKILLS_DIR = _THIS_DIR / "skills"
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))


def _obtener_credenciales_telegram() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        env_path = _APP_ROOT / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    l_str = line.strip()
                    if l_str.startswith("TELEGRAM_BOT_TOKEN=") and not token:
                        token = l_str.split("=", 1)[1].strip().strip('"').strip("'")
                    elif l_str.startswith("TELEGRAM_CHAT_ID=") and not chat_id:
                        chat_id = l_str.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
    return token, chat_id



def _dividir_texto_telegram(texto: str, max_chunk: int = 4000) -> list[str]:
    """Divide un texto en bloques de max_chunk caracteres respetando párrafos y saltos de línea."""
    if not texto or len(texto) <= max_chunk:
        return [texto] if texto else []
    partes = []
    resto = texto.strip()
    while len(resto) > max_chunk:
        corte = resto[:max_chunk].rfind("\n\n")
        if corte == -1 or corte < max_chunk // 2:
            corte = resto[:max_chunk].rfind("\n")
        if corte == -1 or corte < max_chunk // 2:
            corte = resto[:max_chunk].rfind(" ")
        if corte == -1 or corte < max_chunk // 2:
            corte = max_chunk
        partes.append(resto[:corte].strip())
        resto = resto[corte:].strip()
    if resto:
        partes.append(resto)
    return partes


def enviar_mensaje_telegram(mensaje: str, remitente: str = "Agente_Orquestador", audio_url: str = "", espejear_en_consola: bool = True) -> str:
    """
    Envía un mensaje a través de Telegram usando el bot y asegura el espejo en la consola.
    Soporta división automática si excede el límite de Telegram (4096 caracteres).
    """
    token, chat_id = _obtener_credenciales_telegram()
    res = "Telegram no configurado."
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        chunks = _dividir_texto_telegram(mensaje, max_chunk=4000)
        exitos = 0
        errores = []
        for ch in chunks:
            payload = {"chat_id": chat_id, "text": ch}
            try:
                r = requests.post(url, json=payload, timeout=15)
                r.raise_for_status()
                exitos += 1
            except Exception as e:
                errores.append(str(e))
        if exitos > 0 and not errores:
            res = "Mensaje enviado con éxito."
        elif exitos > 0:
            res = f"Mensaje enviado parcialmente ({exitos}/{len(chunks)}): {'; '.join(errores)}"
        else:
            res = f"Error enviando mensaje por Telegram: {'; '.join(errores)}"

    # Espejo automático hacia la consola del Dashboard
    if not espejear_en_consola:
        return res
    try:
        from memory import publicar_mensaje, _cargar_canal
        canal = _cargar_canal("usuario")
        mensajes = canal.get("mensajes", [])
        ya_existe = False
        if mensajes:
            ult = mensajes[-1]
            if ult.get("de") == remitente and ult.get("contenido", {}).get("texto") == mensaje:
                if audio_url and isinstance(ult.get("contenido"), dict):
                    ult["contenido"]["audio_url"] = audio_url
                    ult["contenido"]["es_nota_voz"] = True
                ya_existe = True
        if not ya_existe:
            contenido_obj = {"texto": mensaje}
            if audio_url:
                contenido_obj["audio_url"] = audio_url
                contenido_obj["es_nota_voz"] = True
            publicar_mensaje(
                de=remitente,
                para="usuario",
                tipo="mensaje_dashboard",
                contenido=contenido_obj,
                canal_tipo="usuario",
            )
    except Exception as e_pub:
        print(f"[telegram_bridge] Error espejeando mensaje a consola: {e_pub}")

    return res


def _normalizar_ruta_archivo(ruta_str: str | Path) -> Path | None:
    if not ruta_str:
        return None
    r_str = str(ruta_str).strip().strip('"').strip("'")
    if not r_str:
        return None

    # 1. Probar ruta directa
    try:
        p = Path(r_str)
        if p.exists() and p.is_file():
            return p
    except Exception:
        pass

    # 2. Manejar rutas con formato Windows en Linux/Docker o viceversa
    r_norm = r_str.replace("\\", "/")

    # Si viene con prefijo C:/Users/.../Agentes/
    if "Agentes/" in r_norm:
        sub = r_norm.split("Agentes/", 1)[1]
        p_sub = _APP_ROOT / sub
        if p_sub.exists() and p_sub.is_file():
            return p_sub

    if "Archivos_temporales/" in r_norm:
        sub = r_norm.split("Archivos_temporales/", 1)[1]
        p_arch = _APP_ROOT / "Archivos_temporales" / sub
        if p_arch.exists() and p_arch.is_file():
            return p_arch

    # 3. Probar relativo a _APP_ROOT
    p_rel = _APP_ROOT / r_norm.lstrip("/")
    if p_rel.exists() and p_rel.is_file():
        return p_rel

    # 4. Probar en Archivos_temporales por nombre de archivo
    try:
        p_temp = _APP_ROOT / "Archivos_temporales" / Path(r_norm).name
        if p_temp.exists() and p_temp.is_file():
            return p_temp
    except Exception:
        pass

    return None


_ULTIMAS_FOTOS_ENVIADAS: dict[str, float] = {}

def enviar_foto_telegram(
    ruta_foto: str | Path,
    caption: str = "",
    remitente: str = "Agente_Orquestador",
    espejear_en_consola: bool = True,
) -> str:
    """
    Envía una foto nativa (`sendPhoto`) a Telegram con caption opcional
    y asegura el espejo en la consola del Dashboard.
    """
    token, chat_id = _obtener_credenciales_telegram()
    p_foto = _normalizar_ruta_archivo(ruta_foto)
    if not p_foto or not p_foto.exists():
        return f"Error: Archivo de foto no encontrado en ruta '{ruta_foto}'"

    ahora = time.time()
    nombre_archivo = p_foto.name
    if nombre_archivo in _ULTIMAS_FOTOS_ENVIADAS and (ahora - _ULTIMAS_FOTOS_ENVIADAS[nombre_archivo]) < 15:
        return "Foto ya fue enviada recientemente (anti-duplicados)."
    _ULTIMAS_FOTOS_ENVIADAS[nombre_archivo] = ahora

    res = "Telegram no configurado."
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(p_foto, "rb") as f_img:
                files = {"photo": (p_foto.name, f_img)}
                data = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption[:1024]
                r = requests.post(url, data=data, files=files, timeout=30)
                r.raise_for_status()
                res = "Foto enviada a Telegram con éxito."
        except Exception as e:
            res = f"Error enviando foto por Telegram: {e}"

    if espejear_en_consola:
        try:
            from memory import publicar_mensaje
            img_url = f"/static/capturas/{p_foto.name}"
            publicar_mensaje(
                de=remitente,
                para="usuario",
                tipo="mensaje_dashboard",
                contenido={
                    "texto": caption or f"📸 Captura enviada: {p_foto.name}",
                    "imagen_url": img_url,
                    "archivo": str(p_foto),
                },
                canal_tipo="usuario",
            )
        except Exception as e_pub:
            print(f"[telegram_bridge] Error espejeando foto a consola: {e_pub}")

    return res


def enviar_documento_telegram(
    ruta_documento: str | Path,
    caption: str = "",
    remitente: str = "Agente_Orquestador",
    espejear_en_consola: bool = True,
) -> str:
    """
    Envía un documento o archivo nativo (`sendDocument`) a Telegram (PDF, docx, txt, zip, png, etc.)
    y asegura el espejo en la consola del Dashboard.
    """
    token, chat_id = _obtener_credenciales_telegram()
    p_doc = _normalizar_ruta_archivo(ruta_documento)
    if not p_doc or not p_doc.exists():
        return f"Error: Archivo de documento no encontrado en ruta '{ruta_documento}'"

    res = "Telegram no configurado."
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        try:
            with open(p_doc, "rb") as f_file:
                files = {"document": (p_doc.name, f_file)}
                data = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption[:1024]
                r = requests.post(url, data=data, files=files, timeout=40)
                r.raise_for_status()
                res = "Documento enviado a Telegram con éxito."
        except Exception as e:
            res = f"Error enviando documento por Telegram: {e}"

    if espejear_en_consola:
        try:
            from memory import publicar_mensaje
            publicar_mensaje(
                de=remitente,
                para="usuario",
                tipo="mensaje_dashboard",
                contenido={
                    "texto": caption or f"📎 Documento enviado: {p_doc.name}",
                    "archivo": str(p_doc),
                },
                canal_tipo="usuario",
            )
        except Exception as e_pub:
            print(f"[telegram_bridge] Error espejeando documento a consola: {e_pub}")

    return res


def _es_ruta_audio_existente(valor: str) -> Path | None:
    if not valor or "\n" in valor or "\r" in valor or len(valor) > 240:
        return None
    if not valor.strip().lower().endswith((".mp3", ".ogg", ".wav", ".webm", ".m4a")):
        return None
    try:
        p = Path(valor.strip())
        if p.exists() and p.is_file():
            return p
    except Exception:
        pass
    return None


def enviar_nota_voz_telegram(
    texto_o_ruta_audio: str,
    caption: str = "",
    remitente: str = "Agente_Orquestador",
    espejear_en_consola: bool = True,
) -> str:
    """
    Envía una nota de voz nativa (`sendVoice`) a Telegram y la espejea en la Consola con reproductor de audio.
    `texto_o_ruta_audio` puede ser la ruta a un archivo `.mp3`/`.ogg`/`.wav` existente, o directamente el
    texto que debe sintetizarse en voz.
    """
    token, chat_id = _obtener_credenciales_telegram()
    from voz.skill_voz import generar_audio_voz

    posible_ruta = _es_ruta_audio_existente(texto_o_ruta_audio)
    ruta_mp3 = None
    ruta_ogg = None
    texto_para_consola = caption or texto_o_ruta_audio

    if posible_ruta is not None:
        if posible_ruta.suffix.lower() == ".ogg":
            ruta_ogg = posible_ruta
            ruta_mp3 = posible_ruta
        else:
            ruta_mp3 = posible_ruta
            ruta_ogg = posible_ruta
    else:
        ruta_mp3 = generar_audio_voz(texto_o_ruta_audio, formato="mp3")
        ruta_ogg = ruta_mp3

    archivo_enviar = ruta_ogg or ruta_mp3
    audio_url_consola = f"/static/notas_voz/{Path(ruta_mp3 or archivo_enviar).name}" if (archivo_enviar and Path(archivo_enviar).exists()) else ""
    res_tg = "Telegram no configurado (nota de voz guardada en consola)."

    if archivo_enviar and Path(archivo_enviar).exists() and token and chat_id:
        texto_completo = (caption or (texto_o_ruta_audio if not _es_ruta_audio_existente(texto_o_ruta_audio) else "")).strip()
        es_texto_largo = len(texto_completo) > 950
        caption_audio = texto_completo[:920] + "... 📜 (Texto completo a continuación 👇)" if es_texto_largo else texto_completo

        url_voice = f"https://api.telegram.org/bot{token}/sendVoice"
        try:
            with open(archivo_enviar, "rb") as f_audio:
                mime_type = "audio/ogg" if str(archivo_enviar).lower().endswith(".ogg") else "audio/mpeg"
                files = {"voice": (Path(archivo_enviar).name, f_audio, mime_type)}
                data = {"chat_id": chat_id}
                if caption_audio:
                    data["caption"] = caption_audio
                r = requests.post(url_voice, data=data, files=files, timeout=25)
                if r.status_code == 200:
                    res_tg = "Nota de voz enviada por Telegram con éxito."
                else:
                    url_audio = f"https://api.telegram.org/bot{token}/sendAudio"
                    with open(ruta_mp3 or archivo_enviar, "rb") as f_mp3:
                        r2 = requests.post(
                            url_audio,
                            data={"chat_id": chat_id, "caption": caption_audio, "title": "Voz Tripulación"},
                            files={"audio": (Path(ruta_mp3 or archivo_enviar).name, f_mp3, "audio/mpeg")},
                            timeout=25,
                        )
                        r2.raise_for_status()
                        res_tg = "Audio enviado por Telegram con éxito."
        except Exception as e:
            res_tg = f"Error enviando nota de voz por Telegram: {e}"

        # Si el texto era largo (>950 chars), enviar el texto 100% COMPLETO inmediatamente vía sendMessage
        if es_texto_largo:
            url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
            chunks = _dividir_texto_telegram(texto_completo, max_chunk=4000)
            for ch in chunks:
                try:
                    requests.post(url_msg, json={"chat_id": chat_id, "text": ch}, timeout=15)
                except Exception as e_ch:
                    print(f"[telegram_bridge] Error enviando texto completo post-voz: {e_ch}")

    if espejear_en_consola:
        try:
            from memory import publicar_mensaje
            contenido_msg = {
                "texto": texto_para_consola,
                "es_nota_voz": bool(audio_url_consola),
            }
            if audio_url_consola:
                contenido_msg["audio_url"] = audio_url_consola
            publicar_mensaje(
                de=remitente,
                para="usuario",
                tipo="nota_voz_dashboard" if audio_url_consola else "mensaje_dashboard",
                contenido=contenido_msg,
                canal_tipo="usuario",
            )
        except Exception as e_pub:
            print(f"[telegram_bridge] Error espejeando nota de voz a consola: {e_pub}")

    return res_tg



def _procesar_nota_voz_entrante_telegram(token: str, file_id: str) -> tuple[str, str]:
    """
    Descarga una nota de voz o archivo de audio enviado por el usuario desde Telegram,
    lo guarda en `dashboard/static/notas_voz/` y lo transcribe a texto con `skill_voz`.
    Retorna (texto_transcrito, audio_url_local).
    """
    try:
        r_info = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=15,
        )
        r_info.raise_for_status()
        file_path_tg = r_info.json().get("result", {}).get("file_path", "")
        if not file_path_tg:
            return "", ""

        ext = Path(file_path_tg).suffix or ".ogg"
        notas_dir = _APP_ROOT / "dashboard" / "static" / "notas_voz"
        notas_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_file = notas_dir / f"tg_usuario_{ts}{ext}"

        r_bin = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path_tg}", timeout=30)
        r_bin.raise_for_status()
        local_file.write_bytes(r_bin.content)

        from voz.skill_voz import transcribir_archivo_audio
        res_stt = transcribir_archivo_audio(local_file)
        texto = res_stt.get("texto", "").strip()
        audio_url = f"/static/notas_voz/{local_file.name}"
        return texto, audio_url
    except Exception as e:
        print(f"[telegram_bridge] Error procesando nota de voz entrante de Telegram: {e}")
        return "", ""


def daemon_mode():
    """
    Bucle principal para leer mensajes de texto Y notas de voz de Telegram
    y pasarlos a la memoria del sistema.
    """
    token, _ = _obtener_credenciales_telegram()
    if not token:
        print("[telegram_bridge] TELEGRAM_BOT_TOKEN no definido. Saliendo gracefully...")
        sys.exit(0)

    print("[telegram_bridge] Iniciando puente de Telegram (Texto + Notas de Voz) en background...")

    try:
        from memory import publicar_mensaje
    except ImportError:
        print("[telegram_bridge] ⚠️ Advertencia: No se pudo importar 'publicar_mensaje'.")
        publicar_mensaje = None

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0

    while True:
        try:
            r = requests.get(url, params={"timeout": 30, "offset": offset}, timeout=40)
            if r.status_code == 200:
                data = r.json()
                for item in data.get("result", []):
                    offset = item["update_id"] + 1
                    msg = item.get("message", {})
                    texto = msg.get("text", "")

                    # 1. Mensaje de texto normal
                    if texto:
                        print(f"[telegram_bridge] Comando de usuario recibido: {texto}")
                        if publicar_mensaje:
                            publicar_mensaje(
                                "usuario",
                                "Agente_Orquestador",
                                "mensaje_telegram",
                                {"texto": texto},
                                "usuario",
                            )
                        continue

                    # 2. Nota de voz (voice) o archivo de audio (audio) enviado por el usuario en Telegram
                    voice_obj = msg.get("voice") or msg.get("audio")
                    if voice_obj and isinstance(voice_obj, dict):
                        file_id = voice_obj.get("file_id", "")
                        if file_id:
                            print(f"[telegram_bridge] 🎙️ Nota de voz recibida desde Telegram (file_id={file_id[:16]}...). Transcribiendo...")
                            texto_stt, audio_url = _procesar_nota_voz_entrante_telegram(token, file_id)
                            if texto_stt:
                                print(f"[telegram_bridge] 📝 Nota de voz transcrita: \"{texto_stt}\"")
                                if publicar_mensaje:
                                    publicar_mensaje(
                                        "usuario",
                                        "Agente_Orquestador",
                                        "nota_voz_telegram",
                                        {
                                            "texto": texto_stt,
                                            "es_nota_voz": True,
                                            "origen_voz": "telegram",
                                            "audio_url": audio_url,
                                        },
                                        "usuario",
                                    )
                            else:
                                enviar_mensaje_telegram("⚠️ Recibí tu nota de voz, pero no pude escuchar con claridad el audio. ¿Podrías repetirlo?")
                        continue

                    # 3. Foto o captura enviada por el usuario en Telegram
                    photo_obj = msg.get("photo")
                    doc_obj = msg.get("document")
                    caption_msg = msg.get("caption", "").strip()

                    file_id_img = None
                    if photo_obj and isinstance(photo_obj, list) and len(photo_obj) > 0:
                        file_id_img = photo_obj[-1].get("file_id")
                    elif doc_obj and isinstance(doc_obj, dict) and ('image' in doc_obj.get("mime_type", "") or doc_obj.get("file_name", "").endswith(('.jpg', '.png', '.jpeg', '.webp'))):
                        file_id_img = doc_obj.get("file_id")

                    if file_id_img:
                        print(f"[telegram_bridge] 📸 Captura/Foto recibida desde Telegram (file_id={file_id_img[:16]}...). Descargando...")
                        try:
                            r_info = requests.get(f"https://api.telegram.org/bot{token}/getFile", params={"file_id": file_id_img}, timeout=15)
                            if r_info.status_code == 200:
                                fp_tg = r_info.json().get("result", {}).get("file_path", "")
                                if fp_tg:
                                    ext_img = Path(fp_tg).suffix or ".jpg"
                                    capturas_dir = _APP_ROOT / "Archivos_temporales"
                                    capturas_dir.mkdir(parents=True, exist_ok=True)
                                    ts_img = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    local_img = capturas_dir / f"captura_telegram_{ts_img}{ext_img}"
                                    r_bin = requests.get(f"https://api.telegram.org/file/bot{token}/{fp_tg}", timeout=30)
                                    if r_bin.status_code == 200:
                                        local_img.write_bytes(r_bin.content)
                                        print(f"[telegram_bridge] ✅ Captura guardada en: {local_img} ({len(r_bin.content)} bytes)")
                                        texto_desc = f"[El usuario envió una captura de pantalla del móvil guardada en '{local_img.as_posix()}']"
                                        if caption_msg:
                                            texto_desc += f" Texto adjunto: '{caption_msg}'"
                                        texto_desc += f"\nAnaliza esta imagen con tus herramientas de visión para diagnosticar el error."
                                        if publicar_mensaje:
                                            publicar_mensaje(
                                                "usuario",
                                                "Agente_Orquestador",
                                                "mensaje_telegram",
                                                {
                                                    "texto": texto_desc,
                                                    "ruta_foto": str(local_img),
                                                    "caption": caption_msg,
                                                },
                                                "usuario",
                                            )
                        except Exception as e_foto:
                            print(f"[telegram_bridge] Error descargando foto de Telegram: {e_foto}")
                        continue

            time.sleep(1)
        except Exception as e:
            print(f"[telegram_bridge] Error en polling de Telegram: {e}")
            time.sleep(5)


if __name__ == "__main__":
    daemon_mode()
