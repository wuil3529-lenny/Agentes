"""
skill_seguridad_dashboard.py — Seguridad, SOC y Monitoreo del Dashboard
======================================================================
Habilidad del Subagente de Ciberseguridad (Robin) para auditar incidentes
de intrusión en tiempo real, monitorear y gestionar alarmas perimetrales,
analizar la postura defensiva de la consola web (auth Bcrypt, JWT, whitelist)
y neutralizar vectores de ataque contra el panel de mando central.

Herramientas disponibles:
  - tool_consultar_incidentes_dashboard   : Inspecciona el registro de intrusiones bloqueadas
  - tool_verificar_estado_alarma_dashboard: Comprueba si la alarma perimetral está disparada
  - tool_gestionar_alarma_dashboard       : Silencia alarmas activas o purga el historial tras triage
  - tool_auditar_postura_dashboard        : Evalúa la postura global de seguridad de la consola (0-100)
  - tool_bloquear_ip_dashboard            : Aísla y bloquea una dirección IP agresora en el perímetro
  - obtener_prompt_seguridad_dashboard    : System Prompt especializado para inyección bajo demanda
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["robin", "subagente_ciberseguridad"] else _CURRENT.parents[2]
_DASHBOARD_DIR = _APP_ROOT / "dashboard"
_INCIDENTES_FILE = _DASHBOARD_DIR / "incidentes_seguridad.json"
_USUARIOS_FILE = _DASHBOARD_DIR / "usuarios.json"
_COMANDOS_FILE = _DASHBOARD_DIR / "comandos_remotos.json"
_IPS_BLOQUEADAS_FILE = _DASHBOARD_DIR / "ips_bloqueadas.json"
_ENV_FILE = _APP_ROOT / ".env"


def obtener_prompt_seguridad_dashboard() -> str:
    """
    Retorna el System Prompt especializado para la habilidad de Seguridad y Monitoreo del Dashboard.
    """
    md_path = _CURRENT.parent / "Skill_Seguridad_Dashboard_Subagente_Ciberseguridad.md"
    if md_path.exists():
        try:
            return md_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return """[🛡️ DIRECTIVA OPERATIVA: MODO CENTINELA Y SEGURIDAD DEL DASHBOARD (SOC DEFENSIVO)]
Eres la Oficial de Seguridad (SOC Analyst) y Centinela del Dashboard de la tripulación.
Tu función es auditar activamente los eventos de intrusión registrados en la consola, supervisar el cortafuegos perimetral, analizar la autenticación y gestionar alarmas de intrusión.

PAUTAS CRÍTICAS DE ACTUACIÓN:
1. INSPECCIÓN DE INCIDENTES:
   - Utiliza `tool_consultar_incidentes_dashboard` para revisar ataques recientes, IPs agresoras, rutas buscadas (exploits) y user agents.
2. GESTIÓN DE ALARMAS:
   - Utiliza `tool_verificar_estado_alarma_dashboard` para detectar si el Dashboard tiene una alarma sonora/visual encendida.
   - NUNCA silencies una alarma (`tool_gestionar_alarma_dashboard`) sin haber analizado y registrado el incidente primero.
3. AUDITORÍA DE POSTURA:
   - Emplea `tool_auditar_postura_dashboard` para comprobar que la autenticación esté activa (`CONSOLE_AUTH_ACTIVE=true`), que las contraseñas usen hash Bcrypt y que existan reglas de IPs permitidas.
4. CONTENCIÓN DE AMENAZAS:
   - Si una IP reitera intentos de acceso no autorizado, bloquéala de inmediato con `tool_bloquear_ip_dashboard`.
"""


def _leer_env_dict() -> Dict[str, str]:
    """Helper interno para leer variables del archivo .env."""
    env_vars = {}
    if _ENV_FILE.exists():
        try:
            for linea in _ENV_FILE.read_text(encoding="utf-8").splitlines():
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return env_vars


@tool
def tool_consultar_incidentes_dashboard(limite: int = 20) -> str:
    """
    Inspecciona el historial de incidentes e intrusiones bloqueadas en el Dashboard.
    Retorna un diagnóstico forense con el número total de ataques, IPs más activas,
    rutas atacadas y el detalle de los eventos más recientes.
    """
    if not _INCIDENTES_FILE.exists():
        return json.dumps({
            "status": "ok",
            "mensaje": "No existe registro de incidentes en el Dashboard (archivo no creado aún).",
            "total_incidentes": 0,
            "incidentes": []
        }, ensure_ascii=False, indent=2)

    try:
        data = json.loads(_INCIDENTES_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error leyendo archivo de incidentes: {str(e)}"
        }, ensure_ascii=False)

    total = len(data)
    if total == 0:
        return json.dumps({
            "status": "ok",
            "mensaje": "El historial de incidentes del Dashboard está completamente limpio. 0 intrusiones registradas.",
            "total_incidentes": 0,
            "incidentes": []
        }, ensure_ascii=False, indent=2)

    # Análisis de frecuencia por IP y por ruta
    conteo_ips = {}
    conteo_rutas = {}
    for inc in data:
        ip = inc.get("ip", "Desconocida")
        ruta = inc.get("ruta", "N/A")
        conteo_ips[ip] = conteo_ips.get(ip, 0) + 1
        conteo_rutas[ruta] = conteo_rutas.get(ruta, 0) + 1

    top_ips = sorted(conteo_ips.items(), key=lambda x: x[1], reverse=True)[:5]
    top_rutas = sorted(conteo_rutas.items(), key=lambda x: x[1], reverse=True)[:5]
    recientes = data[:limite]

    resumen = {
        "status": "success",
        "total_incidentes_registrados": total,
        "top_ips_agresoras": [{"ip": ip, "intentos": count} for ip, count in top_ips],
        "top_rutas_atacadas": [{"ruta": ruta, "intentos": count} for ruta, count in top_rutas],
        "incidentes_recientes": recientes
    }
    return json.dumps(resumen, ensure_ascii=False, indent=2)


@tool
def tool_verificar_estado_alarma_dashboard() -> str:
    """
    Comprueba si la alarma perimetral de intrusión está disparada actualmente en el Dashboard.
    Detecta alertas activas en los últimos 120 segundos o eventos de intrusión críticos no atendidos.
    """
    if not _INCIDENTES_FILE.exists():
        return json.dumps({
            "alarma_activa": False,
            "mensaje": "Sin incidentes registrados. Alarma inactiva."
        }, ensure_ascii=False)

    try:
        data = json.loads(_INCIDENTES_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) == 0:
            return json.dumps({
                "alarma_activa": False,
                "mensaje": "Historial vacío. Alarma inactiva (verde)."
            }, ensure_ascii=False)

        ultimo = data[0]
        timestamp = ultimo.get("timestamp", 0)
        ahora = time.time()
        diferencia_segundos = ahora - timestamp

        # Se considera activa si ocurrió en los últimos 120 segundos (umbral del dashboard)
        es_reciente = (diferencia_segundos < 120)

        return json.dumps({
            "alarma_activa": es_reciente,
            "segundos_desde_ultimo_evento": int(diferencia_segundos),
            "estado": "🔴 ALERTA EN CURSO" if es_reciente else "🟢 EN REPOSO",
            "ultimo_evento": ultimo
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "alarma_activa": False,
            "error": f"Error verificando estado de alarma: {str(e)}"
        }, ensure_ascii=False)


@tool
def tool_gestionar_alarma_dashboard(accion: str, motivo: str) -> str:
    """
    Gestiona el sistema de alarmas perimetrales del Dashboard.
    Acciones soportadas:
      - 'silenciar'       : Reconoce el incidente y silencia la alerta visual/sonora tras evaluación.
      - 'limpiar_historial': Pone a cero el historial de incidentes tras archivar el informe de seguridad.
    """
    accion = accion.strip().lower()
    if accion not in ["silenciar", "limpiar_historial"]:
        return json.dumps({
            "status": "error",
            "mensaje": f"Acción inválida '{accion}'. Opciones válidas: 'silenciar', 'limpiar_historial'."
        }, ensure_ascii=False)

    if accion == "silenciar":
        # Registrar acuse de recibo en archivo de control del SOC
        ack_file = _DASHBOARD_DIR / "soc_alarma_ack.json"
        ack_data = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": time.time(),
            "analista": "Subagente_Ciberseguridad (Robin)",
            "motivo": motivo,
            "estado": "SILENCIADA_Y_DOCUMENTADA"
        }
        try:
            ack_file.write_text(json.dumps(ack_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            return json.dumps({"status": "error", "mensaje": f"Fallo al registrar acuse: {str(e)}"})

        return json.dumps({
            "status": "success",
            "accion": "silenciar",
            "mensaje": "Alarma de intrusión silenciada formalmente por el SOC de Ciberseguridad.",
            "acuse_recibo": ack_data
        }, ensure_ascii=False, indent=2)

    elif accion == "limpiar_historial":
        try:
            _INCIDENTES_FILE.write_text("[]", encoding="utf-8")
            return json.dumps({
                "status": "success",
                "accion": "limpiar_historial",
                "mensaje": "Historial de incidentes del Dashboard reseteado a cero (0 eventos).",
                "motivo": motivo
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "mensaje": f"Error limpiando historial: {str(e)}"})


@tool
def tool_auditar_postura_dashboard() -> str:
    """
    Audita la postura global de seguridad de la consola web (Dashboard):
    Verifica autenticación activa (Bcrypt/JWT), lista de IPs permitidas (Whitelist),
    cuentas de usuario configuradas, comandos remotos pendientes y emite una puntuación defensiva (0-100).
    """
    env_vars = _leer_env_dict()
    hallazgos = []
    puntuacion = 100

    # 1. Autenticación de Consola
    auth_activa = env_vars.get("CONSOLE_AUTH_ACTIVE", "").lower() in ["true", "1"]
    if not auth_activa:
        hallazgos.append({
            "severidad": "ALTO",
            "item": "Autenticación de Consola",
            "detalle": "CONSOLE_AUTH_ACTIVE está desactivado o ausente en .env. La consola es accesible sin login."
        })
        puntuacion -= 35
    else:
        hallazgos.append({
            "severidad": "OK",
            "item": "Autenticación de Consola",
            "detalle": "CONSOLE_AUTH_ACTIVE está activado. Requiere usuario y contraseña."
        })

    # 2. Whitelist de IPs
    allowed_ips = env_vars.get("ALLOWED_IPS", "").strip()
    if not allowed_ips:
        hallazgos.append({
            "severidad": "MEDIO",
            "item": "Cortafuegos Perimetral (ALLOWED_IPS)",
            "detalle": "No hay lista blanca de IPs definida. El cortafuegos perimetral no restringe orígenes."
        })
        puntuacion -= 15
    else:
        hallazgos.append({
            "severidad": "OK",
            "item": "Cortafuegos Perimetral (ALLOWED_IPS)",
            "detalle": f"Whitelist activa configurada con reglas: {allowed_ips}"
        })

    # 3. Base de Datos de Usuarios (usuarios.json)
    usuarios_count = 0
    hashes_validos = 0
    if _USUARIOS_FILE.exists():
        try:
            usuarios = json.loads(_USUARIOS_FILE.read_text(encoding="utf-8"))
            if isinstance(usuarios, list):
                usuarios_count = len(usuarios)
                for u in usuarios:
                    pwd_hash = u.get("password_hash", "")
                    if pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$"):
                        hashes_validos += 1
        except Exception:
            pass

    if usuarios_count == 0:
        hallazgos.append({
            "severidad": "MEDIO",
            "item": "Usuarios Registrados",
            "detalle": "No hay usuarios registrados en usuarios.json (opera en modo fallback)."
        })
        puntuacion -= 10
    else:
        hallazgos.append({
            "severidad": "OK",
            "item": "Usuarios Registrados",
            "detalle": f"{usuarios_count} usuario(s) registrados; {hashes_validos}/{usuarios_count} protegidos con Bcrypt."
        })

    # 4. Comandos Remotos Pendientes
    comandos_pendientes = 0
    if _COMANDOS_FILE.exists():
        try:
            cmd_data = json.loads(_COMANDOS_FILE.read_text(encoding="utf-8"))
            if isinstance(cmd_data, dict):
                comandos_pendientes = sum(len(v) for v in cmd_data.values() if isinstance(v, list))
        except Exception:
            pass

    if comandos_pendientes > 0:
        hallazgos.append({
            "severidad": "BAJO",
            "item": "Comandos Remotos en Cola",
            "detalle": f"Hay {comandos_pendientes} comando(s) remoto(s) en cola pendientes de despacho."
        })
    else:
        hallazgos.append({
            "severidad": "OK",
            "item": "Comandos Remotos",
            "detalle": "Cola de comandos remotos limpia. Sin ejecuciones diferidas pendientes."
        })

    # 5. Lista Negra de IPs Activas
    bloqueadas_count = 0
    if _IPS_BLOQUEADAS_FILE.exists():
        try:
            blk = json.loads(_IPS_BLOQUEADAS_FILE.read_text(encoding="utf-8"))
            bloqueadas_count = len(blk) if isinstance(blk, list) else 0
        except Exception:
            pass

    puntuacion = max(0, min(100, puntuacion))
    clasificacion = "EXCELENTE" if puntuacion >= 85 else ("ACEPTABLE" if puntuacion >= 65 else "RIESGOSA")

    reporte_postura = {
        "puntuacion_defensiva": f"{puntuacion}/100",
        "clasificacion": clasificacion,
        "ips_bloqueadas_activas": bloqueadas_count,
        "total_hallazgos": len(hallazgos),
        "hallazgos": hallazgos,
        "recomendaciones": [
            "Mantener CONSOLE_AUTH_ACTIVE=true para evitar accesos anónimos.",
            "Restringir ALLOWED_IPS a rangos locales conocidos en producción.",
            "Supervisar periódicamente los incidentes bloqueados con tool_consultar_incidentes_dashboard."
        ]
    }
    return json.dumps(reporte_postura, ensure_ascii=False, indent=2)


@tool
def tool_bloquear_ip_dashboard(ip: str, motivo: str) -> str:
    """
    Aísla y bloquea una dirección IP agresora en el perímetro de la consola.
    Registra la IP en la base de datos de contención inmediata del SOC.
    """
    ip = ip.strip()
    if not ip or ip in ["127.0.0.1", "localhost", "::1"]:
        return json.dumps({
            "status": "error",
            "mensaje": f"No se puede bloquear la dirección localhost o loopback ({ip})."
        }, ensure_ascii=False)

    bloqueadas = []
    if _IPS_BLOQUEADAS_FILE.exists():
        try:
            data = json.loads(_IPS_BLOQUEADAS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                bloqueadas = data
        except Exception:
            bloqueadas = []

    # Verificar si ya estaba bloqueada
    for b in bloqueadas:
        if b.get("ip") == ip:
            return json.dumps({
                "status": "ok",
                "mensaje": f"La IP {ip} ya se encontraba registrada en la lista de bloqueo perimetral.",
                "registro": b
            }, ensure_ascii=False, indent=2)

    nuevo_bloqueo = {
        "ip": ip,
        "motivo": motivo,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": time.time(),
        "bloqueado_por": "Subagente_Ciberseguridad (Robin - SOC)"
    }
    bloqueadas.append(nuevo_bloqueo)

    try:
        _IPS_BLOQUEADAS_FILE.write_text(json.dumps(bloqueadas, indent=2, ensure_ascii=False), encoding="utf-8")
        return json.dumps({
            "status": "success",
            "mensaje": f"IP {ip} bloqueada exitosamente en el perímetro del Dashboard.",
            "registro": nuevo_bloqueo
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Fallo al escribir lista de bloqueo: {str(e)}"
        }, ensure_ascii=False)
