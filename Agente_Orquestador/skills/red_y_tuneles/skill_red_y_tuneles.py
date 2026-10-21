"""
skill_red_y_tuneles.py — Habilidad: Gestor de Conectividad Wi-Fi Local y Túneles Remotos
========================================================================================
Permite a la tripulación generar, consultar y exponer enlaces de acceso para dispositivos
móviles (teléfonos, tablets) tanto si están conectados en la MISMA red Wi-Fi como si están
en DISTINTAS redes (redes móviles 4G/LTE de Digitel/Movistar o ubicaciones remotas).

Tecnología de túnel:
- SSH inverso seguro hacia localhost.run (sin bloqueos de ISP en Venezuela, sin OFAC, sin token).
"""

import os
import re
import time
import json
import socket
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ARCHIVOS_TEMP = _APP_ROOT / "Archivos_temporales"
_ENLACES_JSON = _ARCHIVOS_TEMP / "enlaces_activos.json"
_TUNEL_LOG = _ARCHIVOS_TEMP / "tunel_remoto.log"

_TUNEL_ACTIVO: Dict[str, Any] = {
    "process": None,
    "puerto": None,
    "url_publica": None,
    "timestamp": None
}


def obtener_ip_local_wifi() -> str:
    """Detecta la dirección IP local de la computadora en la red Wi-Fi activa."""
    # 1. Variable de entorno directa o archivo .env
    host_ip = os.getenv("HOST_WIFI_IP", "").strip()
    if host_ip and not host_ip.startswith(("172.", "127.")):
        return host_ip

    env_file = _APP_ROOT / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("HOST_WIFI_IP="):
                    val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    if val and not val.startswith(("172.", "127.")):
                        return val
        except Exception:
            pass

    # 2. Socket local si se ejecuta en el host Windows
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()

    if not ip.startswith(("172.", "127.")):
        return ip

    return "192.168.0.197"


def verificar_url_tunel(url: str) -> bool:
    """Verifica si una URL pública de túnel responde activamente."""
    if not url:
        return False
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "TripulacionIA-Probe/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in [200, 301, 302, 307]
    except Exception:
        return False


def iniciar_tunel_ssh(puerto: int = 8000) -> Optional[str]:
    # Verificar si ya existe en archivo de estado
    if _ENLACES_JSON.exists():
        try:
            d = json.loads(_ENLACES_JSON.read_text(encoding='utf-8'))
            cached_url = d.get('remoto_tunel', {}).get('url_base')
            if cached_url and verificar_url_tunel(cached_url):
                return cached_url
        except Exception:
            pass

    """
    Inicia un túnel SSH inverso seguro hacia localhost.run para exponer el puerto local a internet.
    Bypasea censuras y filtros ISP de Venezuela.
    """
    global _TUNEL_ACTIVO

    # Si ya hay un túnel activo y funcionando en ese puerto, reutilizarlo
    if _TUNEL_ACTIVO.get("url_publica") and _TUNEL_ACTIVO.get("puerto") == puerto:
        if verificar_url_tunel(_TUNEL_ACTIVO["url_publica"]):
            return _TUNEL_ACTIVO["url_publica"]

    _ARCHIVOS_TEMP.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-R", f"80:127.0.0.1:{puerto}",
        "nokey@localhost.run"
    ]

    try:
        log_file = open(_TUNEL_LOG, "w+", encoding="utf-8", errors="ignore")
        flags = 0
        if os.name == 'nt':
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            start_new_session=True
        )
        _TUNEL_ACTIVO["process"] = proc
        _TUNEL_ACTIVO["puerto"] = puerto
        _TUNEL_ACTIVO["timestamp"] = time.time()

        # Esperar hasta 8 segundos para que localhost.run asigne el subdominio TLS
        patron_url = re.compile(r"https://[a-zA-Z0-9-]+\.lhr\.life")
        url_detectada = None

        for _ in range(16):
            time.sleep(0.5)
            log_file.seek(0)
            contenido = log_file.read()
            match = patron_url.search(contenido)
            if match:
                url_detectada = match.group(0)
                _TUNEL_ACTIVO["url_publica"] = url_detectada
                break

        return url_detectada
    except Exception as e:
        print(f"[skill_red_y_tuneles] Error iniciando tunel SSH: {e}")
        return None


def guardar_estado_enlaces(datos: dict) -> None:
    """Guarda el mapa de enlaces en Archivos_temporales para consulta compartida."""
    try:
        _ARCHIVOS_TEMP.mkdir(parents=True, exist_ok=True)
        _ENLACES_JSON.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


@tool
def tool_obtener_enlaces_acceso(servicio: str = "todos") -> str:
    """
    Genera y devuelve los enlaces de acceso para conectar teléfonos móviles y tablets a los
    proyectos de la tripulación (Dashboard, Portafolio Web u otros servicios locales).
    
    Provee automáticamente DOS vías de acceso:
    1. Misma red Wi-Fi: Conexión ultrarrápida local directa.
    2. Distintas redes (Túnel Remoto 4G/LTE): Conexión global segura HTTPS sin bloqueos de operadoras.
    
    Args:
        servicio: 'todos', 'dashboard', o 'portafolio'.
    """
    ip_wifi = obtener_ip_local_wifi()
    url_tunel = iniciar_tunel_ssh(puerto=8000)

    # Construir enlaces Wi-Fi
    wifi_dashboard = f"http://{ip_wifi}:8000/"
    wifi_portafolio = f"http://{ip_wifi}:8000/portafolio/"

    # Construir enlaces Remotos / Túnel
    if url_tunel:
        remoto_dashboard = f"{url_tunel}/"
        remoto_portafolio = f"{url_tunel}/portafolio/"
    else:
        remoto_dashboard = "Túnel en proceso de inicialización..."
        remoto_portafolio = "Túnel en proceso de inicialización..."

    datos_registro = {
        "ip_wifi": ip_wifi,
        "wifi": {
            "dashboard": wifi_dashboard,
            "portafolio": wifi_portafolio
        },
        "remoto_tunel": {
            "url_base": url_tunel,
            "dashboard": remoto_dashboard,
            "portafolio": remoto_portafolio
        },
        "actualizado_en": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    guardar_estado_enlaces(datos_registro)

    reporte = (
        f"📱 **ENLACES DE ACCESO MÓVIL DISPONIBLES**\n\n"
        f"📶 **1. SI ESTÁS EN EL MISMO WI-FI (Tu casa/oficina):**\n"
        f"• 🖥️ **Dashboard Tripulación:** `{wifi_dashboard}`\n"
        f"• 💼 **Portafolio Web:** `{wifi_portafolio}`\n\n"
        f"🌐 **2. SI ESTÁS EN DISTINTAS REDES (Datos 4G Digitel/Movistar o fuera de casa):**\n"
        f"• 🖥️ **Dashboard Remoto:** {remoto_dashboard}\n"
        f"• 💼 **Portafolio Remoto:** {remoto_portafolio}\n\n"
        f"💡 *Nota:* Ambos enlaces cargan inmediatamente en el navegador del teléfono sin bloqueos."
    )
    return reporte


def obtener_prompt_red_y_tuneles() -> str:
    """Prompt especializado para la gestión de conectividad y túneles."""
    return """[🛑 CAPACIDAD DE CONECTIVIDAD MULTI-RED Y TÚNELES ACTIVA 🛑]
Tienes la capacidad de conectar dispositivos móviles del usuario tanto en la misma red Wi-Fi como en distintas redes (datos móviles 4G remotos).
Siempre que el usuario solicite acceder al Dashboard, al Portafolio o a proyectos desde el teléfono o redes externas:
1. Usa 'tool_obtener_enlaces_acceso' para generar de inmediato ambos enlaces (Wi-Fi local y Túnel seguro).
2. Presenta ambos enlaces con claridad al usuario: la opción Wi-Fi si comparte la red, y la opción de Túnel Remoto si usa datos 4G o está fuera.
3. Asegura que los enlaces apunten a los puertos y rutas correctas: '/portafolio/' para el portafolio y '/' para el Dashboard.
"""

HERRAMIENTAS_RED_Y_TUNELES = [
    tool_obtener_enlaces_acceso
]
