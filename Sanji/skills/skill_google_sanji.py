"""
skill_google_sanji.py — Módulo de Integración de Google Workspace para Sanji
=============================================================================
Este módulo otorga a Sanji acceso a la API de Google Workspace:
  - Gmail (lectura, respuesta, envío de correos)
  - Google Calendar (consulta de agenda, creación de citas y reuniones)
  - Google Drive & Docs (búsqueda, lectura y creación de documentos)
  - Google Keep (notas y listas rápidas)
"""
import os
import sys
from pathlib import Path
# Resolver APP_ROOT de forma robusta: si la ruta calculada no existe (bind-mount Windows),
# usar /app (ruta canónica del contenedor Docker)
_APP_ROOT_CALC = Path(__file__).resolve().parents[2]
_APP_ROOT = Path("/app") if not (_APP_ROOT_CALC / "Sanji").exists() else _APP_ROOT_CALC

import os
import sys
import base64
from pathlib import Path
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ─── Configuración de Rutas y Scopes ──────────────────────────────────────────
BASE_DIR         = (_APP_ROOT / "Sanji")
CREDENTIALS_FILE = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", str(BASE_DIR / "data" / "credentials.json")))
TOKEN_FILE       = Path(os.getenv("GOOGLE_TOKEN_PATH", str(BASE_DIR / "data" / "token.json")))

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
]


# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTENTICACIÓN Y SERVICIOS
# ══════════════════════════════════════════════════════════════════════════════


def obtener_credenciales() -> Credentials:
    """
    Gestiona y retorna las credenciales de Google OAuth 2.0.
    Si token.json no existe o expiró, inicia la renovación o el login local.
    """
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"[Google Auth] Error leyendo token.json: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[Google Auth] Error refrescando token: {e}")
                creds = None

        if not creds:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"No se encontró el archivo de credenciales en {CREDENTIALS_FILE}. "
                    "Asegúrate de colocar credentials.json en esa ruta."
                )
            raise RuntimeError(
                "⚠️ TOKEN EXPIRADO: El token de Google OAuth ha caducado y no puede renovarse "
                "automáticamente desde Docker (no hay navegador disponible). "
                "Para renovarlo, ejecuta en tu máquina Windows: "
                "  python renovar_token_google.py  "
                "El archivo token.json se actualizará y Sanji podrá continuar."
            )

        with open(TOKEN_FILE, 'w', encoding='utf-8') as token_out:
            token_out.write(creds.to_json())

    return creds


def obtener_servicio(service_name: str, version: str):
    """Retorna un servicio de API de Google construido con las credenciales activas."""
    creds = obtener_credenciales()
    return build(service_name, version, credentials=creds)


# ══════════════════════════════════════════════════════════════════════════════
# 2. FUNCIONES DE GMAIL
# ══════════════════════════════════════════════════════════════════════════════

def gmail_listar_no_leidos(max_results: int = 5) -> list[dict]:
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


def gmail_enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> dict:
    """Envía un correo electrónico mediante la cuenta de Gmail autorizada."""
    service = obtener_servicio('gmail', 'v1')
    mensaje = MIMEText(cuerpo)
    mensaje['to'] = destinatario
    mensaje['subject'] = asunto
    
    raw_message = base64.urlsafe_b64encode(mensaje.as_bytes()).decode('utf-8')
    body = {'raw': raw_message}
    
    sent_message = service.users().messages().send(userId='me', body=body).execute()
    return {"status": "enviado", "id": sent_message['id']}


# ══════════════════════════════════════════════════════════════════════════════
# 3. FUNCIONES DE GOOGLE CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

def calendar_listar_eventos(dias_futuros: int = 7) -> list[dict]:
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
) -> dict:
    """
    Agenda una nueva cita o reunión en el Google Calendar principal.
    Formato de fecha: 'YYYY-MM-DDTHH:MM:SS' (ISO string).
    """
    service = obtener_servicio('calendar', 'v3')
    evento_body = {
        'summary': titulo,
        'location': ubicacion,
        'description': descripcion,
        'start': {
            'dateTime': inicio_iso,
            'timeZone': 'America/Caracas', # Ajustado según zona horaria local (-04:00)
        },
        'end': {
            'dateTime': fin_iso,
            'timeZone': 'America/Caracas',
        },
        'reminders': {
            'useDefault': True,
        },
    }

    event = service.events().insert(calendarId='primary', body=evento_body).execute()
    return {"status": "agendado", "id": event.get('id'), "link": event.get('htmlLink')}


# ══════════════════════════════════════════════════════════════════════════════
# 4. FUNCIONES DE GOOGLE DRIVE & DOCS
# ══════════════════════════════════════════════════════════════════════════════

def drive_buscar_archivos(query: str = "", max_results: int = 10, order_by: str = "") -> list[dict]:
    """Busca archivos en Google Drive por nombre o filtro. Para ordenar por tamaño usar order_by='quotaBytesUsed desc'."""
    service = obtener_servicio('drive', 'v3')
    q_str = f"name contains '{query}' and trashed = false" if query else "trashed = false"
    
    results = service.files().list(
        q=q_str, pageSize=max_results, fields="files(id, name, mimeType, modifiedTime, size, quotaBytesUsed)", orderBy=order_by
    ).execute()
    
    return results.get('files', [])


def docs_crear_documento(titulo: str, contenido: str = "") -> dict:
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


# ══════════════════════════════════════════════════════════════════════════════
# 5. FUNCIONES DE GOOGLE KEEP (vía gkeepapi)
# ══════════════════════════════════════════════════════════════════════════════

KEEP_TOKEN_FILE = BASE_DIR / "keep_token.txt"

def keep_conectar(email: str = None, app_password: str = None):
    """
    Conecta con Google Keep mediante gkeepapi.
    Utiliza keep_token.txt persistente o autentica con email y contraseña de aplicación.
    """
    try:
        import gkeepapi
    except ImportError:
        raise ImportError("La librería gkeepapi no está instalada. Ejecuta `pip install gkeepapi`.")

    import os
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR.parent / ".env")
    except ImportError:
        pass

    email = email or os.getenv("KEEP_EMAIL")
    app_password = app_password or os.getenv("KEEP_APP_PASSWORD")

    keep = gkeepapi.Keep()
    
    if KEEP_TOKEN_FILE.exists():
        token = KEEP_TOKEN_FILE.read_text(encoding="utf-8").strip()
        try:
            keep.resume(email or "me", token)
            return keep
        except Exception as e:
            print(f"[Keep Auth] Error reanudando token de Keep: {e}")

    if email and app_password:
        try:
            keep.authenticate(email, app_password)
        except Exception:
            keep.login(email, app_password)
        master_token = keep.getMasterToken()
        KEEP_TOKEN_FILE.write_text(master_token, encoding="utf-8")
        return keep
    else:
        raise ValueError("Se requiere email y Contraseña de Aplicación de Google para iniciar sesión por primera vez en Keep.")


def keep_crear_nota(titulo: str, texto: str, email: str = None, app_password: str = None) -> dict:
    """Crea una nueva nota en tu cuenta personal de Google Keep."""
    keep = keep_conectar(email, app_password)
    note = keep.createNote(titulo, texto)
    keep.sync()
    return {"status": "creada", "id": note.id, "titulo": titulo}


def keep_listar_notas(max_results: int = 10, email: str = None, app_password: str = None) -> list[dict]:
    """Lista las notas activas más recientes en tu Google Keep."""
    keep = keep_conectar(email, app_password)
    keep.sync()
    gnotes = list(keep.all())[:max_results]
    return [{"id": n.id, "titulo": n.title, "texto": n.text} for n in gnotes]


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DIRECTA VIA CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Probando Habilidad Google de Sanji ===")
    try:
        creds = obtener_credenciales()
        print("[OK] Credenciales autenticadas exitosamente.")
        
        print("\n--- Consultando Próximos Eventos del Calendario ---")
        evs = calendar_listar_eventos(dias_futuros=7)
        print(f"Eventos encontrados: {len(evs)}")
        for e in evs:
            print(f"  * [{e['inicio']}] {e['titulo']}")
            
        print("\n--- Consultando Correos No Leídos ---")
        msgs = gmail_listar_no_leidos(max_results=3)
        print(f"Correos no leídos: {len(msgs)}")
        for m in msgs:
            print(f"  * De: {m['remitente']} | Asunto: {m['asunto']}")

    except Exception as err:
        print(f"[ERROR] Error durante la ejecucion: {err}")
