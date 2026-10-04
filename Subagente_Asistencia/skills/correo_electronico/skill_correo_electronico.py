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
from pathlib import Path
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from langchain_core.tools import tool

# Resolver APP_ROOT y rutas del subagente
_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
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
# HERRAMIENTAS EXPORTADAS (CATÁLOGO DE LA SKILL)
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tool_correo_recibir_y_analizar(
    max_correos: int = 10,
    solo_no_leidos: bool = True,
    notificar_prioritarios: bool = True
) -> str:
    """
    Recibe, analiza y cataloga correos entrantes de Gmail por orden de prioridad.
    Filtra automáticamente spam y publicidad. Ante correos de prioridad ALTA o CRÍTICA,
    envía una notificación estructurada a la mensajería del usuario (Telegram) y los
    registra para seguimiento de respuesta.
    """
    if obtener_servicio is None:
        return json.dumps({"status": "error", "mensaje": "Cliente de Google Workspace no disponible."})

    try:
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
            })

        procesados_hist = _cargar_procesados().get("procesados", {})
        analizados = []
        notificados = 0

        for m in messages:
            msg_id = m['id']
            # Omitir si ya fue procesado recientemente
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
                "id": msg_id,
                "thread_id": detalle.get("threadId"),
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

            # Notificación proactiva al usuario si es ALTA o CRÍTICA
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
            "total_analizados": len(analizados),
            "notificaciones_enviadas": notificados,
            "resumen_analizados": analizados
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al recibir y analizar correos: {str(e)}"})


@tool
def tool_correo_consultar_detalle(id_correo_o_tema: str, pregunta_especifica: str = "") -> str:
    """
    Lee a fondo un correo de Gmail y responde preguntas puntuales sobre su contenido
    (ej. fechas, códigos, cotizaciones, instrucciones) sin generar informes burocráticos.
    """
    if obtener_servicio is None:
        return json.dumps({"status": "error", "mensaje": "Cliente de Google Workspace no disponible."})

    try:
        service = obtener_servicio('gmail', 'v1')
        target_id = id_correo_o_tema.strip()

        # Si el input no parece un ID de Gmail (ej. es una búsqueda por texto o remitente)
        if len(target_id) < 15 or " " in target_id:
            busqueda = service.users().messages().list(userId='me', q=target_id, maxResults=1).execute()
            mensajes = busqueda.get('messages', [])
            if not mensajes:
                return json.dumps({"status": "error", "mensaje": f"No se encontró ningún correo con el criterio '{target_id}'."})
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

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al consultar detalle del correo: {str(e)}"})


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
    """
    if obtener_servicio is None:
        return json.dumps({"status": "error", "mensaje": "Cliente de Google Workspace no disponible."})

    try:
        service = obtener_servicio('gmail', 'v1')
        destinatario = id_correo_o_destinatario.strip()
        thread_id = None
        in_reply_to = None
        asunto_final = asunto

        # Verificar si id_correo_o_destinatario es un ID de correo existente en Gmail
        if "@" not in destinatario and len(destinatario) >= 12:
            try:
                original = service.users().messages().get(userId='me', id=destinatario, format='metadata').execute()
                thread_id = original.get('threadId')
                headers = {h['name'].lower(): h['value'] for h in original.get('payload', {}).get('headers', [])}
                
                # Obtener dirección del remitente original
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

        # Construcción del mensaje MIME
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

        # Modo Borrador vs Envío Directo
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

            # Actualizar seguimiento si correspondía a un correo pendiente
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
            "mensaje": mensaje_confirmacion
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al responder correo: {str(e)}"})


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
