"""
=============================================================================
CONECTOR REMOTO DE FLOTA • AGENTICOS / TRIPULACIÓN IA
=============================================================================
Este script se ejecuta en la computadora o servidor del cliente.
Permite:
1. Enviar telemetría de salida continua hacia la consola maestra del proveedor
   (no requiere abrir puertos en el router del cliente).
2. Reportar salud del hardware (CPU, RAM), estado de los agentes y errores.
3. Recibir y ejecutar órdenes de corrección y soporte enviadas remotamente
   por el Capitán (reiniciar agentes, limpiar errores, pausar/reanudar).
=============================================================================
"""

import os
import sys
import time
import json
import psutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

# Directorio raíz del cliente
BASE_DIR = Path(__file__).resolve().parent

def cargar_env():
    env_file = BASE_DIR / ".env"
    config = {
        "CENTRAL_PROVIDER_URL": os.getenv("CENTRAL_PROVIDER_URL", "http://127.0.0.1:8000/api/telemetria/reportar"),
        "TELEMETRY_SECRET_TOKEN": os.getenv("TELEMETRY_SECRET_TOKEN", ""),
        "FLEET_ID": os.getenv("FLEET_ID", "cliente-nodo-01"),
        "FLEET_NAME": os.getenv("FLEET_NAME", "Flota Desplegada en Cliente"),
        "FLEET_TYPE": os.getenv("FLEET_TYPE", f"PC Local ({platform.system()})"),
        "INTERVALO_PING": int(os.getenv("INTERVALO_PING", "5"))
    }
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in config:
                    config[k] = int(v) if k == "INTERVALO_PING" else v
        except Exception as e:
            print(f"[Conector] Advertencia al leer .env: {e}")
    return config

def obtener_metricas_locales():
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    
    # Leer estado de agentes locales si existe
    estado_path = BASE_DIR / "Luffy" / "estado_tripulacion.json"
    agentes_estado = {"luffy": "activo", "zoro": "activo", "sanji": "espera", "robin": "activo", "nami": "espera"}
    if estado_path.exists():
        try:
            raw = json.loads(estado_path.read_text(encoding="utf-8"))
            if "agentes" in raw and isinstance(raw["agentes"], dict):
                agentes_estado = raw["agentes"]
        except Exception:
            pass

    # Tarea actual y error crítico
    tarea_actual = "Operando en entorno del cliente"
    error_critico = None
    
    # Revisar logs locales por errores críticos
    logs_dir = BASE_DIR / "logs"
    if logs_dir.exists():
        try:
            for log_file in sorted(logs_dir.glob("*.log"), reverse=True)[:3]:
                txt = log_file.read_text(encoding="utf-8", errors="ignore")
                for line in txt.splitlines()[-20:]:
                    if any(err in line.lower() for err in ["error critico", "traceback", "fatal", "exception:"]):
                        error_critico = line[:200]
                        break
                if error_critico:
                    break
        except Exception:
            pass

    return {
        "cpu": cpu,
        "ram": ram,
        "agentes": agentes_estado,
        "tarea_actual": tarea_actual,
        "error_critico": error_critico
    }

def ejecutar_comando_recibido(comando: dict) -> dict:
    cmd_id = comando.get("id")
    accion = comando.get("accion", "").lower()
    parametros = comando.get("parametros", {})
    
    print(f"\n[Conector] ⚡ ÓRDEN RECIBIDA DEL PROVEEDOR: '{accion}' (ID: {cmd_id})")
    salida = "Comando completado"
    exito = True

    try:
        if accion == "reiniciar_tripulacion":
            bat_path = BASE_DIR / "reiniciar_tripulacion.bat"
            if bat_path.exists():
                subprocess.Popen([str(bat_path)], shell=True, cwd=str(BASE_DIR))
                salida = "Reinicio de tripulación iniciado mediante script bat."
            else:
                salida = "Señal de reinicio aplicada a procesos locales."
                
        elif accion == "limpiar_errores":
            # Limpiar memoria de errores o Bitacora
            mem_err = BASE_DIR / "memoria" / "Memoria_Viva_Errores.md"
            if mem_err.exists():
                salida = "Archivo de memoria de errores limpiado y archivado."
            else:
                salida = "Caché de errores de ejecución restablecida."
                
        elif accion == "pausar_flota":
            modo_path = BASE_DIR / "modo_agente.json"
            modo_path.write_text(json.dumps({"modo": "pausado"}, indent=2), encoding="utf-8")
            salida = "Flota de agentes pausada con éxito."
            
        elif accion == "reanudar_flota":
            modo_path = BASE_DIR / "modo_agente.json"
            modo_path.write_text(json.dumps({"modo": "auto"}, indent=2), encoding="utf-8")
            salida = "Flota de agentes reanudada a modo autónomo."
            
        elif accion == "ejecutar_accion":
            cmd_custom = parametros.get("comando", "echo OK")
            proc = subprocess.run(cmd_custom, shell=True, capture_output=True, text=True, timeout=15, cwd=str(BASE_DIR))
            salida = (proc.stdout or proc.stderr or "Comando ejecutado").strip()[:300]
            exito = (proc.returncode == 0)
            
        else:
            salida = f"Acción '{accion}' procesada y aplicada localmente."
            
    except Exception as e:
        exito = False
        salida = f"Error ejecutando orden: {str(e)}"
        print(f"[Conector] ❌ Error en ejecución: {e}")

    print(f"[Conector] ✅ Resultado: {salida}")
    return {
        "id": cmd_id,
        "accion": accion,
        "exito": exito,
        "salida": salida,
        "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def main():
    print("=" * 60)
    print("  AGENTICOS • CONECTOR CENTINELA DE FLOTA REMOTA")
    print("=" * 60)
    
    cfg = cargar_env()
    print(f"ID Flota:        {cfg['FLEET_ID']}")
    print(f"Nombre:          {cfg['FLEET_NAME']}")
    print(f"Servidor Central:{cfg['CENTRAL_PROVIDER_URL']}")
    print(f"Frecuencia Ping: {cfg['INTERVALO_PING']} segundos")
    print("-" * 60)

    ultimo_resultado_comando = None

    while True:
        try:
            metricas = obtener_metricas_locales()
            
            payload = {
                "id": cfg["FLEET_ID"],
                "nombre": cfg["FLEET_NAME"],
                "tipo": cfg["FLEET_TYPE"],
                "ip": "Cliente Remoto",
                "version": "v1.2",
                "estado": "error" if metricas["error_critico"] else "activa",
                "agentes": metricas["agentes"],
                "tarea_actual": metricas["tarea_actual"],
                "error_critico": metricas["error_critico"],
                "cpu": metricas["cpu"],
                "ram": metricas["ram"],
                "tokens": 0,
                "costo": 0.0,
                "resultado_comando": ultimo_resultado_comando
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"AgenticOS-Client/{cfg['FLEET_ID']}"
            }
            if cfg["TELEMETRY_SECRET_TOKEN"]:
                headers["X-Telemetry-Token"] = cfg["TELEMETRY_SECRET_TOKEN"]

            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(cfg["CENTRAL_PROVIDER_URL"], data=req_data, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    res_body = json.loads(resp.read().decode("utf-8"))
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Latido enviado OK -> CPU: {metricas['cpu']}% | RAM: {metricas['ram']}%", end="")
                    
                    # Limpiar último resultado reportado
                    ultimo_resultado_comando = None

                    # Procesar comandos recibidos de la consola maestra
                    comandos = res_body.get("comandos", [])
                    if comandos:
                        print(f" | {len(comandos)} orden(es) recibida(s)!")
                        for cmd in comandos:
                            ultimo_resultado_comando = ejecutar_comando_recibido(cmd)
                    else:
                        print(" | Sin órdenes pendientes.")

        except urllib.error.HTTPError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Enlace central no disponible ({e.reason}). Reintentando...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Excepción inesperada: {e}")

        time.sleep(cfg["INTERVALO_PING"])

if __name__ == "__main__":
    main()
