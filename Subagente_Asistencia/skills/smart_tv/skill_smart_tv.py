"""
skill_smart_tv.py — Control Remoto Virtual y Gestión de Smart TVs para Sanji (Subagente_Asistencia)
===================================================================================================
Permite a Sanji interactuar con los televisores inteligentes del hogar/oficina:
- Enviar teclas remotas (arriba, abajo, izquierda, derecha, ok, atras, inicio, menu, subir_volumen, bajar_volumen, silenciar).
- Consultar estado y volumen del televisor.
- Escribir texto en buscadores de la TV o apps multimedia como Magic.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional

_APP_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CERT_DIR = _APP_ROOT / "Archivos_temporales" / "tv_certs"
DEFAULT_IP = "192.168.0.193"

MAPA_TECLAS = {
    "arriba": "DPAD_UP",
    "up": "DPAD_UP",
    "abajo": "DPAD_DOWN",
    "down": "DPAD_DOWN",
    "izquierda": "DPAD_LEFT",
    "left": "DPAD_LEFT",
    "derecha": "DPAD_RIGHT",
    "right": "DPAD_RIGHT",
    "ok": "DPAD_CENTER",
    "enter": "DPAD_CENTER",
    "select": "DPAD_CENTER",
    "atras": "BACK",
    "back": "BACK",
    "inicio": "HOME",
    "home": "HOME",
    "menu": "MENU",
    "subir_volumen": "VOLUME_UP",
    "vol_up": "VOLUME_UP",
    "bajar_volumen": "VOLUME_DOWN",
    "vol_down": "VOLUME_DOWN",
    "silenciar": "MUTE",
    "mute": "MUTE",
    "play": "MEDIA_PLAY_PAUSE",
    "pausa": "MEDIA_PLAY_PAUSE",
}

def tool_silenciar_smart_tv(ip: str = DEFAULT_IP) -> dict:
    """
    Pone en silencio (Mute / Silenciar) la Smart TV inmediatamente.
    Usa el protocolo oficial Android TV Remote con el certificado emparejado.
    """
    return tool_controlar_smart_tv(comando="silenciar", repeticiones=1, ip=ip)

def tool_controlar_smart_tv(comando: str, repeticiones: int = 1, ip: str = DEFAULT_IP, texto_extra: str = "") -> dict:
    """
    Envía comandos de control remoto a la Smart TV:
    - comando: 'arriba', 'abajo', 'izquierda', 'derecha', 'ok', 'atras', 'inicio', 'menu', 'subir_volumen', 'bajar_volumen', 'silenciar', 'escribir', 'abrir'
    - repeticiones: número de veces a pulsar la tecla (ej. 5 para subir volumen 5 veces)
    - ip: dirección IP del televisor (por defecto 192.168.0.193)
    - texto_extra: texto a escribir si el comando es 'escribir'
    """
    try:
        from androidtvremote2 import AndroidTVRemote
    except ImportError:
        return {"status": "error", "mensaje": "Libreria androidtvremote2 no disponible."}

    cert = str(CERT_DIR / "cert.pem")
    key = str(CERT_DIR / "key.pem")

    if not os.path.exists(cert) or not os.path.exists(key):
        return {"status": "error", "mensaje": f"Certificados de TV no encontrados en {CERT_DIR}."}

    async def _run():
        remote = AndroidTVRemote("Flota_Antigravity", cert, key, ip)
        await remote.async_connect()
        cmd_lower = comando.lower().strip()

        if cmd_lower in ["escribir", "text", "type"] and texto_extra:
            remote.send_text(texto_extra)
            await asyncio.sleep(0.5)
            res = f"Texto '{texto_extra}' enviado a la TV."
        elif cmd_lower in MAPA_TECLAS:
            tecla = MAPA_TECLAS[cmd_lower]
            for _ in range(repeticiones):
                remote.send_key_command(tecla, "SHORT")
                await asyncio.sleep(0.15)
            res = f"Tecla '{tecla}' enviada {repeticiones} vez/veces a la TV ({ip})."
        elif cmd_lower == "estado":
            info = {
                "encendido": remote.is_on,
                "volumen": remote.volume_info,
                "dispositivo": remote.device_info,
                "app_actual": remote.current_app
            }
            remote.disconnect()
            return {"status": "success", "info": info}
        else:
            tecla = comando.upper()
            for _ in range(repeticiones):
                remote.send_key_command(tecla, "SHORT")
                await asyncio.sleep(0.15)
            res = f"Tecla cruda '{tecla}' enviada a la TV."

        await asyncio.sleep(0.2)
        remote.disconnect()
        return {"status": "success", "mensaje": res}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resultado = loop.run_until_complete(_run())
        loop.close()
        return resultado
    except Exception as e:
        return {"status": "error", "mensaje": f"Error comunicando con la Smart TV ({ip}): {e}"}

def tool_obtener_estado_smart_tv(ip: str = DEFAULT_IP) -> dict:
    """
    Obtiene el estado en vivo de la Smart TV (encendido, volumen, app activa y dispositivo).
    """
    return tool_controlar_smart_tv(comando="estado", ip=ip)
