"""
skill_tareas_programadas.py — Motor de Gatillos Zero-Token (Event-Driven), Sensores Python y Cron
==================================================================================================
Permite al Agente Orquestador y a la flota recibir CUALQUIER tarea repetitiva, reactiva por eventos
o programada solicitada por el usuario, garantizando CERO CONSUMO DE TOKENS LLM mientras se vigila
la condición o se espera el evento.

Principio Arquitectónico ("Zero-Token Idle / Gatillo en Código Puro"):
  - NUNCA se despierta a un agente LLM solo para preguntar "¿llegó un correo?", "¿bajó el stock?"
    o "¿cambió un archivo/API?".
  - La vigilancia la realiza un GATILLO / SENSOR LIGERO EN PYTHON PURO (0 tokens) ejecutado por
    el demonio `base_listener.py`.
  - ÚNICAMENTE cuando el gatillo detecta un evento real (`disparar == True`, ej. entró un correo
    nuevo no leído, una consulta SQL devolvió `stock < 10`, llegó un archivo/webhook, o se cumplió
    un sensor Python hecho a medida para la tarea del usuario), el motor inyecta el ticket en
    `Bitacora.md` con los datos del evento adjuntos y despierta al subagente especialista.
  - Para tareas generativas por horario fijo (ej. generar video diario a las 09:00), el gatillo de
    reloj espera con 0 tokens hasta la hora exacta y despierta al agente creador.

Herramientas disponibles:
  - tool_crear_gatillo_sensor_python     : Crea un script sensor ligero (.py) de 0 tokens a medida
                                           para cualquier condición/evento que pida el usuario.
  - tool_programar_tarea_repetitiva      : Registra la tarea vinculada a un gatillo de evento (0 tokens)
                                           o a un reloj programado (cron).
  - tool_listar_tareas_repetitivas       : Consulta todas las tareas y gatillos activos.
  - tool_modificar_estado_tarea_repetitiva: Pausa, reanuda, elimina o dispara manualmente una tarea.
"""

import email
import imaplib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR = _APP_ROOT / "Agente_Orquestador" / "data"
_SENSORES_DIR = _DATA_DIR / "sensores"
_TAREAS_FILE = _DATA_DIR / "tareas_programadas.json"
_BITACORA_FILE = _APP_ROOT / "Bitacora.md"
_DASHBOARD_TAREAS_FILE = _APP_ROOT / "dashboard" / "tareas_programadas.json"
_ULTIMO_HASH_BITACORA: str = ""

PLAYBOOK_REC_SCOUT_001 = """Rutina Semanal de Exploración y Postulación Laboral Multiplataforma Zero-Noise (Get on Board, LinkedIn Jobs y Computrabajo).

PROCEDIMIENTO PASO A PASO:
1. Scouting Multiplataforma Zero-Noise (Get on Board & LinkedIn):
   - Invocar `tool_scout_laboral_multiplataforma(plataformas='todas')`.
   - Inspeccionar digest emails IMAP, extraer ofertas activas y descartar expiradas/cerradas.
   - Contrastar requerimientos técnicos contra 'memoria/Perfil_Laboral_Wuil.md' (umbral estricto >= 75%).
   - Descartar en silencio absoluto puestos < 75% o incompatibles.

2. Conexión CDP / Web Browser (Computrabajo Venezuela):
   - Conectar mediante Chrome DevTools Protocol (CDP) a la sesión autenticada en 'http://localhost:9222'.
   - Navegar al listado de ofertas de empleo recientes en Computrabajo.
   - Filtrar áreas estratégicas de IA, Agentes, Python y Software.
   - Responder Killer Questions con honestidad curricular y ejecutar postulación.

3. Trazabilidad y Evidencia Física Zero-Trust:
   - Guardar capturas de confirmación en 'Agente_Orquestador/informes/captura_postulacion_<ID>.png'.
   - Generar reporte físico en 'Agente_Orquestador/informes/reporte_scouting_laboral_<FECHA>.md'.

4. Cierre y Notificación:
   - Notificar al Capitán por Telegram y nota de voz neural con las oportunidades compatibles encontradas o reporte de 0 compatibles."""

_MAPA_CARPETAS_SALIDA = {
    "Subagente_Desarrollo": "Subagente_Desarrollo/proyectos",
    "Subagente_Diseno": "Subagente_Diseno/informes",
    "Subagente_Ciberseguridad": "Subagente_Ciberseguridad/reportes",
    "Subagente_Asistencia": "Subagente_Asistencia/informes",
}


def _asegurar_archivo_tareas() -> dict:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _SENSORES_DIR.mkdir(parents=True, exist_ok=True)
    if not _TAREAS_FILE.exists():
        data_inicial = {"tareas": []}
        _TAREAS_FILE.write_text(json.dumps(data_inicial, indent=2, ensure_ascii=False), encoding="utf-8")
        return data_inicial
    try:
        data = json.loads(_TAREAS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "tareas" not in data:
            return {"tareas": []}
        return data
    except Exception:
        return {"tareas": []}


def _guardar_archivo_tareas(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _TAREAS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _sincronizar_dashboard_json(tareas: list[dict]) -> None:
    """
    Sincroniza la lista de tareas en `dashboard/tareas_programadas.json` agrupadas
    en 'diarias', 'semanales' y 'mensuales', para que la Consola Web del SOC refleje
    fielmente el estado en tiempo real de la flota.
    """
    try:
        _DASHBOARD_TAREAS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ahora = datetime.now()
        diarias = []
        semanales = []
        mensuales = []

        for t in tareas:
            freq = (t.get("frecuencia_reloj") or "").lower()
            nombre = t.get("nombre", "")
            id_tarea = t.get("id_tarea", "")
            resp = t.get("responsable_principal", "")
            estado = t.get("estado", "ACTIVA")
            ult_ejec = t.get("ultima_ejecucion") or ""

            item = {
                "id": id_tarea,
                "titulo": nombre,
                "tarea": t.get("instrucciones_detalladas", "")[:120] + ("..." if len(t.get("instrucciones_detalladas", "")) > 120 else ""),
                "responsable": resp,
                "estado": estado,
                "ultima_ejecucion": ult_ejec,
                "proxima_ejecucion": t.get("proxima_ejecucion") or t.get("proxima_verificacion") or "",
                "tiempo_restante": t.get("tiempo_restante") or "",
            }

            if freq == "semanal" or "scout" in id_tarea.lower():
                item["dias_programados"] = t.get("dias_programados_nombres", ["Lunes", "Jueves"])
                item["estado_hoy"] = t.get("estado_hoy") or ""
                semanales.append(item)
            elif freq == "mensual" or "mant" in id_tarea.lower():
                mensuales.append(item)
            else:
                diarias.append(item)

        payload = {
            "ultima_actualizacion": ahora.isoformat()[:19],
            "diarias": diarias,
            "semanales": semanales,
            "mensuales": mensuales,
        }
        _DASHBOARD_TAREAS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[Tareas Programadas] Advertencia actualizando dashboard/tareas_programadas.json: {e}")


def _normalizar_responsable(nombre: str) -> str:
    n = (nombre or "").strip().lower()
    if any(k in n for k in ["orquestador", "luffy", "agente_orquestador", "scout"]):
        return "Agente_Orquestador"
    if any(k in n for k in ["asistencia", "sanji", "correo", "gmail", "calendar", "ofimatica"]):
        return "Subagente_Asistencia"
    if any(k in n for k in ["diseno", "diseño", "nami", "video", "arte", "imagen", "redes"]):
        return "Subagente_Diseno"
    if any(k in n for k in ["ciberseguridad", "seguridad", "robin", "auditoria", "sast"]):
        return "Subagente_Ciberseguridad"
    if any(k in n for k in ["desarrollo", "zoro", "codigo", "sql", "bd", "base de datos", "n8n", "web"]):
        return "Subagente_Desarrollo"
    return "Subagente_Desarrollo"


DIAS_SEMANA_MAP = {
    "lunes": 0, "lun": 0, "mon": 0, "monday": 0,
    "martes": 1, "mar": 1, "tue": 1, "tuesday": 1,
    "miercoles": 2, "miércoles": 2, "mie": 2, "wed": 2, "wednesday": 2,
    "jueves": 3, "jue": 3, "thu": 3, "thursday": 3,
    "viernes": 4, "vie": 4, "fri": 4, "friday": 4,
    "sabado": 5, "sábado": 5, "sab": 5, "sat": 5, "saturday": 5,
    "domingo": 6, "dom": 6, "sun": 6, "sunday": 6,
}
NOMBRES_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _parsear_dias_semana(texto_frecuencia: str) -> list[int]:
    """Extrae los días de la semana de un texto como 'Semanal (Lun y Jue 09:00)'."""
    if not texto_frecuencia:
        return []
    texto = texto_frecuencia.lower()
    if "diaria" in texto and not any(d in texto for d in ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]):
        return []
    if "mensual" in texto and not any(d in texto for d in ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]):
        return []

    dias = set()
    for token, num in DIAS_SEMANA_MAP.items():
        if re.search(r"\b" + re.escape(token) + r"\b", texto):
            dias.add(num)
        elif len(token) >= 4 and token in texto:
            dias.add(num)
    return sorted(list(dias))


def _formatear_tiempo_restante(segundos: int) -> str:
    """Formatea segundos en una cadena legible como '2 días y 15 horas'."""
    segundos = max(0, int(segundos))
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    minutos = (segundos % 3600) // 60
    if dias > 0:
        return f"{dias} día{'s' if dias > 1 else ''} y {horas} hora{'s' if horas != 1 else ''}"
    if horas > 0:
        return f"{horas} hora{'s' if horas != 1 else ''} y {minutos} min"
    return f"{minutos} min"


def _calcular_proxima_ejecucion_semanal(
    ahora: datetime,
    dias_semana: list[int],
    hora_ejecucion: str = "09:00",
    ultima_ejecucion: Optional[datetime] = None,
) -> tuple[datetime, str, str]:
    """
    Calcula con precisión:
    1. Próxima fecha y hora (datetime).
    2. Nombre del próximo día programado.
    3. Tiempo restante legible (ej: '2 días y 15 horas').
    """
    try:
        partes = hora_ejecucion.strip().split(":")
        hh, mm = int(partes[0]), int(partes[1])
    except Exception:
        hh, mm = 9, 0

    hoy_ejecutado = False
    if ultima_ejecucion:
        hoy_ejecutado = (ultima_ejecucion.date() == ahora.date())

    candidatos = []
    for delta in range(0, 14):
        f = (ahora + timedelta(days=delta)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if f.weekday() in dias_semana:
            if delta == 0:
                if not hoy_ejecutado and f > ahora:
                    candidatos.append(f)
            else:
                candidatos.append(f)

    prox = candidatos[0] if candidatos else (ahora + timedelta(days=7)).replace(hour=hh, minute=mm, second=0, microsecond=0)
    nombre_dia = NOMBRES_DIAS_ES[prox.weekday()]
    diff = prox - ahora
    tiempo_restante_str = _formatear_tiempo_restante(diff.total_seconds())

    return prox, nombre_dia, tiempo_restante_str


def _calcular_proxima_verificacion(
    tipo_activacion: str,
    intervalo_segundos_sensor: int = 30,
    hora_ejecucion: str = "09:00",
    frecuencia_reloj: str = "diaria",
    dias_programados: Optional[list[int]] = None,
    ultima_ejecucion: Optional[datetime] = None,
    desde: Optional[datetime] = None,
) -> str:
    """
    Calcula cuándo debe volver a evaluarse el gatillo (en 0 tokens) o el reloj programado.
    Soporta con precisión tareas diarias, semanales (con días específicos) y sensores por evento.
    """
    ahora = desde or datetime.now()
    ta = (tipo_activacion or "gatillo_script_python").strip().lower()

    if ta != "reloj_programado" and frecuencia_reloj.strip().lower() != "semanal":
        segs = max(10, int(intervalo_segundos_sensor or 30))
        return (ahora + timedelta(seconds=segs)).isoformat()[:19]

    if frecuencia_reloj.strip().lower() == "semanal" or dias_programados:
        dias = dias_programados or [0, 3]
        prox_dt, _, _ = _calcular_proxima_ejecucion_semanal(
            ahora=ahora,
            dias_semana=dias,
            hora_ejecucion=hora_ejecucion,
            ultima_ejecucion=ultima_ejecucion,
        )
        return prox_dt.isoformat()[:19]

    try:
        partes = hora_ejecucion.strip().split(":")
        hh, mm = int(partes[0]), int(partes[1])
    except Exception:
        hh, mm = 9, 0

    candidato = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if candidato <= ahora:
        candidato += timedelta(days=1)
    return candidato.isoformat()[:19]


# ══════════════════════════════════════════════════════════════════════════════
# EVALUADORES DE GATILLOS ZERO-TOKEN (CÓDIGO PYTHON PURO — 0 LLAMADAS AL LLM)
# ══════════════════════════════════════════════════════════════════════════════

def _decodificar_cabecera_mime(valor: str) -> str:
    if not valor:
        return ""
    partes = decode_header(valor)
    resultado = []
    for texto, charset in partes:
        if isinstance(texto, bytes):
            resultado.append(texto.decode(charset or "utf-8", errors="replace"))
        else:
            resultado.append(str(texto))
    return "".join(resultado)


def _sensor_correo_entrante_zero_token(tarea: dict) -> tuple[bool, str]:
    """
    Vigía de correo en Python puro (0 tokens de IA).
    Revisa vía IMAP o Gmail API si existen correos NO LEÍDOS cuyo ID no haya sido procesado aún.
    - Si NO hay correos nuevos: retorna (False, "") -> NO se despierta a ningún agente, 0 tokens.
    - Si SÍ entró correo nuevo: extrae remitente, asunto y resumen en Python puro, guarda el UID
      en estado_sensor y retorna (True, payload) para que el Subagente_Asistencia se despierte
      ÚNICAMENTE con los correos nuevos ya listos para catalogar.
    """
    estado_sensor = tarea.setdefault("estado_sensor", {})
    ids_vistos = set(estado_sensor.get("ultimos_ids_procesados", []))
    config = tarea.get("config_gatillo", {}) or {}

    imap_host = config.get("imap_host") or os.getenv("IMAP_HOST") or "imap.gmail.com"
    imap_user = config.get("imap_user") or os.getenv("IMAP_USER") or os.getenv("GMAIL_USER") or os.getenv("EMAIL_USER")
    imap_pass = (
        config.get("imap_password")
        or os.getenv("IMAP_PASSWORD")
        or os.getenv("GMAIL_APP_PASSWORD")
        or os.getenv("EMAIL_PASSWORD")
    )

    if not imap_user or not imap_pass:
        # Si no hay credenciales IMAP en .env, verificar si existe un buzón local / cola JSON de webhooks de correo
        buzon_local = _DATA_DIR / "cola_correos_entrantes.json"
        if buzon_local.exists():
            try:
                items = json.loads(buzon_local.read_text(encoding="utf-8"))
                nuevos = [m for m in items if str(m.get("id")) not in ids_vistos]
                if not nuevos:
                    return False, ""
                for m in nuevos:
                    ids_vistos.add(str(m.get("id")))
                estado_sensor["ultimos_ids_procesados"] = list(ids_vistos)[-500:]
                return True, json.dumps(nuevos, ensure_ascii=False)
            except Exception:
                return False, ""
        return False, ""

    try:
        mail = imaplib.IMAP4_SSL(imap_host, timeout=15)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX", readonly=True)
        status, response = mail.uid("search", None, "UNSEEN")
        if status != "OK" or not response or not response[0]:
            mail.logout()
            return False, ""

        uids_actuales = [u.decode("utf-8") for u in response[0].split()]
        uids_nuevos = [u for u in uids_actuales if u not in ids_vistos]

        if not uids_nuevos:
            mail.logout()
            return False, ""

        correos_extraidos = []
        for uid in uids_nuevos[:10]:
            st, msg_data = mail.uid("fetch", uid, "(RFC822)")
            if st == "OK" and msg_data and msg_data[0]:
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                asunto = _decodificar_cabecera_mime(msg.get("Subject", "(Sin asunto)"))
                remitente = _decodificar_cabecera_mime(msg.get("From", "(Desconocido)"))
                fecha_msg = msg.get("Date", "")
                cuerpo = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                            payload = part.get_payload(decode=True)
                            if payload:
                                cuerpo = payload.decode(part.get_content_charset() or "utf-8", errors="replace")[:1500]
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        cuerpo = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")[:1500]

                correos_extraidos.append({
                    "uid": uid,
                    "de": remitente,
                    "asunto": asunto,
                    "fecha": fecha_msg,
                    "extracto_cuerpo": cuerpo.strip(),
                })
            ids_vistos.add(uid)

        mail.logout()
        estado_sensor["ultimos_ids_procesados"] = list(ids_vistos)[-500:]
        if not correos_extraidos:
            return False, ""
        return True, json.dumps(correos_extraidos, ensure_ascii=False)
    except Exception:
        return False, ""


def _sensor_sql_sqlite_zero_token(tarea: dict) -> tuple[bool, str]:
    """
    Vigía de Base de Datos SQLite en Python puro (0 tokens de IA).
    Ejecuta una consulta SQL de condición (ej: SELECT id, nombre, stock FROM productos WHERE stock < 10).
    - Si la consulta devuelve 0 filas: retorna (False, "") -> 0 tokens consumidos.
    - Si devuelve filas que cumplen la condición de alerta y han cambiado respecto al último disparo:
      retorna (True, json_filas) para despertar al agente responsable.
    """
    config = tarea.get("config_gatillo", {}) or {}
    ruta_bd = config.get("ruta_bd", "")
    consulta_sql = config.get("consulta_sql", "")
    if not ruta_bd or not consulta_sql:
        return False, ""

    db_path = Path(ruta_bd) if Path(ruta_bd).is_absolute() else (_APP_ROOT / ruta_bd)
    if not db_path.exists():
        return False, ""

    try:
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(consulta_sql)
        filas = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not filas:
            # Limpiar firma previa si la condición dejó de cumplirse
            tarea.setdefault("estado_sensor", {})["ultima_firma_alerta"] = ""
            return False, ""

        firma_actual = json.dumps(filas, sort_keys=True, ensure_ascii=False)
        estado_sensor = tarea.setdefault("estado_sensor", {})
        if estado_sensor.get("ultima_firma_alerta") == firma_actual:
            # Evitar disparar repetidamente por exactamente el mismo estado sin cambios
            return False, ""

        estado_sensor["ultima_firma_alerta"] = firma_actual
        return True, firma_actual
    except Exception:
        return False, ""


def _sensor_directorio_zero_token(tarea: dict) -> tuple[bool, str]:
    """
    Vigía de carpeta/archivos en Python puro (0 tokens de IA).
    Detecta archivos nuevos o modificados en una carpeta vigilada.
    """
    config = tarea.get("config_gatillo", {}) or {}
    ruta_dir = config.get("ruta_vigilada", "")
    if not ruta_dir:
        return False, ""

    dir_path = Path(ruta_dir) if Path(ruta_dir).is_absolute() else (_APP_ROOT / ruta_dir)
    if not dir_path.exists() or not dir_path.is_dir():
        return False, ""

    estado_sensor = tarea.setdefault("estado_sensor", {})
    mapa_previo = estado_sensor.get("archivos_vistos", {})
    mapa_actual = {}
    archivos_evento = []

    for f in dir_path.iterdir():
        if f.is_file():
            mtime = f.stat().st_mtime
            mapa_actual[f.name] = mtime
            if f.name not in mapa_previo or mapa_previo[f.name] < mtime:
                archivos_evento.append(f.name)

    estado_sensor["archivos_vistos"] = mapa_actual
    if not archivos_evento:
        return False, ""
    return True, json.dumps({"archivos_nuevos_o_modificados": archivos_evento}, ensure_ascii=False)


def _sensor_script_python_personalizado(tarea: dict) -> tuple[bool, str]:
    """
    Ejecuta un script sensor ligero en Python puro (.py) hecho a medida para cualquier tarea
    personalizada del usuario (APIs externas, PostgreSQL/MySQL, webhooks, scraping ligero, etc.).
    Costo de IA mientras evalúa: 0 TOKENS.
    El script debe imprimir en stdout un JSON con formato:
      {"disparar": true, "datos_evento": "..."}  o  {"disparar": false}
    """
    config = tarea.get("config_gatillo", {}) or {}
    ruta_script = config.get("ruta_script_sensor", "")
    if not ruta_script:
        return False, ""

    script_path = Path(ruta_script) if Path(ruta_script).is_absolute() else (_APP_ROOT / ruta_script)
    if not script_path.exists():
        return False, ""

    try:
        res = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(_APP_ROOT),
        )
        salida = (res.stdout or "").strip()
        if not salida:
            return (res.returncode == 10), "Gatillo activado por código de salida 10"

        # Buscar la última línea JSON válida en stdout
        for linea in reversed(salida.splitlines()):
            linea = linea.strip()
            if linea.startswith("{") and linea.endswith("}"):
                obj = json.loads(linea)
                if bool(obj.get("disparar", False)):
                    datos = obj.get("datos_evento", "")
                    if isinstance(datos, (dict, list)):
                        datos = json.dumps(datos, ensure_ascii=False)
                    return True, str(datos)
                return False, ""
        return False, ""
    except Exception:
        return False, ""


def _evaluar_gatillo_zero_token(tarea: dict) -> tuple[bool, str]:
    """
    Despachador central de gatillos en Python puro (0 tokens LLM).
    Retorna (debe_disparar_agente_ia: bool, datos_del_evento: str).
    """
    tipo = (tarea.get("tipo_activacion") or "reloj_programado").strip().lower()
    if tipo == "gatillo_correo":
        return _sensor_correo_entrante_zero_token(tarea)
    if tipo == "gatillo_sql":
        return _sensor_sql_sqlite_zero_token(tarea)
    if tipo == "gatillo_archivo":
        return _sensor_directorio_zero_token(tarea)
    if tipo == "gatillo_script_python":
        # Si tiene script configurado, evaluarlo
        cfg = tarea.get("config_gatillo", {}) or {}
        if cfg.get("ruta_script_sensor"):
            return _sensor_script_python_personalizado(tarea)

    # Evaluación de Tarea por Reloj Programado (Semanal / Diaria)
    ahora = datetime.now()
    frecuencia = (tarea.get("frecuencia_reloj") or "diaria").strip().lower()
    dias_prog = tarea.get("dias_programados")
    hora_str = tarea.get("hora_ejecucion", "09:00")

    try:
        hh, mm = map(int, hora_str.split(":"))
    except Exception:
        hh, mm = 9, 0

    # Verificar si ya se ejecutó hoy (Anti-Duplicado diario estricto)
    ult_str = tarea.get("ultima_ejecucion")
    ult_dt = None
    if ult_str:
        try:
            ult_dt = datetime.fromisoformat(ult_str[:19].replace(" ", "T"))
        except Exception:
            ult_dt = None

    ya_ejecutada_hoy = (ult_dt is not None and ult_dt.date() == ahora.date())

    if frecuencia == "semanal" or dias_prog:
        dias = dias_prog or [0, 3]  # Por defecto lunes y jueves
        dia_actual_num = ahora.weekday()

        if dia_actual_num not in dias:
            _, prox_dia, tiempo_rest = _calcular_proxima_ejecucion_semanal(
                ahora=ahora,
                dias_semana=dias,
                hora_ejecucion=hora_str,
                ultima_ejecucion=ult_dt,
            )
            return False, f"Hoy no corresponde ejecución. Próximo día: {prox_dia} a las {hora_str} (faltan {tiempo_rest})."

        if ya_ejecutada_hoy:
            _, prox_dia, tiempo_rest = _calcular_proxima_ejecucion_semanal(
                ahora=ahora,
                dias_semana=dias,
                hora_ejecucion=hora_str,
                ultima_ejecucion=ult_dt,
            )
            return False, f"Ya ejecutada en la sesión de hoy. Próxima ejecución: {prox_dia} a las {hora_str} (faltan {tiempo_rest})."

        # Es hoy y no se ha ejecutado hoy: verificar hora
        if ahora.time() < datetime.min.time().replace(hour=hh, minute=mm):
            return False, f"Hoy es día programado ({NOMBRES_DIAS_ES[dia_actual_num]}), esperando la hora: {hora_str}."

        return True, f"Ejecución semanal programada para {NOMBRES_DIAS_ES[dia_actual_num]} a las {hora_str}."

    # Diaria estándar
    if ya_ejecutada_hoy:
        return False, "Ya ejecutada hoy."

    if ahora.time() < datetime.min.time().replace(hour=hh, minute=mm):
        return False, f"Esperando hora programada: {hora_str}."

    return True, f"Ejecución diaria programada a las {hora_str}."


def obtener_prompt_tareas_programadas() -> str:
    """
    System Prompt especializado y encapsulado para la gestión de Tareas Repetitivas,
    Gatillos por Evento Zero-Token y Cron Generativo.
    """
    return """[⚡ DIRECTIVA DE GATILLOS ZERO-TOKEN, MONITOREO POR EVENTOS Y TAREAS REPETITIVAS]
Eres el Director de Automatización Eficiente de la flota.
REGLA CRÍTICA DE EFICIENCIA DE TOKENS (PROHIBIDO EL POLLING CON LLM):
- JAMÁS debes programar que un subagente LLM se despierte cada X minutos solo para revisar si entró un correo, si cambió una base de datos o si ocurrió un evento. Eso desperdiciaría miles de tokens en vacío.
- En su lugar, TODA tarea reactiva o de monitoreo debe usar un **GATILLO / SENSOR ZERO-TOKEN EN PYTHON PURO**: el demonio vigila el evento en código Python puro (gastando 0 tokens de IA) y **ÚNICAMENTE despierta al subagente en `Bitacora.md` cuando el evento realmente ocurre**, pasándole ya los datos del evento.

CÓMO ORQUESTAR CUALQUIER TAREA REPETITIVA SEGÚN SU NATURALEZA:

1. TAREAS POR EVENTO O MONITOREO DE CONDICIÓN (0 Tokens en espera):
   - **Caso Correo Nuevo (`tipo_activacion='gatillo_correo'`)**:
     El sensor ligero IMAP/buzón vigila en Python puro (0 tokens). Solo cuando entra un correo nuevo no leído, extrae remitente/asunto/cuerpo y despierta a `Subagente_Asistencia` para catalogarlo según las categorías del usuario.
   - **Caso Base de Datos SQLite (`tipo_activacion='gatillo_sql'`)**:
     El sensor ligero ejecuta la consulta SQL (ej. `SELECT * FROM productos WHERE stock < 10`) en Python puro (0 tokens). Mientras no haya filas en alerta, ningún agente se despierta. Solo cuando la consulta devuelve productos bajo el umbral, despierta al agente responsable o emite la alerta.
   - **Caso Vigilancia de Carpeta/Archivos (`tipo_activacion='gatillo_archivo'`)**:
     Vigila en Python puro (0 tokens) si entran archivos nuevos a una carpeta antes de despertar al agente.
   - **Caso Cualquier Otra Tarea / API / BD Externa / Webhook (`tipo_activacion='gatillo_script_python'`)**:
     Como las tareas de cada usuario pueden variar enormemente, primero usa `tool_crear_gatillo_sensor_python(...)` (o delega a `Subagente_Desarrollo`) para crear un micro-script sensor en Python (`Agente_Orquestador/data/sensores/sensor_<nombre>.py`) que verifique la condición sin usar IA e imprima `{"disparar": true/false, "datos_evento": "..."}`. Luego registra la tarea con `tool_programar_tarea_repetitiva(..., tipo_activacion='gatillo_script_python')`.

2. TAREAS GENERATIVAS POR HORARIO FIJO (`tipo_activacion='reloj_programado'`):
   - Para tareas donde sí hay que producir contenido nuevo en un horario (ej. "generar y subir un video diario para redes sociales a las 09:00").
   - El reloj espera en 0 tokens hasta la hora exacta (`hora_ejecucion='09:00'`, `frecuencia_reloj='diaria'`) y en ese momento despierta a `Subagente_Diseno` (y su `pipeline_secundario` si aplica).
"""


def _inyectar_ticket_en_bitacora(tarea: dict, datos_evento: str = "") -> str:
    """
    Inyecta en Bitacora.md el ticket correspondiente SOLO cuando el gatillo se activó
    o llegó la hora del reloj programado, adjuntando los datos del evento capturado.
    """
    ciclo_num = int(tarea.get("ciclos_completados", 0)) + 1
    id_base = tarea.get("id_tarea", "REC-001")
    ticket_id = f"TKT-{id_base}-C{ciclo_num:03d}"
    responsable = tarea.get("responsable_principal", "Subagente_Asistencia")
    pipeline_sec = tarea.get("pipeline_secundario", "")
    condicion_notif = tarea.get("condicion_notificacion", "siempre")
    evidencia_esp = tarea.get("evidencia_esperada", "")
    tipo_act = tarea.get("tipo_activacion", "reloj_programado")
    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    nota_pipeline = ""
    if pipeline_sec:
        nota_pipeline = (
            f" | [PIPELINE MULTI-AGENTE]: Al finalizar tu parte, el Orquestador delegará la siguiente etapa a: {pipeline_sec}."
        )

    nota_evento = ""
    if datos_evento and datos_evento != "Ejecución programada por horario (Cron).":
        nota_evento = f"\n  - **Datos_Evento_Capturado_Por_Gatillo:** `{datos_evento[:1800]}`"

    bloque_ticket = (
        f"\n\n## {ticket_id}\n"
        f"- **Tarea:** [EVENTO DISPARADO #{ciclo_num} - {tarea.get('nombre')}] {tarea.get('instrucciones_detalladas')}{nota_evento}\n"
        f"- **Responsable:** {responsable}\n"
        f"- **Estado:** PENDIENTE\n"
        f"- **Evidencia_Fisica:** {evidencia_esp}\n"
        f"- **Contexto:** Disparo por `{tipo_act}` (Zero-Token Trigger). Notificación: {condicion_notif}.{nota_pipeline}\n"
        f"- **Historial:**\n"
        f"  - [Gatillo_Orquestador - {ahora_str}]: Gatillo `{tipo_act}` activado con evento real. Ticket asignado a {responsable}.\n"
    )

    texto_actual = ""
    if _BITACORA_FILE.exists():
        texto_actual = _BITACORA_FILE.read_text(encoding="utf-8")
    else:
        texto_actual = "# 📓 Pizarra (Tablero de Tareas)\n\n"

    marca_conexiones = "\n---\n**Conexiones:** [[Cerebro]] [[Reglas de la Tripulacion]]"
    if "**Conexiones:**" in texto_actual:
        texto_sin_pie = re.sub(r"\n*---\n\*\*Conexiones:\*\*.*$", "", texto_actual, flags=re.DOTALL).rstrip()
        nuevo_texto = f"{texto_sin_pie}{bloque_ticket}\n{marca_conexiones}\n"
    else:
        nuevo_texto = f"{texto_actual.rstrip()}{bloque_ticket}\n{marca_conexiones}\n"

    _BITACORA_FILE.write_text(nuevo_texto, encoding="utf-8")
    return ticket_id


@tool
def tool_crear_gatillo_sensor_python(
    nombre_sensor: str,
    codigo_python_sensor: str,
    descripcion: str = "",
) -> str:
    """
    Crea un script sensor ligero en Python puro (`Agente_Orquestador/data/sensores/sensor_<nombre>.py`)
    que se ejecutará con CERO CONSUMO DE TOKENS LLM para vigilar cualquier condición, API, correo,
    base de datos o evento personalizado solicitado por el usuario.

    REGLA DEL SCRIPT SENSOR:
    El código Python proporcionado debe evaluar la condición sin usar LLMs e imprimir en stdout
    una línea JSON:
      `print(json.dumps({"disparar": True, "datos_evento": {...}}))` cuando ocurra el evento, o
      `print(json.dumps({"disparar": False}))` cuando no haya novedades (0 tokens).

    Args:
        nombre_sensor: Identificador corto del sensor (ej: 'stock_bajo', 'nuevos_pedidos_api', 'correo_imap').
        codigo_python_sensor: Código Python completo y autónomo del sensor.
        descripcion: Qué condición o evento vigila este sensor.
    """
    try:
        _SENSORES_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9_]+", "_", nombre_sensor.lower()).strip("_") or "personalizado"
        ruta_sensor = _SENSORES_DIR / f"sensor_{slug}.py"
        ruta_sensor.write_text(codigo_python_sensor.strip() + "\n", encoding="utf-8")
        ruta_rel = f"Agente_Orquestador/data/sensores/sensor_{slug}.py"
        return json.dumps(
            {
                "status": "success",
                "mensaje": f"Gatillo sensor Zero-Token creado exitosamente en '{ruta_rel}'.",
                "ruta_script_sensor": ruta_rel,
                "descripcion": descripcion,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al crear sensor Python: {e}"}, ensure_ascii=False)


@tool
def tool_programar_tarea_repetitiva(
    nombre_tarea: str,
    responsable_principal: str,
    instrucciones_detalladas: str,
    tipo_activacion: str = "gatillo_script_python",
    intervalo_segundos_sensor: int = 30,
    hora_ejecucion: str = "09:00",
    frecuencia_reloj: str = "diaria",
    ruta_script_sensor: str = "",
    ruta_bd: str = "",
    consulta_sql: str = "",
    ruta_vigilada: str = "",
    condicion_notificacion: str = "siempre",
    pipeline_secundario: str = "",
    disparar_inmediatamente: bool = False,
) -> str:
    """
    Registra una tarea repetitiva o reactiva en la flota usando Gatillos Zero-Token (0 consumo LLM
    en espera) o Reloj Programado (Cron).

    Tipos de activación (`tipo_activacion`):
      - 'gatillo_correo'        : Vigila en Python puro (0 tokens) la entrada de correos nuevos (IMAP/buzón) y SOLO despierta al agente cuando llega un correo no leído, pasándole remitente, asunto y cuerpo.
      - 'gatillo_sql'           : Ejecuta en Python puro (0 tokens) la `consulta_sql` sobre `ruta_bd` y SOLO despierta al agente cuando la consulta devuelve filas en alerta (ej. `SELECT * FROM productos WHERE stock < 10`).
      - 'gatillo_archivo'       : Vigila en Python puro (0 tokens) `ruta_vigilada` y SOLO despierta al agente cuando entra un archivo nuevo o modificado.
      - 'gatillo_script_python' : Ejecuta en Python puro (0 tokens) el script `ruta_script_sensor` creado a medida para la tarea del usuario y SOLO despierta al agente cuando el script devuelve `{"disparar": true}`.
      - 'reloj_programado'      : Para tareas generativas por horario fijo (ej. generar y subir video diario a las '09:00'). Espera con 0 tokens hasta la `hora_ejecucion` (`frecuencia_reloj`: 'diaria' o 'semanal').

    Args:
        nombre_tarea: Nombre identificativo de la tarea.
        responsable_principal: Subagente que ejecutará la acción cuando el gatillo se active ('Subagente_Asistencia', 'Subagente_Diseno', 'Subagente_Desarrollo', 'Subagente_Ciberseguridad').
        instrucciones_detalladas: Qué debe hacer el subagente con los datos del evento o entrega.
        tipo_activacion: 'gatillo_correo', 'gatillo_sql', 'gatillo_archivo', 'gatillo_script_python', o 'reloj_programado'.
        intervalo_segundos_sensor: Cada cuántos segundos evalúa el sensor ligero en Python puro (0 tokens LLM). Por defecto 30s.
        hora_ejecucion: Hora 'HH:MM' si `tipo_activacion` es 'reloj_programado'.
        frecuencia_reloj: 'diaria' o 'semanal' (solo para 'reloj_programado').
        ruta_script_sensor: Ruta al script `.py` si `tipo_activacion='gatillo_script_python'`.
        ruta_bd: Ruta a la base de datos SQLite si `tipo_activacion='gatillo_sql'`.
        consulta_sql: Query SQL que filtra la condición de disparo (ej. `SELECT * FROM productos WHERE stock < 10`).
        ruta_vigilada: Carpeta a monitorear si `tipo_activacion='gatillo_archivo'`.
        condicion_notificacion: 'siempre' o condición específica para notificar por Telegram.
        pipeline_secundario: Si otro subagente debe intervenir en cadena tras el primero.
        disparar_inmediatamente: Si es True, fuerza un primer disparo inmediato en Bitacora.md además de dejar activo el gatillo.
    """
    try:
        data = _asegurar_archivo_tareas()
        tareas = data.get("tareas", [])

        resp_canonico = _normalizar_responsable(responsable_principal)
        slug = re.sub(r"[^A-Z0-9]+", "", nombre_tarea.upper())[:10] or "TAREA"
        id_tarea = f"REC-{slug}-{len(tareas) + 1:03d}"

        carpeta_base = _MAPA_CARPETAS_SALIDA.get(resp_canonico, "Archivos_temporales")
        nombre_archivo_ev = re.sub(r"[^a-z0-9_]+", "_", nombre_tarea.lower()).strip("_")[:35]
        evidencia_esperada = f"{carpeta_base}/reporte_{nombre_archivo_ev}.md"

        ahora = datetime.now()
        proxima = _calcular_proxima_verificacion(
            tipo_activacion=tipo_activacion,
            intervalo_segundos_sensor=intervalo_segundos_sensor,
            hora_ejecucion=hora_ejecucion,
            frecuencia_reloj=frecuencia_reloj,
            desde=ahora,
        )

        nueva_tarea = {
            "id_tarea": id_tarea,
            "nombre": nombre_tarea.strip(),
            "responsable_principal": resp_canonico,
            "pipeline_secundario": pipeline_secundario.strip(),
            "instrucciones_detalladas": instrucciones_detalladas.strip(),
            "tipo_activacion": tipo_activacion.strip().lower(),
            "intervalo_segundos_sensor": int(intervalo_segundos_sensor or 30),
            "hora_ejecucion": hora_ejecucion.strip(),
            "frecuencia_reloj": frecuencia_reloj.strip().lower(),
            "config_gatillo": {
                "ruta_script_sensor": ruta_script_sensor.strip(),
                "ruta_bd": ruta_bd.strip(),
                "consulta_sql": consulta_sql.strip(),
                "ruta_vigilada": ruta_vigilada.strip(),
            },
            "estado_sensor": {},
            "condicion_notificacion": condicion_notificacion.strip(),
            "evidencia_esperada": evidencia_esperada,
            "estado": "ACTIVA",
            "fecha_creacion": ahora.isoformat()[:19],
            "ultima_ejecucion": None,
            "proxima_verificacion": proxima,
            "ciclos_completados": 0,
        }

        ticket_inicial = None
        if disparar_inmediatamente:
            ticket_inicial = _inyectar_ticket_en_bitacora(nueva_tarea, datos_evento="Disparo inicial solicitado al crear la tarea.")
            nueva_tarea["ciclos_completados"] = 1
            nueva_tarea["ultima_ejecucion"] = ahora.isoformat()[:19]
            nueva_tarea["ultimo_ticket_id"] = ticket_inicial

        tareas.append(nueva_tarea)
        data["tareas"] = tareas
        _guardar_archivo_tareas(data)

        return json.dumps(
            {
                "status": "success",
                "mensaje": (
                    f"Tarea '{nombre_tarea}' ({id_tarea}) registrada en modo '{tipo_activacion}' (0 tokens en espera) "
                    f"asignada a {resp_canonico}. "
                    + (f"Ticket inicial creado: {ticket_inicial}. " if ticket_inicial else "Esperando activación del gatillo sin consumir tokens LLM. ")
                    + f"Próxima verificación del sensor: {proxima}."
                ),
                "tarea": nueva_tarea,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al programar tarea repetitiva: {e}"}, ensure_ascii=False)


@tool
def tool_listar_tareas_repetitivas() -> str:
    """
    Lista todas las tareas repetitivas, gatillos Zero-Token y relojes programados activos en el sistema.
    Calcula dinámicamente el tiempo restante, la próxima ejecución y el estado de cada tarea
    para que la tripulación tenga visibilidad completa y precisa en tiempo real.
    """
    try:
        data = _asegurar_archivo_tareas()
        tareas = data.get("tareas", [])
        ahora = datetime.now()

        for t in tareas:
            freq = (t.get("frecuencia_reloj") or "diaria").lower()
            dias_prog = t.get("dias_programados")
            ult_str = t.get("ultima_ejecucion")
            ult_dt = None
            if ult_str:
                try:
                    ult_dt = datetime.fromisoformat(ult_str[:19].replace(" ", "T"))
                except Exception:
                    ult_dt = None

            if freq == "semanal" or dias_prog or "scout" in t.get("id_tarea", "").lower():
                dias = dias_prog or [0, 3]
                hora_str = t.get("hora_ejecucion", "09:00")
                prox_dt, nom_dia, rest_str = _calcular_proxima_ejecucion_semanal(
                    ahora=ahora,
                    dias_semana=dias,
                    hora_ejecucion=hora_str,
                    ultima_ejecucion=ult_dt,
                )
                t["proxima_ejecucion"] = prox_dt.isoformat()[:19]
                t["proxima_verificacion"] = prox_dt.isoformat()[:19]
                t["nombre_proximo_dia"] = nom_dia
                t["tiempo_restante"] = rest_str
                hoy_ejec = (ult_dt is not None and ult_dt.date() == ahora.date())
                dia_actual_num = ahora.weekday()
                if dia_actual_num in dias and hoy_ejec:
                    t["estado_hoy"] = f"Ejecutada hoy {NOMBRES_DIAS_ES[dia_actual_num]}. Próxima ejecución: {nom_dia} {prox_dt.strftime('%d/%m')} a las {hora_str} (faltan {rest_str}). Modo Zero-Token Idle."
                elif dia_actual_num in dias and not hoy_ejec:
                    t["estado_hoy"] = f"Corresponde hoy {NOMBRES_DIAS_ES[dia_actual_num]} a las {hora_str}."
                else:
                    t["estado_hoy"] = f"Hoy ({NOMBRES_DIAS_ES[dia_actual_num]}) no corresponde. Próxima ejecución: {nom_dia} {prox_dt.strftime('%d/%m')} a las {hora_str} (faltan {rest_str}). Modo Zero-Token Idle."

        return json.dumps(
            {
                "status": "success",
                "total_tareas": len(tareas),
                "tareas": tareas,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_modificar_estado_tarea_repetitiva(id_tarea: str, accion: str) -> str:
    """
    Modifica el estado de una tarea repetitiva o gatillo existente.

    Args:
        id_tarea: ID de la tarea (ej: 'REC-CORREOS-001').
        accion: 'pausar', 'reanudar', 'eliminar', o 'disparar_ahora'.
    """
    try:
        data = _asegurar_archivo_tareas()
        tareas = data.get("tareas", [])
        acc = accion.strip().lower()

        for t in tareas:
            if t.get("id_tarea", "").upper() == id_tarea.strip().upper():
                if acc == "pausar":
                    t["estado"] = "PAUSADA"
                    _guardar_archivo_tareas(data)
                    return json.dumps({"status": "success", "mensaje": f"Tarea/gatillo {id_tarea} PAUSADA."}, ensure_ascii=False)
                elif acc == "reanudar":
                    t["estado"] = "ACTIVA"
                    t["proxima_verificacion"] = _calcular_proxima_verificacion(
                        t.get("tipo_activacion", "gatillo_script_python"),
                        t.get("intervalo_segundos_sensor", 30),
                        t.get("hora_ejecucion", "09:00"),
                        t.get("frecuencia_reloj", "diaria"),
                    )
                    _guardar_archivo_tareas(data)
                    return json.dumps(
                        {"status": "success", "mensaje": f"Tarea/gatillo {id_tarea} REANUDADA."},
                        ensure_ascii=False,
                    )
                elif acc == "eliminar":
                    data["tareas"] = [x for x in tareas if x.get("id_tarea", "").upper() != id_tarea.strip().upper()]
                    _guardar_archivo_tareas(data)
                    return json.dumps({"status": "success", "mensaje": f"Tarea/gatillo {id_tarea} ELIMINADA."}, ensure_ascii=False)
                elif acc in ("disparar_ahora", "ejecutar_ahora"):
                    ticket_id = _inyectar_ticket_en_bitacora(t, datos_evento="Disparo manual forzado por el usuario.")
                    t["ciclos_completados"] = int(t.get("ciclos_completados", 0)) + 1
                    t["ultima_ejecucion"] = datetime.now().isoformat()[:19]
                    t["ultimo_ticket_id"] = ticket_id
                    _guardar_archivo_tareas(data)
                    return json.dumps(
                        {"status": "success", "mensaje": f"Disparo manual inyectado en Bitacora.md ({ticket_id})."},
                        ensure_ascii=False,
                    )
                else:
                    return json.dumps(
                        {"status": "error", "mensaje": f"Acción '{accion}' no válida. Usa: pausar, reanudar, eliminar, disparar_ahora."},
                        ensure_ascii=False,
                    )

        return json.dumps({"status": "error", "mensaje": f"No se encontró ninguna tarea con ID '{id_tarea}'."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


def sincronizar_tareas_desde_bitacora(forzar: bool = False) -> dict:
    """
    Lee la sección '## 🕒 Registro de Tareas Programadas y Rutinas' en `Bitacora.md`
    y sincroniza el estado de las tareas con `tareas_programadas.json` y `dashboard/tareas_programadas.json`.
    Garantiza que la Pizarra (`Bitacora.md`) sea la SSOT visual que el Orquestador
    inspecciona al despertar sin depender exclusivamente de archivos JSON.
    """
    global _ULTIMO_HASH_BITACORA
    if not _BITACORA_FILE.exists():
        return {}

    try:
        contenido = _BITACORA_FILE.read_text(encoding="utf-8")
        if "## 🕒 Registro de Tareas Programadas y Rutinas" not in contenido:
            return {}

        import hashlib
        h_actual = hashlib.md5(contenido.encode("utf-8")).hexdigest()
        if not forzar and h_actual == _ULTIMO_HASH_BITACORA:
            data = _asegurar_archivo_tareas()
            return {t.get("id_tarea"): t for t in data.get("tareas", [])}

        data = _asegurar_archivo_tareas()
        tareas = data.get("tareas", [])
        mapa_tareas = {t.get("id_tarea"): t for t in tareas}

        lineas = contenido.splitlines()
        en_seccion = False
        cambios = False
        ahora = datetime.now()
        cabeceras = []

        for linea in lineas:
            linea_str = linea.strip()
            if "## 🕒 Registro de Tareas Programadas y Rutinas" in linea:
                en_seccion = True
                continue
            if en_seccion and linea_str.startswith("## ") and not linea_str.startswith("## 🕒"):
                break
            if en_seccion and linea_str.startswith("|"):
                if linea_str.startswith("| :---") or linea_str.startswith("|:---"):
                    continue
                partes = [p.strip() for p in linea_str.split("|")[1:-1]]
                if not partes:
                    continue

                # Detectar cabecera
                if any(x.lower() in ("id", "tarea / rutina", "responsable") for x in partes):
                    cabeceras = [p.lower() for p in partes]
                    continue

                raw_id = partes[0].replace("`", "").strip()
                if not raw_id:
                    continue

                col_map = {}
                if cabeceras and len(cabeceras) == len(partes):
                    for idx, h in enumerate(cabeceras):
                        if "id" in h:
                            col_map["id"] = partes[idx].replace("`", "").strip()
                        elif "tarea" in h or "rutina" in h:
                            col_map["nombre"] = partes[idx].replace("**", "").strip()
                        elif "responsable" in h:
                            col_map["responsable"] = partes[idx].replace("`", "").strip()
                        elif "frecuencia" in h:
                            col_map["frecuencia"] = partes[idx].strip()
                        elif "próxima" in h or "proxima" in h:
                            col_map["proxima"] = partes[idx].strip()
                        elif "tipo" in h or "gatillo" in h:
                            col_map["tipo"] = partes[idx].strip()
                        elif "estado" in h:
                            col_map["estado"] = partes[idx].replace("`", "").strip().upper()
                        elif "última" in h or "ultima" in h:
                            col_map["ultima"] = partes[idx].strip()
                else:
                    col_map["id"] = raw_id
                    col_map["nombre"] = partes[1].replace("**", "").strip() if len(partes) > 1 else ""
                    col_map["responsable"] = partes[2].replace("`", "").strip() if len(partes) > 2 else ""
                    col_map["frecuencia"] = partes[3].strip() if len(partes) > 3 else ""
                    if len(partes) >= 8:
                        col_map["proxima"] = partes[4].strip()
                        col_map["tipo"] = partes[5].strip()
                        col_map["estado"] = partes[6].replace("`", "").strip().upper()
                        col_map["ultima"] = partes[7].strip()
                    elif len(partes) >= 7:
                        col_map["tipo"] = partes[4].strip()
                        col_map["estado"] = partes[5].replace("`", "").strip().upper()
                        col_map["ultima"] = partes[6].strip()
                    elif len(partes) >= 6:
                        col_map["tipo"] = partes[4].strip()
                        col_map["estado"] = partes[5].replace("`", "").strip().upper()

                nombre = col_map.get("nombre", raw_id)
                responsable = col_map.get("responsable", "Agente_Orquestador")
                frecuencia = col_map.get("frecuencia", "diaria")
                tipo = col_map.get("tipo", "gatillo_script_python")
                estado = col_map.get("estado", "ACTIVA")
                ult_ejec = col_map.get("ultima", "")

                dias_semana_prog = _parsear_dias_semana(frecuencia)
                es_mensual = ("mensual" in frecuencia.lower()) or ("mant" in raw_id.lower())
                es_semanal = (("semanal" in frecuencia.lower()) or (len(dias_semana_prog) > 0) or ("scout" in raw_id.lower())) and not es_mensual
                if es_semanal and not dias_semana_prog:
                    dias_semana_prog = [0, 3]

                m_hora = re.search(r"(\d{1,2}:\d{2})", frecuencia)
                hora_ejec = m_hora.group(1) if m_hora else "09:00"
                if len(hora_ejec) == 4 and hora_ejec[1] == ':':
                    hora_ejec = f"0{hora_ejec}"

                ult_dt = None
                if ult_ejec:
                    m_ult = re.search(r"(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?)", ult_ejec)
                    if m_ult:
                        try:
                            ult_dt = datetime.fromisoformat(m_ult.group(1).replace(" ", "T"))
                        except Exception:
                            ult_dt = None

                if raw_id in mapa_tareas:
                    t = mapa_tareas[raw_id]
                    if t.get("estado") != estado:
                        t["estado"] = estado
                        cambios = True
                    if es_semanal:
                        if t.get("frecuencia_reloj") != "semanal":
                            t["frecuencia_reloj"] = "semanal"
                            cambios = True
                        if t.get("dias_programados") != dias_semana_prog:
                            t["dias_programados"] = dias_semana_prog
                            cambios = True
                        t["dias_programados_nombres"] = [NOMBRES_DIAS_ES[d] for d in dias_semana_prog]
                        t["hora_ejecucion"] = hora_ejec
                    elif es_mensual:
                        if t.get("frecuencia_reloj") != "mensual":
                            t["frecuencia_reloj"] = "mensual"
                            cambios = True
                        t["dias_programados"] = None
                        t["dias_programados_nombres"] = None
                    else:
                        if t.get("frecuencia_reloj") != "diaria":
                            t["frecuencia_reloj"] = "diaria"
                            cambios = True
                        t["dias_programados"] = None
                        t["dias_programados_nombres"] = None

                    if ult_dt:
                        ult_str_norm = ult_dt.isoformat()[:19]
                        if t.get("ultima_ejecucion") != ult_str_norm:
                            t["ultima_ejecucion"] = ult_str_norm
                            t["ultimo_dia_ejecutado"] = NOMBRES_DIAS_ES[ult_dt.weekday()].lower()
                            cambios = True

                    if raw_id == "REC-SCOUT-001" or "scout" in raw_id.lower():
                        if "Computrabajo" not in t.get("instrucciones_detalladas", ""):
                            t["instrucciones_detalladas"] = PLAYBOOK_REC_SCOUT_001.strip()
                            t["evidencia_esperada"] = "Agente_Orquestador/informes/reporte_scouting_laboral.md"
                            cambios = True

                    if es_semanal:
                        prox_dt, nom_dia, rest_str = _calcular_proxima_ejecucion_semanal(
                            ahora=ahora,
                            dias_semana=dias_semana_prog,
                            hora_ejecucion=hora_ejec,
                            ultima_ejecucion=ult_dt,
                        )
                        prox_iso = prox_dt.isoformat()[:19]
                        if t.get("proxima_ejecucion") != prox_iso:
                            t["proxima_ejecucion"] = prox_iso
                            t["proxima_verificacion"] = prox_iso
                            t["nombre_proximo_dia"] = nom_dia
                            cambios = True
                        if t.get("tiempo_restante") != rest_str:
                            t["tiempo_restante"] = rest_str
                            cambios = True
                        hoy_ejec = (ult_dt is not None and ult_dt.date() == ahora.date())
                        dia_num = ahora.weekday()
                        if dia_num in dias_semana_prog and hoy_ejec:
                            estado_hoy = f"Ya ejecutada hoy ({NOMBRES_DIAS_ES[dia_num]}). Próxima ejecución: {nom_dia} a las {hora_ejec} (faltan {rest_str})."
                        elif dia_num in dias_semana_prog and not hoy_ejec:
                            estado_hoy = f"Corresponde hoy ({NOMBRES_DIAS_ES[dia_num]}) a las {hora_ejec}."
                        else:
                            estado_hoy = f"Hoy no corresponde ({NOMBRES_DIAS_ES[dia_num]}). Próxima ejecución: {nom_dia} a las {hora_ejec} (faltan {rest_str})."
                        if t.get("estado_hoy") != estado_hoy:
                            t["estado_hoy"] = estado_hoy
                            cambios = True
                    elif es_mensual:
                        if t.get("tiempo_restante") != "Primer día del próximo mes" or t.get("estado_hoy") != "Monitoreo mensual activo":
                            t["tiempo_restante"] = "Primer día del próximo mes"
                            t["estado_hoy"] = "Monitoreo mensual activo"
                            cambios = True
                    else:
                        if t.get("tiempo_restante") != "Inmediata / Continuo" or t.get("estado_hoy") != "Monitoreo diario continuo activo":
                            t["tiempo_restante"] = "Inmediata / Continuo"
                            t["estado_hoy"] = "Monitoreo diario continuo activo"
                            cambios = True
                else:
                    nueva = {
                        "id_tarea": raw_id,
                        "nombre": nombre,
                        "responsable_principal": _normalizar_responsable(responsable),
                        "pipeline_secundario": "",
                        "instrucciones_detalladas": PLAYBOOK_REC_SCOUT_001.strip() if (raw_id == "REC-SCOUT-001" or "scout" in raw_id.lower()) else f"Rutina programada desde Bitacora: {nombre}",
                        "tipo_activacion": "reloj_programado" if "reloj" in tipo.lower() else ("gatillo_script_python" if not es_semanal else "reloj_programado"),
                        "intervalo_segundos_sensor": 60,
                        "hora_ejecucion": hora_ejec,
                        "frecuencia_reloj": "semanal" if es_semanal else ("mensual" if "mensual" in frecuencia.lower() else "diaria"),
                        "dias_programados": dias_semana_prog if es_semanal else None,
                        "dias_programados_nombres": [NOMBRES_DIAS_ES[d] for d in dias_semana_prog] if es_semanal else None,
                        "config_gatillo": {},
                        "estado": estado,
                        "fecha_creacion": ahora.isoformat()[:19],
                        "ultima_ejecucion": ult_dt.isoformat()[:19] if ult_dt else None,
                        "ultimo_dia_ejecutado": NOMBRES_DIAS_ES[ult_dt.weekday()].lower() if ult_dt else None,
                        "ciclos_completados": 1 if ult_dt else 0,
                    }
                    if es_semanal:
                        prox_dt, nom_dia, rest_str = _calcular_proxima_ejecucion_semanal(
                            ahora=ahora,
                            dias_semana=dias_semana_prog,
                            hora_ejecucion=hora_ejec,
                            ultima_ejecucion=ult_dt,
                        )
                        nueva["proxima_ejecucion"] = prox_dt.isoformat()[:19]
                        nueva["proxima_verificacion"] = prox_dt.isoformat()[:19]
                        nueva["nombre_proximo_dia"] = nom_dia
                        nueva["tiempo_restante"] = rest_str
                        hoy_ejec = (ult_dt is not None and ult_dt.date() == ahora.date())
                        dia_num = ahora.weekday()
                        if dia_num in dias_semana_prog and hoy_ejec:
                            nueva["estado_hoy"] = f"Ya ejecutada hoy ({NOMBRES_DIAS_ES[dia_num]}). Próxima ejecución: {nom_dia} a las {hora_ejec} (faltan {rest_str})."
                        else:
                            nueva["estado_hoy"] = f"Próxima ejecución: {nom_dia} a las {hora_ejec} (faltan {rest_str})."

                    tareas.append(nueva)
                    mapa_tareas[raw_id] = nueva
                    cambios = True

        _ULTIMO_HASH_BITACORA = h_actual
        if cambios:
            data["tareas"] = tareas
            _guardar_archivo_tareas(data)
            _sincronizar_dashboard_json(tareas)
            print("[Tareas Programadas] Sincronización desde Bitacora.md completada.")
        else:
            _sincronizar_dashboard_json(tareas)

        return mapa_tareas
    except Exception as e:
        print(f"[Tareas Programadas] Error sincronizando desde Bitacora: {e}")
        return {}


def actualizar_estado_tarea_en_bitacora(
    id_tarea: str,
    nuevo_estado: Optional[str] = None,
    ultima_ejecucion: Optional[str] = None,
    proxima_ejecucion: Optional[str] = None,
) -> bool:
    """Actualiza en caliente la fila de la tarea en la tabla Markdown de Bitacora.md (7 u 8 columnas)."""
    if not _BITACORA_FILE.exists():
        return False
    try:
        contenido = _BITACORA_FILE.read_text(encoding="utf-8")
        if "## 🕒 Registro de Tareas Programadas y Rutinas" not in contenido:
            return False

        lineas = contenido.splitlines()
        nuevas_lineas = []
        modificado = False
        cabeceras = []

        for linea in lineas:
            linea_str = linea.strip()
            if linea_str.startswith("|") and not (linea_str.startswith("| :---") or linea_str.startswith("|:---")):
                partes = [p.strip() for p in linea_str.split("|")[1:-1]]
                if any(x.lower() in ("id", "tarea", "responsable") for x in partes):
                    cabeceras = [p.lower() for p in partes]
                    nuevas_lineas.append(linea)
                    continue

                if f"`{id_tarea}`" in linea or (partes and partes[0].replace("`", "").strip().upper() == id_tarea.upper()):
                    if cabeceras and len(cabeceras) == len(partes):
                        for idx, h in enumerate(cabeceras):
                            if "estado" in h and nuevo_estado:
                                partes[idx] = f"`{nuevo_estado.upper()}`"
                            elif ("última" in h or "ultima" in h) and ultima_ejecucion:
                                partes[idx] = ultima_ejecucion
                            elif ("próxima" in h or "proxima" in h) and proxima_ejecucion:
                                partes[idx] = proxima_ejecucion
                    else:
                        if len(partes) >= 8:
                            if proxima_ejecucion:
                                partes[4] = proxima_ejecucion
                            if nuevo_estado:
                                partes[6] = f"`{nuevo_estado.upper()}`"
                            if ultima_ejecucion:
                                partes[7] = ultima_ejecucion
                        elif len(partes) >= 7:
                            if nuevo_estado:
                                partes[5] = f"`{nuevo_estado.upper()}`"
                            if ultima_ejecucion:
                                partes[6] = ultima_ejecucion
                    linea = f"| {' | '.join(partes)} |"
                    modificado = True

            nuevas_lineas.append(linea)

        if modificado:
            _BITACORA_FILE.write_text("\n".join(nuevas_lineas) + "\n", encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"[Tareas Programadas] Advertencia actualizando Bitacora: {e}")
        return False


def ejecutar_ciclo_tareas_programadas() -> list[str]:
    """
    Invocada por el demonio `base_listener.py`.
    1. Sincroniza tareas declaradas en `Bitacora.md` con `tareas_programadas.json`.
    2. Revisa si llegó el momento de evaluar el sensor (`proxima_verificacion`).
    3. Evalúa el gatillo en CÓDIGO PYTHON PURO (`_evaluar_gatillo_zero_token`), consumiendo 0 TOKENS DE IA.
    4. Si el gatillo retorna `False`: actualiza `proxima_verificacion` y no crea tickets.
    5. Si el gatillo retorna `True`: inyecta el ticket en `Bitacora.md` para despertar al subagente.
    """
    tickets_generados = []
    try:
        # Sincronización bidireccional desde la Pizarra (SSOT)
        sincronizar_tareas_desde_bitacora()

        if not _TAREAS_FILE.exists():
            return tickets_generados

        data = _asegurar_archivo_tareas()
        tareas = data.get("tareas", [])
        if not tareas:
            return tickets_generados

        ahora = datetime.now()
        texto_bitacora = _BITACORA_FILE.read_text(encoding="utf-8") if _BITACORA_FILE.exists() else ""
        hubo_cambios = False

        for t in tareas:
            if t.get("estado") != "ACTIVA":
                continue

            prox_str = t.get("proxima_verificacion") or t.get("proxima_ejecucion")
            if not prox_str:
                continue

            try:
                prox_dt = datetime.fromisoformat(prox_str)
            except Exception:
                continue

            if ahora < prox_dt:
                continue

            # Anti-solapamiento: no evaluar ni disparar si ya hay un ticket de esta tarea procesándose
            id_tarea = t.get("id_tarea", "REC")
            patron_activo = rf"##\s+TKT-{re.escape(id_tarea)}-C\d+[\s\S]*?-\s*\*\*Estado:\*\*\s*(PENDIENTE|EN_PROGRESO|ESPERANDO_CORRECCION|PENDIENTE_REVISION)"
            if re.search(patron_activo, texto_bitacora, flags=re.IGNORECASE):
                continue

            # Evaluar gatillo en Python puro (0 TOKENS LLM)
            disparar, datos_evento = _evaluar_gatillo_zero_token(t)

            # Parsear ultima_ejecucion para reprogramar
            ult_str = t.get("ultima_ejecucion")
            ult_dt = None
            if ult_str:
                try:
                    ult_dt = datetime.fromisoformat(ult_str[:19].replace(" ", "T"))
                except Exception:
                    ult_dt = None

            # Reprogramar el próximo chequeo del sensor
            t["proxima_verificacion"] = _calcular_proxima_verificacion(
                tipo_activacion=t.get("tipo_activacion", "gatillo_script_python"),
                intervalo_segundos_sensor=t.get("intervalo_segundos_sensor", 30),
                hora_ejecucion=t.get("hora_ejecucion", "09:00"),
                frecuencia_reloj=t.get("frecuencia_reloj", "diaria"),
                dias_programados=t.get("dias_programados"),
                ultima_ejecucion=ult_dt,
                desde=ahora,
            )
            hubo_cambios = True

            if not disparar:
                # 0 tokens gastados: el sensor verificó que no hay evento nuevo
                continue

            # ¡El gatillo detectó un evento real! Inyectar ticket y despertar al subagente
            nuevo_ticket_id = _inyectar_ticket_en_bitacora(t, datos_evento=datos_evento)
            t["ciclos_completados"] = int(t.get("ciclos_completados", 0)) + 1
            t["ultima_ejecucion"] = ahora.isoformat()[:19]
            t["ultimo_ticket_id"] = nuevo_ticket_id
            tickets_generados.append(nuevo_ticket_id)
            print(
                f"[Gatillo Zero-Token] ⚡ Evento detectado en '{t.get('nombre')}' ({t.get('tipo_activacion')}) "
                f"-> Ticket {nuevo_ticket_id} despachado a {t.get('responsable_principal')}."
            )

        if hubo_cambios:
            _guardar_archivo_tareas(data)
            _sincronizar_dashboard_json(tareas)

    except Exception as e:
        print(f"[Gatillo Zero-Token] Advertencia en evaluación de sensores: {e}")

    return tickets_generados


HERRAMIENTAS_TAREAS_PROGRAMADAS = [
    tool_crear_gatillo_sensor_python,
    tool_programar_tarea_repetitiva,
    tool_listar_tareas_repetitivas,
    tool_modificar_estado_tarea_repetitiva,
]
