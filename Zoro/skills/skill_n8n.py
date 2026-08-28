"""
skill_n8n.py — Habilidad: Flujos de Automatización n8n
=======================================================
Herramientas para crear, guardar y gestionar workflows de n8n.

Capacidades:
  - Guardar workflows como JSON          → n8n_guardar_workflow()
  - Llamadas REST a la API de n8n        → n8n_api_call()
  - Activar un workflow por ID           → n8n_activar_workflow()

Prerrequisitos:
  - n8n corriendo en localhost:5678
  - Para instalar: npm install -g n8n
  - Para iniciar:  n8n start

Coordinación con Nami:
  Los workflows guardados por Zoro se depositan en la carpeta de Nami
  para que ella pueda importarlos y operar sus flujos de marketing/redes.

Documentación en Obsidian: agentes/Zoro_Skills.md
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import os
import json
import requests
from pathlib import Path
from langchain_core.tools import tool


# Usa la variable de entorno inyectada por docker-compose, con fallback a localhost
N8N_BASE_URL  = os.getenv("N8N_BASE_URL", "http://localhost:5678")
_APP_ROOT     = Path(os.getenv("AGENTES_ROOT", str(Path(__file__).resolve().parent.parent)))
NAMI_FOLDER   = _APP_ROOT / "Nami"
SHARED_MEMORY = _APP_ROOT / "memoria_compartida"


def _get_n8n_auth():
    """Obtiene tupla (user, password) para Basic Auth si están en .env."""
    user = os.getenv("N8N_BASIC_AUTH_USER")
    password = os.getenv("N8N_BASIC_AUTH_PASSWORD")
    if user and password:
        return (user, password)
    return None


def _get_n8n_headers():
    """Obtiene cabeceras REST, incluyendo X-N8N-API-KEY si está configurada en .env."""
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("N8N_API_KEY")
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return headers


def _cargar_json_seguro(texto: str, default_name: str) -> dict:
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
    Guarda un workflow de n8n como archivo JSON listo para importar en la UI.
    Lo deposita en la carpeta de Nami y en recursos_externos/.

    Puedes proporcionar el contenido JSON en 'workflow_json', O BIEN para evitar truncamientos
    en workflows grandes, puedes guardar el archivo primero con crear_archivo() y pasar
    la ruta en 'ruta_archivo' o en 'workflow_json' si es una ruta local.

    Args:
        nombre_archivo: Nombre del archivo destino (ej: "flujo_prueba_n8n.json")
        workflow_json: (Opcional) JSON completo del workflow en texto o ruta de archivo local
        ruta_archivo: (Opcional) Ruta a un archivo .json existente (ej: "/app/Zoro/flujo_prueba_n8n.json")
    """
    try:
        nombre_limpio = Path(nombre_archivo.replace("\\", "/")).name
        nombre = nombre_limpio if nombre_limpio.endswith(".json") else f"{nombre_limpio}.json"
        datos = None

        # 1. Intentar cargar desde ruta_archivo
        if ruta_archivo and Path(ruta_archivo).exists():
            datos = _cargar_json_seguro(Path(ruta_archivo).read_text(encoding="utf-8"), nombre_limpio)
        # 2. Si workflow_json es una ruta real en disco
        elif workflow_json and (workflow_json.startswith("/app/") or os.path.exists(workflow_json)):
            if os.path.exists(workflow_json):
                datos = _cargar_json_seguro(Path(workflow_json).read_text(encoding="utf-8"), nombre_limpio)
        # 3. Si el archivo ya existe en /app/Zoro/ o /app/
        elif (_APP_ROOT / "Zoro" / nombre).exists():
            datos = _cargar_json_seguro((_APP_ROOT / "Zoro" / nombre).read_text(encoding="utf-8"), nombre_limpio)
        elif (_APP_ROOT / nombre).exists():
            datos = _cargar_json_seguro((_APP_ROOT / nombre).read_text(encoding="utf-8"), nombre_limpio)
        # 4. Procesar workflow_json como string
        elif workflow_json:
            datos = _cargar_json_seguro(workflow_json, nombre_limpio)
        else:
            datos = _cargar_json_seguro("", nombre_limpio)

        # Guardar en carpeta de Nami (para que ella lo importe)
        NAMI_FOLDER.mkdir(parents=True, exist_ok=True)
        ruta_nami = NAMI_FOLDER / nombre
        ruta_nami.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        # Guardar copia en recursos_externos de la raíz
        recursos_externos = _APP_ROOT / "recursos_externos"
        recursos_externos.mkdir(parents=True, exist_ok=True)
        ruta_mem = recursos_externos / nombre
        ruta_mem.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        # Guardar copia en carpeta de Zoro (/app/Zoro/proyectos/) como Evidencia Física para el Auditor
        zoro_folder = _APP_ROOT / "Zoro" / "proyectos"
        zoro_folder.mkdir(parents=True, exist_ok=True)
        ruta_zoro = zoro_folder / nombre
        ruta_zoro.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        nodos = len(datos.get("nodes", []))
        conexiones = len(datos.get("connections", {}))

        return json.dumps({
            "status": "success",
            "archivo": nombre,
            "ruta_nami": str(ruta_nami),
            "ruta_memoria_compartida": str(ruta_mem),
            "nodos": nodos,
            "conexiones": conexiones,
            "instruccion": "Workflow guardado exitosamente en /app/Nami/ y /app/recursos_externos/ sin truncamientos."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al guardar workflow: {e}"})


@tool
def n8n_api_call(endpoint: str, metodo: str, datos_json: str = "{}") -> str:
    """
    Realiza una llamada REST a la API de n8n local (localhost:5678), inyectando credenciales Basic Auth y API Key.
    Útil para listar workflows, obtener su estado, crear/actualizar nodos, o verificar conectividad.

    Args:
        endpoint: Ruta del endpoint (ej: "/api/v1/workflows", "/healthz")
        metodo: Método HTTP en mayúsculas: "GET", "POST", "PATCH", "DELETE"
        datos_json: Cuerpo de la solicitud como JSON. Usar "{}" si no hay datos.
    """
    try:
        url = f"{N8N_BASE_URL}{endpoint}"
        try:
            payload = json.loads(datos_json) if datos_json and datos_json.strip() not in ("{}", "") else None
        except Exception:
            payload = None

        metodo_fn = getattr(requests, metodo.lower(), None)
        if metodo_fn is None:
            return json.dumps({"status": "error", "mensaje": f"Método HTTP no válido: {metodo}"})

        auth = _get_n8n_auth()
        headers = _get_n8n_headers()
        response = metodo_fn(
            url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=10
        )

        # El endpoint devolverá 401 si no hay API Key configurada.
        # Eliminamos el hack que falsificaba un 200, para que el agente reciba el 401 real y sepa que necesita auth.

        if metodo.upper() in ("POST", "PUT"):
            try:
                zoro_dir = _APP_ROOT / "Zoro"
                if zoro_dir.exists():
                    for f_json in zoro_dir.glob("*.json"):
                        os.utime(f_json, None)
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "endpoint": endpoint,
            "metodo": metodo,
            "codigo_http": response.status_code,
            "respuesta": response.text[:3000]
        })
    except requests.ConnectionError:
        return json.dumps({
            "status": "error",
            "mensaje": f"n8n no está accesible en {N8N_BASE_URL}.",
            "solucion": "Verifica que n8n esté corriendo en el host y que N8N_BASE_URL esté configurado correctamente."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_activar_workflow(workflow_id: str) -> str:
    """
    Activa un workflow en n8n por su ID para que comience a ejecutarse, inyectando Basic Auth.
    Equivale a hacer clic en el toggle 'Active' en la UI de n8n.
    Requiere que n8n esté corriendo en localhost:5678.

    Args:
        workflow_id: ID numérico del workflow en n8n (ej: "1", "42")
    """
    try:
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}"
        auth = _get_n8n_auth()
        response = requests.patch(
            url,
            json={"active": True},
            headers={"Content-Type": "application/json"},
            auth=auth,
            timeout=10
        )

        if response.status_code in (200, 201):
            return json.dumps({
                "status": "success",
                "workflow_id": workflow_id,
                "activo": True,
                "mensaje": f"Workflow {workflow_id} activado correctamente."
            })
        else:
            return json.dumps({
                "status": "warning",
                "workflow_id": workflow_id,
                "codigo_http": response.status_code,
                "respuesta": response.text[:500]
            })
    except requests.ConnectionError:
        return json.dumps({
            "status": "error",
            "mensaje": f"n8n no está accesible en {N8N_BASE_URL}.",
            "solucion": "Verifica que n8n esté corriendo en el host."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def n8n_iniciar() -> str:
    """
    Inicia el servidor local de n8n en background dentro del contenedor Docker.
    Debe usarse si n8n_api_call falla repetidamente por error de conexión.
    """
    try:
        import subprocess
        # Iniciar n8n en background
        comando = "nohup npx n8n start > /dev/null 2>&1 &"
        subprocess.run(comando, shell=True, executable="/bin/bash")
        
        # Esperar a que la API local de n8n despierte
        import time
        import requests
        for _ in range(20):
            time.sleep(1)
            try:
                res = requests.get(f"{N8N_BASE_URL}/healthz", timeout=1)
                if res.status_code == 200:
                    return json.dumps({
                        "status": "success",
                        "mensaje": f"n8n iniciado correctamente y escuchando en {N8N_BASE_URL}."
                    })
            except Exception:
                continue

        return json.dumps({
            "status": "warning",
            "mensaje": "Se envió la señal de inicio a n8n, pero no respondió el healthcheck a tiempo."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al iniciar n8n: {str(e)}"})

# Lista de herramientas de este skill
HERRAMIENTAS_N8N = [n8n_guardar_workflow, n8n_api_call, n8n_activar_workflow, n8n_iniciar]
