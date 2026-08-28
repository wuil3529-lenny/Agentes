"""
skill_ngrok.py — Habilidad: Túneles Ngrok
===========================================
Herramientas para que Zoro pueda establecer y monitorear túneles Ngrok
de forma automática dentro del contenedor Docker.

Capacidades:
  - Iniciar un túnel Ngrok en un puerto específico
  - Obtener la URL pública del túnel activo
"""
import os
import time
import json
import subprocess
import requests
from pathlib import Path
from langchain_core.tools import tool

# API local de Ngrok para consultar el estado del túnel
NGROK_API_URL = "http://localhost:4040/api/tunnels"

@tool
def ngrok_iniciar_tunel(puerto: int) -> str:
    """
    Inicia el cliente de Ngrok en background apuntando al puerto especificado.
    Útil para exponer servicios locales como n8n al internet público.

    Args:
        puerto: El puerto local a exponer (ej: 5678 para n8n)
    """
    try:
        # Verificar si ya está corriendo
        try:
            res = requests.get(NGROK_API_URL, timeout=2)
            if res.status_code == 200:
                tunnels = res.json().get("tunnels", [])
                for t in tunnels:
                    if str(puerto) in t.get("config", {}).get("addr", ""):
                        return json.dumps({
                            "status": "success",
                            "mensaje": f"Ngrok ya está corriendo y apuntando al puerto {puerto}.",
                            "url_publica": t.get("public_url")
                        })
        except requests.ConnectionError:
            pass # Ngrok no está corriendo, proceder a iniciar

        # Autenticación con Token (si existe en el entorno)
        auth_token = os.getenv("NGROK_AUTHTOKEN")
        if auth_token:
            subprocess.run(["ngrok", "config", "add-authtoken", auth_token], capture_output=True, text=True)

        # Iniciar ngrok en background
        # NOTA: Redirigimos output a /dev/null para evitar bloqueos
        comando = f"nohup ngrok http {puerto} > /dev/null 2>&1 &"
        subprocess.run(comando, shell=True, executable="/bin/bash")
        
        # Esperar a que la API local de ngrok despierte (máximo 5 segundos)
        url_publica = None
        for _ in range(10):
            time.sleep(0.5)
            try:
                res = requests.get(NGROK_API_URL, timeout=1)
                if res.status_code == 200:
                    tunnels = res.json().get("tunnels", [])
                    if tunnels:
                        url_publica = tunnels[0].get("public_url")
                        break
            except Exception:
                continue

        if url_publica:
            return json.dumps({
                "status": "success",
                "mensaje": f"Túnel Ngrok iniciado correctamente en el puerto {puerto}.",
                "url_publica": url_publica
            })
        else:
            return json.dumps({
                "status": "warning",
                "mensaje": "El proceso de Ngrok inició pero no se pudo recuperar la URL pública de inmediato."
            })

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al iniciar Ngrok: {str(e)}"})


@tool
def ngrok_obtener_url() -> str:
    """
    Consulta la API local de Ngrok (puerto 4040) para obtener la URL pública actual del túnel.
    Devuelve la URL para compartirla o usarla en configuraciones de webhooks.
    """
    try:
        res = requests.get(NGROK_API_URL, timeout=2)
        if res.status_code == 200:
            tunnels = res.json().get("tunnels", [])
            if tunnels:
                url_publica = tunnels[0].get("public_url")
                return json.dumps({
                    "status": "success",
                    "url_publica": url_publica
                })
            else:
                return json.dumps({
                    "status": "warning",
                    "mensaje": "La API de Ngrok responde, pero no hay túneles activos."
                })
        else:
            return json.dumps({"status": "error", "mensaje": f"Código HTTP {res.status_code} de la API Ngrok."})
    except requests.ConnectionError:
        return json.dumps({
            "status": "error",
            "mensaje": "Ngrok no está corriendo. Debes iniciarlo primero con ngrok_iniciar_tunel."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})

# Exponer herramientas
HERRAMIENTAS_NGROK = [ngrok_iniciar_tunel, ngrok_obtener_url]
