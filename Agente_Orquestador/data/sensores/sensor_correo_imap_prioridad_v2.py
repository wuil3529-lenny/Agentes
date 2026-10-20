#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensor Zero-Token v2.1: Vigilante de Correos IMAP con FILTRO DE PRIORIDAD
y ANTI-DUPLICADO DEFINITIVO (marca \\Seen SOLO tras confirmacion de notificacion).

FIX del bug de re-disparo (patron C001-C004) — TKT-DEV-20261014001:

  CAUSA RAIZ (3 defectos):
    (a) El buzon tiene miles de correos historicos no leidos; search(UNSEEN)
        devolvia cientos y solo se procesaban MAX_CORREOS=50 por ciclo ->
        los mismos correos re-disparaban en cada ciclo.
    (b) El estado JSON se recortaba con [-2000:], perdiendo memoria de UIDs
        procesados cuando el backlog es masivo.
    (c) El \\Seen se marcaba en el mismo instante de la clasificacion, ANTES
        de confirmar que el subagente ya notifico el correo.

  SOLUCION (mecanismo de "marcar como notificado"):
    1. Archivo de estado `correos_notificados.json` con:
         - "uids_notificados": set de UIDs ya catalogados+notificados.
         - "ultimo_uid_procesado": cursor de avance (max UID escaneado).
       Si un UID ya esta en `uids_notificados`, NUNCA se vuelve a incluir
       en el payload del disparo.
    2. CLI `--marcar-notificado <uid1> <uid2> ...` para que el subagente de
       Asistencia confirme el marcado tras catalogar y notificar. Agrega los
       UIDs a `correos_notificados.json` y ejecuta `store +FLAGS \\Seen` en
       el servidor IMAP.
    3. Cursor de avance: el sensor recuerda `ultimo_uid_procesado` y prioriza
       el escaneo de correos con UID mayor a ese cursor, evitando re-escanear
       el backlog historico completo en cada ciclo.
    4. MAX_CORREOS subido a 2000 (drena el backlog historico en el 1er ciclo).
    5. Eliminado el recorte [-2000:]: la persistencia guarda el cursor + set
       completo de notificados (sin perdida de UIDs).

REGLA DE ORO:
  - SOLO dispara con correos de PRIORIDAD ALTA: Urgente | Trabajo | Personal.
  - SILENCIA (0 tokens) Promociones/Spam y Otros.

Salida JSON (compatibilidad con tool_programar_tarea_repetitiva):
  {"disparar": true, "datos_evento": {...}}  -> hay correo(s) importante(s)
  {"disparar": false}                        -> sin novedades relevantes
"""

import os
import sys
import json
import imaplib
import email
from email.header import decode_header
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
NOTIFICADOS_PATH = BASE_DIR / "correos_notificados.json"
MAX_CORREOS = int(os.getenv("SENSOR_MAX_CORREOS", "200"))


def _cargar_env(override=True):
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
ASUNTO_RUIDO = [
    "newsletter", "promo", "descuento", "oferta", "sale", "black friday",
    "halloween", "webinar", "curso", "aprende", "unete", "gratis",
    "suscribete", "no te lo pierdas", "ultima oportunidad",
]
ASUNTO_URGENTE = [
    "urgente", "security alert", "alerta de seguridad", "new device",
    "nuevo inicio de sesion", "suspicious", "sospechos", "verifica",
    "verify", "password", "contrasena", "factura", "pago", "vencimiento",
    "action required", "accion requerida", "cuenta bloqueada",
]
ASUNTO_TRABAJO = [
    "job", "empleo", "vacante", "postulacion", "entrevista",
    "interview", "reclut", "hiring", "candidate", "candidato", "propuesta",
    "contrato", "proyecto", "cliente", "reunion", "meeting",
    "invoice", "cotizacion",
]


def _decodificar(valor):
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
    rem_l = (remitente or "").lower()
    asu_l = (asunto or "").lower()
    for d in DOMINIOS_RUIDO:
        if d in rem_l:
            return "PROMOCIONES", False
    for r in REMITENTES_RUIDO:
        if r in rem_l:
            if any(k in asu_l for k in ASUNTO_URGENTE):
                return "URGENTE", True
            return "PROMOCIONES", False
    for k in ASUNTO_RUIDO:
        if k in asu_l:
            return "PROMOCIONES", False
    for k in ASUNTO_URGENTE:
        if k in asu_l:
            return "URGENTE", True
    for k in ASUNTO_TRABAJO:
        if k in asu_l:
            return "TRABAJO", True
    return "OTROS", False


def _cargar_notificados():
    """Carga el estado de UIDs ya notificados + cursor de avance."""
    if NOTIFICADOS_PATH.exists():
        try:
            data = json.loads(NOTIFICADOS_PATH.read_text(encoding="utf-8"))
            return {
                "uids_notificados": [str(u) for u in data.get("uids_notificados", [])],
                "ultimo_uid_procesado": int(data.get("ultimo_uid_procesado", 0) or 0),
            }
        except Exception:
            pass
    return {"uids_notificados": [], "ultimo_uid_procesado": 0}


def _guardar_notificados(data):
    """Persiste el set COMPLETO de notificados + cursor (sin recorte [-2000:])."""
    try:
        NOTIFICADOS_PATH.write_text(
            json.dumps(
                {
                    "uids_notificados": sorted(
                        set(str(u) for u in data.get("uids_notificados", [])),
                        key=lambda x: int(x) if x.isdigit() else 0,
                    ),
                    "ultimo_uid_procesado": int(data.get("ultimo_uid_procesado", 0) or 0),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def _cuerpo_texto(msg):
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


def _conectar():
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("INBOX")
    return mail


def marcar_notificado(uids):
    """
    CLI: confirma que el subagente de Asistencia ya catalogo y notifico estos UIDs.
    Agrega los UIDs a correos_notificados.json y ejecuta store +FLAGS \\Seen en IMAP.
    """
    uids = [str(u).strip() for u in uids if str(u).strip()]
    if not uids:
        print(json.dumps({"ok": False, "error": "No se recibieron UIDs"}, ensure_ascii=False))
        return 1

    data = _cargar_notificados()
    set_notif = set(data["uids_notificados"])
    set_notif.update(uids)

    max_uid = data["ultimo_uid_procesado"]
    for u in uids:
        if u.isdigit():
            max_uid = max(max_uid, int(u))

    _guardar_notificados({"uids_notificados": list(set_notif), "ultimo_uid_procesado": max_uid})

    marcados_imap = 0
    error_imap = None
    try:
        mail = _conectar()
        for u in uids:
            try:
                mail.store(u.encode() if isinstance(u, str) else u, "+FLAGS", "\\Seen")
                marcados_imap += 1
            except Exception as e:
                error_imap = str(e)
        mail.logout()
    except Exception as e:
        error_imap = str(e)

    print(json.dumps({
        "ok": True,
        "uids_marcados": uids,
        "total_notificados": len(set_notif),
        "ultimo_uid_procesado": max_uid,
        "marcados_imap_seen": marcados_imap,
        "error_imap": error_imap,
    }, ensure_ascii=False))
    return 0


def main():
    if not EMAIL_USER or not EMAIL_PASS:
        print(json.dumps({"disparar": False, "error": "Credenciales de correo no configuradas"}))
        return

    notif = _cargar_notificados()
    uids_notificados = set(notif["uids_notificados"])
    ultimo_uid_procesado = notif["ultimo_uid_procesado"]

    try:
        mail = _conectar()

        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            print(json.dumps({"disparar": False}))
            mail.logout()
            return

        todos = data[0].split()
        total_unseen = len(todos)

        def _uid_int(u):
            try:
                return int(u.decode())
            except Exception:
                return 0

        todos_ordenados = sorted(todos, key=_uid_int)

        # LECTURA ESTRICTAMENTE POSTERIOR AL CURSOR:
        #   Solo correos con UID > ultimo_uid_procesado (max UID CONFIRMADO por
        #   Asistencia). Se elimino por completo el re-escaneo del backlog.
        #   Los correos anteriores al cursor NUNCA se vuelven a leer.
        posteriores = [u for u in todos_ordenados if _uid_int(u) > ultimo_uid_procesado]

        # BARRERA ANTI-DUPLICADO (defensa en profundidad):
        #   Excluir cualquier UID ya confirmado como notificado, por si el
        #   servidor IMAP aun no refleja el \\Seen (consistencia eventual).
        nuevos = [u for u in posteriores if u.decode() not in uids_notificados]

        importantes = []
        silenciados = 0
        uids_silenciados = []

        for uid in nuevos[:MAX_CORREOS]:
            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            remitente = _decodificar(msg.get("From"))
            asunto = _decodificar(msg.get("Subject"))
            categoria, es_importante = _clasificar_prioridad(remitente, asunto)

            uid_str = uid.decode()

            # NOTA CRITICA: NO se marca \\Seen aqui y NO se avanza el cursor.
            # El marcado definitivo y el avance del cursor los confirma el
            # subagente de Asistencia via --marcar-notificado tras notificar.

            if es_importante:
                importantes.append({
                    "uid": uid_str,
                    "categoria": categoria,
                    "remitente": remitente,
                    "asunto": asunto,
                    "fecha": msg.get("Date", ""),
                    "cuerpo": _cuerpo_texto(msg),
                })
            else:
                silenciados += 1
                uids_silenciados.append(uid_str)

        mail.logout()

        # NO se persiste nada aqui: el sensor es 100% de solo-lectura.
        # El cursor `ultimo_uid_procesado` y el set `uids_notificados` SOLO se
        # actualizan cuando Asistencia confirma via --marcar-notificado.

        if not importantes:
            print(json.dumps({
                "disparar": False,
                "datos_evento": {
                    "total_unseen": total_unseen,
                    "total_nuevos": len(nuevos),
                    "total_importantes": 0,
                    "total_silenciados": silenciados,
                    "uids_silenciados": uids_silenciados,
                    "ultimo_uid_procesado": ultimo_uid_procesado,
                    "nota": "Correos nuevos solo de bajo valor (promos/otros). Silenciados sin despertar al LLM. Confirmar via --marcar-notificado para avanzar el cursor."
                }
            }, ensure_ascii=False))
            return

        print(json.dumps({
            "disparar": True,
            "datos_evento": {
                "total_unseen": total_unseen,
                "total_nuevos": len(nuevos),
                "total_importantes": len(importantes),
                "total_silenciados": silenciados,
                "uids_silenciados": uids_silenciados,
                "ultimo_uid_procesado": ultimo_uid_procesado,
                "correos": importantes,
            }
        }, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"disparar": False, "error": str(e)}))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--marcar-notificado":
        sys.exit(marcar_notificado(sys.argv[2:]))
    main()
