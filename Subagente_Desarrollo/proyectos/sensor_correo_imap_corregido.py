#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensor Zero-Token: Vigilante de Correos IMAP
--------------------------------------------
Vigila el buzón configurado en el .env (KEEP_EMAIL / KEEP_APP_PASSWORD) por IMAP.
Detecta correos NUEVOS NO LEÍDOS y los reporta como evento.

- 0 tokens LLM mientras no hay novedades.
- Imprime una línea JSON:
    {"disparar": true, "datos_evento": {...}}  -> cuando hay correo(s) nuevo(s)
    {"disparar": false}                        -> cuando no hay novedades

Estado persistente: guarda los UIDs ya procesados en un archivo JSON local
para no volver a disparar por el mismo correo.

NOTA (TKT-DEV-20261014001): La carga del .env se realiza con OVERRIDE FORZADO.
El uso previo de os.environ.setdefault() impedía sobreescribir variables ya
presentes en el entorno del proceso (p. ej. una contraseña de aplicación de
Gmail antigua), provocando fallos de autenticación IMAP. Ahora el .env es la
fuente de verdad y SIEMPRE sobreescribe el entorno.
"""

import os
import sys
import json
import imaplib
import email
from email.header import decode_header
from pathlib import Path

# ------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ESTADO_PATH = BASE_DIR / "estado_correo_imap.json"


def _cargar_env(override=True):
    """Carga el .env manualmente (sin dependencias externas).

    Con override=True (por defecto) el valor del .env SIEMPRE sobreescribe
    cualquier variable preexistente en os.environ, garantizando que el sensor
    lea la credencial fresca y no una obsoleta heredada del entorno.
    """
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
MAX_CORREOS = int(os.getenv("SENSOR_MAX_CORREOS", "5"))


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

        # Buscar correos NO leídos
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

        correos = []
        for uid in nuevos[-MAX_CORREOS:]:
            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            correos.append({
                "uid": uid.decode(),
                "remitente": _decodificar(msg.get("From")),
                "asunto": _decodificar(msg.get("Subject")),
                "fecha": msg.get("Date", ""),
                "cuerpo": _cuerpo_texto(msg),
            })
            uids_procesados.add(uid.decode())

        mail.logout()

        estado["uids_procesados"] = list(uids_procesados)[-500:]
        _guardar_estado(estado)

        print(json.dumps({
            "disparar": True,
            "datos_evento": {
                "total_nuevos": len(correos),
                "correos": correos,
            }
        }, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"disparar": False, "error": str(e)}))


if __name__ == "__main__":
    main()
