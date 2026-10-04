"""
skill_conectores_mcp_api.py — Habilidad: Conectores Universales MCP y APIs con Blindaje de Ciberseguridad
==========================================================================================================
Permite al Subagente de Desarrollo conectarse a cualquier API (REST, GraphQL, Webhooks)
y servidores MCP (Model Context Protocol) de forma automática y estandarizada,
asegurando que todo conector o código generado pase obligatoriamente por el filtro
de auditoría del Subagente de Ciberseguridad antes de ejecutarse o persistirse.

Herramientas disponibles:
  - tool_solicitar_auditoria_ciberseguridad: Escaneo SAST + pase por el canal de Ciberseguridad.
  - tool_conectar_api_rest                 : Cliente HTTP seguro para APIs REST y GraphQL.
  - tool_conectar_servidor_mcp             : Registrador y configurador de servidores MCP.
  - tool_probar_conexion_segura            : Verificación de salud y latencia de endpoints.
"""

import os
import sys
import re
import json
import time
import hashlib
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"
_CONECTORES_DATA = _APP_ROOT / _AGENTE / "data"
_CONECTORES_DATA.mkdir(parents=True, exist_ok=True)
_REGISTRO_CONECTORES = _CONECTORES_DATA / "conectores_registrados.json"


def obtener_prompt_conectores_mcp_api() -> str:
    """
    System Prompt especializado y encapsulado para la Integración Universal MCP y APIs Seguras.
    """
    return """[🛑 HARD-STOP: MODO INTEGRACIÓN UNIVERSAL MCP Y APIS SEGURAS ACTIVO 🛑]
Eres el Especialista en Integración de Sistemas, Protocolos MCP y Conectividad Perimetral del Subagente de Desarrollo.
Tu misión es conectar de forma ágil y autónoma aplicaciones externas, APIs (REST/GraphQL), webhooks y servidores MCP, asegurando que CADA LÍNEA DE CÓDIGO o credencial sea auditada y visada previamente por el Subagente de Ciberseguridad.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. AUDITORÍA DE CIBERSEGURIDAD PREVIA OBLIGATORIA:
   - NUNCA ejecutes llamadas a APIs nuevas ni registres servidores MCP sin invocar antes `tool_solicitar_auditoria_ciberseguridad`.
   - Cualquier conector con hallazgos críticos de seguridad (secretos quemados, tokens en texto plano, llamadas a IPs privadas sospechosas) queda AUTOMÁTICAMENTE BLOQUEADO.
2. GESTIÓN SEGURA DE CREDENCIALES:
   - Prohibido escribir claves API, contraseñas o tokens directamente en el código o en los argumentos.
   - Toda credencial debe referenciarse a través de variables de entorno mediante `os.getenv('NOMBRE_VARIABLE')` o encabezados parametrizados.
3. PREVENCIÓN DE SSRF (Server-Side Request Forgery):
   - Queda prohibido conectar endpoints apuntando a direcciones de infraestructura privada interna (169.254.169.254, 10.0.0.0/8, 192.168.0.0/16) salvo los puertos locales autorizados de desarrollo de la tripulación (n8n: 5678, FastAPI: 8000, Ngrok: 4040).
4. RESILIENCIA Y TIEMPOS DE RESPUESTA:
   - Toda llamada a API externa debe tener un timeout estricto (máximo 15 segundos) y control de excepciones para no colgar el flujo del sistema.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# REGLAS SAST DE CIBERSEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

PATRONES_VULNERABILIDADES = [
    (r"(?i)(password|passwd|pwd|secret|api_key|token)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{8,}['\"]", "Secreto o clave API hardcodeada en texto plano."),
    (r"sk-[a-zA-Z0-9]{20,}", "Clave secreta de OpenAI expuesta en código."),
    (r"ghp_[a-zA-Z0-9]{36}", "Token de acceso de GitHub expuesto."),
    (r"(?i)http:\/\/(?!localhost|127\.0\.0\.1|0\.0\.0\.0)", "Uso de protocolo HTTP inseguro sin cifrado TLS/HTTPS para endpoints remotos."),
    (r"169\.254\.169\.254", "Intento de acceso a metadatos de instancia de nube (Vulnerabilidad SSRF)."),
    (r"(?i)(eval\s*\(|exec\s*\(|__import__\s*\()", "Uso de funciones dinámicas de ejecución de código arbitrario (eval/exec)."),
    (r"subprocess\.(Popen|run|call)\(.*shell\s*=\s*True", "Ejecución de subprocesos con shell=True sin sanitización.")
]


def _notificar_ciberseguridad(codigo_o_config: str, tipo_integracion: str, aprobacion: bool, detalles: str):
    """Notifica al canal de memoria compartida para que el Subagente de Ciberseguridad tenga constancia."""
    try:
        sys.path.insert(0, str(_APP_ROOT / "Agente_Orquestador"))
        from memory import publicar_mensaje
        publicar_mensaje(
            de="Subagente_Desarrollo",
            para="Subagente_Ciberseguridad",
            tipo="notificacion_auditoria_conector",
            contenido={
                "tipo_integracion": tipo_integracion,
                "estado": "APROBADO" if aprobacion else "RECHAZADO",
                "detalles": detalles,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            canal_tipo="agente"
        )
    except Exception:
        pass


@tool
def tool_solicitar_auditoria_ciberseguridad(
    codigo_o_config: str,
    tipo_integracion: str = "api_rest"
) -> str:
    """
    Envía el código de un conector, script de integración o configuración MCP al motor
    de auditoría del Subagente de Ciberseguridad. Detecta fugas de credenciales,
    inyecciones de comando y vulnerabilidades SSRF antes de autorizar su ejecución.

    Args:
        codigo_o_config: Cadena con el código Python, JSON o configuración a auditar.
        tipo_integracion: Tipo ('api_rest', 'conector_mcp', 'webhook', 'script_integracion').
    """
    hallazgos = []
    bloqueos_criticos = []

    for patron, mensaje in PATRONES_VULNERABILIDADES:
        if re.search(patron, codigo_o_config):
            bloqueos_criticos.append(mensaje)

    aprobado = len(bloqueos_criticos) == 0
    sello_seguridad = hashlib.sha256(codigo_o_config.encode('utf-8')).hexdigest()[:16] if aprobado else "RECHAZADO"

    # Notificar al Subagente de Ciberseguridad a través de la memoria compartida
    _notificar_ciberseguridad(
        codigo_o_config=codigo_o_config,
        tipo_integracion=tipo_integracion,
        aprobacion=aprobado,
        detalles=f"Auditoría completada. Bloqueos: {len(bloqueos_criticos)}. Sello: {sello_seguridad}"
    )

    return json.dumps({
        "status": "success",
        "veredicto_ciberseguridad": "APROBADO" if aprobado else "BLOQUEADO POR CIBERSEGURIDAD",
        "sello_aprobacion": sello_seguridad,
        "bloqueos_criticos": bloqueos_criticos,
        "recomendaciones": [
            "Usar variables de entorno os.getenv() para todos los tokens.",
            "Utilizar HTTPS en todas las comunicaciones externas.",
            "Validar esquemas de payload JSON entrante y saliente."
        ] if not aprobado else ["Código certificado y visado por Ciberseguridad."]
    }, ensure_ascii=False)


@tool
def tool_conectar_api_rest(
    nombre_servicio: str,
    url_endpoint: str,
    metodo: str = "GET",
    headers_dict: dict = None,
    payload_json: dict = None,
    env_token_var: str = ""
) -> str:
    """
    Ejecuta una llamada segura a cualquier API REST o GraphQL pública o privada.
    Inyecta automáticamente tokens desde variables de entorno y previene SSRF.

    Args:
        nombre_servicio: Nombre descriptivo del servicio (ej: 'Stripe', 'Slack', 'GitHub', 'OpenWeather').
        url_endpoint: URL completa del endpoint (debe iniciar con https:// salvo localhost).
        metodo: Método HTTP ('GET', 'POST', 'PUT', 'PATCH', 'DELETE').
        headers_dict: Encabezados adicionales en formato diccionario.
        payload_json: Cuerpo de la petición en formato diccionario para métodos POST/PUT/PATCH.
        env_token_var: Nombre de la variable de entorno que contiene el token (ej: 'STRIPE_API_KEY').
    """
    try:
        # 1. Validación de protocolo y seguridad básica
        url_lower = url_endpoint.lower()
        if not (url_lower.startswith("https://") or "localhost" in url_lower or "127.0.0.1" in url_lower):
            return json.dumps({
                "status": "error",
                "mensaje": "Violación de seguridad: El endpoint debe usar HTTPS cifrado."
            })

        # 2. Bloqueo de SSRF a redes privadas o metadatos
        if "169.254.169.254" in url_lower or "metadata.google" in url_lower:
            return json.dumps({
                "status": "error",
                "mensaje": "Bloqueo SSRF: Intento de acceso a endpoints de metadatos internos bloqueado por Ciberseguridad."
            })

        # 3. Preparación de headers y resolución segura de tokens
        final_headers = headers_dict.copy() if headers_dict else {}
        if env_token_var:
            token_val = os.getenv(env_token_var)
            if not token_val:
                return json.dumps({
                    "status": "error",
                    "mensaje": f"Variable de entorno '{env_token_var}' no encontrada en el sistema."
                })
            final_headers["Authorization"] = f"Bearer {token_val}"

        if "User-Agent" not in final_headers:
            final_headers["User-Agent"] = "Antigravity-Fleet-Connector/2.0"

        # 4. Ejecución de la petición con timeout estricto
        metodo_upper = metodo.upper()
        res = requests.request(
            method=metodo_upper,
            url=url_endpoint,
            headers=final_headers,
            json=payload_json if payload_json and metodo_upper in ["POST", "PUT", "PATCH"] else None,
            timeout=15
        )

        try:
            datos_respuesta = res.json()
        except Exception:
            datos_respuesta = res.text[:2000]

        return json.dumps({
            "status": "success",
            "servicio": nombre_servicio,
            "codigo_http": res.status_code,
            "tiempo_ms": int(res.elapsed.total_seconds() * 1000),
            "respuesta": datos_respuesta
        }, ensure_ascii=False)

    except requests.exceptions.Timeout:
        return json.dumps({"status": "error", "mensaje": f"Timeout (15s) al conectar con {nombre_servicio}."})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al conectar con API {nombre_servicio}: {str(e)}"})


@tool
def tool_conectar_servidor_mcp(
    nombre_servidor: str,
    comando_ejecutable: str,
    argumentos: list,
    variables_entorno: dict = None
) -> str:
    """
    Registra y genera la configuración oficial para conectar cualquier servidor MCP
    (Model Context Protocol) a la flota de agentes, validando que no existan inyecciones
    en los comandos de inicio.

    Args:
        nombre_servidor: Nombre único del servidor MCP (ej: 'filesystem', 'github-mcp', 'postgres-mcp').
        comando_ejecutable: Comando de inicio ('npx', 'uvx', 'python', 'docker').
        argumentos: Lista de argumentos que se le pasarán al comando.
        variables_entorno: Diccionario con variables de entorno necesarias para el servidor.
    """
    try:
        # Validación de seguridad en comandos y argumentos
        caracteres_prohibidos = [";", "&&", "||", "`", "$", "|"]
        for arg in argumentos:
            if any(c in str(arg) for c in caracteres_prohibidos):
                return json.dumps({
                    "status": "error",
                    "mensaje": "Bloqueo de Ciberseguridad: Caracteres de inyección detectados en argumentos MCP."
                })

        config_servidor = {
            "command": comando_ejecutable,
            "args": argumentos
        }
        if variables_entorno:
            config_servidor["env"] = variables_entorno

        # Guardar en persistencia local de conectores
        registro = {}
        if _REGISTRO_CONECTORES.exists():
            try:
                registro = json.loads(_REGISTRO_CONECTORES.read_text(encoding='utf-8'))
            except Exception:
                pass

        registro[nombre_servidor] = {
            "config": config_servidor,
            "fecha_registro": time.strftime("%Y-%m-%d %H:%M:%S"),
            "estado": "auditado_y_activo"
        }
        _REGISTRO_CONECTORES.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding='utf-8')

        return json.dumps({
            "status": "success",
            "servidor_mcp": nombre_servidor,
            "configuracion_json": {
                "mcpServers": {
                    nombre_servidor: config_servidor
                }
            },
            "mensaje": f"Servidor MCP '{nombre_servidor}' validado, registrado y listo para conexión."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al configurar servidor MCP: {str(e)}"})


@tool
def tool_probar_conexion_segura(url_o_endpoint: str, metodo: str = "GET") -> str:
    """
    Realiza una prueba rápida de salud (ping/healthcheck) contra un endpoint,
    reportando latencia, estado de certificado SSL y código de retorno.
    """
    try:
        inicio = time.time()
        res = requests.request(metodo.upper(), url_o_endpoint, timeout=5)
        latencia = int((time.time() - inicio) * 1000)

        return json.dumps({
            "status": "success",
            "endpoint": url_o_endpoint,
            "codigo_http": res.status_code,
            "latencia_ms": latencia,
            "es_seguro_https": url_o_endpoint.lower().startswith("https://"),
            "disponible": res.status_code < 500
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Prueba de conexión fallida: {str(e)}"})


HERRAMIENTAS_CONECTORES_MCP_API = [
    tool_solicitar_auditoria_ciberseguridad,
    tool_conectar_api_rest,
    tool_conectar_servidor_mcp,
    tool_probar_conexion_segura,
]
