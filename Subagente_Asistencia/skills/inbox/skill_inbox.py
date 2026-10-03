"""
skill_inbox.py — Triaje Inteligente y Monitoreo de Nuevos Correos en Gmail
==========================================================================
Habilidad del Subagente de Asistencia para vigilar, analizar y clasificar cada
nuevo correo entrante en tiempo real o en rutinas de tareas programadas (fleet tasks).

No genera documentos en Google Docs. Su función es analizar semánticamente cada
correo, clasificarlo en categorías estratégicas y disparar notificaciones inmediatas
cuando se detecta un correo importante para que el usuario decida si responder
o instruir al agente para que redacte la respuesta.

Categorías soportadas:
  - alerta_seguridad : Alertas de Google, accesos sospechosos, bancos, 2FA. (Prioridad: CRÍTICA)
  - respuesta_humano : Respuestas en hilos, procesos de selección, clientes, personas reales. (Prioridad: ALTA)
  - oferta_laboral   : Propuestas y vacantes de empleo (evaluando perfil técnico IA/Python).
  - beca             : Becas, bootcamps IA, subvenciones, convocatorias de formación. (Prioridad: ALTA)
  - oferta_compra    : Promociones de productos, ventas comerciales, publicidad. (Prioridad: BAJA)
  - spam             : Correo basura, phishing, boletines vacíos, notificaciones sociales masivas. (Prioridad: BAJA)
  - otro             : Transaccionales, recibos o notificaciones informativas estándar.

Herramientas disponibles:
  - tool_inbox_analizar_nuevos_correos : Monitorea y clasifica nuevos correos entrantes, notificando los prioritarios.
  - tool_inbox_clasificar_correo       : Analiza a fondo un correo específico por su ID.
  - tool_inbox_resumen_estado          : Consulta estadísticas de correos procesados y clasificación histórica.
  - obtener_prompt_inbox               : System Prompt especializado para el agente.
"""

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from langchain_core.tools import tool

# Resolver APP_ROOT de forma robusta
_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"

BASE_DIR = _APP_ROOT / _AGENTE
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROCESADOS_FILE = DATA_DIR / "correos_procesados.json"

# Importar cliente oficial de Google
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


def obtener_prompt_inbox() -> str:
    """
    System Prompt especializado y encapsulado para el Triaje y Monitoreo de Correos.
    """
    return """[🛑 HARD-STOP: MODO VIGILANCIA Y TRIAJE DE CORREOS EN TIEMPO REAL ACTIVO 🛑]
Eres el Analista de Comunicaciones y Triaje de Correos del Subagente de Asistencia.
Tu misión es analizar cada nuevo correo recibido en Gmail, clasificarlo con precisión quirúrgica y notificar al usuario de inmediato cuando detectes mensajes relevantes para que él decida si responder o pedirte que redactes la respuesta.

REGLAS DE CLASIFICACIÓN OBLIGATORIAS:
1. CATEGORÍAS DISPONIBLES:
   - alerta_seguridad : Alertas de cuentas, 2FA, accesos sospechosos o bancos. (CRÍTICA)
   - respuesta_humano : Respuestas de reclutadores, procesos de selección, clientes o personas individuales. (ALTA)
   - oferta_laboral   : Vacantes o propuestas de trabajo (indicar si coincide con perfil técnico Python/IA/Data o si se descarta).
   - beca             : Becas, aceleradoras, investigación, subvenciones o programas de IA. (ALTA)
   - oferta_compra    : Promociones de tiendas, descuentos de servicios o publicidad comercial. (BAJA)
   - spam             : Correo no deseado, newsletters masivas vacías o alertas de redes tipo 'alguien vio tu perfil'. (SILENCIAR)
   - otro             : Notificaciones transaccionales o administrativas neutras.

2. PROTOCOLO DE NOTIFICACIÓN DE CORREOS IMPORTANTES:
   - Cuando un correo sea clasificado como alerta_seguridad, respuesta_humano, beca u oferta_laboral de alto match:
     Genera una ALERTA DESTACADA con:
     * 🔔 Remitente y Asunto.
     * 🏷️ Categoría y Nivel de Prioridad.
     * 📝 Resumen conciso del mensaje (2-3 líneas).
     * 🔗 Enlace directo para abrir el correo en Gmail.
     * ❓ Pregunta de acción al usuario: "¿Deseas que prepare un borrador de respuesta o prefieres responder tú directamente?".

3. MEMORIA Y FILTRADO:
   - No repitas notificaciones de correos ya analizados.
   - El spam y ofertas de compra deben registrarse sin generar alertas molestas al usuario.
"""


# ─── Gestión de Persistencia de Correos Procesados ───────────────────────────

def _cargar_procesados() -> Dict[str, Any]:
    """Carga el registro histórico de IDs de correos procesados."""
    if PROCESADOS_FILE.exists():
        try:
            return json.loads(PROCESADOS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {"procesados": {}, "ultimo_analisis": None}
    return {"procesados": {}, "ultimo_analisis": None}


def _guardar_procesado(msg_id: str, info: Dict[str, Any]):
    """Registra un correo como procesado para no volver a notificarlo."""
    datos = _cargar_procesados()
    datos["procesados"][msg_id] = {
        "asunto": info.get("asunto", ""),
        "de": info.get("de", ""),
        "fecha": info.get("fecha", ""),
        "categoria": info.get("categoria", "otro"),
        "es_importante": info.get("es_importante", False),
        "prioridad": info.get("prioridad", "BAJA"),
        "timestamp_procesado": datetime.now().isoformat()
    }
    datos["ultimo_analisis"] = datetime.now().isoformat()

    # Limitar el historial a los últimos 500 correos para evitar crecimiento excesivo
    if len(datos["procesados"]) > 500:
        claves_ordenadas = sorted(
            datos["procesados"].keys(),
            key=lambda k: datos["procesados"][k].get("timestamp_procesado", "")
        )
        for k in claves_ordenadas[:-400]:
            del datos["procesados"][k]

    try:
        PROCESADOS_FILE.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"[Inbox Skill] Advertencia al persistir correos_procesados: {e}")


# ─── Criterios y Heurística de Triaje ─────────────────────────────────────────

PERFIL_KEYWORDS = [
    'python', 'ia', 'inteligencia artificial', 'artificial intelligence',
    'machine learning', 'deep learning', 'data', 'datos', 'analista',
    'programador', 'desarrollador', 'developer', 'engineer', 'ingeniero',
    'computer vision', 'nlp', 'backend', 'software', 'remoto', 'remote',
    'automatizacion', 'automation', 'ai', 'ml', 'fullstack', 'full stack',
    'vision', 'modelo', 'model', 'junior', 'senior', 'sistemas', 'tech',
    'tecnologia', 'ciencias', 'computer', 'analytics', 'servicenow',
    'modernization', 'cloud', 'agente', 'agent'
]

NO_PERFIL_KEYWORDS = [
    'ventas', 'sales', 'conductor', 'obrero', 'almacen', 'cajero',
    'atencion al cliente', 'secretaria', 'recepcionista', 'limpieza',
    'vigilante', 'costurera', 'operario', 'chofer', 'motorizad',
    'mensajero', 'cocinero', 'cocina', 'medico', 'médico', 'enfermera',
    'supervisor de cobranza', 'cobranza', 'abogado', 'psiquiatra',
    'trader', 'trading'
]

FALSOS_POSITIVOS_OFERTAS = [
    'ha publicado un contenido', 'perfect match', 'jobalerts', 'jobs-noreply',
    'hire feed', 'alerta de empleo', 'job alert', 'boletín', 'newsletter',
    'recomendaciones de empleo', 'empleos sugeridos', 'nuevos empleos para',
    'talento joven para', 'vacantes en', 'publicaciones destacadas',
    'novedades de tu red', 'te invitamos a conocer', 'descubre más',
    'ha aparecido en una búsqueda', 'búsqueda reciente', 'ha sido visitado',
    'descuento en todo', 'reuniones aburridas', 'hacen un buen match',
    'un solo clic', 'booyah', 'has aparecido en', 'búsquedas recientes',
    'búsquedas esta semana', 'un clic de distancia', 'a solo un clic',
    'ha publicado', 'añade a', 'nueva publicación'
]

KEYWORDS_COMPRA_PROMO = [
    'descuento', 'rebaja', 'promoción', 'promocion', 'sale', 'off',
    'black friday', 'cyber', 'cupón', 'cupon', 'oferta exclusiva',
    'compra ahora', 'tienda', 'envío gratis', 'envio gratis', 'carrito',
    'liquidación', '2x1', 'ahorra', 'oferta por tiempo limitado'
]


def _extraer_cuerpo_texto(payload: Dict[str, Any], max_chars: int = 800) -> str:
    """Extrae el contenido de texto plano del mensaje de correo."""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body += _extraer_cuerpo_texto(part, max_chars)
    elif payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body[:max_chars].strip()


def _clasificar_mensaje_individual(
    sender: str,
    subject: str,
    snippet: str,
    body: str,
    headers_dict: Dict[str, str]
) -> Dict[str, Any]:
    """
    Clasifica un correo individual en:
    - alerta_seguridad
    - respuesta_humano
    - beca
    - oferta_laboral
    - oferta_compra
    - spam
    - otro
    Determinando si es_importante y su nivel de prioridad.
    """
    texto_completo = f"{subject} {sender} {snippet} {body}".lower()
    es_hilo_respuesta = "in-reply-to" in headers_dict or "references" in headers_dict or subject.lower().startswith("re:")

    # 1. Alertas de Seguridad (Máxima Prioridad)
    if any(k in sender.lower() for k in ['accounts.google.com', 'security', 'seguridad', 'auth', 'no-reply@google.com']) and \
       any(k in texto_completo for k in ['alerta', 'contraseña', 'password', 'security', 'código de verificación', 'verificacion', 'inicio de sesión']):
        return {
            "categoria": "alerta_seguridad",
            "prioridad": "CRÍTICA",
            "es_importante": True,
            "motivo": "Alerta crítica de seguridad o verificación de cuenta",
            "accion_sugerida": "Verificar de inmediato si el acceso o solicitud fue autorizado por el usuario."
        }

    # 2. Respuestas de Personas / Procesos de Selección
    frases_respuesta = [
        'entrevista', 'interview', 'tu postulación', 'your application',
        'proceso de selección', 'assessment', 'next steps', 'siguientes pasos',
        'hemos revisado tu perfil', 'hemos recibido tu', 'we have received your',
        'application status', 'estado de tu solicitud', 'conversar contigo', 'reunión'
    ]
    if (es_hilo_respuesta or any(k in texto_completo for k in frases_respuesta)) and not any(f in texto_completo for f in FALSOS_POSITIVOS_OFERTAS):
        return {
            "categoria": "respuesta_humano",
            "prioridad": "ALTA",
            "es_importante": True,
            "motivo": "Respuesta directa de persona, cliente o seguimiento de selección laboral",
            "accion_sugerida": "Revisar detalles y decidir si responder directamente o solicitar borrador de respuesta al agente."
        }

    # 3. Becas y Oportunidades Académicas / IA
    palabras_becas = ['scholarship', 'beca', 'interview kickstart', 'bootcamp', 'fellowship', 'grant', 'mentorship', 'residency']
    if any(k in texto_completo for k in palabras_becas):
        return {
            "categoria": "beca",
            "prioridad": "ALTA",
            "es_importante": True,
            "motivo": "Convocatoria o beca de formación técnica / Inteligencia Artificial",
            "accion_sugerida": "Evaluar plazos de postulación y requisitos de la convocatoria."
        }

    # 4. Ofertas Laborales
    palabras_oferta = ['vacante', 'empleo', 'oferta', 'hiring', 'recruiter', 'reclutador', 'position', 'job', 'postula']
    portales_empleo = ['linkedin', 'computrabajo', 'indeed', 'getmanfred', 'getonbrd', 'bairesdev', 'toptal']
    
    es_portal = any(p in sender.lower() or p in texto_completo for p in portales_empleo)
    tiene_palabra_oferta = any(w in texto_completo for w in palabras_oferta)
    es_falso_positivo = any(f in texto_completo for f in FALSOS_POSITIVOS_OFERTAS)

    if (es_portal or tiene_palabra_oferta) and not es_falso_positivo:
        coincide_perfil = any(k in texto_completo for k in PERFIL_KEYWORDS) and not any(k in texto_completo for k in NO_PERFIL_KEYWORDS)
        if coincide_perfil:
            return {
                "categoria": "oferta_laboral",
                "prioridad": "ALTA",
                "es_importante": True,
                "motivo": "Oferta de trabajo alineada al perfil técnico (Python, IA, Backend, Remoto)",
                "accion_sugerida": "Revisar vacante y considerar postulación."
            }
        else:
            return {
                "categoria": "oferta_laboral",
                "prioridad": "BAJA",
                "es_importante": False,
                "motivo": "Oferta laboral fuera del perfil técnico de interés",
                "accion_sugerida": "Archivar o ignorar."
            }

    # 5. Ofertas de Compra / Promociones
    if any(c in texto_completo for c in KEYWORDS_COMPRA_PROMO):
        return {
            "categoria": "oferta_compra",
            "prioridad": "BAJA",
            "es_importante": False,
            "motivo": "Publicidad comercial, descuento o promoción de producto",
            "accion_sugerida": "Ignorar o silenciar."
        }

    # 6. Detección de Spam / Ruido Social Masivo
    if es_falso_positivo or any(s in sender.lower() for s in ['noreply', 'no-reply', 'newsletter', 'mailer', 'promotions']):
        return {
            "categoria": "spam",
            "prioridad": "BAJA",
            "es_importante": False,
            "motivo": "Boletín masivo, notificación de feed o correo no solicitado",
            "accion_sugerida": "Ignorar."
        }

    # 7. Por defecto: Otro / Administrativo
    return {
        "categoria": "otro",
        "prioridad": "MEDIA" if es_hilo_respuesta else "BAJA",
        "es_importante": es_hilo_respuesta,
        "motivo": "Correo administrativo o transaccional estándar",
        "accion_sugerida": "Revisar si es relevante."
    }


# ─── Herramientas Principales ─────────────────────────────────────────────────

@tool
def tool_inbox_analizar_nuevos_correos(
    max_correos: int = 15,
    solo_no_leidos: bool = True
) -> str:
    """
    Monitorea y analiza los correos más recientes en Gmail que no hayan sido analizados previamente.
    Clasifica cada correo (spam, oferta_laboral, oferta_compra, beca, respuesta_humano, alerta_seguridad),
    evalúa si es importante y genera notificaciones inmediatas solo para los correos prioritarios,
    permitiendo al usuario decidir si responder o solicitar que el agente redacte una respuesta.

    Args:
        max_correos: Cantidad máxima de correos a inspeccionar (por defecto 15).
        solo_no_leidos: Si es True, filtra la búsqueda en Gmail con 'is:unread'.
    """
    if obtener_servicio is None:
        return "Error: El cliente de autenticación de Google Workspace no está disponible."

    try:
        service = obtener_servicio('gmail', 'v1')
        historial = _cargar_procesados()
        procesados_ids = set(historial.get("procesados", {}).keys())

        query = "label:INBOX is:unread" if solo_no_leidos else "label:INBOX"
        results = service.users().messages().list(
            userId='me', q=query, maxResults=min(max_correos, 30)
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            return "📭 No hay correos nuevos pendientes de análisis en la bandeja de entrada."

        nuevos_analizados = []
        alertas_importantes = []
        conteo_categorias = {}

        for msg in messages:
            msg_id = msg['id']
            if msg_id in procesados_ids:
                continue  # Ya fue analizado y notificado previamente

            try:
                det = service.users().messages().get(
                    userId='me', id=msg_id, format='full'
                ).execute()

                headers = det.get('payload', {}).get('headers', [])
                headers_dict = {h['name'].lower(): h['value'] for h in headers}

                subject = headers_dict.get('subject', '(Sin asunto)')
                sender = headers_dict.get('from', '(Desconocido)')
                date = headers_dict.get('date', '')[:22].strip()
                snippet = det.get('snippet', '')
                body = _extraer_cuerpo_texto(det.get('payload', {}))

                # Clasificar con heurística avanzada
                clasif = _clasificar_mensaje_individual(sender, subject, snippet, body, headers_dict)
                cat = clasif["categoria"]
                es_imp = clasif["es_importante"]
                prio = clasif["prioridad"]

                conteo_categorias[cat] = conteo_categorias.get(cat, 0) + 1

                info_registro = {
                    "id": msg_id,
                    "asunto": subject,
                    "de": sender,
                    "fecha": date,
                    "snippet": snippet,
                    "categoria": cat,
                    "es_importante": es_imp,
                    "prioridad": prio,
                    "motivo": clasif["motivo"],
                    "accion_sugerida": clasif["accion_sugerida"]
                }

                # Registrar en base de datos local para no repetir
                _guardar_procesado(msg_id, info_registro)
                nuevos_analizados.append(info_registro)

                if es_imp:
                    alertas_importantes.append(info_registro)

            except Exception as item_err:
                print(f"[Inbox Skill] Error al procesar correo {msg_id}: {item_err}")
                continue

        if not nuevos_analizados:
            return "📭 Todos los correos en la bandeja ya han sido analizados y clasificados previamente."

        # Construir entrega ejecutiva para el usuario
        salida = [f"📬 **Monitoreo de Bandeja de Entrada — {len(nuevos_analizados)} nuevo(s) correo(s) analizado(s)**\n"]

        # Si se detectaron correos importantes, generar alertas ejecutivas destacadas
        if alertas_importantes:
            salida.append(f"🚨 **¡ATENCIÓN! Se detectaron {len(alertas_importantes)} correo(s) prioritario(s):**\n")
            for a in alertas_importantes:
                icono = "🚨" if a["prioridad"] == "CRÍTICA" else "🔔"
                salida.append(f"{icono} **[{a['prioridad']}] {a['asunto']}**")
                salida.append(f"   • **De:** {a['de']}")
                salida.append(f"   • **Categoría:** `{a['categoria']}` ({a['motivo']})")
                salida.append(f"   • **Resumen:** {a['snippet'][:180]}...")
                salida.append(f"   • **Acción Sugerida:** {a['accion_sugerida']}")
                salida.append(f"   • 🔗 **Abrir en Gmail:** https://mail.google.com/mail/u/0/#inbox/{a['id']}")
                salida.append(f"   • 💬 *¿Deseas que redacte una propuesta de respuesta o prefieres gestionarlo tú directamente?*\n")

        # Resumen cuantitativo del resto (spam, compras, etc.)
        resto_conteo = [f"{k}: {v}" for k, v in conteo_categorias.items() if not any(a["categoria"] == k for a in alertas_importantes)]
        if resto_conteo:
            salida.append(f"ℹ️ **Correos de baja prioridad o silenciados:** {', '.join(resto_conteo)}.")

        return "\n".join(salida)

    except Exception as e:
        return f"Error al monitorear correos en Gmail: {str(e)}"


@tool
def tool_inbox_clasificar_correo(correo_id: str) -> str:
    """
    Inspecciona y clasifica un correo específico dado su ID de Gmail.
    Devuelve la categoría, nivel de prioridad, motivo de clasificación y enlace de apertura.

    Args:
        correo_id: Identificador alfanumérico del mensaje en Gmail.
    """
    if obtener_servicio is None:
        return "Error: El cliente de autenticación de Google Workspace no está disponible."

    try:
        service = obtener_servicio('gmail', 'v1')
        det = service.users().messages().get(userId='me', id=correo_id, format='full').execute()

        headers = det.get('payload', {}).get('headers', [])
        headers_dict = {h['name'].lower(): h['value'] for h in headers}

        subject = headers_dict.get('subject', '(Sin asunto)')
        sender = headers_dict.get('from', '(Desconocido)')
        date = headers_dict.get('date', '')
        snippet = det.get('snippet', '')
        body = _extraer_cuerpo_texto(det.get('payload', {}))

        clasif = _clasificar_mensaje_individual(sender, subject, snippet, body, headers_dict)

        return (
            f"📧 **Análisis del Correo ID:** `{correo_id}`\n"
            f"- **Asunto:** {subject}\n"
            f"- **De:** {sender}\n"
            f"- **Fecha:** {date}\n"
            f"- **Categoría:** `{clasif['categoria']}`\n"
            f"- **Prioridad:** {clasif['prioridad']}\n"
            f"- **Es Importante:** {'Sí' if clasif['es_importante'] else 'No'}\n"
            f"- **Motivo:** {clasif['motivo']}\n"
            f"- **Acción Sugerida:** {clasif['accion_sugerida']}\n"
            f"- 🔗 **Enlace:** https://mail.google.com/mail/u/0/#inbox/{correo_id}"
        )
    except Exception as e:
        return f"Error al clasificar correo {correo_id}: {str(e)}"


@tool
def tool_inbox_resumen_estado() -> str:
    """
    Consulta las estadísticas generales de correos analizados y almacenados en la memoria local del subagente.
    """
    historial = _cargar_procesados()
    procesados = historial.get("procesados", {})
    total = len(procesados)
    ultimo = historial.get("ultimo_analisis", "Sin registros previos")

    conteo = {}
    importantes = 0
    for p in procesados.values():
        c = p.get("categoria", "otro")
        conteo[c] = conteo.get(c, 0) + 1
        if p.get("es_importante"):
            importantes += 1

    desglose = "\n".join([f"  - `{k}`: {v}" for k, v in conteo.items()]) if conteo else "  (Sin correos en memoria)"

    return (
        f"📊 **Estado del Triaje de Correos:**\n"
        f"- **Total Correos en Registro Local:** {total}\n"
        f"- **Correos Importantes Notificados:** {importantes}\n"
        f"- **Último Análisis Ejecutado:** {ultimo}\n"
        f"- **Desglose por Categoría:**\n{desglose}"
    )


# Alias de retrocompatibilidad
tool_inbox_gmail = tool_inbox_analizar_nuevos_correos
