"""
skill_google.py — Núcleo de Integración y Autenticación de Google Workspace
===========================================================================
Módulo central de autenticación OAuth 2.0 y factoría de clientes de API para todo
el ecosistema de Google Workspace en el Subagente de Asistencia:
  - Gmail (lectura, filtrado y envío de correos)
  - Google Calendar (consulta de agenda, creación de citas y reuniones)
  - Google Drive & Docs (búsqueda, lectura y creación de documentos)

Proporciona la base de conexión compartida para las habilidades especializadas
de Docs, Calendar, Drive e Inbox.
"""

import os
import sys
import base64
from pathlib import Path
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"

# Carga segura de dependencias de Google
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    Request = None
    Credentials = None
    build = None

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
]


def _resolver_ruta_credencial(nombre_archivo: str) -> Path:
    """
    Busca de forma jerárquica y agnóstica el archivo de credencial o token
    en las rutas estándar del workspace y del contenedor Docker.
    """
    candidatos = [
        # 1. Variable de entorno explícita
        os.getenv(f"GOOGLE_{nombre_archivo.upper().replace('.', '_')}_PATH"),
        # 2. Carpeta data del Subagente de Asistencia
        _APP_ROOT / _AGENTE / "data" / nombre_archivo,
        # 3. Carpeta data del Agente Orquestador (donde se conserva el token canónico)
        _APP_ROOT / "Agente_Orquestador" / "data" / nombre_archivo,
        # 4. Rutas en contenedor Docker /app
        Path(f"/app/{_AGENTE}/data/{nombre_archivo}"),
        Path(f"/app/Agente_Orquestador/data/{nombre_archivo}"),
    ]
    for c in candidatos:
        if c:
            p = Path(c)
            if p.exists() and p.is_file():
                return p

    # Fallback predeterminado a data de Asistencia
    return _APP_ROOT / _AGENTE / "data" / nombre_archivo


def obtener_prompt_google_core() -> str:
    """
    System Prompt especializado y encapsulado para el Administrador de Conexión de Google Workspace.
    """
    return """[🛑 HARD-STOP: MODO ADMINISTRACIÓN DE GOOGLE WORKSPACE ACTIVO 🛑]
Eres el Administrador de Integración y Servicios de Google Workspace del Subagente de Asistencia.
Tu misión es gestionar la autenticación OAuth 2.0 y despachar las operaciones sobre Gmail, Calendar, Docs y Drive con el más alto estándar de seguridad y privacidad de datos.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRIVACIDAD Y ÉTICA DE DATOS:
   - Toda información leída desde correos electrónicos, calendarios o documentos de Drive pertenece estrictamente al Usuario.
   - Prohibido filtrar o compartir contenidos de correos o citas en canales no autorizados.
2. CONFIRMACIÓN PREVIA PARA ENVÍOS Y MODIFICACIONES:
   - Las operaciones de LECTURA (consultar bandeja de entrada, listar eventos de calendario, buscar archivos en Drive) son autónomas.
   - Toda operación de ESCRITURA CON IMPACTO EXTERNO (enviar correos electrónicos a terceros, eliminar archivos o sobrescribir documentos públicos) debe contar con validación clara del objetivo.
3. PROTOCOLO ANTE TOKEN EXPIRADO:
   - Si una llamada arroja error de autenticación (401 Unauthorized o Token Expired), invoca el flujo de refresco automático. Si el token no es renovable por requerir navegador, notifica con claridad las instrucciones de renovación al usuario.
"""


def obtener_credenciales() -> Optional[Any]:
    """
    Gestiona y retorna las credenciales activas de Google OAuth 2.0.
    Si el token expiró pero tiene refresh_token, lo renueva automáticamente.
    """
    if not GOOGLE_LIBS_AVAILABLE:
        raise RuntimeError("Las librerías de Google (google-auth, google-api-python-client) no están disponibles en el entorno.")

    token_file = _resolver_ruta_credencial("token.json")
    credentials_file = _resolver_ruta_credencial("credentials.json")

    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            print(f"[Google Auth] Error leyendo {token_file.name}: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[Google Auth] Error al refrescar token: {e}")
                creds = None

        if not creds:
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"No se encontró el archivo de credenciales 'credentials.json'. "
                    f"Buscado en: {_APP_ROOT / _AGENTE / 'data'} y {_APP_ROOT / 'Agente_Orquestador' / 'data'}."
                )
            raise RuntimeError(
                "⚠️ TOKEN EXPIRADO: El token de Google OAuth ha caducado y requiere re-autenticación. "
                "Ejecuta 'python renovar_token_google.py' en la máquina host para regenerar token.json."
            )

        # Guardar token renovado
        try:
            token_file.parent.mkdir(parents=True, exist_ok=True)
            token_file.write_text(creds.to_json(), encoding="utf-8")
        except Exception as e:
            print(f"[Google Auth] Advertencia al persistir token renovado: {e}")

    return creds


def obtener_servicio(service_name: str, version: str) -> Any:
    """
    Retorna una instancia del cliente de servicio de Google API oficial construida con credenciales válidas.
    """
    creds = obtener_credenciales()
    return build(service_name, version, credentials=creds, cache_discovery=False)


# ══════════════════════════════════════════════════════════════════════════════
# SERVICIOS BÁSICOS DE GOOGLE WORKSPACE (UTILIDADES COMPARTIDAS)
# ══════════════════════════════════════════════════════════════════════════════

def gmail_listar_no_leidos(max_results: int = 5) -> List[Dict[str, Any]]:
    """Lista los correos no leídos más recientes en la bandeja de entrada."""
    service = obtener_servicio('gmail', 'v1')
    results = service.users().messages().list(
        userId='me', q='is:unread in:inbox', maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    lista_correos = []

    for msg in messages:
        detalle = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = detalle.get('payload', {}).get('headers', [])

        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(Sin asunto)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Desconocido')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        snippet = detalle.get('snippet', '')

        lista_correos.append({
            'id': msg['id'],
            'threadId': msg.get('threadId'),
            'remitente': sender,
            'asunto': subject,
            'fecha': date,
            'resumen': snippet
        })

    return lista_correos


def gmail_enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> Dict[str, Any]:
    """Envía un correo electrónico mediante la cuenta de Gmail autorizada."""
    service = obtener_servicio('gmail', 'v1')
    mensaje = MIMEText(cuerpo)
    mensaje['to'] = destinatario
    mensaje['subject'] = asunto

    raw_message = base64.urlsafe_b64encode(mensaje.as_bytes()).decode('utf-8')
    body = {'raw': raw_message}

    sent_message = service.users().messages().send(userId='me', body=body).execute()
    return {"status": "enviado", "id": sent_message['id']}


def calendar_listar_eventos(dias_futuros: int = 7) -> List[Dict[str, Any]]:
    """Lista los próximos eventos del calendario para los siguientes N días."""
    service = obtener_servicio('calendar', 'v3')
    ahora = datetime.now(timezone.utc).isoformat()
    limite = (datetime.now(timezone.utc) + timedelta(days=dias_futuros)).isoformat()

    events_result = service.events().list(
        calendarId='primary', timeMin=ahora, timeMax=limite,
        singleEvents=True, orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    lista_eventos = []

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        lista_eventos.append({
            'id': event['id'],
            'titulo': event.get('summary', '(Sin título)'),
            'inicio': start,
            'fin': end,
            'descripcion': event.get('description', ''),
            'ubicacion': event.get('location', '')
        })

    return lista_eventos


def calendar_agendar_evento(
    titulo: str,
    inicio_iso: str,
    fin_iso: str,
    descripcion: str = "",
    ubicacion: str = ""
) -> Dict[str, Any]:
    """Agenda una nueva cita o reunión en el Google Calendar principal."""
    service = obtener_servicio('calendar', 'v3')
    evento_body = {
        'summary': titulo,
        'location': ubicacion,
        'description': descripcion,
        'start': {'dateTime': inicio_iso, 'timeZone': 'America/Caracas'},
        'end': {'dateTime': fin_iso, 'timeZone': 'America/Caracas'},
        'reminders': {'useDefault': True},
    }

    event = service.events().insert(calendarId='primary', body=evento_body).execute()
    return {"status": "agendado", "id": event.get('id'), "link": event.get('htmlLink')}


def drive_buscar_archivos(query: str = "", max_results: int = 10, order_by: str = "") -> List[Dict[str, Any]]:
    """Busca archivos en Google Drive por nombre o filtro."""
    service = obtener_servicio('drive', 'v3')
    q_str = f"name contains '{query}' and trashed = false" if query else "trashed = false"

    results = service.files().list(
        q=q_str, pageSize=max_results, fields="files(id, name, mimeType, modifiedTime, size, quotaBytesUsed)", orderBy=order_by
    ).execute()

    return results.get('files', [])


def docs_crear_documento(titulo: str, contenido: str = "") -> Dict[str, Any]:
    """Crea un nuevo documento en Google Docs e inserta el contenido inicial."""
    docs_service = obtener_servicio('docs', 'v1')
    doc = docs_service.documents().create(body={'title': titulo}).execute()
    doc_id = doc.get('documentId')

    if contenido:
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': contenido
            }
        }]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

    return {"status": "creado", "documentId": doc_id, "titulo": titulo}


__all__ = [
    "obtener_credenciales",
    "obtener_servicio",
    "obtener_prompt_google_core",
    "gmail_listar_no_leidos",
    "gmail_enviar_correo",
    "calendar_listar_eventos",
    "calendar_agendar_evento",
    "drive_buscar_archivos",
    "docs_crear_documento",
]
