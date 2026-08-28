"""
skill_inbox_luffy.py — Skill de Análisis de Bandeja de Entrada para Luffy
=========================================================================
Analiza el inbox de Gmail, clasifica correos por categorías relevantes al
perfil del usuario y genera un informe profesional.

Modos de salida:
  - generar_informe_google_docs() → Google Doc con tabla en resumen ejecutivo
                                    (siempre el mismo documento, se sobreescribe)
  - generar_informe_local()       → Archivo .md en Luffy/informes/

Categorías:
  - Alertas de seguridad
  - Becas y oportunidades de IA
  - Cursos y formación
  - Ofertas laborales acordes al perfil de Wuil
  - Ofertas laborales descartadas
  - Otros
"""
import os
import sys
from pathlib import Path
# Resolver APP_ROOT de forma robusta: si la ruta calculada no existe (bind-mount Windows),
# usar /app (ruta canónica del contenedor Docker)
_APP_ROOT_CALC = Path(__file__).resolve().parents[2]
_APP_ROOT = Path("/app") if not (_APP_ROOT_CALC / "Luffy").exists() else _APP_ROOT_CALC

import sys
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from skill_google_sanji import obtener_servicio

BASE_DIR    = (_APP_ROOT / "Luffy")
REPORT_DIR  = BASE_DIR / "informes"
DOC_ID_FILE = BASE_DIR / "data" / "inbox_report_doc_id.txt"
REPORT_DIR.mkdir(exist_ok=True)

# ─── Perfil de Wuil: palabras clave que SÍ aplican ───────────────────────────
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

# ─── Palabras clave que NO aplican al perfil ─────────────────────────────────
NO_PERFIL_KEYWORDS = [
    'ventas', 'sales', 'conductor', 'obrero', 'almacen', 'cajero',
    'atencion al cliente', 'secretaria', 'recepcionista', 'limpieza',
    'vigilante', 'costurera', 'operario', 'chofer', 'motorizad',
    'mensajero', 'cocinero', 'cocina', 'medico', 'médico', 'enfermera',
    'supervisor de cobranza', 'cobranza', 'abogado', 'psiquiatra',
    'trader', 'trading'
]

# ─── Detectores de categorías ─────────────────────────────────────────────────

def _es_alerta(sender, texto):
    return 'accounts.google.com' in sender.lower() and \
           any(k in texto for k in ['alerta', 'contraseña', 'password', 'security'])

def _es_beca(sender, texto):
    return any(k in texto for k in
               ['scholarship', 'beca', 'interview kickstart', 'bootcamp',
                'maang', 'faang', 'grant', 'fellowship', '1:1', 'mentorship'])

def _es_curso(sender, texto):
    return any(k in sender.lower() or k in texto for k in
               ['coursera', 'worldquant', 'udemy', 'platzi', 'edx',
                'datacamp', 'deeplearning', 'fast.ai', 'aprender'])

# ─── Palabras clave de notificaciones genéricas (falsos positivos) ───────────
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

def _es_oferta(sender, texto):
    # Descartamos si es una alerta automática o contenido de feed
    if any(f in texto for f in FALSOS_POSITIVOS_OFERTAS):
        return False
        
    return any(k in sender.lower() or k in texto for k in
               ['linkedin', 'computrabajo', 'indeed', 'getmanfred', 'getonbrd',
                'vacante', 'empleo', 'oferta', 'hiring', 'recruiter', 'reclutador',
                'position', 'job', 'career', 'postula', 'loft', 'bairesdev'])

def _es_respuesta_empresa(sender, texto):
    if any(f in texto for f in FALSOS_POSITIVOS_OFERTAS):
        return False
    return any(k in texto for k in [
        'entrevista', 'interview', 'tu postulación', 'your application', 
        'proceso de selección', 'assessment', 'next steps', 'siguientes pasos',
        'hemos revisado tu perfil', 'hemos recibido tu', 'we have received your',
        'application status', 'estado de tu solicitud'
    ])

def _aplica_perfil(texto):
    return any(k in texto for k in PERFIL_KEYWORDS) and \
           not any(k in texto for k in NO_PERFIL_KEYWORDS)

def _get_body(payload, max_chars=600):
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body += _get_body(part, max_chars)
    elif payload.get('mimeType') == 'text/plain':
        data = payload['body'].get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body[:max_chars].strip()


# ─── Clasificación principal ──────────────────────────────────────────────────
def _clasificar_inbox(max_results: int = 100) -> tuple:
    service = obtener_servicio('gmail', 'v1')
    print(f"[Inbox Skill] Obteniendo los {max_results} correos más recientes...")
    results = service.users().messages().list(
        userId='me', labelIds=['INBOX'], maxResults=max_results
    ).execute()
    messages = results.get('messages', [])
    print(f"[Inbox Skill] {len(messages)} correos obtenidos. Clasificando...")

    cats = {
        "alertas": [], "respuestas": [], "becas": [], "cursos": [],
        "ofertas_ok": [], "ofertas_no": [], "otros": []
    }

    for i, msg in enumerate(messages):
        det = service.users().messages().get(
            userId='me', id=msg['id'], format='full'
        ).execute()
        headers = det.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(Sin asunto)')
        sender  = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        date    = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        snippet = det.get('snippet', '')
        body    = _get_body(det.get('payload', {}))
        texto   = (subject + " " + sender + " " + snippet + " " + body).lower()

        entry = {
            "id": msg['id'],
            "asunto": subject, "de": sender,
            "fecha": date[:22].strip(),
            "snippet": snippet[:160].strip(),
            "body": body
        }

        if _es_alerta(sender, texto):       cats["alertas"].append(entry)
        elif _es_respuesta_empresa(sender, texto): cats["respuestas"].append(entry)
        elif _es_beca(sender, texto):       cats["becas"].append(entry)
        elif _es_curso(sender, texto):      cats["cursos"].append(entry)
        elif _es_oferta(sender, texto):
            if _aplica_perfil(texto):       cats["ofertas_ok"].append(entry)
            else:                           cats["ofertas_no"].append(entry)
        else:                               cats["otros"].append(entry)

        if (i + 1) % 20 == 0:
            print(f"  → Procesados {i+1}/{len(messages)}...")

    return cats, len(messages)


# ─── Construcción del informe ─────────────────────────────────────────────────
def _build_informe(cats: dict, total: int):
    """Construye el informe con ProDocBuilder incluyendo tabla, estilos, espaciado y saltos de página."""
    from skill_google_docs_sanji import ProDocBuilder
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    doc = ProDocBuilder()

    doc.h1("Informe de Bandeja de Entrada", space_below=10)
    doc.para(f"Generado: {now}   |   Total analizado: {total} correos   |   Agente: Luffy", font_size=10, italic=True, space_below=20)

    # Resumen ejecutivo con tabla nativa
    doc.h2("Resumen ejecutivo", space_below=10)
    doc.table(
        headers=["Categoría", "Cantidad"],
        rows=[
            ["Alertas de seguridad",        str(len(cats['alertas']))],
            ["Respuestas de empresas",      str(len(cats['respuestas']))],
            ["Becas y oportunidades de IA", str(len(cats['becas']))],
            ["Ofertas acordes al perfil",    str(len(cats['ofertas_ok']))],
        ]
    )
    doc.blank()

    def _render_section(titulo, items, show_body=False, body_limit=300):
        doc.page_break()
        doc.h2(f"{titulo}  ({len(items)})", space_above=20, space_below=15)
        if not items:
            doc.para("Ningún correo en esta categoría.", italic=True, space_below=10)
            return

        for e in items:
            doc.h3(e['asunto'], space_below=4)
            doc.para(f"De: {e['de']}  |  Fecha: {e['fecha']}", font_size=10, italic=True, space_below=2)
            doc.para(f"Enlace: https://mail.google.com/mail/u/0/#inbox/{e['id']}", font_size=10, italic=True, space_below=6)
            doc.para(e['snippet'], space_below=10 if not (show_body and e['body']) else 4)
            if show_body and e['body']:
                doc.para(e['body'][:body_limit] + "...", font_size=9, space_below=15)
            else:
                doc.blank()

    # Renderizar secciones con estilos de espaciado
    _render_section("Alertas de seguridad", cats['alertas'], show_body=True, body_limit=300)
    _render_section("Respuestas de empresas", cats['respuestas'], show_body=True, body_limit=400)
    _render_section("Becas y oportunidades de IA", cats['becas'], show_body=True, body_limit=400)
    
    doc.page_break()
    doc.h2(f"Ofertas laborales acordes al perfil  ({len(cats['ofertas_ok'])})", space_above=20, space_below=5)
    doc.para("Filtradas por: Python, IA, Data, Ingeniería de Sistemas, Developer, Remoto, ML, NLP, Cloud, Automatización.", font_size=10, italic=True, space_below=15)
    if cats['ofertas_ok']:
        for e in cats['ofertas_ok']:
            doc.h3(e['asunto'], space_below=4)
            doc.para(f"De: {e['de']}  |  Fecha: {e['fecha']}", font_size=10, italic=True, space_below=2)
            doc.para(f"Enlace: https://mail.google.com/mail/u/0/#inbox/{e['id']}", font_size=10, italic=True, space_below=6)
            doc.para(e['snippet'], space_below=15)
    else:
        doc.para("Sin ofertas acordes al perfil.", italic=True)

    return doc


# ─── Generar informe en Google Docs ──────────────────────────────────────────
def generar_informe_google_docs(max_results: int = 100) -> str:
    from skill_google_docs_sanji import DocManager

    cats, total = _clasificar_inbox(max_results)
    doc_builder = _build_informe(cats, total)

    dm = DocManager(
        title="Informe de Bandeja de Entrada — Luffy",
        id_file=str(DOC_ID_FILE)
    )
    url = dm.publicar(doc_builder)
    print(f"\n[Inbox Skill] Informe disponible en: {url}")
    return url


# ─── Generar informe local (.md) ─────────────────────────────────────────────
def generar_informe_local(max_results: int = 100) -> str:
    cats, total = _clasificar_inbox(max_results)
    now  = datetime.now()
    ruta = REPORT_DIR / "informe_inbox.md"

    lines = [
        "# Informe de Bandeja de Entrada — EL INFORME",
        f"**GENERADO EL:** {now.strftime('%Y-%m-%d %H:%M:%S')} | Total correos analizados: {total} | Agente: Luffy\n",
        "## Resumen",
        f"- Alertas de seguridad: {len(cats['alertas'])}",
        f"- Respuestas de empresas: {len(cats['respuestas'])}",
        f"- Becas y oportunidades de IA: {len(cats['becas'])}",
        f"- Ofertas acordes al perfil: {len(cats['ofertas_ok'])}\n"
    ]
    for key, titulo in [
        ('alertas', 'Alertas de Seguridad'), ('respuestas', 'Respuestas de Empresas'),
        ('becas', 'Becas y Oportunidades de IA'), ('ofertas_ok', 'Ofertas Acordes al Perfil')
    ]:
        lines.append(f"## {titulo} ({len(cats[key])})")
        for e in cats[key]:
            lines += [
                f"### {e['asunto']}", 
                f"De: {e['de']} | {e['fecha']}", 
                f"[Abrir en Gmail](https://mail.google.com/mail/u/0/#inbox/{e['id']})", 
                e['snippet'], 
                ""
            ]

    ruta.write_text("\n".join(lines), encoding='utf-8')
    print(f"[Inbox Skill] Informe local generado: {ruta}")
    return str(ruta)


from langchain_core.tools import tool

from langchain_core.tools import tool

@tool
def tool_inbox_gmail(max_results: int = 50) -> str:
    """
    Herramienta atómica para leer y extraer los correos de la bandeja de entrada (inbox) de Gmail.
    Clasifica los correos y devuelve un resumen estructurado en texto plano.
    No genera ni guarda documentos automáticamente; el agente debe usar otras herramientas si desea guardar esto.
    """
    try:
        cats, total = _clasificar_inbox(max_results)
        lines = [f"Total correos analizados: {total}\n"]
        for key, titulo in [
            ('alertas', 'Alertas de Seguridad'), ('respuestas', 'Respuestas de Empresas'),
            ('becas', 'Becas y Oportunidades de IA'), ('ofertas_ok', 'Ofertas Acordes al Perfil')
        ]:
            if cats[key]:
                lines.append(f"## {titulo} ({len(cats[key])})")
                for e in cats[key]:
                    lines.append(f"- Asunto: {e['asunto']} | De: {e['de']} | Fecha: {e['fecha']}")
                    lines.append(f"  Snippet: {e['snippet']}...\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error al procesar el inbox: {str(e)}"
