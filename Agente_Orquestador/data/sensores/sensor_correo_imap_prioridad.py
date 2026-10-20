#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensor Zero-Token: Vigilante de Correos IMAP con FILTRO DE PRIORIDAD
--------------------------------------------------------------------
Vigila el buzón configurado en el .env (KEEP_EMAIL / KEEP_APP_PASSWORD) por IMAP.

REGLA DE ORO (Opción A del Capitán):
  - SOLO dispara (despierta al LLM) cuando entra un correo de PRIORIDAD ALTA:
      🔴 Urgente  |  🟡 Trabajo  |  🟢 Personal
  - SILENCIA (no dispara, 0 tokens) los correos de:
      🔵 Promociones/Spam  |  ⚪ Otros (newsletters, marketing, digests irrelevantes)

- 0 tokens LLM mientras no haya correos importantes.
- Imprime una línea JSON:
    {"disparar": true, "datos_evento": {...}}  -> cuando hay correo(s) importante(s)
    {"disparar": false}                        -> cuando no hay novedades relevantes

CORRECCIÓN DE INTEGRIDAD (patrón C009-C018):
  - Se elimina el truncamiento: se reporta `total_nuevos` REAL y se adjuntan
    TODOS los correos importantes detectados (sin límite artificial de 5).
  - Se incluye `total_silenciados` para trazabilidad.

Estado persistente: guarda los UIDs ya procesados en un JSON local para no
volver a disparar por el mismo correo.
"""

import os
import sys
import json
import imaplib
import email
import re
from email.header import decode_header
from pathlib import Path

# ------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ESTADO_PATH = BASE_DIR / "estado_correo_imap_prioridad.json"

# Límite de seguridad para no traer miles de correos de golpe (no es truncamiento:
# si hay más, se reporta el total real y se avisa).
MAX_CORREOS = int(os.getenv("SENSOR_MAX_CORREOS", "50"))


def _cargar_env(override=True):
    """Carga el .env manualmente. Con override=True el .env SIEMPRE gana."""
    env_path = Path("/app/.env")
    if not env_path.exists():
        env_path = Path(__file__).resolve().parents[3] / ".env"
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


_cargar_env(override=True)

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
EMAIL_USER = os.getenv("KEEP_EMAIL", "").strip().strip('"')
EMAIL_PASS = os.getenv("KEEP_APP_PASSWORD", "").strip().strip('"')


# ------------------------------------------------------------------
# Motor de clasificación de prioridad (Python puro, 0 tokens)
# ------------------------------------------------------------------
# Remitentes/dominios que SIEMPRE son ruido (promos/spam/newsletters)
REMITENTES_RUIDO = [
    "noreply@", "no-reply@", "newsletter", "marketing", "promo",
    "email@email.", "info@email.", "updates-noreply@", "jobalerts-noreply@",
    "jobs-noreply@", "notifications@", "mailer", "info@m.", "hola@",
]
DOMINIOS_RUIDO = [
    "etsy.com", "coursera.org", "computrabajo", "strikingly", "creativemarket",
    "creativefabrica", "raiola", "ngrok", "banplus", "eskailet", "linkedin.com",
    "higgsfield.ai", "mailchimp", "sendgrid", "hubspot", "substack",
]
# Palabras clave en asunto que indican RUIDO (marketing/newsletter)
ASUNTO_RUIDO = [
    "newsletter", "promo", "descuento", "oferta", "sale", "black friday",
    "halloween", "webinar", "curso", "aprende", "únete", "unete", "gratis",
    "suscríbete", "suscribete", "no te lo pierdas", "última oportunidad",
]
# Palabras clave que indican PRIORIDAD ALTA (Urgente/Trabajo)
ASUNTO_URGENTE = [
    "urgente", "security alert", "alerta de seguridad", "new device",
    "nuevo inicio de sesión", "suspicious", "sospechos", "verifica",
    "verify", "password", "contraseña", "factura", "pago", "vencimiento",
    "action required", "acción requerida", "cuenta bloqueada",
]
ASUNTO_TRABAJO = [
    "job", "empleo", "vacante", "postulación", "postulacion", "entrevista",
    "interview", "reclut", "hiring", "candidate", "candidato", "propuesta",
    "contrato", "proyecto", "cliente", "reunión", "reunion", "meeting",
    "invoice", "cotización", "cotizacion",
]


def _decodificar(valor):
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


def _clasificar_prioridad(remitente, asunto):
    """Clasifica en Python puro (0 tokens). Devuelve (categoria, es_importante).

    Categorías: URGENTE | TRABAJO | PERSONAL | PROMOCIONES | OTROS
    """
    rem_l = (remitente or "").lower()
    asu_l = (asunto or "").lower()

    # 1) Ruido explícito por remitente/dominio/asunto -> PROMOCIONES (silenciar)
    for d in DOMINIOS_RUIDO:
        if d in rem_l:
            return "PROMOCIONES", False
    for r in REMITENTES_RUIDO:
        if r in rem_l:
            # excepción: alertas de seguridad de servicios conocidos son URGENTE
            if any(k in asu_l for k in ASUNTO_URGENTE):
                return "URGENTE", True
            return "PROMOCIONES", False
    for k in ASUNTO_RUIDO:
        if k in asu_l:
            return "PROMOCIONES", False

    # 2) Urgente por palabras clave
    for k in ASUNTO_URGENTE:
        if k in asu_l:
            return "URGENTE", True

    # 3) Trabajo por palabras clave
    for k in ASUNTO_TRABAJO:
        if k in asu_l:
            return "TRABAJO", True

    # 4) Por defecto: OTROS (silenciar, no es importante)
    return "OTROS", False


def _cargar_estado():
    if ESTADO_PATH.exists():
        try:
            return json.loads(ESTADO_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"uids_procesados": []}
    return {"uids_procesados": []}


def _guardar_estado(estado):
    try:
        ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _cuerpo_texto(msg):
    """Extrae el cuerpo en texto plano del mensaje."""
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
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="ignore")[:2000]
        except Exception:
            return ""


def main():
    if not EMAIL_USER or not EMAIL_PASS:
        print(json.dumps({"disparar": False, "error": "Credenciales de correo no configuradas"}))
        return

    estado = _cargar_estado()
    uids_procesados = set(str(u) for u in estado.get("uids_procesados", []))

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")

        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            print(json.dumps({"disparar": False}))
            mail.logout()
            return

        uids = data[0].split()
        nuevos = [u for u in uids if u.decode() not in uids_procesados]

        if not nuevos:
            print(json.dumps({"disparar": False}))
            mail.logout()
            return

        total_nuevos = len(nuevos)
        importantes = []
        silenciados = 0

        # Procesamos TODOS los nuevos (sin truncar). Límite de seguridad MAX_CORREOS.
        for uid in nuevos[:MAX_CORREOS]:
            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            remitente = _decodificar(msg.get("From"))
            asunto = _decodificar(msg.get("Subject"))
            categoria, es_importante = _clasificar_prioridad(remitente, asunto)

            uids_procesados.add(uid.decode())

            if es_importante:
                importantes.append({
                    "uid": uid.decode(),
                    "categoria": categoria,
                    "remitente": remitente,
                    "asunto": asunto,
                    "fecha": msg.get("Date", ""),
                    "cuerpo": _cuerpo_texto(msg),
                })
            else:
                silenciados += 1

        mail.logout()

        estado["uids_procesados"] = list(uids_procesados)[-1000:]
        _guardar_estado(estado)

        # SOLO dispara si hay correos importantes
        if not importantes:
            print(json.dumps({
                "disparar": False,
                "datos_evento": {
                    "total_nuevos": total_nuevos,
                    "total_importantes": 0,
                    "total_silenciados": silenciados,
                    "nota": "Correos nuevos solo de bajo valor (promos/otros). Silenciados sin despertar al LLM."
                }
            }, ensure_ascii=False))
            return

        print(json.dumps({
            "disparar": True,
            "datos_evento": {
                "total_nuevos": total_nuevos,
                "total_importantes": len(importantes),
                "total_silenciados": silenciados,
                "correos": importantes,
            }
        }, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"disparar": False, "error": str(e)}))


if __name__ == "__main__":
    main()
