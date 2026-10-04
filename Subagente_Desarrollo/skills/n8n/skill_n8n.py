"""
skill_n8n.py — Habilidad: Automatización y Gestión de Flujos n8n
==================================================================
Herramientas para crear, guardar, activar y administrar workflows en n8n.
Soporte para interacción vía API REST y guardado estructurado de JSON.

Herramientas disponibles:
  - n8n_guardar_workflow : Guarda un flujo de n8n en JSON en proyectos y carpetas de destino
  - n8n_api_call         : Ejecuta llamadas REST a la API de n8n (GET, POST, PATCH, DELETE)
  - n8n_activar_workflow : Activa o desactiva un workflow por ID en la instancia de n8n
  - n8n_iniciar          : Despierta el servidor n8n en background dentro del contenedor
"""

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"
_NAMI_FOLDER = _APP_ROOT / "Subagente_Diseno" if (_APP_ROOT / "Subagente_Diseno").exists() else _APP_ROOT / "Nami"
_RECURSOS_EXTERNOS = _APP_ROOT / "recursos_externos"

N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")


def obtener_prompt_n8n() -> str:
    """
    System Prompt especializado y encapsulado para la automatización con n8n
    del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO AUTOMATIZACIÓN DE FLUJOS N8N ACTIVO 🛑]
Eres el Especialista en Automatizaciones y Orquestación n8n del Subagente de Desarrollo.
Tu misión es diseñar, validar y desplegar flujos de trabajo en n8n con estructuras JSON válidas, conexiones precisas y ejecución confiable.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. VALIDEZ DEL ESQUEMA JSON:
   - Todo flujo n8n debe contener como mínimo un nodo de inicio (`n8n-nodes-base.start` o `n8n-nodes-base.manualTrigger`), su matriz `nodes` y su mapeo `connections`.
   - Antes de guardar un flujo con `n8n_guardar_workflow`, valida que el JSON no contenga errores de sintaxis.
2. GESTIÓN MULTI-DESTINO Y EVIDENCIA:
   - Al guardar un workflow, la herramienta lo replica automáticamente en `/app/Subagente_Desarrollo/proyectos/` (evidencia física de desarrollo) y en `/app/Subagente_Diseno/` si corresponde coordinación inter-agente.
3. COMUNICACIÓN REST CON LA API:
   - Usa `n8n_api_call` para interactuar con la instancia activa (inspeccionar estados, consultar endpoints de salud `/healthz`).
   - Si la instancia n8n local no responde, intenta levantarla con `n8n_iniciar` antes de reportar un fallo de infraestructura.
4. SEGURIDAD DE CREDENCIALES:
   - Nunca expongas contraseñas o tokens en texto plano dentro de los parámetros de los nodos exportados. Usa variables de entorno o credenciales gestionadas en n8n.
"""


def _get_n8n_auth() -> Optional[tuple]:
    """Obtiene credenciales Basic Auth si están presentes en las variables de entorno."""
    user = os.getenv("N8N_BASIC_AUTH_USER")
    password = os.getenv("N8N_BASIC_AUTH_PASSWORD")
    if user and password:
        return (user, password)
    return None


def _get_n8n_headers() -> Dict[str, str]:
    """Cabeceras estándar inyectando API Key si está configurada."""
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("N8N_API_KEY")
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return headers


def _cargar_json_seguro(texto: str, default_name: str) -> Dict[str, Any]:
    """Parsea texto como JSON de forma resiliente con fallback a estructura n8n mínima."""
    try:
        return json.loads(texto)
    except Exception:
        pass
    try:
        import ast
        val = ast.literal_eval(texto)
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    return {
        "name": default_name.replace(".json", ""),
        "nodes": [
            {
                "parameters": {},
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "typeVersion": 1,
                "position": [240, 300]
            }
        ],
        "connections": {}
    }


@tool
def n8n_guardar_workflow(nombre_archivo: str, workflow_json: str = "", ruta_archivo: str = "") -> str:
    """
    Guarda un workflow de n8n como archivo JSON listo para importar en la interfaz o API.
    Lo persiste en '/app/Subagente_Desarrollo/proyectos/' y lo replica para coordinación.

    Args:
        nombre_archivo: Nombre del archivo .json (ej: 'flujo_notificaciones.json').
        workflow_json: Contenido JSON del workflow en texto o ruta a archivo.
        ruta_archivo: Ruta a un archivo JSON existente en disco para leer y migrar.
    """
    try:
        nombre_limpio = Path(nombre_archivo.replace("\\", "/")).name
        nombre = nombre_limpio if nombre_limpio.endswith(".json") else f"{nombre_limpio}.json"
        datos = None

        if ruta_archivo and Path(ruta_archivo).exists():
            datos = _cargar_json_seguro(Path(ruta_archivo).read_text(encoding="utf-8"), nombre_limpio)
        elif workflow_json and (workflow_json.startswith("/") or Path(workflow_json).exists()):
            if Path(workflow_json).exists():
                datos = _cargar_json_seguro(Path(workflow_json).read_text(encoding="utf-8"), nombre_limpio)
        elif workflow_json:
            datos = _cargar_json_seguro(workflow_json, nombre_limpio)
        else:
            datos = _cargar_json_seguro("", nombre_limpio)

        # 1. Guardar en proyectos de Subagente_Desarrollo como Evidencia Física principal
        _PROYECTOS.mkdir(parents=True, exist_ok=True)
        ruta_desarrollo = _PROYECTOS / nombre
        ruta_desarrollo.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. Guardar copia en recursos_externos si existe
        _RECURSOS_EXTERNOS.mkdir(parents=True, exist_ok=True)
        ruta_recursos = _RECURSOS_EXTERNOS / nombre
        ruta_recursos.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        # 3. Replicar a carpeta de diseño si está disponible
        _NAMI_FOLDER.mkdir(parents=True, exist_ok=True)
        ruta_nami = _NAMI_FOLDER / nombre
        ruta_nami.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        nodos = len(datos.get("nodes", []))
        conexiones = len(datos.get("connections", {}))

        return json.dumps({
            "status": "success",
            "archivo": nombre,
            "ruta_evidencia": str(ruta_desarrollo),
            "ruta_coordinacion": str(ruta_nami),
            "nodos": nodos,
            "conexiones": conexiones,
            "mensaje": f"Workflow '{nombre}' guardado exitosamente con {nodos} nodos."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_api_call(endpoint: str, metodo: str = "GET", datos_json: str = "{}") -> str:
    """
    Realiza una petición HTTP a la API REST de n8n local inyectando credenciales y cabeceras.

    Args:
        endpoint: Ruta del endpoint (ej: '/api/v1/workflows', '/healthz').
        metodo: Método HTTP en mayúsculas ('GET', 'POST', 'PATCH', 'DELETE').
        datos_json: Cuerpo de la solicitud en formato JSON string.
    """
    try:
        url = f"{N8N_BASE_URL}{endpoint}"
        payload = None
        if datos_json and datos_json.strip() not in ("{}", ""):
            try:
                payload = json.loads(datos_json)
            except Exception:
                payload = None

        metodo_fn = getattr(requests, metodo.lower(), None)
        if metodo_fn is None:
            return json.dumps({"status": "error", "mensaje": f"Método HTTP no soportado: {metodo}"})

        auth = _get_n8n_auth()
        headers = _get_n8n_headers()
        response = metodo_fn(
            url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=10
        )

        return json.dumps({
            "status": "success" if response.status_code < 400 else "warning",
            "endpoint": endpoint,
            "metodo": metodo,
            "codigo_http": response.status_code,
            "respuesta": response.text[:2500]
        })
    except requests.ConnectionError:
        return json.dumps({
            "status": "error",
            "mensaje": f"No se pudo conectar con la instancia de n8n en {N8N_BASE_URL}.",
            "solucion": "Verifica que el servicio esté corriendo o intenta 'n8n_iniciar'."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_activar_workflow(workflow_id: str) -> str:
    """
    Activa un workflow en n8n por su ID para habilitar sus triggers automáticos.

    Args:
        workflow_id: ID numérico o alfanumérico del workflow en n8n.
    """
    try:
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}"
        auth = _get_n8n_auth()
        headers = _get_n8n_headers()
        response = requests.patch(
            url,
            json={"active": True},
            headers=headers,
            auth=auth,
            timeout=10
        )

        if response.status_code in (200, 201):
            return json.dumps({
                "status": "success",
                "workflow_id": workflow_id,
                "activo": True,
                "mensaje": f"Workflow {workflow_id} activado con éxito en n8n."
            })
        return json.dumps({
            "status": "warning",
            "workflow_id": workflow_id,
            "codigo_http": response.status_code,
            "respuesta": response.text[:400]
        })
    except requests.ConnectionError:
        return json.dumps({
            "status": "error",
            "mensaje": f"n8n no está accesible en {N8N_BASE_URL}."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_iniciar() -> str:
    """
    Inicia o verifica el servidor local de n8n en segundo plano (compatible con Linux/Docker y Windows).
    Utilízalo si la API no responde tras varios intentos.
    """
    try:
        # 1. Comprobación rápida: si ya está escuchando, reportar éxito inmediato
        try:
            res = requests.get(f"{N8N_BASE_URL}/healthz", timeout=1.5)
            if res.status_code == 200:
                return json.dumps({
                    "status": "success",
                    "mensaje": f"Servidor n8n ya está activo y escuchando en {N8N_BASE_URL}."
                })
        except Exception:
            pass

        # 2. Intento de inicio según el sistema operativo
        if sys.platform == "win32":
            subprocess.Popen(
                "npx n8n start",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        else:
            comando = "nohup npx n8n start > /dev/null 2>&1 &"
            subprocess.run(comando, shell=True, executable="/bin/bash")

        for _ in range(12):
            time.sleep(1)
            try:
                res = requests.get(f"{N8N_BASE_URL}/healthz", timeout=1)
                if res.status_code == 200:
                    return json.dumps({
                        "status": "success",
                        "mensaje": f"Servidor n8n iniciado correctamente y escuchando en {N8N_BASE_URL}."
                    })
            except Exception:
                continue

        return json.dumps({
            "status": "warning",
            "mensaje": f"Se envió el comando de arranque a n8n, pero no respondió el healthcheck en {N8N_BASE_URL} dentro del tiempo límite. Verifica si n8n o Docker están instalados en el host."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_N8N = [
    n8n_guardar_workflow,
    n8n_api_call,
    n8n_activar_workflow,
    n8n_iniciar
]
