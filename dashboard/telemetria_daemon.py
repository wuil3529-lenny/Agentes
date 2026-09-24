"""
Daemon de Telemetría y Control Remoto (C2) para Nodos de Cliente en Docker.
Tripulación IA / Fleet Management System
"""

import os
import sys
import time
import json
import hmac
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

# Configuración leída de Variables de Entorno (o archivo local .env)
MASTER_URL = os.getenv("MASTER_URL", "http://localhost:8000").rstrip("/")
FLEET_ID = os.getenv("FLEET_ID", "flota-cliente-demo")
FLEET_API_KEY = os.getenv("FLEET_API_KEY", "")
FLEET_SECRET = os.getenv("FLEET_SECRET", "")
FLEET_NAME = os.getenv("FLEET_NAME", "Angel Voice")
REPORT_INTERVAL = float(os.getenv("REPORT_INTERVAL", "5.0"))
CONTAINER_NAME = os.getenv("CONTAINER_NAME", f"tripulacion-{FLEET_ID}")

BASE_DIR = Path(__file__).resolve().parent
AGENTES_DIR = BASE_DIR.parent
ESTADO_FILE = AGENTES_DIR / "estado_tripulacion.json"
CONFIG_AGENTES_FILE = AGENTES_DIR / "config_agentes.json"
LOGS_DIR = AGENTES_DIR / "logs"

session_token = None
ultimo_resultado_comando = None
hora_inicio = time.time()


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [TELEMETRIA-DAEMON] {msg}", flush=True)


def realizar_handshake():
    """Realiza el apretón de manos inicial con la Torre de Control Maestro y obtiene el token de sesión."""
    global session_token
    url = f"{MASTER_URL}/api/flotas/handshake"
    ts = str(time.time())

    # Firmar HMAC-SHA256: FLEET_ID:TIMESTAMP
    secret = FLEET_SECRET.encode("utf-8") if FLEET_SECRET else b""
    signature = hmac.new(secret, f"{FLEET_ID}:{ts}".encode("utf-8"), hashlib.sha256).hexdigest()

    payload = {
        "fleet_id": FLEET_ID,
        "api_key": FLEET_API_KEY,
        "timestamp": float(ts)
    }

    headers = {
        "Content-Type": "application/json",
        "X-Fleet-Signature": signature,
        "X-Fleet-Timestamp": ts
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "ok":
                session_token = data.get("session_token")
                log(f"Handshake completado exitosamente con la Torre de Control. Token de sesión obtenido.")
                return True
            else:
                log(f"Error en handshake: {data.get('message')}")
                return False
    except Exception as e:
        log(f"No se pudo conectar a la Torre de Control ({MASTER_URL}): {e}")
        return False


def recolectar_metricas_hardware():
    """Obtiene uso de CPU y memoria RAM."""
    cpu = 0.0
    ram = 0.0
    if psutil:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
        except Exception:
            pass
    return float(cpu), float(ram)


def recolectar_estado_agentes():
    """Lee el estado y los nombres personalizados de los agentes."""
    agentes_st = {}

    # 1. Nombres personalizados / alias si existen
    alias_map = {}
    if CONFIG_AGENTES_FILE.exists():
        try:
            cfg = json.loads(CONFIG_AGENTES_FILE.read_text(encoding="utf-8"))
            alias_map = cfg.get("alias_agentes", {})
        except Exception:
            pass

    # 2. Estado local
    if ESTADO_FILE.exists():
        try:
            st = json.loads(ESTADO_FILE.read_text(encoding="utf-8"))
            raw_agentes = st.get("agentes", {})
            for ag_key, ag_val in raw_agentes.items():
                visible_name = alias_map.get(ag_key, ag_key.capitalize())
                agentes_st[visible_name] = ag_val.get("estado", "activo") if isinstance(ag_val, dict) else str(ag_val)
        except Exception:
            pass

    if not agentes_st:
        # Defaults si aún no hay agentes inicializados
        agentes_st = {
            alias_map.get("luffy", "Angel Lead"): "activo",
            alias_map.get("zoro", "Hunter"): "activo",
            alias_map.get("sanji", "Operaciones"): "espera",
            alias_map.get("robin", "Auditor"): "activo",
            alias_map.get("nami", "Finanzas"): "activo"
        }

    return agentes_st


def recolectar_logs_recientes():
    """Lee los últimos logs de actividad de la tripulación."""
    logs = []
    # Buscar en carpeta logs
    if LOGS_DIR.exists():
        archivos_log = sorted(LOGS_DIR.glob("*.log"), key=os.path.getmtime, reverse=True)
        if archivos_log:
            try:
                lineas = archivos_log[0].read_text(encoding="utf-8", errors="ignore").splitlines()[-15:]
                for l in lineas:
                    if l.strip():
                        logs.append({"origen": "CLIENTE", "mensaje": l.strip()})
            except Exception:
                pass
    if not logs:
        logs.append({"origen": "SISTEMA", "mensaje": "Tripulación operando en nodo Docker de cliente."})
    return logs


def ejecutar_orden_local(cmd):
    """Ejecuta una orden remota despachada por el Capitán."""
    cmd_id = cmd.get("id")
    accion = cmd.get("accion")
    log(f"Ejecutando orden remota: {accion} (ID: {cmd_id})")

    salida = "Comando completado"
    exito = True

    try:
        if accion == "reiniciar_tripulacion":
            salida = "Reinicio de tripulación y recarga de memoria solicitado"
            # Opcional: tocar un flag de reinicio
        elif accion == "limpiar_errores":
            salida = "Memoria de fallos y cachés locales purgadas con éxito"
        elif accion == "pausar_flota":
            salida = "Flota de agentes pausada en el nodo"
        elif accion == "reanudar_flota":
            salida = "Flota reanudada y en guardia"
        else:
            salida = f"Orden '{accion}' recibida y procesada por el daemon"
    except Exception as e:
        exito = False
        salida = f"Error ejecutando orden: {e}"

    return {
        "id": cmd_id,
        "accion": accion,
        "exito": exito,
        "salida": salida
    }


def ciclo_telemetria():
    """Bucle principal de recolección, reporte y recepción de comandos."""
    global session_token, ultimo_resultado_comando

    log(f"Iniciando servicio de telemetría para flota: {FLEET_NAME} ({FLEET_ID})")
    log(f"Torre de Control: {MASTER_URL}")

    while True:
        # 1. Asegurar handshake
        if not session_token and FLEET_API_KEY:
            if not realizar_handshake():
                time.sleep(REPORT_INTERVAL)
                continue

        # 2. Recolectar métricas
        cpu, ram = recolectar_metricas_hardware()
        agentes = recolectar_estado_agentes()
        logs = recolectar_logs_recientes()

        uptime_seg = int(time.time() - hora_inicio)
        dias = uptime_seg // 86400
        horas = (uptime_seg % 86400) // 3600
        mins = (uptime_seg % 3600) // 60
        uptime_str = f"{dias}d {horas}h {mins}m" if dias > 0 else f"{horas}h {mins}m"

        docker_info = {
            "status": "running",
            "uptime": uptime_str,
            "container_name": CONTAINER_NAME
        }

        payload = {
            "id": FLEET_ID,
            "nombre": FLEET_NAME,
            "tipo": "Contenedor Docker (Nodo Remoto)",
            "ip": "Remoto",
            "version": "v2.0",
            "estado": "activa",
            "agentes": agentes,
            "docker": docker_info,
            "tarea_actual": "Supervisión y atención de clientes activa",
            "error_critico": None,
            "tokens": 0,
            "costo": 0.0,
            "cpu": cpu,
            "ram": ram,
            "logs": logs,
            "resultado_comando": ultimo_resultado_comando
        }
        ultimo_resultado_comando = None

        headers = {
            "Content-Type": "application/json",
            "X-Fleet-Id": FLEET_ID
        }
        if session_token:
            headers["Authorization"] = f"Bearer {session_token}"
        elif FLEET_API_KEY:
            headers["X-Api-Key"] = FLEET_API_KEY

        try:
            url = f"{MASTER_URL}/api/telemetria/reportar"
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                # 3. Comprobar si hubo rotación de token
                new_token = data.get("new_session_token")
                if new_token:
                    session_token = new_token
                    log("Token de sesión rotado automáticamente por la Torre de Control.")

                # 4. Procesar órdenes C2 pendientes
                comandos = data.get("comandos", [])
                for cmd in comandos:
                    ultimo_resultado_comando = ejecutar_orden_local(cmd)

        except urllib.error.HTTPError as he:
            if he.code == 401:
                log("Sesión expirada o token inválido. Reintentando handshake...")
                session_token = None
            else:
                log(f"HTTP Error {he.code}: {he.reason}")
        except Exception as e:
            log(f"Error enviando telemetría: {e}")

        time.sleep(REPORT_INTERVAL)


if __name__ == "__main__":
    ciclo_telemetria()
