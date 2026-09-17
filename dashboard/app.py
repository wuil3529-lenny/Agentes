import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import psutil
import platform

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

@app.get("/api/config/env")
async def read_env():
    env_path = AGENTES_DIR / ".env"
    data = {"keys": {}, "default_model": ""}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k == "DEFAULT_MODEL":
                    data["default_model"] = v.strip()
                elif k.endswith("_API_KEY"):
                    provider = k.replace("_API_KEY", "").lower()
                    data["keys"][provider] = v.strip()
    return data

@app.post("/api/config/env")
async def update_env(config: EnvConfig):
    env_path = AGENTES_DIR / ".env"
    # Leer lineas existentes
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    
    # Actualizar o agregar variables (ejemplo simple)
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
    key_name = f"{provider.upper()}_API_KEY"
    
    new_lines = [line for line in lines if not line.startswith(f"{key_name}=")]
    
    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "success", "message": f"Llave de {provider.upper()} eliminada"}

@app.post("/api/system/restart")
async def restart_system():
    try:
        # Ejemplo de reinicio de contenedor asumiendo nombre 'tripulacion_ia'
        # Se enva de fondo para que no bloquee la respuesta a la peticion web
        subprocess.Popen(["docker", "restart", "tripulacion_ia_v3"])
        return {"status": "success", "message": "Reiniciando contenedor..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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



def parse_bitacora(ruta):
    if not ruta.exists(): return []
    content = ruta.read_text(encoding="utf-8")
    import re
    blocks = re.split(r'\n##\s+', '\n' + content)
    tareas = []
    for block in blocks[1:]:
        lines = block.split('\n')
        titulo = lines[0].strip()
        responsable = "Luffy"
        estado = "Pendiente"
        desc = ""
        for line in lines[1:]:
            if "**Responsable:**" in line:
                responsable = line.split("**Responsable:**")[1].strip()
            elif "**Estado:**" in line:
                estado = line.split("**Estado:**")[1].strip()
            elif "**Descripci" in line or "**Tarea:**" in line:
                desc = line.split(":", 1)[1].strip() if ":" in line else line.replace("- **Descripción:**", "").strip()
        if not desc: desc = "Tarea en progreso..."
        tareas.append({"titulo": titulo, "tarea": desc, "responsable": responsable, "estado": estado})
    return tareas

def parse_tickets_md(ruta):
    if not ruta.exists(): return []
    content = ruta.read_text(encoding="utf-8")
    tickets = []
    import re
    blocks = re.split(r'\n##\s+', '\n' + content)
    for block in blocks[1:]:
        lines = block.split('\n')
        titulo = lines[0].strip()
        responsable = "Luffy"
        estado = "Completado"
        tarea = ""
        for line in lines[1:]:
            if "**Responsable:**" in line:
                responsable = line.split("**Responsable:**")[1].strip()
            elif "**Estado:**" in line:
                estado = line.split("**Estado:**")[1].strip()
            elif "**Descripci" in line or "**Tarea:**" in line:
                tarea = line.split(":", 1)[1].strip() if ":" in line else line
        if not tarea: tarea = "Ticket archivado en memoria."
        tickets.append({"titulo": titulo, "tarea": tarea, "responsable": responsable, "estado": estado})
    return tickets

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
            costos_path = AGENTES_DIR / "costos.json"
            costos = leer_archivo_json(costos_path) if costos_path.exists() else {"tokens": 0, "costo": 0.0}
            
            # 6. Estado de la tripulacion
            estado_path = LUFFY_DIR / "estado_tripulacion.json"
            estado_tripulacion = leer_archivo_json(estado_path) if estado_path.exists() else {"estado": "desconectada"}
            
            # Detectar si docker o los agentes estan activos
            docker_activo = check_docker_tripulacion()
            is_activo = docker_activo or (isinstance(estado_tripulacion, dict) and estado_tripulacion.get("estado") in ["activa", "activo", "conectada"])
            if is_activo:
                if isinstance(estado_tripulacion, dict):
                    estado_tripulacion["estado"] = "activa"
            else:
                if isinstance(estado_tripulacion, dict):
                    estado_tripulacion["estado"] = "desconectada"
            
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
                "tripulacion_activa": is_activo
            }
            
            await websocket.send_json(data)
            await asyncio.sleep(1) # Actualizar cada 1 segundo
            
    except WebSocketDisconnect:
        print("Cliente desconectado")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
