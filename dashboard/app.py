import asyncio
import json
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import psutil
import platform
from typing import Optional, List, Dict, Any

# Intentar importar GPUtil para monitoreo de GPU
try:
    import GPUtil
except ImportError:
    GPUtil = None

app = FastAPI(title="Tripulacion.IA Dashboard")

BASE_DIR = Path(__file__).resolve().parent
AGENTES_DIR = BASE_DIR.parent
LUFFY_DIR = AGENTES_DIR / "Luffy"

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

from pydantic import BaseModel
import subprocess
import os

class ChatMessage(BaseModel):
    texto: str
    modo: str = "auto"

class ModeConfig(BaseModel):
    modo: str

@app.get("/api/modo")
async def get_modo():
    modo_path = AGENTES_DIR / "modo_agente.json"
    if modo_path.exists():
        try:
            return json.loads(modo_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"modo": "auto"}

@app.post("/api/modo")
async def set_modo(cfg: ModeConfig):
    modo_path = AGENTES_DIR / "modo_agente.json"
    data = {"modo": cfg.modo}
    modo_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "modo": cfg.modo}

@app.post("/api/chat")
async def send_chat(msg: ChatMessage):
    import datetime
    canal_path = AGENTES_DIR / "canal_usuario.json"
    try:
        if canal_path.exists():
            with open(canal_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = {"mensajes": []}
    except Exception:
        raw = {"mensajes": []}
    
    if isinstance(raw, dict):
        mensajes = raw.get("mensajes", [])
    elif isinstance(raw, list):
        mensajes = raw
    else:
        mensajes = []

    # Guardar modo activo seleccionado
    if msg.modo:
        modo_path = AGENTES_DIR / "modo_agente.json"
        try:
            modo_path.write_text(json.dumps({"modo": msg.modo}, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    msg_id = f"msg-{len(mensajes) + 1:03d}"
    nuevo_msg = {
        "id": msg_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "de": "usuario",
        "para": "Luffy",
        "tipo": "mensaje_dashboard",
        "modo": msg.modo,
        "estado": "enviado",
        "leido_por": ["usuario"],
        "contenido": {"texto": msg.texto}
    }
    mensajes.append(nuevo_msg)
    
    if len(mensajes) > 60:
        mensajes = mensajes[-60:]
        
    data_to_save = {"mensajes": mensajes}
    with open(canal_path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
    return {"status": "ok", "mensaje": nuevo_msg}

class EnvConfig(BaseModel):
    provider: str
    api_key: str
    model: str

def obtener_modelos_agentes():
    env_path = AGENTES_DIR / ".env"
    default_model = "deepseek-chat"
    agent_models = {}
    
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "DEFAULT_MODEL":
                    default_model = v
                elif k.startswith("MODEL_"):
                    ag_name = k.replace("MODEL_", "").lower()
                    agent_models[ag_name] = v
        except Exception:
            pass

    agentes = ["luffy", "zoro", "sanji", "robin", "nami"]
    return {ag: agent_models.get(ag, default_model) for ag in agentes}

class FullConfigPayload(BaseModel):
    keys: Optional[Dict[str, str]] = None
    base_urls: Optional[Dict[str, str]] = None
    default_model: Optional[str] = None
    default_provider: Optional[str] = None
    modelos: Optional[Dict[str, str]] = None
    presupuesto_maximo: Optional[float] = None
    telegram: Optional[Dict[str, str]] = None
    ollama: Optional[Dict[str, str]] = None

@app.get("/api/config/env")
async def read_env():
    env_path = AGENTES_DIR / ".env"
    data = {
        "keys": {},
        "base_urls": {},
        "default_model": "deepseek-chat",
        "default_provider": "deepseek",
        "modelos": obtener_modelos_agentes(),
        "presupuesto_maximo": 10.0,
        "telegram": {"token": "", "chat_id": ""},
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3"}
    }
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            val = v.strip().strip('"').strip("'")
            if k == "DEFAULT_MODEL":
                data["default_model"] = val
            elif k == "DEFAULT_PROVIDER":
                data["default_provider"] = val
            elif k == "PRESUPUESTO_MAXIMO":
                try:
                    data["presupuesto_maximo"] = float(val)
                except ValueError:
                    pass
            elif k == "TELEGRAM_BOT_TOKEN":
                data["telegram"]["token"] = val
            elif k == "TELEGRAM_CHAT_ID":
                data["telegram"]["chat_id"] = val
            elif k == "OLLAMA_BASE_URL":
                data["ollama"]["base_url"] = val
            elif k == "OLLAMA_MODEL":
                data["ollama"]["model"] = val
            elif k.endswith("_BASE_URL"):
                prov = k.replace("_BASE_URL", "").lower()
                data["base_urls"][prov] = val
            elif k.endswith("_API_KEY") or k.endswith("_KEY"):
                provider = k.replace("_API_KEY", "").replace("_KEY", "").lower()
                data["keys"][provider] = val
    return data

@app.post("/api/config/guardar")
async def guardar_config(payload: FullConfigPayload):
    env_path = AGENTES_DIR / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        
    env_dict = {}
    ordered_keys = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        env_dict[k] = v
        if k not in ordered_keys:
            ordered_keys.append(k)

    if payload.keys:
        for prov, val in payload.keys.items():
            if val is not None:
                env_key = f"{prov.upper()}_API_KEY"
                if prov.lower() == "fal":
                    env_key = "FAL_KEY"
                env_dict[env_key] = val
                if env_key not in ordered_keys:
                    ordered_keys.append(env_key)

    if payload.base_urls:
        for prov, url_val in payload.base_urls.items():
            if url_val is not None and url_val.strip():
                url_key = f"{prov.upper()}_BASE_URL"
                env_dict[url_key] = url_val.strip()
                if url_key not in ordered_keys:
                    ordered_keys.append(url_key)

    if payload.default_model:
        env_dict["DEFAULT_MODEL"] = payload.default_model
        if "DEFAULT_MODEL" not in ordered_keys:
            ordered_keys.append("DEFAULT_MODEL")
    if payload.default_provider:
        env_dict["DEFAULT_PROVIDER"] = payload.default_provider
        if "DEFAULT_PROVIDER" not in ordered_keys:
            ordered_keys.append("DEFAULT_PROVIDER")

    if payload.modelos:
        for ag, mod in payload.modelos.items():
            ag_key = f"MODEL_{ag.upper()}"
            env_dict[ag_key] = mod
            if ag_key not in ordered_keys:
                ordered_keys.append(ag_key)

    if payload.presupuesto_maximo is not None:
        pres_val = float(payload.presupuesto_maximo)
        env_dict["PRESUPUESTO_MAXIMO"] = str(pres_val)
        if "PRESUPUESTO_MAXIMO" not in ordered_keys:
            ordered_keys.append("PRESUPUESTO_MAXIMO")
        # Actualizar costos.json y si el presupuesto supera el costo actual, desmarcar bloqueo
        costos_path = AGENTES_DIR / "costos.json"
        if costos_path.exists():
            try:
                c_data = json.loads(costos_path.read_text(encoding="utf-8"))
                c_data["presupuesto_maximo"] = pres_val
                if float(c_data.get("costo", 0.0)) < pres_val:
                    c_data["bloqueado_por_presupuesto"] = False
                costos_path.write_text(json.dumps(c_data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    if payload.telegram:
        if "token" in payload.telegram and payload.telegram["token"] is not None:
            env_dict["TELEGRAM_BOT_TOKEN"] = payload.telegram["token"]
            if "TELEGRAM_BOT_TOKEN" not in ordered_keys:
                ordered_keys.append("TELEGRAM_BOT_TOKEN")
        if "chat_id" in payload.telegram and payload.telegram["chat_id"] is not None:
            env_dict["TELEGRAM_CHAT_ID"] = payload.telegram["chat_id"]
            if "TELEGRAM_CHAT_ID" not in ordered_keys:
                ordered_keys.append("TELEGRAM_CHAT_ID")

    if payload.ollama:
        if "base_url" in payload.ollama and payload.ollama["base_url"] is not None:
            env_dict["OLLAMA_BASE_URL"] = payload.ollama["base_url"]
            if "OLLAMA_BASE_URL" not in ordered_keys:
                ordered_keys.append("OLLAMA_BASE_URL")
        if "model" in payload.ollama and payload.ollama["model"] is not None:
            env_dict["OLLAMA_MODEL"] = payload.ollama["model"]
            if "OLLAMA_MODEL" not in ordered_keys:
                ordered_keys.append("OLLAMA_MODEL")
            if "OLLAMA_BASE_URL" not in ordered_keys:
                ordered_keys.append("OLLAMA_BASE_URL")
        if "model" in payload.ollama and payload.ollama["model"] is not None:
            env_dict["OLLAMA_MODEL"] = payload.ollama["model"]
            if "OLLAMA_MODEL" not in ordered_keys:
                ordered_keys.append("OLLAMA_MODEL")

    new_lines = []
    seen = set()
    for line in lines:
        raw = line.strip()
        if raw.startswith("#") or not raw:
            new_lines.append(line)
            continue
        if "=" in raw:
            k = raw.split("=", 1)[0].strip()
            if k in env_dict:
                v = env_dict[k]
                new_lines.append(f'{k}="{v}"' if (" " in v or any(c in v for c in "!@#$%^&*()")) else f'{k}={v}')
                seen.add(k)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k in ordered_keys:
        if k not in seen and k in env_dict:
            v = env_dict[k]
            new_lines.append(f'{k}="{v}"' if (" " in v or any(c in v for c in "!@#$%^&*()")) else f'{k}={v}')

    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "ok", "message": "Configuración guardada correctamente"}

@app.post("/api/config/test-telegram")
async def test_telegram():
    env_path = AGENTES_DIR / ".env"
    token = ""
    chat_id = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token or not chat_id:
        return {"status": "error", "message": "Falta configurar Token o Chat ID de Telegram"}
    try:
        import urllib.request
        msg = "🏴‍☠️ [AgenticOS] Mensaje de prueba exitoso desde el panel de Configuración."
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": msg}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                return {"status": "ok", "message": "¡Mensaje de prueba recibido en Telegram!"}
    except Exception as e:
        return {"status": "error", "message": f"Error conectando con Telegram: {str(e)}"}
    return {"status": "error", "message": "No se pudo entregar el mensaje a Telegram"}

def obtener_presupuesto_maximo() -> float:
    env_path = AGENTES_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRESUPUESTO_MAXIMO="):
                try:
                    return float(line.split("=", 1)[1].strip().strip('"').strip("'"))
                except Exception:
                    pass
    return 10.0

def enviar_alerta_telegram_presupuesto(gasto: float, limite: float):
    env_path = AGENTES_DIR / ".env"
    token = ""
    chat_id = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token or not chat_id:
        return
    try:
        import urllib.request
        msg = f"🚨 [AgenticOS] PARADA DURA ACTIVADA:\n\nLa tripulación ha alcanzado el límite mensual de presupuesto (${gasto:.2f} / ${limite:.2f} USD).\n\nLos agentes han sido detenidos automáticamente para proteger tu factura. Puedes ampliar el presupuesto o reiniciar el contador desde el panel de control."
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": msg}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception as e:
        print(f"Error enviando alerta Telegram presupuesto: {e}")

def detener_tripulacion_emergencia():
    try:
        subprocess.run(["docker", "compose", "stop"], cwd=str(AGENTES_DIR), capture_output=True, timeout=5)
    except Exception:
        pass
    try:
        current_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            if p.info['pid'] == current_pid:
                continue
            if 'python' in (p.info['name'] or '').lower():
                cmd = " ".join(p.info['cmdline'] or []).lower()
                if any(x in cmd for x in ['base_listener', 'luffy_agent', 'zoro_agent', 'sanji_agent', 'robin_agent', 'nami_agent']):
                    p.terminate()
    except Exception:
        pass

@app.post("/api/config/reset-costos")
async def reset_costos():
    from datetime import datetime
    mes_actual = datetime.now().strftime("%Y-%m")
    costos_path = AGENTES_DIR / "costos.json"
    default_costos = {
        "mes_activo": mes_actual,
        "tokens": 0,
        "costo": 0.0,
        "bloqueado_por_presupuesto": False,
        "presupuesto_maximo": obtener_presupuesto_maximo(),
        "agentes": {
            "luffy": {"tokens": 0, "costo": 0.0},
            "zoro": {"tokens": 0, "costo": 0.0},
            "sanji": {"tokens": 0, "costo": 0.0},
            "robin": {"tokens": 0, "costo": 0.0},
            "nami": {"tokens": 0, "costo": 0.0}
        },
        "historial_meses": {}
    }
    if costos_path.exists():
        try:
            curr = json.loads(costos_path.read_text(encoding="utf-8"))
            if isinstance(curr, dict) and "historial_meses" in curr:
                default_costos["historial_meses"] = curr["historial_meses"]
        except Exception:
            pass
    costos_path.write_text(json.dumps(default_costos, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "message": f"Contador de costos del mes {mes_actual} restablecido a $0.00"}

@app.post("/api/config/env")
async def update_env(config: EnvConfig):
    env_path = AGENTES_DIR / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    key_name = f"{config.provider.upper()}_API_KEY"
    new_lines = []
    key_found = False
    model_found = False
    provider_found = False
    for line in lines:
        if line.startswith(f"{key_name}="):
            new_lines.append(f"{key_name}={config.api_key}")
            key_found = True
        elif line.startswith("DEFAULT_MODEL="):
            new_lines.append(f"DEFAULT_MODEL={config.model}")
            model_found = True
        elif line.startswith("DEFAULT_PROVIDER="):
            new_lines.append(f"DEFAULT_PROVIDER={config.provider}")
            provider_found = True
        else:
            new_lines.append(line)
    if not key_found: new_lines.append(f"{key_name}={config.api_key}")
    if not model_found: new_lines.append(f"DEFAULT_MODEL={config.model}")
    if not provider_found: new_lines.append(f"DEFAULT_PROVIDER={config.provider}")
    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "success", "message": "Entorno actualizado"}

@app.delete("/api/config/env/{provider}")
async def delete_env_key(provider: str):
    env_path = AGENTES_DIR / ".env"
    if not env_path.exists():
        return {"status": "error", "message": "Archivo de entorno no encontrado"}
    lines = env_path.read_text(encoding="utf-8").splitlines()
    p_up = provider.upper()
    key_name = f"{p_up}_API_KEY"
    url_name = f"{p_up}_BASE_URL"
    new_lines = [line for line in lines if not line.startswith(f"{key_name}=") and not line.startswith(f"{url_name}=")]
    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "success", "message": f"Proveedor {p_up} eliminado"}

@app.post("/api/system/restart")
async def restart_system():
    try:
        bat_path = AGENTES_DIR / "reiniciar_tripulacion.bat"
        if bat_path.exists():
            subprocess.Popen([str(bat_path)], shell=True, cwd=str(AGENTES_DIR))
        else:
            subprocess.Popen("docker compose down && docker compose up -d", shell=True, cwd=str(AGENTES_DIR))
        return {"status": "success", "message": "Ejecutando script de reinicio de contenedor Docker..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------- MONITOREO DE FLOTA REMOTA -----------------
FLOTA_REMOTA_DB = {}

class ReporteTelemetria(BaseModel):
    id: str
    nombre: str
    tipo: Optional[str] = "Nodo Remoto"
    ip: Optional[str] = "Remoto"
    version: Optional[str] = "v1.0"
    estado: Optional[str] = "activa" # activa | espera | error | desconectada
    agentes: Optional[dict] = None
    tarea_actual: Optional[str] = "En ejecución..."
    error_critico: Optional[str] = None
    tokens: Optional[int] = 0
    costo: Optional[float] = 0.0
    cpu: Optional[float] = 0.0
    ram: Optional[float] = 0.0

@app.post("/api/telemetria/reportar")
async def reportar_telemetria(data: ReporteTelemetria):
    ahora_ts = time.time()
    eq_dict = data.dict()
    eq_dict["ultimo_ping"] = ahora_ts
    FLOTA_REMOTA_DB[data.id] = eq_dict
    
    equipos_path = AGENTES_DIR / "equipos_remotos.json"
    try:
        equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return {"status": "ok", "message": f"Telemetría de {data.nombre} recibida"}

@app.post("/api/telemetria/simular")
async def simular_telemetria():
    ahora_ts = time.time()
    mock_nodes = [
        {
            "id": "cliente-alpha",
            "nombre": "Equipo Alpha • Cliente Retail",
            "tipo": "Servidor Cloud (AWS EC2)",
            "ip": "54.210.88.14",
            "version": "v1.2",
            "estado": "activa",
            "ultimo_ping": ahora_ts,
            "agentes": {
                "luffy": "activo", "zoro": "activo", "sanji": "espera", "robin": "espera", "nami": "activo"
            },
            "tarea_actual": "Sincronización automatizada de inventario y catálogo",
            "error_critico": None,
            "tokens": 142500,
            "costo": 0.285,
            "cpu": 18.4,
            "ram": 42.1
        },
        {
            "id": "cliente-beta",
            "nombre": "Equipo Beta • Finanzas y Auditoría",
            "tipo": "Servidor On-Premise",
            "ip": "192.168.10.45",
            "version": "v1.1",
            "estado": "error",
            "ultimo_ping": ahora_ts,
            "agentes": {
                "luffy": "activo", "zoro": "error", "sanji": "espera", "robin": "activo", "nami": "espera"
            },
            "tarea_actual": "Auditoría de balances fiscales trimestrales",
            "error_critico": "Error 429: OpenAI Rate Limit Exceeded en agente Zoro. Cuota diaria agotada.",
            "tokens": 389200,
            "costo": 0.778,
            "cpu": 64.2,
            "ram": 71.5
        }
    ]
    for m in mock_nodes:
        FLOTA_REMOTA_DB[m["id"]] = m
    
    equipos_path = AGENTES_DIR / "equipos_remotos.json"
    try:
        equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return {"status": "ok", "message": "Equipos de prueba simulados añadidos a la flota"}

@app.delete("/api/telemetria/eliminar/{equipo_id}")
async def eliminar_equipo_remoto(equipo_id: str):
    if equipo_id in FLOTA_REMOTA_DB:
        del FLOTA_REMOTA_DB[equipo_id]
        equipos_path = AGENTES_DIR / "equipos_remotos.json"
        try:
            equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return {"status": "ok", "message": f"Equipo {equipo_id} retirado"}

def obtener_estado_flota(local_activo, local_estado, local_pizarra, local_metrics, local_costos, local_logs):
    ahora_ts = time.time()
    
    # 1. Instancia local HQ
    error_local = None
    if local_logs:
        for l in reversed(local_logs[-10:]):
            texto = (l.get("mensaje") or "").lower()
            if any(k in texto for k in ["error crítico", "traceback", "exception:", "error code: 402", "error code: 429", "crash"]):
                error_local = l.get("mensaje")
                break

    ultimo_log_str = "Tripulación en reposo y a la espera de instrucciones"
    if local_logs:
        last_item = local_logs[-1]
        origen_tag = f"[{last_item.get('origen', 'LOG').upper()}] " if last_item.get("origen") else ""
        ultimo_log_str = origen_tag + (last_item.get("texto") or last_item.get("mensaje") or "")

    local_instance = {
        "id": "local-hq",
        "nombre": "Tripulación IA",
        "tipo": "",
        "ip": "",
        "version": "",
        "plugin_info": "Plugin: En vivo" if local_activo else "Plugin: Apagado",
        "estado": "activa" if local_activo else "desconectada",
        "ultimo_ping": ahora_ts,
        "ultimo_ping_relativo": "Plugin: En vivo" if local_activo else "Plugin: Apagado",
        "agentes": local_estado.get("agentes", {}),
        "tarea_actual": ultimo_log_str,
        "ultimo_log": ultimo_log_str,
        "logs": local_logs[-25:] if local_logs else [],
        "error_critico": error_local,
        "tokens": local_costos.get("tokens", 0),
        "costo": local_costos.get("costo", 0.0),
        "cpu": local_metrics.get("cpu", 0),
        "ram": local_metrics.get("ram", {}).get("percent", 0)
    }

    # Cargar equipos remotos persistidos
    equipos_path = AGENTES_DIR / "equipos_remotos.json"
    if equipos_path.exists():
        try:
            equipos_guardados = json.loads(equipos_path.read_text(encoding="utf-8"))
            if isinstance(equipos_guardados, list):
                for eq in equipos_guardados:
                    if isinstance(eq, dict) and eq.get("id") and eq.get("id") != "local-hq":
                        if eq["id"] not in FLOTA_REMOTA_DB:
                            FLOTA_REMOTA_DB[eq["id"]] = eq
        except Exception:
            pass

    flota = [local_instance]
    for eq_id, eq in FLOTA_REMOTA_DB.items():
        if eq_id == "local-hq":
            continue
        last_seen = eq.get("ultimo_ping", 0)
        seg_diff = int(ahora_ts - last_seen) if last_seen else 9999
        if seg_diff < 10:
            rel = "Hace unos segundos"
        elif seg_diff < 60:
            rel = f"Hace {seg_diff}s"
        elif seg_diff < 3600:
            rel = f"Hace {seg_diff // 60}m"
        else:
            rel = f"Hace {seg_diff // 3600}h"

        eq_copy = dict(eq)
        eq_copy["ultimo_ping_relativo"] = rel
        if seg_diff > 60 and eq_copy.get("estado") != "error":
            eq_copy["estado"] = "desconectada"
        flota.append(eq_copy)

    return flota

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = BASE_DIR / "static" / "index.html"
    return index_file.read_text(encoding="utf-8")

# Utilidad para leer archivos de forma segura
def leer_archivo_json(ruta: Path):
    if ruta.exists():
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return []

def leer_archivo_texto(ruta: Path):
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    return ""

def check_docker_tripulacion():
    try:
        res = subprocess.run(["docker", "ps", "--filter", "status=running", "--format", "{{.Names}}"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            return True
    except Exception:
        pass
    return False

def check_procesos_tripulacion():
    try:
        current_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            if p.info['pid'] == current_pid:
                continue
            if 'python' in (p.info['name'] or '').lower():
                cmd = " ".join(p.info['cmdline'] or []).lower()
                if any(x in cmd for x in ['base_listener', 'luffy_agent', 'zoro_agent', 'sanji_agent', 'robin_agent', 'nami_agent']):
                    return True
    except Exception:
        pass
    return False

def calcular_estados_agentes(is_activo: bool, pizarra: list, logs_dir: Path) -> dict:
    agentes = ["luffy", "zoro", "sanji", "robin", "nami"]
    
    if not is_activo:
        return {ag: "off" for ag in agentes}
        
    estados = {}
    
    # 1. Identificar si hay agentes con tareas en progreso en la pizarra
    agentes_con_tarea = set()
    if isinstance(pizarra, list):
        for t in pizarra:
            if isinstance(t, dict):
                est = str(t.get("estado", "")).strip().upper()
                resp = str(t.get("responsable", "")).strip().lower()
                if est in ["EN_PROCESO", "EJECUTANDO", "TRABAJANDO", "PROCESANDO", "EN PROCESO", "NUEVO"]:
                    for ag in agentes:
                        if ag in resp:
                            agentes_con_tarea.add(ag)
                            
    # 2. Identificar procesos de python corriendo específicamente por agente
    procesos_por_agente = set()
    try:
        current_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            if p.info['pid'] == current_pid:
                continue
            if 'python' in (p.info['name'] or '').lower():
                cmd = " ".join(p.info['cmdline'] or []).lower()
                for ag in agentes:
                    if f"{ag}_agent" in cmd or (ag in cmd and "base_listener" in cmd):
                        procesos_por_agente.add(ag)
    except Exception:
        pass

    ahora = time.time()
    for ag in agentes:
        # A. Si el proceso de este agente está corriendo
        if ag in procesos_por_agente:
            estados[ag] = "activo"
            continue
            
        # B. Si tiene una tarea en proceso en la pizarra
        if ag in agentes_con_tarea:
            estados[ag] = "activo"
            continue
            
        # C. Analizar archivo de log del agente
        log_file = logs_dir / f"{ag.capitalize()}.log"
        if not log_file.exists():
            log_file = logs_dir / f"{ag}.log"
            
        if log_file.exists() and log_file.stat().st_size > 0:
            mtime = log_file.stat().st_mtime
            delta_seg = ahora - mtime
            
            # Si el log se modificó en los últimos 45 segundos
            if delta_seg <= 45:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        ultimas_lineas = [l.strip() for l in f.readlines() if l.strip()][-8:]
                    texto_reciente = " ".join(ultimas_lineas).lower()
                    
                    if any(err in texto_reciente for err in ["error crítico", "traceback", "exception:", "error code: 402", "error code: 429", "crash"]):
                        estados[ag] = "error"
                    else:
                        estados[ag] = "activo"
                    continue
                except Exception:
                    pass
                
        # D. Si la tripulación está activa pero el agente no tiene tarea activa ni log reciente
        estados[ag] = "espera"
        
    return estados

def obtener_metricas_costos() -> dict:
    from datetime import datetime
    mes_actual = datetime.now().strftime("%Y-%m")
    costos_path = AGENTES_DIR / "costos.json"
    default_costos = {
        "mes_activo": mes_actual,
        "tokens": 0,
        "costo": 0.0,
        "bloqueado_por_presupuesto": False,
        "presupuesto_maximo": obtener_presupuesto_maximo(),
        "agentes": {
            "luffy": {"tokens": 0, "costo": 0.0},
            "zoro": {"tokens": 0, "costo": 0.0},
            "sanji": {"tokens": 0, "costo": 0.0},
            "robin": {"tokens": 0, "costo": 0.0},
            "nami": {"tokens": 0, "costo": 0.0}
        },
        "historial_meses": {}
    }
    
    data = default_costos
    if costos_path.exists():
        try:
            raw = json.loads(costos_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except Exception:
            data = default_costos

    # 1. Asegurar campos base
    data.setdefault("tokens", 0)
    data.setdefault("costo", 0.0)
    data.setdefault("bloqueado_por_presupuesto", False)
    if "agentes" not in data or not isinstance(data["agentes"], dict):
        data["agentes"] = default_costos["agentes"]
    else:
        for ag in ["luffy", "zoro", "sanji", "robin", "nami"]:
            if ag not in data["agentes"]:
                data["agentes"][ag] = {"tokens": 0, "costo": 0.0}

    # 2. Verificar cambio de mes en el calendario (Rollover automático mensual)
    mes_registrado = data.get("mes_activo")
    if not mes_registrado:
        data["mes_activo"] = mes_actual
        mes_registrado = mes_actual

    necesita_guardar = False
    if mes_registrado != mes_actual:
        if "historial_meses" not in data or not isinstance(data["historial_meses"], dict):
            data["historial_meses"] = {}
        data["historial_meses"][mes_registrado] = {
            "costo": data.get("costo", 0.0),
            "tokens": data.get("tokens", 0)
        }
        data["mes_activo"] = mes_actual
        data["costo"] = 0.0
        data["tokens"] = 0
        data["bloqueado_por_presupuesto"] = False
        for ag in ["luffy", "zoro", "sanji", "robin", "nami"]:
            data["agentes"][ag] = {"tokens": 0, "costo": 0.0}
        necesita_guardar = True

    # 3. Límite de presupuesto mensual y Parada Dura
    presupuesto_max = obtener_presupuesto_maximo()
    if data.get("presupuesto_maximo") != presupuesto_max:
        data["presupuesto_maximo"] = presupuesto_max
        necesita_guardar = True
    costo_actual = float(data.get("costo", 0.0))

    if presupuesto_max > 0 and costo_actual >= presupuesto_max:
        if not data.get("bloqueado_por_presupuesto", False):
            data["bloqueado_por_presupuesto"] = True
            necesita_guardar = True
            detener_tripulacion_emergencia()
            enviar_alerta_telegram_presupuesto(costo_actual, presupuesto_max)
    else:
        if data.get("bloqueado_por_presupuesto", False):
            data["bloqueado_por_presupuesto"] = False
            necesita_guardar = True

    if necesita_guardar:
        try:
            costos_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return data

def obtener_ultimos_logs(max_lineas=40):
    lineas_combinadas = []
    
    # 1. Leer de archivos *.log en logs/
    logs_dir = AGENTES_DIR / "logs"
    if logs_dir.exists():
        for log_file in sorted(logs_dir.glob("*.log")):
            if log_file.is_file() and log_file.stat().st_size > 0:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                        for line in lines[-max_lineas:]:
                            origen = log_file.stem
                            texto = line
                            if line.startswith("[") and "]" in line:
                                origen = line[1:line.index("]")].strip()
                                texto = line[line.index("]")+1:].strip()
                            lineas_combinadas.append({"origen": origen, "texto": texto})
                except Exception:
                    pass

    # 2. Si no hay logs en disco, consultar logs del contenedor Docker (activo o recién detenido)
    if not lineas_combinadas:
        try:
            res = subprocess.run(
                ["docker", "logs", "--tail", str(max_lineas), "tripulacion_ia_v3"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1.5
            )
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line:
                        origen = "Tripulación"
                        texto = line
                        if line.startswith("[") and "]" in line:
                            origen = line[1:line.index("]")].strip()
                            texto = line[line.index("]")+1:].strip()
                        lineas_combinadas.append({"origen": origen, "texto": texto})
        except Exception:
            pass

    return lineas_combinadas[-max_lineas:]

async def obtener_metricas_sistema():
    cpu_usage = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ram_usage = mem.percent
    ram_used_gb = mem.used / (1024**3)
    ram_total_gb = mem.total / (1024**3)
    
    net = psutil.net_io_counters()
    
    gpu_info = []
    if GPUtil:
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            gpu_info.append({
                "name": gpu.name,
                "load": round(gpu.load * 100, 1),
                "temp": gpu.temperature,
                "memory_used": gpu.memoryUsed,
                "memory_total": gpu.memoryTotal
            })
            
    return {
        "cpu": cpu_usage,
        "ram": {
            "percent": ram_usage,
            "used_gb": round(ram_used_gb, 1),
            "total_gb": round(ram_total_gb, 1)
        },
        "gpu": gpu_info,
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv
        },
        "specs": {
            "system": platform.system(),
            "processor": platform.processor()
        }
    }



def limpiar_formato_md(txt: str) -> str:
    if not txt:
        return ""
    import re
    # Convertir wikilinks Obsidian [[algo|alias]] o [[algo]]
    txt = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', txt)
    # Convertir links standard markdown [texto](url)
    txt = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', txt)
    # Quitar negritas y cursivas
    txt = re.sub(r'\*\*(.*?)\*\*', r'\1', txt)
    txt = re.sub(r'\*(.*?)\*', r'\1', txt)
    # Quitar backticks
    txt = txt.replace('`', '')
    # Quitar listas o viñetas iniciales y guiones
    txt = re.sub(r'^\s*[-*•]\s*', '', txt)
    # Quitar espacios múltiples
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()

def extraer_id_y_titulo(titulo_raw: str):
    import re
    t_clean = limpiar_formato_md(titulo_raw)
    m = re.match(r'^(TKT-[A-Z0-9\-]+)[:\s\-]+(.*)$', t_clean, re.IGNORECASE)
    if m:
        return m.group(1).upper().strip(), m.group(2).strip()
    return None, t_clean

def parse_bitacora(ruta):
    if not ruta.exists(): return []
    content = ruta.read_text(encoding="utf-8")
    import re
    blocks = re.split(r'\n##\s+', '\n' + content)
    tareas = []
    for block in blocks[1:]:
        lines = block.split('\n')
        t_id, titulo = extraer_id_y_titulo(lines[0])
        responsable = "Luffy"
        estado = "Pendiente"
        desc = ""
        tarea_especifica = ""
        criterios = ""
        
        for line in lines[1:]:
            l_str = line.strip()
            if not l_str:
                continue
            if re.search(r'\*{0,2}Responsable:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Responsable:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                responsable = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Estado:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Estado:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                estado = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                desc = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Tarea:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Tarea:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                tarea_especifica = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                criterios = limpiar_formato_md(val)
        
        tareas.append({
            "id": t_id,
            "titulo": titulo,
            "descripcion": desc or tarea_especifica or "Tarea en progreso...",
            "tarea": tarea_especifica,
            "criterios": criterios,
            "responsable": responsable,
            "estado": estado
        })
    return tareas

def parse_tickets_md(ruta):
    if not ruta.exists(): return []
    content = ruta.read_text(encoding="utf-8")
    tickets = []
    import re
    blocks = re.split(r'\n##\s+', '\n' + content)
    for block in blocks[1:]:
        lines = block.split('\n')
        t_id, titulo = extraer_id_y_titulo(lines[0])
        responsable = "Luffy"
        estado = "Completado"
        desc = ""
        tarea_especifica = ""
        criterios = ""
        
        for line in lines[1:]:
            l_str = line.strip()
            if not l_str:
                continue
            if re.search(r'\*{0,2}Responsable:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Responsable:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                responsable = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Estado:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Estado:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                estado = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                desc = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Tarea:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Tarea:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                tarea_especifica = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                criterios = limpiar_formato_md(val)
        
        # Ignorar encabezados que no sean tickets (ej: enlaces a memoria u Obsidian)
        if not t_id and not desc and not tarea_especifica:
            continue

        tickets.append({
            "id": t_id,
            "titulo": titulo,
            "descripcion": desc or tarea_especifica or "Ticket archivado en memoria.",
            "tarea": tarea_especifica,
            "criterios": criterios,
            "responsable": responsable,
            "estado": estado or "Completado"
        })
    return tickets

TIEMPO_INICIO_CREW = None
tiempo_acumulado_trabajo = 0.0
ultimo_check_activo = time.time()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Guardar valores anteriores de red para calcular velocidad
        last_net = psutil.net_io_counters()
        
        while True:
            # 1. Hardware metrics
            metrics = await obtener_metricas_sistema()
            
            # Calcular velocidad de red rudimentaria (diferencia por segundo)
            current_net = psutil.net_io_counters()
            metrics["network"]["up_speed"] = current_net.bytes_sent - last_net.bytes_sent
            metrics["network"]["down_speed"] = current_net.bytes_recv - last_net.bytes_recv
            last_net = current_net
            
            
                        # 2. Pizarra de agentes (JSON array of tasks)
            pizarra_path = AGENTES_DIR / "Bitacora.md"
            pizarra = parse_bitacora(pizarra_path)
            
            # Tickets archivados
            tickets_path_md = AGENTES_DIR / "memoria" / "Tickets_Archivados.md"
            tickets_archivados = parse_tickets_md(tickets_path_md)
            
            # Tareas programadas
            programadas_path = Path(__file__).resolve().parent / "tareas_programadas.json"
            tareas_programadas = leer_archivo_json(programadas_path) if programadas_path.exists() else {"diarias":[], "semanales":[], "mensuales":[]}
            
            # 3. Chat de usuario
            canal_path = AGENTES_DIR / "canal_usuario.json"
            chat_raw = leer_archivo_json(canal_path)
            if isinstance(chat_raw, dict):
                chat = chat_raw.get("mensajes", [])
            elif isinstance(chat_raw, list):
                chat = chat_raw
            else:
                chat = []
            
            # 4. Logs en vivo de la tripulacion
            logs = obtener_ultimos_logs()
            
            # 5. Costos/Tokens
            costos = obtener_metricas_costos()
            
            # 6. Estado de la tripulacion
            estado_path = LUFFY_DIR / "estado_tripulacion.json"
            estado_tripulacion = leer_archivo_json(estado_path) if estado_path.exists() else {"estado": "desconectada"}
            if not isinstance(estado_tripulacion, dict):
                estado_tripulacion = {"estado": "desconectada"}
            
            # Detectar si docker o los agentes estan activos
            docker_activo = check_docker_tripulacion()
            procesos_activos = check_procesos_tripulacion()
            is_activo = docker_activo or procesos_activos or (estado_tripulacion.get("estado") in ["activa", "activo", "conectada"])
            if costos.get("bloqueado_por_presupuesto"):
                is_activo = False
                estado_tripulacion["estado"] = "bloqueada_presupuesto"
            elif is_activo:
                estado_tripulacion["estado"] = "activa"
            else:
                estado_tripulacion["estado"] = "desconectada"
                
            estado_tripulacion["agentes"] = calcular_estados_agentes(is_activo, pizarra, AGENTES_DIR / "logs")
            
            # Rastrear tiempo de trabajo activo de los agentes
            global TIEMPO_INICIO_CREW, tiempo_acumulado_trabajo, ultimo_check_activo
            ahora_ts = time.time()
            dt = ahora_ts - ultimo_check_activo
            ultimo_check_activo = ahora_ts
            if dt < 0 or dt > 10:
                dt = 1.0

            if is_activo:
                if TIEMPO_INICIO_CREW is None:
                    TIEMPO_INICIO_CREW = ahora_ts
                tiempo_acumulado_trabajo += dt
            else:
                TIEMPO_INICIO_CREW = None

            horas_totales = int(tiempo_acumulado_trabajo // 3600)
            minutos_totales = int((tiempo_acumulado_trabajo % 3600) // 60)
            
            sesion_seg = int(ahora_ts - TIEMPO_INICIO_CREW) if TIEMPO_INICIO_CREW else 0
            sesion_min = int(sesion_seg // 60)
            
            tiempo_trabajo = {
                "segundos": int(tiempo_acumulado_trabajo),
                "formateado": f"{horas_totales}h {minutos_totales:02d}m",
                "sesion_minutos": sesion_min,
                "is_activo": is_activo
            }
            
            data = {
                "type": "update",
                "system": metrics,
                "pizarra": pizarra,
                "tickets_archivados": tickets_archivados,
                "tareas_programadas": tareas_programadas,
                "chat": chat,
                "logs": logs,
                "costos": costos,
                "estado_tripulacion": estado_tripulacion,
                "tripulacion_activa": is_activo,
                "modelos": obtener_modelos_agentes(),
                "tiempo_trabajo": tiempo_trabajo,
                "flota_remota": obtener_estado_flota(is_activo, estado_tripulacion, pizarra, metrics, costos, logs)
            }
            
            await websocket.send_json(data)
            await asyncio.sleep(1) # Actualizar cada 1 segundo
            
    except WebSocketDisconnect:
        print("Cliente desconectado")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
