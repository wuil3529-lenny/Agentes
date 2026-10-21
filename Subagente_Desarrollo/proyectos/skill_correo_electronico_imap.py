"""
skill_correo_electronico.py — Gestión Integral, Triaje, Alertas y Respuesta de Correo Electrónico
===================================================================================================
Habilidad unificada del Subagente de Asistencia para el ciclo completo de correo:
1. Recibir y analizar correos entrantes en Gmail.
2. Catalogar con lista de prioridades rigurosa (CRÍTICA, ALTA, MEDIA, BAJA/SPAM).
3. Notificar al usuario por mensajería (Telegram / canal usuario) con resúmenes concisos.
4. Responder correos en nombre del usuario (enviar respuestas o crear borradores en Gmail).
5. Consultar y comprender información puntual sin generar informes pesados.
6. Llevar seguimiento interactivo de correos esperando decisión del usuario.

Herramientas disponibles:
  - tool_correo_recibir_y_analizar   : Vigila, analiza, clasifica y notifica correos prioritarios.
  - tool_correo_consultar_detalle    : Lee un correo y responde dudas puntuales sin rodeos.
  - tool_correo_notificar_usuario    : Envía alertas estructuradas a la mensajería del usuario.
  - tool_correo_responder            : Redacta y envía respuestas o crea borradores en Gmail.
  - tool_correo_seguimiento_pendientes: Lista los correos prioritarios esperando acción.
"""

import os
import sys
import json
import base64
import html
import re
import time
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from langchain_core.tools import tool
import imaplib
import email
from email.header import decode_header

# Resolver APP_ROOT y rutas del subagente
def _resolver_app_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".env").exists() or (parent / "Bitacora.md").exists():
            return parent
    return p.parents[3] if len(p.parents) > 3 else p.parent

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _resolver_app_root()
_AGENTE = "Subagente_Asistencia"

BASE_DIR = _APP_ROOT / _AGENTE
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROCESADOS_FILE = DATA_DIR / "correos_procesados.json"
SEGUIMIENTO_FILE = DATA_DIR / "correos_seguimiento.json"

# Importar cliente oficial de Google Workspace
try:
    from Subagente_Asistencia.skills.google_workspace.skill_google import obtener_servicio
except ImportError:
    try:
        from skills.google_workspace.skill_google import obtener_servicio
    except ImportError:
        try:
            from skill_google_sanji import obtener_servicio
        except ImportError:
            obtener_servicio = None

# Importar puente de mensajería (Telegram)
def _notificar_mensajeria(texto: str) -> str:
    """Envía la notificación vía Telegram y la espejea en la memoria del usuario."""
    try:
        sys.path.insert(0, str(_APP_ROOT / "Agente_Orquestador"))
        from telegram_bridge import enviar_mensaje_telegram
        return enviar_mensaje_telegram(texto, remitente="Subagente_Asistencia")
    except Exception as e:
        # Fallback a publicar_mensaje en memoria compartida
        try:
            from memory import publicar_mensaje
            publicar_mensaje(
                de="Subagente_Asistencia",
                para="usuario",
                tipo="notificacion_correo",
                contenido={"texto": texto},
                canal_tipo="usuario"
            )
            return "Notificación publicada en canal usuario."
        except Exception:
            return f"Aviso registrado en buffer local (error puente: {e})"


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT ESPECIALIZADO DE LA HABILIDAD
# ═══════════════════════════════════════════════════════════════════════════════

def obtener_prompt_correo_electronico() -> str:
    """
    System Prompt especializado y encapsulado para la gestión de correo electrónico.
    """
    return """[🛑 HARD-STOP: MODO GESTOR DE CORREO ELECTRÓNICO ACTIVO 🛑]
Eres el Gestor y Operador de Correo Electrónico del Subagente de Asistencia.
Tu misión es vigilar la bandeja de entrada, comprender a fondo los mensajes recibidos, catalogar estrictamente por prioridades descartando spam, notificar al usuario de inmediato ante asuntos de alto valor y responder en su nombre cuando corresponda.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CERO INFORMES PESADOS O BUROCRÁTICOS:
   - Prohibido generar documentos en Google Docs o archivos markdown extensos para volcar correos.
   - Si el usuario o el sistema te pide información de un correo, consulta directamente los datos (`tool_correo_consultar_detalle`) y responde la duda puntual (fechas, códigos, instrucciones o importes) de forma concisa.
2. LISTA ESTRICTA DE PRIORIDADES:
   - CRÍTICA : Alertas de seguridad, bancos, 2FA, accesos sospechosos o caídas de servicios. (Notificación inmediata).
   - ALTA    : Clientes, propuestas de negocios, respuestas en hilos de personas reales, ofertas laborales técnicas alineadas o becas de IA. (Notificación inmediata).
   - MEDIA   : Recibos transaccionales, confirmaciones de compras o trámites administrativos estándar. (No genera alerta inmediata salvo que se solicite).
   - BAJA    : Publicidad comercial, promociones de tiendas, newsletters vacías o notificaciones masivas de redes sociales. (SILENCIAR TOTALMENTE).
3. PROTOCOLO DE NOTIFICACIÓN EJECUTIVA:
   - Toda notificación al usuario debe ser limpia, concisa y estructurada para lectura rápida o dictado en briefing de audio matutino:
     * Remitente, Asunto, Síntesis del requerimiento y pregunta de acción: "¿Deseas que responda [propuesta de respuesta] o prefieres responder tú?".
4. RESPUESTA EN NOMBRE DEL USUARIO:
   - Cuando el usuario te ordene responder un correo ("respóndele que sí", "dile que el jueves a las 4pm"), utiliza `tool_correo_responder` con un tono profesional, cortés y resolutivo.
   - Si no estás seguro de la intención del usuario, prepara un borrador (`como_borrador=True`) y pídele confirmación.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCIA LOCAL (CORREOS PROCESADOS Y SEGUIMIENTO)
# ═══════════════════════════════════════════════════════════════════════════════

def _cargar_procesados() -> Dict[str, Any]:
    if PROCESADOS_FILE.exists():
        try:
            return json.loads(PROCESADOS_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"ultimo_analisis": None, "procesados": {}}


def _registrar_correo_procesado(msg_id: str, info: Dict[str, Any]):
    datos = _cargar_procesados()
    datos["procesados"][msg_id] = {
        "asunto": info.get("asunto", ""),
        "de": info.get("de", ""),
        "fecha": info.get("fecha", ""),
        "categoria": info.get("categoria", "otro"),
        "prioridad": info.get("prioridad", "BAJA"),
        "timestamp_procesado": datetime.now().isoformat()
    }
    datos["ultimo_analisis"] = datetime.now().isoformat()

    # Mantener historial acotado a los últimos 500
    if len(datos["procesados"]) > 500:
        claves = sorted(datos["procesados"].keys(), key=lambda k: datos["procesados"][k].get("timestamp_procesado", ""))
        for k in claves[:-400]:
            del datos["procesados"][k]

    try:
        PROCESADOS_FILE.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"[Correo] Advertencia al persistir correos_procesados: {e}")


def _cargar_seguimiento() -> List[Dict[str, Any]]:
    if SEGUIMIENTO_FILE.exists():
        try:
            return json.loads(SEGUIMIENTO_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return []


def _guardar_seguimiento(lista: List[Dict[str, Any]]):
    try:
        SEGUIMIENTO_FILE.write_text(json.dumps(lista, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"[Correo] Advertencia al persistir seguimiento: {e}")


def _agregar_seguimiento(correo_id: str, remitente: str, asunto: str, resumen: str, prioridad: str):
    lista = _cargar_seguimiento()
    for item in lista:
        if item.get("id") == correo_id:
            return
    lista.append({
        "id": correo_id,
        "remitente": remitente,
        "asunto": asunto,
        "resumen": resumen,
        "prioridad": prioridad,
        "estado": "pendiente_decision_usuario",
        "timestamp_notificado": datetime.now().isoformat(),
        "respuesta_enviada": None
    })
    _guardar_seguimiento(lista)


# ═══════════════════════════════════════════════════════════════════════════════
# HEURÍSTICA DE TRIAJE Y PRIORIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

PERFIL_KEYWORDS = [
    'python', 'ia', 'inteligencia artificial', 'artificial intelligence',
    'machine learning', 'deep learning', 'data', 'datos', 'analista',
    'programador', 'desarrollador', 'developer', 'engineer', 'ingeniero',
    'backend', 'software', 'remoto', 'remote', 'automation', 'fullstack',
    'agente', 'agent', 'fastapi', 'react', 'api', 'docker'
]

FALSOS_POSITIVOS_OFERTAS = [
    'ha publicado un contenido', 'perfect match', 'jobalerts', 'jobs-noreply',
    'boletín', 'newsletter', 'recomendaciones de empleo', 'empleos sugeridos',
    'novedades de tu red', 'ha aparecido en una búsqueda', 'descuento en todo'
]

KEYWORDS_COMPRA_PROMO = [
    'descuento', 'rebaja', 'promoción', 'promocion', 'sale', 'off',
    'black friday', 'cyber', 'cupón', 'cupon', 'oferta exclusiva',
    'compra ahora', 'tienda', 'envío gratis', 'liquidación', '2x1'
]


def _extraer_cuerpo_texto(payload: Dict[str, Any], max_chars: int = 1500) -> str:
    """Extrae texto plano limpio y decodificado de los datos de un mensaje."""
    body = ""
    try:
        if 'parts' in payload:
            for part in payload['parts']:
                mime = part.get('mimeType', '')
                if mime == 'text/plain' and 'data' in part.get('body', {}):
                    data = part['body']['data']
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif mime == 'text/html' and not body and 'data' in part.get('body', {}):
                    data = part['body']['data']
                    raw_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    body += re.sub(r'<[^>]+>', ' ', raw_html)
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            raw = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            body = re.sub(r'<[^>]+>', ' ', raw) if payload.get('mimeType') == 'text/html' else raw
    except Exception:
        pass

    body = html.unescape(body)
    body = re.sub(r'\s+', ' ', body).strip()
    return body[:max_chars]


def _clasificar_correo(sender: str, subject: str, snippet: str, body: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Clasifica el correo determinando su categoría y prioridad estricta."""
    texto = f"{subject} {sender} {snippet} {body}".lower()

    # 1. Seguridad y 2FA (CRÍTICA)
    if any(k in sender.lower() for k in ['accounts.google.com', 'security', 'seguridad', 'auth', 'no-reply@google.com', 'banco', 'bank', 'verification']) and \
       any(k in texto for k in ['código de seguridad', 'alerta de seguridad', 'intento de acceso', 'verificación', 'security alert', 'code']):
        return {
            "categoria": "alerta_seguridad",
            "prioridad": "CRÍTICA",
            "motivo": "Alerta crítica de seguridad o verificación de cuenta.",
            "accion_sugerida": "Revisar inmediatamente y verificar accesos."
        }

    # 2. Respuestas humanas de personas reales (ALTA)
    es_respuesta_hilo = subject.lower().startswith('re:') or bool(headers.get('in-reply-to'))
    es_persona_real = not any(s in sender.lower() for s in ['noreply', 'no-reply', 'newsletter', 'mailer', 'promotions', 'notification'])
    if es_respuesta_hilo and es_persona_real:
        return {
            "categoria": "respuesta_humano",
            "prioridad": "ALTA",
            "motivo": "Respuesta directa en un hilo de conversación por una persona.",
            "accion_sugerida": "Responder al remitente para dar continuidad."
        }

    # 3. Propuestas y ofertas de empleo
    if any(w in texto for w in ['vacante', 'oferta de empleo', 'propuesta laboral', 'job offer', 'position', 'contratación']):
        es_spam_portal = any(p in sender.lower() or p in texto for p in FALSOS_POSITIVOS_OFERTAS)
        tiene_perfil_tech = any(k in texto for k in PERFIL_KEYWORDS)
        if not es_spam_portal and tiene_perfil_tech:
            return {
                "categoria": "oferta_laboral",
                "prioridad": "ALTA",
                "motivo": "Propuesta laboral técnica coincidente con perfil de software e IA.",
                "accion_sugerida": "Evaluar condiciones y responder si es de interés."
            }

    # 4. Becas y convocatorias académicas (ALTA)
    if any(w in texto for w in ['beca', 'scholarship', 'fellowship', 'convocatoria', 'subvención', 'bootcamp']):
        return {
            "categoria": "beca",
            "prioridad": "ALTA",
            "motivo": "Convocatoria formativa, beca o programa acelerador.",
            "accion_sugerida": "Revisar requisitos de postulación y plazos."
        }

    # 5. Promociones / Compras (BAJA - Silenciado)
    if any(k in texto for k in KEYWORDS_COMPRA_PROMO):
        return {
            "categoria": "oferta_compra",
            "prioridad": "BAJA",
            "motivo": "Promoción comercial o publicidad.",
            "accion_sugerida": "Ignorar o archivar."
        }

    # 6. Spam evidente
    if any(s in sender.lower() for s in ['newsletter', 'marketing', 'promo', 'boletin', 'alerts@']):
        return {
            "categoria": "spam",
            "prioridad": "BAJA",
            "motivo": "Boletín masivo o notificación comercial no prioritaria.",
            "accion_sugerida": "Silenciar."
        }

    return {
        "categoria": "otro",
        "prioridad": "MEDIA" if es_persona_real else "BAJA",
        "motivo": "Comunicación general transaccional o informativa.",
        "accion_sugerida": "Revisar según conveniencia."
    }



# ═══════════════════════════════════════════════════════════════════════════════
# MIGRACIÓN A IMAP PURO (TKT-DEV-20261014002)
# Lectura de correos SIN Gmail API / SIN OAuth / SIN token.json.
# Reutiliza la lógica probada de Agente_Orquestador/data/sensores/sensor_correo_imap.py
# ═══════════════════════════════════════════════════════════════════════════════

def _cargar_env(override: bool = True):
    """Carga el .env manualmente (sin dependencias externas).

    Con override=True (por defecto) el valor del .env SIEMPRE sobreescribe
    cualquier variable preexistente en os.environ, garantizando credenciales
    frescas y evitando heredar una contraseña de aplicación obsoleta.
    """
    env_path = Path("/app/.env")
    if not env_path.exists():
        env_path = _APP_ROOT / ".env"
    if env_path.exists():
        for linea in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if override:
                os.environ[clave] = valor
            else:
                os.environ.setdefault(clave, valor)


def _decodificar_header(valor: str) -> str:
    """Decodifica cabeceras MIME a texto legible."""
    if not valor:
        return ""
    partes = decode_header(valor)
    resultado = ""
    for texto, encoding in partes:
        if isinstance(texto, bytes):
            try:
                resultado += texto.decode(encoding or "utf-8", errors="ignore")
            except Exception:
                resultado += texto.decode("utf-8", errors="ignore")
        else:
            resultado += texto
    return resultado


def _cuerpo_texto_imap(msg) -> str:
    """Extrae el cuerpo en texto plano del mensaje IMAP."""
    if msg.is_multipart():
        for parte in msg.walk():
            ctype = parte.get_content_type()
            disp = str(parte.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    payload = parte.get_payload(decode=True)
                    charset = parte.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="ignore")[:2000]
                except Exception:
                    continue
        return ""
    try:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="ignore")[:2000]
    except Exception:
        return ""


def _leer_correos_imap(max_correos: int, solo_no_leidos: bool) -> List[Dict[str, Any]]:
    """Conecta a imap.gmail.com:993 y devuelve los últimos N correos.

    Lee credenciales frescas del .env con override forzado. NO requiere token.json.
    Lanza excepción si falla la conexión/autenticación (el llamador aplica fallback).
    """
    _cargar_env(override=True)
    imap_host = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
    imap_port = int(os.getenv("IMAP_PORT", "993"))
    email_user = os.getenv("KEEP_EMAIL", "").strip().strip('"')
    email_pass = os.getenv("KEEP_APP_PASSWORD", "").strip().strip('"')

    if not email_user or not email_pass:
        raise RuntimeError("Credenciales IMAP no configuradas en .env (KEEP_EMAIL / KEEP_APP_PASSWORD).")

    mail = imaplib.IMAP4_SSL(imap_host, imap_port)
    try:
        mail.login(email_user, email_pass)
        mail.select("INBOX")

        criterio = "UNSEEN" if solo_no_leidos else "ALL"
        status, data = mail.search(None, criterio)
        if status != "OK":
            return []

        uids = data[0].split()
        if not uids:
            return []

        correos: List[Dict[str, Any]] = []
        for uid in uids[-max_correos:]:
            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            correos.append({
                "id": uid.decode(),
                "uid": uid.decode(),
                "de": _decodificar_header(msg.get("From")),
                "asunto": _decodificar_header(msg.get("Subject")) or "(Sin asunto)",
                "fecha": msg.get("Date", ""),
                "cuerpo": _cuerpo_texto_imap(msg),
                "message_id": msg.get("Message-ID", ""),
                "in_reply_to": msg.get("In-Reply-To", ""),
            })
        return correos
    finally:
        try:
            mail.logout()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS EXPORTADAS (CATÁLOGO DE LA SKILL)
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tool_correo_recibir_y_analizar(
    max_correos: int = 10,
    solo_no_leidos: bool = True,
    notificar_prioritarios: bool = True
) -> str:
    """
    Recibe, analiza y cataloga correos entrantes por orden de prioridad usando
    IMAP puro (imap.gmail.com:993). NO requiere Gmail API ni OAuth ni token.json.
    Filtra automáticamente spam y publicidad. Ante correos de prioridad ALTA o
    CRÍTICA, envía una notificación estructurada a la mensajería del usuario
    (Telegram) y los registra para seguimiento de respuesta.
    """
    try:
        correos = _leer_correos_imap(max_correos=max_correos, solo_no_leidos=solo_no_leidos)
    except Exception as e:
        # Fallback seguro: si IMAP falla, intentar Gmail API si estuviera disponible.
        if obtener_servicio is not None:
            try:
                return _recibir_via_gmail_api(max_correos, solo_no_leidos, notificar_prioritarios)
            except Exception:
                pass
        return json.dumps({
            "status": "error",
            "mensaje": f"Fallo al recibir correos por IMAP: {str(e)}",
            "fallback": "Gmail API no disponible o también falló."
        }, ensure_ascii=False)

    if not correos:
        return json.dumps({
            "status": "success",
            "mensaje": "Bandeja limpia: no se encontraron correos nuevos para procesar.",
            "total_analizados": 0,
            "notificaciones_enviadas": 0
        }, ensure_ascii=False)

    procesados_hist = _cargar_procesados().get("procesados", {})
    analizados = []
    notificados = 0

    for correo in correos:
        msg_id = correo["id"]
        if msg_id in procesados_hist:
            continue

        sender = correo["de"]
        subject = correo["asunto"]
        date = correo["fecha"]
        body = correo["cuerpo"]
        snippet = body[:200]
        headers_dict = {
            "in-reply-to": correo.get("in_reply_to", ""),
            "message-id": correo.get("message_id", ""),
        }

        clasif = _clasificar_correo(sender, subject, snippet, body, headers_dict)
        prioridad = clasif["prioridad"]
        categoria = clasif["categoria"]

        info_msg = {
            "id": msg_id,
            "thread_id": None,
            "de": sender,
            "asunto": subject,
            "fecha": date,
            "categoria": categoria,
            "prioridad": prioridad,
            "motivo": clasif["motivo"],
            "resumen": snippet
        }
        _registrar_correo_procesado(msg_id, info_msg)
        analizados.append(info_msg)

        if notificar_prioritarios and prioridad in ["ALTA", "CRÍTICA"]:
            notificados += 1
            _agregar_seguimiento(msg_id, sender, subject, snippet, prioridad)

            icono = "🚨" if prioridad == "CRÍTICA" else "📬"
            mensaje_alerta = (
                f"{icono} **Correo Prioritario ({prioridad})**\n"
                f"**De:** {sender}\n"
                f"**Asunto:** {subject}\n"
                f"**Resumen:** {snippet}\n\n"
                f"❓ *¿Deseas que prepare y envíe una respuesta o prefieres responder tú directamente?*"
            )
            _notificar_mensajeria(mensaje_alerta)

    return json.dumps({
        "status": "success",
        "origen": "imap",
        "total_analizados": len(analizados),
        "notificaciones_enviadas": notificados,
        "resumen_analizados": analizados
    }, ensure_ascii=False)


def _recibir_via_gmail_api(max_correos: int, solo_no_leidos: bool, notificar_prioritarios: bool) -> str:
    """Fallback legacy: lectura vía Gmail API (solo si IMAP falla y OAuth disponible)."""
    service = obtener_servicio('gmail', 'v1')
    query = 'is:unread in:inbox' if solo_no_leidos else 'in:inbox'
    results = service.users().messages().list(userId='me', q=query, maxResults=max_correos).execute()
    messages = results.get('messages', [])
    if not messages:
        return json.dumps({
            "status": "success",
            "mensaje": "Bandeja limpia: no se encontraron correos nuevos para procesar.",
            "total_analizados": 0,
            "notificaciones_enviadas": 0
        }, ensure_ascii=False)

    procesados_hist = _cargar_procesados().get("procesados", {})
    analizados = []
    notificados = 0
    for m in messages:
        msg_id = m['id']
        if msg_id in procesados_hist:
            continue
        detalle = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        headers = detalle.get('payload', {}).get('headers', [])
        headers_dict = {h['name'].lower(): h['value'] for h in headers}
        subject = headers_dict.get('subject', '(Sin asunto)')
        sender = headers_dict.get('from', '(Desconocido)')
        date = headers_dict.get('date', '')
        snippet = detalle.get('snippet', '')
        body = _extraer_cuerpo_texto(detalle.get('payload', {}))
        clasif = _clasificar_correo(sender, subject, snippet, body, headers_dict)
        prioridad = clasif["prioridad"]
        categoria = clasif["categoria"]
        info_msg = {
            "id": msg_id, "thread_id": detalle.get("threadId"), "de": sender,
            "asunto": subject, "fecha": date, "categoria": categoria,
            "prioridad": prioridad, "motivo": clasif["motivo"], "resumen": snippet
        }
        _registrar_correo_procesado(msg_id, info_msg)
        analizados.append(info_msg)
        if notificar_prioritarios and prioridad in ["ALTA", "CRÍTICA"]:
            notificados += 1
            _agregar_seguimiento(msg_id, sender, subject, snippet, prioridad)
            icono = "🚨" if prioridad == "CRÍTICA" else "📬"
            _notificar_mensajeria(
                f"{icono} **Correo Prioritario ({prioridad})**\n**De:** {sender}\n"
                f"**Asunto:** {subject}\n**Resumen:** {snippet}\n\n"
                f"❓ *¿Deseas que prepare y envíe una respuesta o prefieres responder tú directamente?*"
            )
    return json.dumps({
        "status": "success", "origen": "gmail_api_fallback",
        "total_analizados": len(analizados),
        "notificaciones_enviadas": notificados,
        "resumen_analizados": analizados
    }, ensure_ascii=False)


def _consultar_detalle_imap(target_id: str) -> Optional[Dict[str, Any]]:
    """Consulta un correo en IMAP por UID o búsqueda de texto."""
    _cargar_env(override=True)
    email_user = os.getenv("KEEP_EMAIL", "").strip().strip('"')
    email_pass = os.getenv("KEEP_APP_PASSWORD", "").strip().strip('"')
    if not email_user or not email_pass:
        return None

    imap_host = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
    imap_port = int(os.getenv("IMAP_PORT", "993"))
    mail = imaplib.IMAP4_SSL(imap_host, imap_port)
    try:
        mail.login(email_user, email_pass)
        mail.select("INBOX", readonly=True)

        uid_to_fetch = None
        if target_id.isdigit():
            uid_to_fetch = target_id
        else:
            status, data = mail.search(None, f'(OR FROM "{target_id}" SUBJECT "{target_id}")')
            if status == "OK" and data and data[0]:
                uids = data[0].split()
                if uids:
                    uid_to_fetch = uids[-1].decode()

        if not uid_to_fetch:
            return None

        status, data = mail.fetch(uid_to_fetch, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            return None

        msg = email.message_from_bytes(data[0][1])
        sender = _decodificar_header(msg.get("From")) or "(Desconocido)"
        subject = _decodificar_header(msg.get("Subject")) or "(Sin asunto)"
        date = msg.get("Date", "")
        body = _cuerpo_texto_imap(msg)

        return {
            "id": uid_to_fetch,
            "de": sender,
            "asunto": subject,
            "fecha": date,
            "cuerpo_texto": body
        }
    except Exception:
        return None
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def _responder_via_smtp_imap(
    id_correo_o_destinatario: str,
    mensaje_respuesta: str,
    asunto: str = "",
    como_borrador: bool = False
) -> Dict[str, Any]:
    """Envío o borrador vía SMTP / IMAP usando KEEP_EMAIL y KEEP_APP_PASSWORD."""
    _cargar_env(override=True)
    email_user = os.getenv("KEEP_EMAIL", "").strip().strip('"')
    email_pass = os.getenv("KEEP_APP_PASSWORD", "").strip().strip('"')
    if not email_user or not email_pass:
        raise RuntimeError("Credenciales no configuradas en .env (KEEP_EMAIL / KEEP_APP_PASSWORD).")

    destinatario = id_correo_o_destinatario.strip()
    asunto_final = asunto
    in_reply_to = None

    if "@" not in destinatario:
        detalle = _consultar_detalle_imap(destinatario)
        if detalle:
            raw_from = detalle.get("de", "")
            email_match = re.search(r'<([^>]+)>', raw_from)
            destinatario = email_match.group(1) if email_match else raw_from
            orig_subj = detalle.get("asunto", "")
            if not asunto_final and orig_subj:
                asunto_final = orig_subj if orig_subj.lower().startswith("re:") else f"Re: {orig_subj}"

    if not asunto_final:
        asunto_final = "Comunicación de Asistencia"

    mime_msg = MIMEText(mensaje_respuesta, "plain", "utf-8")
    mime_msg['From'] = email_user
    mime_msg['To'] = destinatario
    mime_msg['Subject'] = asunto_final
    if in_reply_to:
        mime_msg['In-Reply-To'] = in_reply_to
        mime_msg['References'] = in_reply_to

    if como_borrador:
        imap_host = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
        imap_port = int(os.getenv("IMAP_PORT", "993"))
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        try:
            mail.login(email_user, email_pass)
            res, _ = mail.append('"[Gmail]/Drafts"', '\\Draft', imaplib.Time2Internaldate(time.time()), mime_msg.as_bytes())
            if res != "OK":
                res, _ = mail.append('"[Gmail]/Borradores"', '\\Draft', imaplib.Time2Internaldate(time.time()), mime_msg.as_bytes())
            res_id = f"draft_imap_{int(time.time())}"
            estado = "borrador_creado"
            mensaje_confirmacion = f"Borrador creado en Gmail para {destinatario} con asunto '{asunto_final}'. ID: {res_id}"
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    else:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        smtp_port = int(os.getenv("SMTP_PORT", "465"))
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=25) as server:
            server.login(email_user, email_pass)
            server.send_message(mime_msg)
        res_id = f"smtp_{int(time.time())}"
        estado = "enviado"
        mensaje_confirmacion = f"Correo enviado exitosamente a {destinatario} con asunto '{asunto_final}'. ID: {res_id}"

    # Actualizar seguimiento si correspondía a un correo pendiente
    try:
        seguimiento = _cargar_seguimiento()
        actualizado = False
        for item in seguimiento:
            if item.get("id") == id_correo_o_destinatario or item.get("remitente") == destinatario:
                item["estado"] = "respondido"
                item["respuesta_enviada"] = mensaje_respuesta
                actualizado = True
        if actualizado:
            _guardar_seguimiento(seguimiento)
    except Exception:
        pass

    return {
        "status": "success",
        "estado": estado,
        "id": res_id,
        "destinatario": destinatario,
        "asunto": asunto_final,
        "mensaje": mensaje_confirmacion,
        "via": "smtp" if not como_borrador else "imap_draft"
    }


@tool
def tool_correo_consultar_detalle(id_correo_o_tema: str, pregunta_especifica: str = "") -> str:
    """
    Lee a fondo un correo de Gmail y responde preguntas puntuales sobre su contenido
    (ej. fechas, códigos, cotizaciones, instrucciones) sin generar informes burocráticos.
    Soporta fallback autónomo vía IMAP si Google Workspace OAuth no está disponible.
    """
    target_id = id_correo_o_tema.strip()

    # 1. Intentar Gmail API si está disponible
    if obtener_servicio is not None:
        try:
            service = obtener_servicio('gmail', 'v1')
            if service:
                if len(target_id) < 15 or " " in target_id:
                    busqueda = service.users().messages().list(userId='me', q=target_id, maxResults=1).execute()
                    mensajes = busqueda.get('messages', [])
                    if mensajes:
                        target_id = mensajes[0]['id']

                detalle = service.users().messages().get(userId='me', id=target_id, format='full').execute()
                headers = {h['name'].lower(): h['value'] for h in detalle.get('payload', {}).get('headers', [])}
                subject = headers.get('subject', '(Sin asunto)')
                sender = headers.get('from', '(Desconocido)')
                date = headers.get('date', '')
                body = _extraer_cuerpo_texto(detalle.get('payload', {}), max_chars=3000)

                respuesta = {
                    "id": target_id,
                    "de": sender,
                    "asunto": subject,
                    "fecha": date,
                    "cuerpo_texto": body
                }
                if pregunta_especifica:
                    respuesta["pregunta_atendida"] = pregunta_especifica
                    respuesta["instruccion_para_agente"] = (
                        f"Analiza el cuerpo del correo anterior y responde al usuario puntualmente sobre: '{pregunta_especifica}'. "
                        "Sé directo, conciso y responde sin generar documentos."
                    )
                return json.dumps(respuesta, ensure_ascii=False)
        except Exception:
            pass

    # 2. Fallback resiliente vía IMAP
    detalle_imap = _consultar_detalle_imap(target_id)
    if detalle_imap:
        if pregunta_especifica:
            detalle_imap["pregunta_atendida"] = pregunta_especifica
            detalle_imap["instruccion_para_agente"] = (
                f"Analiza el cuerpo del correo anterior y responde al usuario puntualmente sobre: '{pregunta_especifica}'. "
                "Sé directo, conciso y responde sin generar documentos."
            )
        return json.dumps(detalle_imap, ensure_ascii=False)

    return json.dumps({"status": "error", "mensaje": f"No se pudo consultar el correo '{target_id}' ni por Gmail API ni por IMAP."})


@tool
def tool_correo_responder(
    id_correo_o_destinatario: str,
    mensaje_respuesta: str,
    asunto: str = "",
    como_borrador: bool = False
) -> str:
    """
    Redacta y envía un correo electrónico en nombre del usuario a través de Gmail,
    o crea un borrador para revisión previa. Permite responder directamente en el mismo
    hilo de conversación o iniciar una nueva comunicación.
    Cuenta con fallback resiliente vía SMTP/IMAP si Google Workspace OAuth está expirado.
    """
    destinatario = id_correo_o_destinatario.strip()

    # 1. Intentar Gmail API si está disponible
    if obtener_servicio is not None:
        try:
            service = obtener_servicio('gmail', 'v1')
            if service:
                thread_id = None
                in_reply_to = None
                asunto_final = asunto

                if "@" not in destinatario and len(destinatario) >= 12:
                    try:
                        original = service.users().messages().get(userId='me', id=destinatario, format='metadata').execute()
                        thread_id = original.get('threadId')
                        headers = {h['name'].lower(): h['value'] for h in original.get('payload', {}).get('headers', [])}
                        raw_from = headers.get('from', '')
                        email_match = re.search(r'<([^>]+)>', raw_from)
                        destinatario = email_match.group(1) if email_match else raw_from
                        orig_subject = headers.get('subject', '')
                        if not asunto_final:
                            asunto_final = orig_subject if orig_subject.lower().startswith('re:') else f"Re: {orig_subject}"
                        in_reply_to = headers.get('message-id')
                    except Exception:
                        pass

                if not asunto_final:
                    asunto_final = "Comunicación de Asistencia"

                mime_msg = MIMEText(mensaje_respuesta)
                mime_msg['to'] = destinatario
                mime_msg['subject'] = asunto_final
                if in_reply_to:
                    mime_msg['In-Reply-To'] = in_reply_to
                    mime_msg['References'] = in_reply_to

                raw_str = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode('utf-8')
                body_payload: Dict[str, Any] = {'raw': raw_str}
                if thread_id:
                    body_payload['threadId'] = thread_id

                if como_borrador:
                    draft = service.users().drafts().create(userId='me', body={'message': body_payload}).execute()
                    res_id = draft.get('id')
                    estado = "borrador_creado"
                    mensaje_confirmacion = f"Borrador creado en Gmail para {destinatario} con asunto '{asunto_final}'. ID: {res_id}"
                else:
                    enviado = service.users().messages().send(userId='me', body=body_payload).execute()
                    res_id = enviado.get('id')
                    estado = "enviado"
                    mensaje_confirmacion = f"Correo enviado exitosamente a {destinatario} con asunto '{asunto_final}'. ID: {res_id}"

                seguimiento = _cargar_seguimiento()
                actualizado = False
                for item in seguimiento:
                    if item.get("id") == id_correo_o_destinatario or item.get("remitente") == destinatario:
                        item["estado"] = "respondido"
                        item["respuesta_enviada"] = mensaje_respuesta
                        actualizado = True
                if actualizado:
                    _guardar_seguimiento(seguimiento)

                return json.dumps({
                    "status": "success",
                    "estado": estado,
                    "id": res_id,
                    "destinatario": destinatario,
                    "asunto": asunto_final,
                    "mensaje": mensaje_confirmacion,
                    "via": "gmail_api"
                }, ensure_ascii=False)
        except Exception:
            # Fallback a SMTP
            pass

    # 2. Fallback resiliente vía SMTP / IMAP
    try:
        resultado = _responder_via_smtp_imap(id_correo_o_destinatario, mensaje_respuesta, asunto, como_borrador)
        return json.dumps(resultado, ensure_ascii=False)
    except Exception as e_smtp:
        return json.dumps({"status": "error", "mensaje": f"Error al responder correo (SMTP fallback): {str(e_smtp)}"})


@tool
def tool_correo_notificar_usuario(mensaje_notificacion: str, prioridad: str = "ALTA") -> str:
    """
    Envía una alerta o síntesis ejecutiva de correo directamente a la mensajería del usuario (Telegram).
    Asegura un formato conciso y estructurado, apto para lectura rápida o briefing matutino de audio.
    """
    try:
        icono = "🚨" if prioridad.upper() == "CRÍTICA" else "📬"
        texto_formateado = f"{icono} [NOTIFICACIÓN DE CORREO - {prioridad.upper()}]\n{mensaje_notificacion}"
        resultado = _notificar_mensajeria(texto_formateado)
        return json.dumps({
            "status": "success",
            "resultado_envio": resultado,
            "mensaje_notificado": mensaje_notificacion
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al notificar usuario: {str(e)}"})


@tool
def tool_correo_seguimiento_pendientes() -> str:
    """
    Consulta la lista de correos prioritarios que fueron notificados al usuario
    y que aún se encuentran pendientes de decisión o respuesta.
    """
    try:
        seguimiento = _cargar_seguimiento()
        pendientes = [item for item in seguimiento if item.get("estado") == "pendiente_decision_usuario"]
        return json.dumps({
            "status": "success",
            "total_pendientes": len(pendientes),
            "correos_pendientes": pendientes
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al consultar seguimiento: {str(e)}"})


# Catálogo oficial de herramientas de la habilidad
HERRAMIENTAS_CORREO_ELECTRONICO = [
    tool_correo_recibir_y_analizar,
    tool_correo_consultar_detalle,
    tool_correo_responder,
    tool_correo_notificar_usuario,
    tool_correo_seguimiento_pendientes,
]
