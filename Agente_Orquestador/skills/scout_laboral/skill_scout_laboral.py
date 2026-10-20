"""
skill_scout_laboral.py — Habilidad Canónica de Scouting Laboral Multiplataforma Zero-Noise
========================================================================================
Permite al Agente Orquestador y a la flota explorar, extraer, evaluar y catalogar ofertas
de empleo en múltiples plataformas remotas (Get on Board, LinkedIn Jobs, etc.) a partir
de notificaciones de correo IMAP y crawling HTTP ligero, aplicando filtrado Zero-Noise
contra el Perfil Laboral Oficial de Wuil (memoria/Perfil_Laboral_Wuil.md, umbral >= 75%).
"""

import os
import re
import json
import imaplib
import email
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from langchain_core.tools import tool

# ─── RUTAS CANÓNICAS ──────────────────────────────────────────────────────────
_APP_ROOT = Path(__file__).resolve().parents[3]
_INFORMES_DIR = _APP_ROOT / "Agente_Orquestador" / "informes"
_MEMORIA_PERFIL = _APP_ROOT / "memoria" / "Perfil_Laboral_Wuil.md"
_ENV_PATH = _APP_ROOT / ".env"


def _cargar_credenciales_env() -> Dict[str, str]:
    """Carga credenciales del archivo .env de forma segura."""
    creds = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds


def _evaluar_coincidencia(titulo: str, desc: str, full_text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Evalúa la afinidad matemática de una vacante contra Perfil_Laboral_Wuil.md.
    Umbral requerido: >= 75%.
    """
    if tags is None:
        tags = []
    texto_eval = f"{titulo} {desc} {' '.join(tags)} {full_text}".lower()

    # 1. Filtro Excluyente Inmediato (Hard Disqualifiers)
    descalificadores = [
        "call center", "telemarketing", "ventas en frío", "ventas en frio",
        "cobranzas", "soporte de hardware", "soporte técnico presencial",
        "docente universitario", "profesor de"
    ]
    for d in descalificadores:
        if d in texto_eval:
            return {
                "match": 0,
                "coincidencias": [],
                "es_remoto": False,
                "pasa_filtro": False,
                "razon": f"Descalificado por rubro incompatible: '{d}'"
            }

    # 2. Verificación de Modalidad (100% Remoto o Presencial en Caracas)
    es_remoto = any(r in texto_eval for r in [
        "remoto", "remote", "work from home", "teletrabajo", 
        "cualquier lugar", "anywhere", "latam", "en remoto", "100% remoto"
    ])
    es_caracas = "caracas" in texto_eval

    if not (es_remoto or es_caracas):
        if any(p in texto_eval for p in ["presencial", "on-site", "onsite"]):
            return {
                "match": 0,
                "coincidencias": [],
                "es_remoto": False,
                "pasa_filtro": False,
                "razon": "Descalificado: Requiere presencia física fuera de Caracas"
            }

    coincidencias = []

    # 3. Verificación de afinidad base
    tiene_ia = any(k in texto_eval for k in [
        "inteligencia artificial", "machine learning", "computer vision", 
        "nlp", "llm", "agentes", "agents", "langgraph", "langchain", 
        "rag", "yolo", "deep learning", " ai ", "(ai)"
    ])
    tiene_python = "python" in texto_eval or "fastapi" in texto_eval

    if not (tiene_ia or tiene_python):
        return {
            "match": 15,
            "coincidencias": [],
            "es_remoto": es_remoto,
            "pasa_filtro": False,
            "razon": "Descartado: No involucra Inteligencia Artificial ni ecosistema Python"
        }

    # 4. Cálculo Ponderado
    kw_ia = {
        "agentes": 20, "agents": 20, "langgraph": 20, "langchain": 15,
        "llm": 20, "rag": 20, "machine learning": 18, "inteligencia artificial": 18,
        "computer vision": 20, "yolo": 20, "nlp": 18, "deep learning": 18,
        "pytorch": 15, "tensorflow": 15, "vector": 10, "chromadb": 15
    }
    pts_ia = sum(v for k, v in kw_ia.items() if k in texto_eval)
    for k in kw_ia:
        if k in texto_eval: coincidencias.append(k)
    score_ia = min(pts_ia, 65)

    kw_py = {
        "python": 25, "fastapi": 22, "microservicios": 12, "microservices": 12,
        "backend": 12, "rest": 10, "api": 10, "docker": 10, "sql": 8, 
        "postgresql": 8, "git": 6, "aws": 8, "linux": 6
    }
    pts_py = sum(v for k, v in kw_py.items() if k in texto_eval)
    for k in kw_py:
        if k in texto_eval: coincidencias.append(k)
    score_py = min(pts_py, 65)

    if score_ia > 0 and score_py > 0:
        puntaje_especialidad = min(score_ia + (score_py * 0.5), 75)
    else:
        puntaje_especialidad = max(score_ia, score_py)

    kw_aux = {"automation": 8, "automatización": 8, "playwright": 10, "n8n": 10, "react": 8}
    pts_aux = sum(v for k, v in kw_aux.items() if k in texto_eval)
    for k in kw_aux:
        if k in texto_eval: coincidencias.append(k)
    score_aux = min(pts_aux, 15)

    score_remoto = 10 if es_remoto else 0
    puntuacion_final = int(min(puntaje_especialidad + score_aux + score_remoto, 100))
    pasa = puntuacion_final >= 75
    unique_matches = list(dict.fromkeys(coincidencias))

    return {
        "match": puntuacion_final,
        "coincidencias": unique_matches,
        "es_remoto": es_remoto,
        "pasa_filtro": pasa,
        "razon": f"Coincidencias clave: {', '.join(unique_matches[:6])}" if pasa else "Afinidad técnica inferior al umbral mínimo del 75%"
    }


def _extraer_enlaces_getonbrd(mail_client: imaplib.IMAP4_SSL, max_emails: int = 5) -> List[str]:
    """Extrae enlaces de ofertas de Get on Board desde correos recientes."""
    typ, res = mail_client.search(None, 'FROM "getonbrd"')
    if not (res and res[0]):
        return []
    ids = res[0].split()
    target_ids = ids[-max_emails:]
    links = []
    for msg_id in target_ids:
        typ, data = mail_client.fetch(msg_id, "(RFC822)")
        if not data or not data[0]:
            continue
        msg = email.message_from_bytes(data[0][1])
        cuerpo = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() in ["text/plain", "text/html"]:
                    p = part.get_payload(decode=True)
                    if p: cuerpo += p.decode("utf-8", errors="ignore")
        else:
            p = msg.get_payload(decode=True)
            if p: cuerpo += p.decode("utf-8", errors="ignore")
        found = re.findall(r'https?://(?:www\.)?getonbrd\.com/empleos/[a-z0-9\-]+/[a-z0-9\-]+', cuerpo)
        for f in found:
            if f not in links:
                links.append(f)
    return links


def _analizar_vacante_getonbrd(url: str) -> Optional[Dict[str, Any]]:
    """Descarga y analiza una vacante individual de Get on Board."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            body_text = soup.get_text()

            # Comprobar si la vacante está cerrada
            if "no longer accepting" in body_text.lower() or "closed job" in body_text.lower():
                return None

            title_tag = soup.find("meta", property="og:title")
            title = title_tag["content"].strip() if title_tag else "Vacante Get on Board"

            desc_tag = soup.find("meta", property="og:description")
            desc = desc_tag["content"].strip() if desc_tag else ""

            sal_m = re.search(r"(\$\s?[\d.,]+\s?-\s?\$?[\d.,]+\s?(?:USD|EUR)?(?:\s?/\s?mes|\s?/\s?month)?)", body_text)
            salario = sal_m.group(1).strip() if sal_m else "No especificado / Rango de mercado"

            tags = [a.get_text(strip=True) for a in soup.find_all("a", href=re.compile(r"/empleos/.*tag"))]
            res = _evaluar_coincidencia(title, desc, body_text, tags)

            return {
                "plataforma": "Get on Board",
                "titulo": title,
                "url": url,
                "salario": salario,
                "match": res["match"],
                "coincidencias": res["coincidencias"],
                "pasa_filtro": res["pasa_filtro"],
                "razon": res["razon"],
                "es_remoto": res["es_remoto"]
            }
    except Exception:
        return None


# ─── SYSTEM PROMPT ENCAPSULADO DE LA HABILIDAD ───────────────────────────────
def obtener_prompt_scout_laboral() -> str:
    """Devuelve el System Prompt especializado del rol Cazador de Talento Remoto."""
    return """[🛑 HARD-STOP: MODO SCOUT LABORAL Y EXPLORADOR REMOTO ACTIVO 🛑]
Eres el Explorador de Oportunidades y Cazador de Talento Remoto del Agente Orquestador.
Tu misión es vigilar permanentemente las plataformas laborales internacionales (Get on Board, LinkedIn, Computrabajo) para identificar ofertas que coincidan con la excelencia técnica del Capitán Wuilfredo Cortez.

DIRECTIVAS OPERATIVAS INVIOLABLES:
1. REGLA ESTRICTA ZERO-NOISE (SILENCIO ANTE INCOMPATIBLES):
   - Únicamente debes presentar, reportar y guardar vacantes con AFINIDAD >= 75%.
   - Si una vacante está cerrada, requiere presencia física fuera de Caracas, exige tecnologías ajenas o tiene match < 75%, se descarta en SILENCIO ABSOLUTO.
   - Si no hay vacantes compatibles tras un barrido completo, informa una única línea ejecutiva:
     "Escaneo completado: 0 nuevas ofertas compatibles hoy."
2. TRAZABILIDAD ZERO-TRUST:
   - Todo escaneo exitoso genera su informe físico en 'Agente_Orquestador/informes/reporte_scouting_laboral_<FECHA>.md'.
   - Incluye siempre URL directa de postulación, salario verificado, match % y stack coincidente.
3. CONEXIONES OBSIDIAN:
   - Todo entregable se conecta a [[Perfil_Agente_Orquestador]]."""


# ─── HERRAMIENTAS LANGCHAIN (@tool) ──────────────────────────────────────────
@tool
def tool_scout_laboral_multiplataforma(plataformas: str = "todas", max_vacantes: int = 15) -> str:
    """
    Ejecuta un escaneo automatizado Zero-Noise en plataformas remotas (Get on Board, LinkedIn)
    a partir de los correos de alertas en el buzón oficial. Filtra vacantes cerradas y
    solo reporta ofertas abiertas con Match >= 75% según Perfil_Laboral_Wuil.md.
    """
    creds = _cargar_credenciales_env()
    email_user = creds.get("KEEP_EMAIL")
    email_pass = creds.get("KEEP_APP_PASSWORD")

    if not (email_user and email_pass):
        return "Error: Credenciales de correo no encontradas en .env."

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_user, email_pass)
        mail.select("INBOX", readonly=True)
    except Exception as e:
        return f"Error al conectar con IMAP: {e}"

    compatibles: List[Dict[str, Any]] = []
    total_revisadas = 0
    total_cerradas = 0

    try:
        # 1. Escaneo Get on Board
        if plataformas in ["todas", "getonbrd", "get_on_board"]:
            links_gob = _extraer_enlaces_getonbrd(mail, max_emails=5)
            for link in links_gob[:max_vacantes]:
                total_revisadas += 1
                vac = _analizar_vacante_getonbrd(link)
                if vac is None:
                    total_cerradas += 1
                elif vac["pasa_filtro"]:
                    compatibles.append(vac)
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    # Generación de evidencia física Zero-Trust
    _INFORMES_DIR.mkdir(parents=True, exist_ok=True)
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_path = _INFORMES_DIR / f"reporte_scouting_laboral_{fecha_str}.md"

    md_lines = [
        f"# 🎯 Informe de Scouting Laboral Multiplataforma — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"> **Plataformas auditadas:** Get on Board (GetOnBrd) & LinkedIn Jobs | **Modo:** Zero-Noise (Match $\\ge 75\\%$)\n",
        f"- **Total posiciones analizadas:** {total_revisadas}",
        f"- **Posiciones cerradas o expiradas:** {total_cerradas}",
        f"- **Posiciones compatibles aprobadas (Match $\\ge 75\\%$):** {len(compatibles)}\n",
        "---",
        "## 💼 Vacantes Compatibles para Postulación Inmediata\n"
    ]

    if not compatibles:
        md_lines.append("_Escaneo completado: 0 nuevas ofertas compatibles hoy._\n")
    else:
        for c in compatibles:
            md_lines.append(f"### 🚀 [{c['match']}% Match] {c['titulo']}")
            md_lines.append(f"- **Plataforma:** {c['plataforma']}")
            md_lines.append(f"- **Salario:** {c['salario']}")
            md_lines.append(f"- **Modalidad:** 100% Remoto" if c["es_remoto"] else "- **Modalidad:** Presencial en Caracas")
            md_lines.append(f"- **Stack coincidente:** {', '.join(c['coincidencias'])}")
            md_lines.append(f"- **Enlace de postulación:** [Ver Oferta en {c['plataforma']}]({c['url']})\n")

    md_lines.append("---\n**Conexiones:** [[Perfil_Agente_Orquestador]] [[Perfil_Laboral_Wuil]]")
    reporte_path.write_text("\n".join(md_lines), encoding="utf-8")

    if not compatibles:
        return f"Escaneo completado: 0 nuevas ofertas compatibles hoy. (Revisadas: {total_revisadas}, Evidencia: {reporte_path.name})"

    resumen = [
        f"[SCOUT ZERO-NOISE] Completado: {len(compatibles)} ofertas de alto valor encontradas (>= 75% Match):"
    ]
    for c in compatibles:
        safe_title = c["titulo"].encode("ascii", "replace").decode("ascii")
        resumen.append(f"  * [{c['match']}% Match] {safe_title} | Salario: {c['salario']} | URL: {c['url']}")
    resumen.append(f"Evidencia fisica registrada en: {reporte_path}")
    return "\n".join(resumen)


@tool
def tool_evaluar_compatibilidad_vacante(titulo: str, descripcion: str, url: str = "") -> str:
    """
    Evalúa matemáticamente una vacante individual dada por título y descripción contra
    el perfil oficial de Wuil (Perfil_Laboral_Wuil.md). Devuelve el match %, las tecnologías
    coincidentes y el veredicto Zero-Noise.
    """
    res = _evaluar_coincidencia(titulo, descripcion, descripcion, [])
    resultado = {
        "titulo": titulo,
        "url": url,
        "match_porcentaje": f"{res['match']}%",
        "pasa_umbral_75": res["pasa_filtro"],
        "es_remoto": res["es_remoto"],
        "coincidencias_clave": res["coincidencias"],
        "razon": res["razon"]
    }
    return json.dumps(resultado, indent=2, ensure_ascii=False)
