"""
skill_ngrok.py — Habilidad: Exposición de Servicios con Túneles Ngrok
=====================================================================
Herramientas para crear y gestionar túneles seguros hacia el internet público,
exponiendo puertos locales (n8n, FastAPI, React Vite) de forma temporal para webhooks.

Herramientas disponibles:
  - ngrok_iniciar_tunel : Inicia el proceso de túnel en segundo plano
  - ngrok_obtener_url   : Consulta la API local de Ngrok (puerto 4040) para recuperar la URL pública
"""

import os
import time
import json
import subprocess
import requests
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

NGROK_API_URL = "http://localhost:4040/api/tunnels"


def obtener_prompt_ngrok() -> str:
    """
    System Prompt especializado y encapsulado para la gestión de túneles Ngrok
    del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO TÚNELES NGROK ACTIVO 🛑]
Eres el Especialista en Redes y Exposición Perimetral del Subagente de Desarrollo.
Tu misión es exponer puertos de servicios locales al internet de forma segura para permitir pruebas de webhooks, callbacks externos e integraciones remotas.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PUERTOS AUTORIZADOS:
   - Exponer únicamente puertos de desarrollo autorizados (ej. `5678` para n8n, `8000` para FastAPI, `5173` para Vite).
2. OBTENCIÓN Y CONFIRMACIÓN DE URL:
   - Tras iniciar el túnel con `ngrok_iniciar_tunel`, confirma la URL pública usando `ngrok_obtener_url` para verificar que el túnel esté operativo.
3. SEGURIDAD DE ENTORNO:
   - Nunca expongas servicios sin autenticación a largo plazo. Los túneles son temporales para pruebas de desarrollo.
"""


@tool
def ngrok_iniciar_tunel(puerto: int) -> str:
    """
    Inicia un túnel Ngrok en background apuntando al puerto local especificado.
    Útil para exponer servicios como n8n (5678) o APIs locales (8000) a internet público.

    Args:
        puerto: Número de puerto local a exponer (ej: 5678, 8000, 3000).
    """
    try:
        # Verificar si ya existe un túnel corriendo en ese puerto
        try:
            res = requests.get(NGROK_API_URL, timeout=2)
            if res.status_code == 200:
                tunnels = res.json().get("tunnels", [])
                for t in tunnels:
                    if str(puerto) in t.get("config", {}).get("addr", ""):
                        return json.dumps({
                            "status": "success",
                            "mensaje": f"Ngrok ya está activo y exponiendo el puerto {puerto}.",
                            "url_publica": t.get("public_url")
                        })
        except requests.ConnectionError:
            pass

        # Configurar authtoken si existe en variables de entorno
        auth_token = os.getenv("NGROK_AUTHTOKEN")
        if auth_token:
            subprocess.run(["ngrok", "config", "add-authtoken", auth_token], capture_output=True, text=True)

        # Iniciar en background
        comando = f"nohup ngrok http {puerto} > /dev/null 2>&1 &"
        subprocess.run(comando, shell=True)

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
                "puerto": puerto,
                "mensaje": f"Túnel Ngrok iniciado exitosamente en puerto {puerto}.",
                "url_publica": url_publica
            })
        else:
            return json.dumps({
                "status": "warning",
                "puerto": puerto,
                "mensaje": "El proceso de Ngrok fue iniciado pero la URL pública aún no está lista. Consulta con ngrok_obtener_url."
            })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def ngrok_obtener_url() -> str:
    """
    Consulta la API local de Ngrok para obtener la URL pública activa del túnel.
    Devuelve la URL generada para configurar webhooks o accesos externos.
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
            return json.dumps({
                "status": "warning",
                "mensaje": "La API de Ngrok responde pero no hay túneles activos actualmente."
            })
        return json.dumps({
            "status": "error",
            "mensaje": f"Respuesta inesperada de la API de Ngrok (código {res.status_code})."
        })
    except requests.ConnectionError:
        return json.dumps({
            "status": "error",
            "mensaje": "El cliente de Ngrok no está en ejecución. Inicia un túnel con ngrok_iniciar_tunel."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_NGROK = [
    ngrok_iniciar_tunel,
    ngrok_obtener_url
]
