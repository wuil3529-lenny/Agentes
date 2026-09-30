import asyncio
import json
import time
import os
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse
import bcrypt
import jwt
import secrets
import hmac
import hashlib
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import psutil
import platform
from typing import Optional, List, Dict, Any, Tuple

# Intentar importar GPUtil para monitoreo de GPU
try:
    import GPUtil
except ImportError:
    GPUtil = None

app = FastAPI(title="Tripulacion.IA Dashboard")

BASE_DIR = Path(__file__).resolve().parent
AGENTES_DIR = BASE_DIR.parent
LUFFY_DIR = AGENTES_DIR / "Luffy"

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# ----------------- REGISTRO Y ALARMA DE INTRUSIÓN -----------------
INCIDENTES_SEGURIDAD_FILE = BASE_DIR / "incidentes_seguridad.json"
HISTORIAL_INTRUSIONES = []
if INCIDENTES_SEGURIDAD_FILE.exists():
    try:
        HISTORIAL_INTRUSIONES = json.loads(INCIDENTES_SEGURIDAD_FILE.read_text(encoding="utf-8"))
        if not isinstance(HISTORIAL_INTRUSIONES, list):
            HISTORIAL_INTRUSIONES = []
    except Exception:
        HISTORIAL_INTRUSIONES = []

ULTIMA_ALERTA_INTRUSION = None
ULTIMA_NOTIF_TELEGRAM_POR_IP = {}

def enviar_telegram_alerta_sync(mensaje: str):
    env_path = AGENTES_DIR / ".env"
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        if env_path.exists():
            try:
                for l in env_path.read_text(encoding="utf-8").splitlines():
                    if l.strip().startswith("TELEGRAM_BOT_TOKEN="):
                        token = l.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    elif l.strip().startswith("TELEGRAM_CHAT_ID="):
                        chat_id = l.strip().split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        try:
            payload_plain = json.dumps({"chat_id": chat_id, "text": mensaje}).encode("utf-8")
            req2 = urllib.request.Request(url, data=payload_plain, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req2, timeout=5)
        except Exception:
            pass

async def notificar_alerta_seguridad_telegram(ip: str, ruta: str, metodo: str, user_agent: str):
    ahora = time.time()
    ultimo = ULTIMA_NOTIF_TELEGRAM_POR_IP.get(ip, 0)
    # Rate limit: máximo 1 alerta por IP cada 30 segundos
    if ahora - ultimo < 30:
        return
    ULTIMA_NOTIF_TELEGRAM_POR_IP[ip] = ahora
    
    hora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mensaje = (
        f"🚨 *¡ALERTA DE SEGURIDAD! INTRUSIÓN BLOQUEADA* 🚨\n\n"
        f"🛡️ *Evento:* Intento de conexión no autorizada detectado\n"
        f"🌐 *IP Bloqueada:* `{ip}`\n"
        f"🎯 *Ruta:* `{metodo} {ruta}`\n"
        f"⏰ *Hora:* `{hora_str}`\n"
        f"💻 *Agente:* `{user_agent[:60]}`\n"
        f"🛑 *Acción:* Cortafuegos perimetral bloqueó el acceso (403 Forbidden).\n\n"
        f"⚡ _Tripulación IA • Centinela Activo_"
    )
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, enviar_telegram_alerta_sync, mensaje)
    except Exception:
        pass

# Cortafuegos Perimetral: Filtro de IPs Permitidas (Whitelist)
@app.middleware("http")
async def ip_whitelist_middleware(request: Request, call_next):
    env_path = AGENTES_DIR / ".env"
    allowed_ips_raw = os.getenv("ALLOWED_IPS", "").strip()
    if not allowed_ips_raw and env_path.exists():
        try:
            for l in env_path.read_text(encoding="utf-8").splitlines():
                if l.strip().startswith("ALLOWED_IPS="):
                    allowed_ips_raw = l.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass

    if allowed_ips_raw:
        client_ip = request.client.host if request.client else "127.0.0.1"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # Siempre permitir localhost y loopback
        is_allowed = client_ip in ["127.0.0.1", "::1", "localhost", "testclient"]

        if not is_allowed:
            rules = [r.strip() for r in allowed_ips_raw.split(",") if r.strip()]
            for rule in rules:
                if rule == client_ip:
                    is_allowed = True
                    break
                if rule.endswith("*") and client_ip.startswith(rule[:-1]):
                    is_allowed = True
                    break
                if rule.endswith(".") and client_ip.startswith(rule):
                    is_allowed = True
                    break
                if "/" in rule:
                    try:
                        import ipaddress
                        if ipaddress.ip_address(client_ip) in ipaddress.ip_network(rule, strict=False):
                            is_allowed = True
                            break
                    except Exception:
                        pass

        if not is_allowed:
            global ULTIMA_ALERTA_INTRUSION
            user_agent = request.headers.get("user-agent", "Desconocido")
            incidente = {
                "id": f"inc-{int(time.time()*1000)}",
                "ip": client_ip,
                "ruta": request.url.path,
                "metodo": request.method,
                "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": time.time(),
                "user_agent": user_agent[:120],
                "bloqueado": True
            }
            HISTORIAL_INTRUSIONES.insert(0, incidente)
            if len(HISTORIAL_INTRUSIONES) > 100:
                HISTORIAL_INTRUSIONES.pop()
            try:
                INCIDENTES_SEGURIDAD_FILE.write_text(json.dumps(HISTORIAL_INTRUSIONES, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            ULTIMA_ALERTA_INTRUSION = incidente
            try:
                asyncio.create_task(notificar_alerta_seguridad_telegram(client_ip, request.url.path, request.method, user_agent))
            except Exception:
                pass

            return JSONResponse(
                status_code=403,
                content={
                    "status": "error",
                    "message": f"Acceso denegado: Tu dirección IP ({client_ip}) no está autorizada por el cortafuegos perimetral.",
                    "alarma": "Alarma de intrusión activada y notificada al administrador"
                }
            )

    return await call_next(request)

from pydantic import BaseModel
import subprocess
import os

# ----------------- AUTENTICACIÓN Y GESTIÓN DE USUARIOS (BCRYPT + JWT) -----------------
USUARIOS_DB_FILE = BASE_DIR / "usuarios.json"
# Generar una clave de firma dinámica y única por cada arranque del servidor
# para invalidar de inmediato todas las sesiones anteriores al reiniciar la consola
SERVER_BOOT_INSTANCE_ID = secrets.token_hex(16)
JWT_SECRET_KEY = f"{os.getenv('JWT_SECRET_KEY', 'tripulacion-ia-c2')}-{SERVER_BOOT_INSTANCE_ID}"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 4 * 3600  # Máximo 4 horas de validez de sesión

# Registro en memoria de intentos fallidos por IP (Anti Fuerza Bruta)
INTENTOS_FALLIDOS: Dict[str, dict] = {}  # ip -> {"conteo": int, "bloqueado_hasta": float}

# Registro en memoria de PINs de autorización de registro (10 min TTL)
PINS_REGISTRO: Dict[str, dict] = {}  # pin -> {"username": str, "nombre": str, "ip": str, "creado_en": float, "expira_en": float}
ULTIMA_SOLICITUD_PIN_POR_IP: Dict[str, float] = {}  # ip -> timestamp (cooldown 60s)


def cargar_usuarios() -> List[dict]:
    if USUARIOS_DB_FILE.exists():
        try:
            data = json.loads(USUARIOS_DB_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass

    # Inicializar con el usuario administrador por defecto desde .env
    env_user = os.getenv("CONSOLE_AUTH_USER", "").strip() or "Wuilfredo"
    env_pass = os.getenv("CONSOLE_AUTH_PASSWORD", "").strip()
    if not env_pass:
        raise RuntimeError(
            "SEC-015 FAIL-CLOSED: CONSOLE_AUTH_PASSWORD no esta definida o esta vacia. "
            "La consola se niega a arrancar sin una contrasena de administrador explicita. "
            "Defina CONSOLE_AUTH_PASSWORD en el archivo .env antes de iniciar el servicio."
        )
    env_avatar = os.getenv("CONSOLE_AUTH_AVATAR", "/static/avatars/bot_dark.jpg").strip()

    salt = bcrypt.gensalt(rounds=12)
    hashed_pwd = bcrypt.hashpw(env_pass.encode("utf-8"), salt).decode("utf-8")

    usuario_inicial = {
        "id": "usr-admin-01",
        "username": env_user,
        "password_hash": hashed_pwd,
        "nombre": f"Capitán {env_user}",
        "avatar": env_avatar,
        "rol": "admin",
        "creado_en": datetime.now().isoformat()
    }
    guardar_usuarios([usuario_inicial])
    return [usuario_inicial]

def guardar_usuarios(usuarios: List[dict]):
    try:
        USUARIOS_DB_FILE.write_text(json.dumps(usuarios, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Error guardando usuarios: {e}")

def verificar_bloqueo_fuerza_bruta(ip: str) -> Optional[str]:
    ahora = time.time()
    registro = INTENTOS_FALLIDOS.get(ip)
    if registro and registro.get("bloqueado_hasta", 0) > ahora:
        segundos_restantes = int(registro["bloqueado_hasta"] - ahora)
        return f"Acceso temporalmente bloqueado por demasiados intentos fallidos. Por seguridad, espera {segundos_restantes} segundos antes de reintentar."
    return None

def registrar_intento_fallido(ip: str):
    ahora = time.time()
    registro = INTENTOS_FALLIDOS.get(ip, {"conteo": 0, "bloqueado_hasta": 0})
    registro["conteo"] += 1
    if registro["conteo"] >= 5:
        registro["bloqueado_hasta"] = ahora + 300  # 5 minutos de bloqueo
        registro["conteo"] = 0
    INTENTOS_FALLIDOS[ip] = registro

def resetear_intentos_fallidos(ip: str):
    if ip in INTENTOS_FALLIDOS:
        del INTENTOS_FALLIDOS[ip]

def generar_jwt_token(usuario: dict) -> str:
    ahora = time.time()
    payload = {
        "sub": usuario["id"],
        "username": usuario["username"],
        "nombre": usuario.get("nombre", usuario["username"]),
        "avatar": usuario.get("avatar", "/static/avatars/bot_cyan.jpg"),
        "rol": usuario.get("rol", "usuario"),
        "iat": int(ahora),
        "exp": int(ahora + JWT_EXPIRATION_SECONDS)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def validar_jwt_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None

def obtener_usuario_actual(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("authorization", "")
    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("x-auth-token")
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    return validar_jwt_token(token)

class LoginPayload(BaseModel):
    username: str
    password: str

class SolicitarPinPayload(BaseModel):
    username: str
    nombre: Optional[str] = None

class RegisterPayload(BaseModel):
    username: str
    password: str
    nombre: Optional[str] = None
    avatar: Optional[str] = "/static/avatars/bot_cyan.jpg"
    pin: str

class ValidarPinPayload(BaseModel):
    username: str
    pin: str

@app.post("/api/auth/login")
async def auth_login(payload: LoginPayload, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    bloqueo = verificar_bloqueo_fuerza_bruta(client_ip)
    if bloqueo:
        return JSONResponse(status_code=429, content={"status": "error", "message": bloqueo})

    usuarios = cargar_usuarios()
    usuario_encontrado = None
    for u in usuarios:
        u_name = u["username"].strip().lower()
        input_name = payload.username.strip().lower()
        if u_name == input_name or (u_name == "wuilfredo" and input_name == "wuil") or (u_name == "wuil" and input_name == "wuilfredo"):
            usuario_encontrado = u
            break

    if not usuario_encontrado:
        registrar_intento_fallido(client_ip)
        return JSONResponse(status_code=401, content={"status": "error", "message": "Usuario o contraseña incorrectos"})

    try:
        password_valida = bcrypt.checkpw(payload.password.encode("utf-8"), usuario_encontrado["password_hash"].encode("utf-8"))
    except Exception:
        password_valida = False

    if not password_valida:
        registrar_intento_fallido(client_ip)
        return JSONResponse(status_code=401, content={"status": "error", "message": "Usuario o contraseña incorrectos"})

    resetear_intentos_fallidos(client_ip)
    token = generar_jwt_token(usuario_encontrado)

    user_safe = {
        "id": usuario_encontrado["id"],
        "username": usuario_encontrado["username"],
        "nombre": usuario_encontrado.get("nombre", usuario_encontrado["username"]),
        "avatar": usuario_encontrado.get("avatar", "/static/avatars/bot_cyan.jpg"),
        "rol": usuario_encontrado.get("rol", "usuario")
    }

    resp = JSONResponse(content={
        "status": "ok",
        "message": f"¡Bienvenido, {user_safe['nombre']}!",
        "token": token,
        "user": user_safe
    })
    resp.set_cookie(key="access_token", value=token, max_age=JWT_EXPIRATION_SECONDS, httponly=True, samesite="lax")
    return resp

@app.post("/api/auth/solicitar-pin")
async def auth_solicitar_pin(payload: SolicitarPinPayload, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    username_clean = payload.username.strip()
    if len(username_clean) < 3:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Ingresa al menos 3 caracteres en el nombre de usuario para solicitar el PIN"})

    usuarios = cargar_usuarios()
    for u in usuarios:
        if u["username"].strip().lower() == username_clean.lower():
            return JSONResponse(status_code=400, content={"status": "error", "message": "Ese nombre de usuario ya está registrado en el sistema"})

    ahora = time.time()
    ultimo = ULTIMA_SOLICITUD_PIN_POR_IP.get(client_ip, 0)
    if ahora - ultimo < 60:
        espera = int(60 - (ahora - ultimo))
        return JSONResponse(status_code=429, content={"status": "error", "message": f"Por favor espera {espera} segundos antes de solicitar otro PIN."})

    ULTIMA_SOLICITUD_PIN_POR_IP[client_ip] = ahora

    import random
    pin = f"{random.randint(100000, 999999)}"
    nombre_display = payload.nombre.strip() if (payload.nombre and payload.nombre.strip()) else username_clean
    expira_en = ahora + 600  # 10 minutos de validez

    # Limpiar pines expirados
    pines_a_borrar = [p for p, d in PINS_REGISTRO.items() if d.get("expira_en", 0) < ahora]
    for p in pines_a_borrar:
        del PINS_REGISTRO[p]

    PINS_REGISTRO[pin] = {
        "username": username_clean.lower(),
        "nombre": nombre_display,
        "ip": client_ip,
        "creado_en": ahora,
        "expira_en": expira_en
    }

    hora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mensaje_telegram = (
        f"🔐 *SOLICITUD DE REGISTRO EN AGENTICOS*\n\n"
        f"👤 *Tripulante:* `{username_clean}`\n"
        f"🌐 *Dirección IP:* `{client_ip}`\n"
        f"⏰ *Hora:* `{hora_str}`\n\n"
        f"🔑 *PIN DE AUTORIZACIÓN:* `{pin}`\n"
        f"⏳ *Validez:* 10 minutos (un solo uso)\n\n"
        f"⚡ _Si autorizas a este tripulante a registrarse en la consola, compártele este PIN._"
    )

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, enviar_telegram_alerta_sync, mensaje_telegram)
    except Exception as e:
        print(f"Error enviando PIN a Telegram: {e}")

    print(f"=== PIN DE REGISTRO GENERADO === [Usuario: {username_clean}] PIN: {pin} (Expira en 10 min)")

    return {
        "status": "ok",
        "message": "Solicitud enviada al Capitán vía Telegram. Contacta al Capitán para obtener tu PIN de acceso de 6 dígitos.",
        "ttl_segundos": 600
    }

@app.post("/api/auth/validar-pin")
async def auth_validar_pin(payload: ValidarPinPayload):
    username_clean = payload.username.strip().lower()
    pin_clean = payload.pin.strip()
    if not pin_clean or len(pin_clean) != 6:
        return JSONResponse(status_code=400, content={"status": "error", "message": "El PIN debe tener 6 dígitos numéricos"})
    
    if not username_clean:
        return JSONResponse(status_code=400, content={"status": "error", "message": "El nombre de usuario es requerido para validar el PIN"})

    registro_pin = PINS_REGISTRO.get(pin_clean)
    ahora = time.time()
    if not registro_pin or registro_pin.get("expira_en", 0) < ahora:
        return JSONResponse(status_code=403, content={"status": "error", "message": "PIN incorrecto o ha expirado. Solicita uno nuevo."})

    if registro_pin.get("username") != username_clean:
        return JSONResponse(status_code=403, content={"status": "error", "message": "El PIN de autorización no corresponde a este usuario"})

    return {"status": "ok", "message": "PIN verificado y autorizado por el Capitán"}

@app.post("/api/auth/register")
async def auth_register(payload: RegisterPayload, request: Request):
    username_clean = payload.username.strip()
    if len(username_clean) < 3:
        return JSONResponse(status_code=400, content={"status": "error", "message": "El nombre de usuario debe tener al menos 3 caracteres"})

    if len(payload.password) < 8:
        return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña debe tener al menos 8 caracteres"})

    import re
    if not re.search(r"[A-Z]", payload.password):
        return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña debe incluir al menos una letra mayúscula (A-Z)"})

    if not re.search(r"[0-9]", payload.password):
        return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña debe incluir al menos un número (0-9)"})

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", payload.password):
        return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña debe incluir al menos un carácter especial o símbolo (!@#$%&*...)"})

    # Validar PIN de autorización del Capitán
    pin_ingresado = payload.pin.strip() if (payload.pin and payload.pin.strip()) else ""
    if not pin_ingresado:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Debes solicitar e ingresar el PIN de autorización de 6 dígitos"})

    registro_pin = PINS_REGISTRO.get(pin_ingresado)
    ahora = time.time()
    if not registro_pin or registro_pin.get("expira_en", 0) < ahora:
        return JSONResponse(status_code=403, content={"status": "error", "message": "El PIN de autorización es inválido o ha expirado. Solicita un nuevo PIN al Capitán."})

    if registro_pin.get("username") != username_clean.lower():
        return JSONResponse(status_code=403, content={"status": "error", "message": "El PIN de autorización no corresponde a este nombre de usuario"})

    # Destruir PIN inmediatamente (un solo uso)
    del PINS_REGISTRO[pin_ingresado]

    usuarios = cargar_usuarios()
    for u in usuarios:
        if u["username"].strip().lower() == username_clean.lower():
            return JSONResponse(status_code=400, content={"status": "error", "message": "Ese nombre de usuario ya está en uso. Por favor elige otro."})

    salt = bcrypt.gensalt(rounds=12)
    hashed_pwd = bcrypt.hashpw(payload.password.encode("utf-8"), salt).decode("utf-8")

    nuevo_id = f"usr-{int(time.time()*1000)}"
    nombre_display = payload.nombre.strip() if (payload.nombre and payload.nombre.strip()) else username_clean
    avatar_elegido = payload.avatar if (payload.avatar and payload.avatar.strip()) else "/static/avatars/bot_cyan.jpg"

    rol = "admin" if len(usuarios) == 0 else "usuario"

    nuevo_usuario = {
        "id": nuevo_id,
        "username": username_clean,
        "password_hash": hashed_pwd,
        "nombre": nombre_display,
        "avatar": avatar_elegido,
        "rol": rol,
        "creado_en": datetime.now().isoformat()
    }

    usuarios.append(nuevo_usuario)
    guardar_usuarios(usuarios)

    token = generar_jwt_token(nuevo_usuario)
    user_safe = {
        "id": nuevo_usuario["id"],
        "username": nuevo_usuario["username"],
        "nombre": nuevo_usuario["nombre"],
        "avatar": nuevo_usuario["avatar"],
        "rol": nuevo_usuario["rol"]
    }

    resp = JSONResponse(content={
        "status": "ok",
        "message": f"¡Cuenta creada con éxito! Bienvenido, {user_safe['nombre']}.",
        "token": token,
        "user": user_safe
    })
    resp.set_cookie(key="access_token", value=token, max_age=JWT_EXPIRATION_SECONDS, httponly=True, samesite="lax")
    return resp

@app.get("/api/auth/me")
async def auth_me(request: Request):
    user_payload = obtener_usuario_actual(request)
    if not user_payload:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Sesión no válida o expirada"})
    return {"status": "ok", "user": user_payload}

@app.post("/api/auth/logout")
async def auth_logout():
    resp = JSONResponse(content={"status": "ok", "message": "Sesión cerrada correctamente"})
    resp.delete_cookie(key="access_token")
    return resp

@app.get("/api/auth/status")
async def auth_status():
    env_path = AGENTES_DIR / ".env"
    auth_active = True
    if env_path.exists():
        try:
            for l in env_path.read_text(encoding="utf-8").splitlines():
                if l.strip().startswith("CONSOLE_AUTH_ACTIVE="):
                    auth_active = (l.strip().split("=", 1)[1].strip().strip('"').strip("'").lower() == "true")
                    break
        except Exception:
            pass
    usuarios = cargar_usuarios()
    return {
        "auth_active": auth_active,
        "total_usuarios": len(usuarios)
    }

class ChatMessage(BaseModel):
    texto: str
    modo: str = "auto"

class ModeConfig(BaseModel):
    modo: str

@app.get("/api/modo")
async def get_modo():
    modo_path = BASE_DIR / "modo_agente.json"
    if modo_path.exists():
        try:
            return json.loads(modo_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"modo": "auto"}

@app.post("/api/modo")
async def set_modo(cfg: ModeConfig):
    modo_path = BASE_DIR / "modo_agente.json"
    data = {"modo": cfg.modo}
    modo_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "modo": cfg.modo}

# -----------------------------------------------------------------------------
# GESTIÓN DE SESIONES Y CANALES AISLADOS DE CONVERSACIÓN
# -----------------------------------------------------------------------------
CANALES_DIR = AGENTES_DIR / "memoria" / "canales"
CANALES_DIR.mkdir(parents=True, exist_ok=True)
SESIONES_INDEX_PATH = CANALES_DIR / "sesiones_index.json"

def cargar_sesiones_index():
    try:
        if not SESIONES_INDEX_PATH.exists():
            sesion_id = f"sesion_{int(time.time())}"
            mensajes_existentes = []
            canal_u = BASE_DIR / "canal_usuario.json"
            if canal_u.exists():
                try:
                    raw = json.loads(canal_u.read_text(encoding="utf-8"))
                    mensajes_existentes = raw.get("mensajes", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
                except Exception:
                    mensajes_existentes = []
            
            archivo_canal = CANALES_DIR / f"{sesion_id}.json"
            archivo_canal.write_text(json.dumps({"mensajes": mensajes_existentes}, indent=2, ensure_ascii=False), encoding="utf-8")

            primer_titulo = "Conversación Principal"
            if mensajes_existentes:
                for m in mensajes_existentes:
                    txt = m.get("contenido", {}).get("texto", "") if isinstance(m.get("contenido"), dict) else str(m.get("contenido", ""))
                    if txt.strip():
                        clean_t = txt.strip().replace("\n", " ")
                        primer_titulo = (clean_t[:28] + "...") if len(clean_t) > 28 else clean_t
                        break

            indice = [{
                "id": sesion_id,
                "titulo": primer_titulo,
                "creado": datetime.now().isoformat(),
                "actualizado": datetime.now().isoformat(),
                "total_mensajes": len(mensajes_existentes),
                "activo": True
            }]
            SESIONES_INDEX_PATH.write_text(json.dumps(indice, indent=2, ensure_ascii=False), encoding="utf-8")
            return indice

        sesiones = json.loads(SESIONES_INDEX_PATH.read_text(encoding="utf-8"))
        ancladas = [s for s in sesiones if s.get("anclado")]
        no_ancladas = [s for s in sesiones if not s.get("anclado")]
        return ancladas + no_ancladas
    except Exception as e:
        print(f"Error cargando sesiones_index: {e}")
        return []

def guardar_sesiones_index(sesiones):
    try:
        SESIONES_INDEX_PATH.write_text(json.dumps(sesiones, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Error guardando sesiones_index: {e}")

def sincronizar_canal_activo_con_disco():
    try:
        sesiones = cargar_sesiones_index()
        activa = next((s for s in sesiones if s.get("activo")), None)
        if activa:
            canal_u = BASE_DIR / "canal_usuario.json"
            if canal_u.exists():
                raw = json.loads(canal_u.read_text(encoding="utf-8"))
                msgs = raw.get("mensajes", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
                (CANALES_DIR / f"{activa['id']}.json").write_text(json.dumps({"mensajes": msgs}, indent=2, ensure_ascii=False), encoding="utf-8")
                activa["total_mensajes"] = len(msgs)
                guardar_sesiones_index(sesiones)
    except Exception:
        pass

@app.get("/api/chat/sesiones")
async def api_listar_sesiones_chat():
    sincronizar_canal_activo_con_disco()
    return {"status": "ok", "sesiones": cargar_sesiones_index()}

@app.post("/api/chat/sesiones/nueva")
async def api_nueva_sesion_chat():
    sincronizar_canal_activo_con_disco()
    sesiones = cargar_sesiones_index()
    for s in sesiones:
        s["activo"] = False
    
    nueva_id = f"sesion_{int(time.time())}"
    nueva = {
        "id": nueva_id,
        "titulo": f"Chat #{len(sesiones) + 1}",
        "anclado": False,
        "creado": datetime.now().isoformat(),
        "actualizado": datetime.now().isoformat(),
        "total_mensajes": 0,
        "activo": True
    }
    ancladas = [s for s in sesiones if s.get("anclado")]
    no_ancladas = [s for s in sesiones if not s.get("anclado")]
    sesiones = ancladas + [nueva] + no_ancladas
    guardar_sesiones_index(sesiones)
    
    (CANALES_DIR / f"{nueva_id}.json").write_text(json.dumps({"mensajes": []}, indent=2, ensure_ascii=False), encoding="utf-8")
    (BASE_DIR / "canal_usuario.json").write_text(json.dumps({"mensajes": []}, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return {"status": "ok", "sesion": nueva, "sesiones": sesiones}

@app.post("/api/chat/sesiones/{sesion_id}/activar")
async def api_activar_sesion_chat(sesion_id: str):
    sincronizar_canal_activo_con_disco()
    sesiones = cargar_sesiones_index()
    target = next((s for s in sesiones if s.get("id") == sesion_id), None)
    if not target:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Sesión no encontrada"})
    
    for s in sesiones:
        s["activo"] = (s.get("id") == sesion_id)
    guardar_sesiones_index(sesiones)
    
    archivo = CANALES_DIR / f"{sesion_id}.json"
    mensajes_cargados = []
    if archivo.exists():
        try:
            raw = json.loads(archivo.read_text(encoding="utf-8"))
            mensajes_cargados = raw.get("mensajes", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        except Exception:
            mensajes_cargados = []
    
    (BASE_DIR / "canal_usuario.json").write_text(json.dumps({"mensajes": mensajes_cargados}, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "activa": target, "sesiones": sesiones, "mensajes": mensajes_cargados}

class RenombrarSesionPayload(BaseModel):
    titulo: str

@app.post("/api/chat/sesiones/{sesion_id}/renombrar")
async def api_renombrar_sesion_chat(sesion_id: str, payload: RenombrarSesionPayload):
    sesiones = cargar_sesiones_index()
    target = next((s for s in sesiones if s.get("id") == sesion_id), None)
    if not target:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Sesión no encontrada"})
    nuevo_titulo = payload.titulo.strip()
    if not nuevo_titulo:
        return JSONResponse(status_code=400, content={"status": "error", "message": "El título no puede estar vacío"})
    target["titulo"] = nuevo_titulo
    target["actualizado"] = datetime.now().isoformat()
    guardar_sesiones_index(sesiones)
    return {"status": "ok", "sesion": target, "sesiones": sesiones}

@app.post("/api/chat/sesiones/{sesion_id}/anclar")
async def api_anclar_sesion_chat(sesion_id: str):
    sesiones = cargar_sesiones_index()
    target = next((s for s in sesiones if s.get("id") == sesion_id), None)
    if not target:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Sesión no encontrada"})
    target["anclado"] = not target.get("anclado", False)
    target["actualizado"] = datetime.now().isoformat()
    ancladas = [s for s in sesiones if s.get("anclado")]
    no_ancladas = [s for s in sesiones if not s.get("anclado")]
    sesiones = ancladas + no_ancladas
    guardar_sesiones_index(sesiones)
    return {"status": "ok", "anclado": target["anclado"], "sesiones": sesiones}

@app.delete("/api/chat/sesiones/{sesion_id}")
async def api_eliminar_sesion_chat(sesion_id: str):
    sesiones = cargar_sesiones_index()
    era_activa = False
    nuevas_sesiones = []
    for s in sesiones:
        if s.get("id") == sesion_id:
            era_activa = s.get("activo", False)
        else:
            nuevas_sesiones.append(s)
    
    archivo = CANALES_DIR / f"{sesion_id}.json"
    if archivo.exists():
        try:
            archivo.unlink()
        except Exception:
            pass
    
    if not nuevas_sesiones:
        nueva_id = f"sesion_{int(time.time())}"
        nuevas_sesiones = [{
            "id": nueva_id,
            "titulo": "Conversación Principal",
            "anclado": False,
            "creado": datetime.now().isoformat(),
            "actualizado": datetime.now().isoformat(),
            "total_mensajes": 0,
            "activo": True
        }]
        (CANALES_DIR / f"{nueva_id}.json").write_text(json.dumps({"mensajes": []}, indent=2, ensure_ascii=False), encoding="utf-8")
        (BASE_DIR / "canal_usuario.json").write_text(json.dumps({"mensajes": []}, indent=2, ensure_ascii=False), encoding="utf-8")
    elif era_activa:
        nuevas_sesiones[0]["activo"] = True
        act_id = nuevas_sesiones[0]["id"]
        archivo_act = CANALES_DIR / f"{act_id}.json"
        msgs = []
        if archivo_act.exists():
            try:
                raw = json.loads(archivo_act.read_text(encoding="utf-8"))
                msgs = raw.get("mensajes", []) if isinstance(raw, dict) else []
            except Exception:
                msgs = []
        (BASE_DIR / "canal_usuario.json").write_text(json.dumps({"mensajes": msgs}, indent=2, ensure_ascii=False), encoding="utf-8")
    
    ancladas = [s for s in nuevas_sesiones if s.get("anclado")]
    no_ancladas = [s for s in nuevas_sesiones if not s.get("anclado")]
    nuevas_sesiones = ancladas + no_ancladas
    guardar_sesiones_index(nuevas_sesiones)
    return {"status": "ok", "sesiones": nuevas_sesiones}

@app.post("/api/chat")
async def send_chat(msg: ChatMessage):
    import datetime
    canal_path = BASE_DIR / "canal_usuario.json"
    try:
        if canal_path.exists():
            with open(canal_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = {"mensajes": []}
    except Exception:
        raw = {"mensajes": []}
    
    if isinstance(raw, dict):
        mensajes = raw.get("mensajes", [])
    elif isinstance(raw, list):
        mensajes = raw
    else:
        mensajes = []

    # Guardar modo activo seleccionado
    if msg.modo:
        modo_path = BASE_DIR / "modo_agente.json"
        try:
            modo_path.write_text(json.dumps({"modo": msg.modo}, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    msg_id = f"msg-{len(mensajes) + 1:03d}"
    nuevo_msg = {
        "id": msg_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "de": "usuario",
        "para": "Luffy",
        "tipo": "mensaje_dashboard",
        "modo": msg.modo,
        "estado": "enviado",
        "leido_por": ["usuario"],
        "contenido": {"texto": msg.texto}
    }
    mensajes.append(nuevo_msg)
    
    if len(mensajes) > 60:
        mensajes = mensajes[-60:]
        
    data_to_save = {"mensajes": mensajes}
    with open(canal_path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
    # Guardar en la sesión activa y auto-titular si es nueva
    try:
        sesiones = cargar_sesiones_index()
        activa = next((s for s in sesiones if s.get("activo")), None)
        if activa:
            if activa.get("titulo", "").startswith("Chat #") or activa.get("total_mensajes", 0) <= 1:
                clean_text = msg.texto.strip().replace("\n", " ")
                activa["titulo"] = (clean_text[:28] + "...") if len(clean_text) > 28 else clean_text
            activa["total_mensajes"] = len(mensajes)
            activa["actualizado"] = datetime.datetime.now().isoformat()
            guardar_sesiones_index(sesiones)
            (CANALES_DIR / f"{activa['id']}.json").write_text(json.dumps({"mensajes": mensajes}, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e_s:
        print(f"Error sincronizando sesion activa en send_chat: {e_s}")
        
    return {"status": "ok", "mensaje": nuevo_msg}

class EnvConfig(BaseModel):
    provider: str
    api_key: str
    model: str

def obtener_modelos_agentes():
    env_path = AGENTES_DIR / ".env"
    default_model = "deepseek-chat"
    agent_models = {}
    
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "DEFAULT_MODEL":
                    default_model = v
                elif k.startswith("MODEL_"):
                    ag_name = k.replace("MODEL_", "").lower()
                    agent_models[ag_name] = v
        except Exception:
            pass

    agentes = ["luffy", "zoro", "sanji", "robin", "nami"]
    return {ag: agent_models.get(ag, default_model) for ag in agentes}

class FullConfigPayload(BaseModel):
    keys: Optional[Dict[str, str]] = None
    base_urls: Optional[Dict[str, str]] = None
    default_model: Optional[str] = None
    default_provider: Optional[str] = None
    modelos: Optional[Dict[str, str]] = None
    presupuesto_maximo: Optional[float] = None
    telegram: Optional[Dict[str, str]] = None
    ollama: Optional[Dict[str, str]] = None
    seguridad: Optional[Dict[str, Any]] = None

@app.get("/api/config/env")
async def read_env():
    env_path = AGENTES_DIR / ".env"
    data = {
        "keys": {},
        "base_urls": {},
        "default_model": "deepseek-chat",
        "default_provider": "deepseek",
        "modelos": obtener_modelos_agentes(),
        "presupuesto_maximo": 10.0,
        "telegram": {"token": "", "chat_id": ""},
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3"},
        "seguridad": {
            "auth_active": False,
            "auth_user": "admin",
            "auth_password": "",
            "auth_avatar": "/static/avatars/bot_cyan.jpg",
            "telemetry_token": "",
            "ip_whitelist": ""
        }
    }
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            val = v.strip().strip('"').strip("'")
            if k == "DEFAULT_MODEL":
                data["default_model"] = val
            elif k == "DEFAULT_PROVIDER":
                data["default_provider"] = val
            elif k == "PRESUPUESTO_MAXIMO":
                try:
                    data["presupuesto_maximo"] = float(val)
                except ValueError:
                    pass
            elif k == "TELEGRAM_BOT_TOKEN":
                data["telegram"]["token"] = val
            elif k == "TELEGRAM_CHAT_ID":
                data["telegram"]["chat_id"] = val
            elif k == "OLLAMA_BASE_URL":
                data["ollama"]["base_url"] = val
            elif k == "OLLAMA_MODEL":
                data["ollama"]["model"] = val
            elif k == "CONSOLE_AUTH_ACTIVE":
                data["seguridad"]["auth_active"] = (val.lower() == "true")
            elif k == "CONSOLE_AUTH_USER":
                data["seguridad"]["auth_user"] = val
            elif k == "CONSOLE_AUTH_PASSWORD":
                data["seguridad"]["auth_password"] = ""
                data["seguridad"]["has_password"] = bool(val)
            elif k == "CONSOLE_AUTH_AVATAR":
                data["seguridad"]["auth_avatar"] = val
            elif k == "TELEMETRY_SECRET_TOKEN":
                data["seguridad"]["telemetry_token"] = val
            elif k == "ALLOWED_IPS":
                data["seguridad"]["ip_whitelist"] = val
            elif k.endswith("_BASE_URL"):
                prov = k.replace("_BASE_URL", "").lower()
                data["base_urls"][prov] = val
            elif k.endswith("_API_KEY") or k.endswith("_KEY"):
                provider = k.replace("_API_KEY", "").replace("_KEY", "").lower()
                data["keys"][provider] = val
    return data

@app.post("/api/config/guardar")
async def guardar_config(payload: FullConfigPayload):
    env_path = AGENTES_DIR / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        
    env_dict = {}
    ordered_keys = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        env_dict[k] = v
        if k not in ordered_keys:
            ordered_keys.append(k)

    if payload.keys:
        for prov, val in payload.keys.items():
            if val is not None:
                env_key = f"{prov.upper()}_API_KEY"
                if prov.lower() == "fal":
                    env_key = "FAL_KEY"
                env_dict[env_key] = val
                if env_key not in ordered_keys:
                    ordered_keys.append(env_key)

    if payload.base_urls:
        for prov, url_val in payload.base_urls.items():
            if url_val is not None and url_val.strip():
                url_key = f"{prov.upper()}_BASE_URL"
                env_dict[url_key] = url_val.strip()
                if url_key not in ordered_keys:
                    ordered_keys.append(url_key)

    if payload.default_model:
        env_dict["DEFAULT_MODEL"] = payload.default_model
        if "DEFAULT_MODEL" not in ordered_keys:
            ordered_keys.append("DEFAULT_MODEL")
    if payload.default_provider:
        env_dict["DEFAULT_PROVIDER"] = payload.default_provider
        if "DEFAULT_PROVIDER" not in ordered_keys:
            ordered_keys.append("DEFAULT_PROVIDER")

    if payload.modelos:
        for ag, mod in payload.modelos.items():
            ag_key = f"MODEL_{ag.upper()}"
            env_dict[ag_key] = mod
            if ag_key not in ordered_keys:
                ordered_keys.append(ag_key)

    if payload.presupuesto_maximo is not None:
        pres_val = float(payload.presupuesto_maximo)
        env_dict["PRESUPUESTO_MAXIMO"] = str(pres_val)
        if "PRESUPUESTO_MAXIMO" not in ordered_keys:
            ordered_keys.append("PRESUPUESTO_MAXIMO")
        # Actualizar costos.json y si el presupuesto supera el costo actual, desmarcar bloqueo
        costos_path = BASE_DIR / "costos.json"
        if costos_path.exists():
            try:
                c_data = json.loads(costos_path.read_text(encoding="utf-8"))
                c_data["presupuesto_maximo"] = pres_val
                if float(c_data.get("costo", 0.0)) < pres_val:
                    c_data["bloqueado_por_presupuesto"] = False
                costos_path.write_text(json.dumps(c_data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    if payload.telegram:
        if "token" in payload.telegram and payload.telegram["token"] is not None:
            env_dict["TELEGRAM_BOT_TOKEN"] = payload.telegram["token"]
            if "TELEGRAM_BOT_TOKEN" not in ordered_keys:
                ordered_keys.append("TELEGRAM_BOT_TOKEN")
        if "chat_id" in payload.telegram and payload.telegram["chat_id"] is not None:
            env_dict["TELEGRAM_CHAT_ID"] = payload.telegram["chat_id"]
            if "TELEGRAM_CHAT_ID" not in ordered_keys:
                ordered_keys.append("TELEGRAM_CHAT_ID")

    if payload.ollama:
        if "base_url" in payload.ollama and payload.ollama["base_url"] is not None:
            env_dict["OLLAMA_BASE_URL"] = payload.ollama["base_url"]
            if "OLLAMA_BASE_URL" not in ordered_keys:
                ordered_keys.append("OLLAMA_BASE_URL")
        if "model" in payload.ollama and payload.ollama["model"] is not None:
            env_dict["OLLAMA_MODEL"] = payload.ollama["model"]
            if "OLLAMA_MODEL" not in ordered_keys:
                ordered_keys.append("OLLAMA_MODEL")
            if "OLLAMA_BASE_URL" not in ordered_keys:
                ordered_keys.append("OLLAMA_BASE_URL")
        if "model" in payload.ollama and payload.ollama["model"] is not None:
            env_dict["OLLAMA_MODEL"] = payload.ollama["model"]
            if "OLLAMA_MODEL" not in ordered_keys:
                ordered_keys.append("OLLAMA_MODEL")

    if payload.seguridad:
        s = payload.seguridad
        if "auth_active" in s:
            auth_act = "true" if s["auth_active"] in [True, "true", "True", 1] else "false"
            env_dict["CONSOLE_AUTH_ACTIVE"] = auth_act
            if "CONSOLE_AUTH_ACTIVE" not in ordered_keys:
                ordered_keys.append("CONSOLE_AUTH_ACTIVE")

        old_user = env_dict.get("CONSOLE_AUTH_USER", "admin")
        if "auth_user" in s and s["auth_user"] is not None:
            new_user = str(s["auth_user"]).strip()
            if new_user:
                env_dict["CONSOLE_AUTH_USER"] = new_user
                if "CONSOLE_AUTH_USER" not in ordered_keys:
                    ordered_keys.append("CONSOLE_AUTH_USER")
                if new_user.lower() != old_user.lower():
                    usuarios = cargar_usuarios()
                    for u in usuarios:
                        if u["username"].lower() == old_user.lower():
                            u["username"] = new_user
                            u["nombre"] = f"Capitán {new_user}"
                    guardar_usuarios(usuarios)

        # GESTIÓN SEGURA DE CAMBIO DE CONTRASEÑA
        new_pass = str(s.get("new_password") or s.get("auth_password") or "").strip()
        if new_pass:
            old_pass = str(s.get("old_password") or "").strip()
            current_pass = env_dict.get("CONSOLE_AUTH_PASSWORD", "")
            
            usuarios = cargar_usuarios()
            admin_u = None
            target_user = env_dict.get("CONSOLE_AUTH_USER", "admin").lower()
            for u in usuarios:
                if u["username"].lower() == target_user:
                    admin_u = u
                    break

            valida = False
            if current_pass and old_pass == current_pass:
                valida = True
            elif admin_u and "password_hash" in admin_u:
                try:
                    if bcrypt.checkpw(old_pass.encode("utf-8"), admin_u["password_hash"].encode("utf-8")):
                        valida = True
                except Exception:
                    pass

            if not valida:
                return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña actual es incorrecta. No se autorizó el cambio de clave."})

            env_dict["CONSOLE_AUTH_PASSWORD"] = new_pass
            if "CONSOLE_AUTH_PASSWORD" not in ordered_keys:
                ordered_keys.append("CONSOLE_AUTH_PASSWORD")

            # Actualizar bcrypt hash en usuarios.json
            salt = bcrypt.gensalt(rounds=12)
            new_hash = bcrypt.hashpw(new_pass.encode("utf-8"), salt).decode("utf-8")
            if admin_u:
                admin_u["password_hash"] = new_hash
            else:
                usuarios.append({
                    "id": f"usr-{int(time.time())}",
                    "username": target_user,
                    "password_hash": new_hash,
                    "nombre": f"Capitán {target_user}",
                    "avatar": env_dict.get("CONSOLE_AUTH_AVATAR", "/static/avatars/bot_cyan.jpg"),
                    "rol": "admin",
                    "creado_en": datetime.now().isoformat()
                })
            guardar_usuarios(usuarios)

        if "auth_avatar" in s and s["auth_avatar"] is not None:
            new_avatar = str(s["auth_avatar"]).strip()
            env_dict["CONSOLE_AUTH_AVATAR"] = new_avatar
            if "CONSOLE_AUTH_AVATAR" not in ordered_keys:
                ordered_keys.append("CONSOLE_AUTH_AVATAR")
            usuarios = cargar_usuarios()
            target_user = env_dict.get("CONSOLE_AUTH_USER", "admin").lower()
            for u in usuarios:
                if u["username"].lower() == target_user:
                    u["avatar"] = new_avatar
            guardar_usuarios(usuarios)

        if "telemetry_token" in s and s["telemetry_token"] is not None:
            env_dict["TELEMETRY_SECRET_TOKEN"] = str(s["telemetry_token"]).strip()
            if "TELEMETRY_SECRET_TOKEN" not in ordered_keys:
                ordered_keys.append("TELEMETRY_SECRET_TOKEN")
        if "ip_whitelist" in s and s["ip_whitelist"] is not None:
            env_dict["ALLOWED_IPS"] = str(s["ip_whitelist"]).strip()
            if "ALLOWED_IPS" not in ordered_keys:
                ordered_keys.append("ALLOWED_IPS")

    new_lines = []
    seen = set()
    for line in lines:
        raw = line.strip()
        if raw.startswith("#") or not raw:
            new_lines.append(line)
            continue
        if "=" in raw:
            k = raw.split("=", 1)[0].strip()
            if k in env_dict:
                v = env_dict[k]
                new_lines.append(f'{k}="{v}"' if (" " in v or any(c in v for c in "!@#$%^&*()")) else f'{k}={v}')
                seen.add(k)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k in ordered_keys:
        if k not in seen and k in env_dict:
            v = env_dict[k]
            new_lines.append(f'{k}="{v}"' if (" " in v or any(c in v for c in "!@#$%^&*()")) else f'{k}={v}')

    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "ok", "message": "Configuración guardada correctamente"}

@app.post("/api/config/test-telegram")
async def test_telegram():
    env_path = AGENTES_DIR / ".env"
    token = ""
    chat_id = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token or not chat_id:
        return {"status": "error", "message": "Falta configurar Token o Chat ID de Telegram"}
    try:
        import urllib.request
        msg = "🏴‍☠️ [AgenticOS] Mensaje de prueba exitoso desde el panel de Configuración."
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": msg}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                return {"status": "ok", "message": "¡Mensaje de prueba recibido en Telegram!"}
    except Exception as e:
        return {"status": "error", "message": f"Error conectando con Telegram: {str(e)}"}
    return {"status": "error", "message": "No se pudo entregar el mensaje a Telegram"}

class TestProviderPayload(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = ""

def validar_conexion_proveedor(provider: str, api_key: str, base_url: str = "") -> Tuple[bool, str]:
    import urllib.request
    import urllib.error

    prov = (provider or "").strip().lower()
    key = (api_key or "").strip()
    url = (base_url or "").strip()

    if not key and prov != "ollama":
        return False, "La API Key no puede estar vacía"

    default_urls = {
        "groq": "https://api.groq.com/openai/v1",
        "deepseek": "https://api.deepseek.com",
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "together": "https://api.together.xyz/v1",
        "fireworks": "https://api.fireworks.ai/inference/v1",
        "mistral": "https://api.mistral.ai/v1",
        "cerebras": "https://api.cerebras.ai/v1",
        "xai": "https://api.x.ai/v1",
        "ollama": "http://localhost:11434"
    }

    if not url:
        url = default_urls.get(prov, "")

    try:
        if prov in ("gemini", "google"):
            test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            req = urllib.request.Request(test_url, headers={"User-Agent": "AgenticOS-Validator/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.status < 300:
                    return True, "API Key de Google Gemini verificada y autorizada con éxito"
        elif prov in ("claude", "anthropic"):
            test_url = "https://api.anthropic.com/v1/models"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "User-Agent": "AgenticOS-Validator/1.0"
            }
            req = urllib.request.Request(test_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.status < 300:
                    return True, "API Key de Anthropic Claude verificada y autorizada con éxito"
        elif prov == "ollama":
            test_url = f"{url.rstrip('/')}/api/tags" if url else "http://localhost:11434/api/tags"
            req = urllib.request.Request(test_url, headers={"User-Agent": "AgenticOS-Validator/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                if 200 <= resp.status < 300:
                    return True, "Servidor local Ollama conectado correctamente"
        else:
            if not url:
                url = "https://api.openai.com/v1"
            clean_base = url.rstrip("/")
            test_url = clean_base if clean_base.endswith("/models") else f"{clean_base}/models"
            headers = {
                "Authorization": f"Bearer {key}",
                "User-Agent": "AgenticOS-Validator/1.0"
            }
            req = urllib.request.Request(test_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.status < 300:
                    return True, f"API Key de {prov.upper()} verificada y autorizada con éxito"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, f"Autenticación fallida (Error 401): La API Key ingresada es inválida o expiró en {prov.upper()}."
        elif e.code == 403:
            return False, f"Acceso denegado (Error 403): La clave de {prov.upper()} no tiene permisos o saldo disponible."
        elif e.code == 404:
            return False, f"Ruta no encontrada (Error 404): Revisa la URL Base del proveedor ({url})."
        elif e.code == 429:
            return False, f"Límite de cuota alcanzado (Error 429): La cuenta en {prov.upper()} superó la tasa de peticiones o fondos."
        else:
            return False, f"El proveedor {prov.upper()} rechazó la conexión (Código HTTP {e.code}): {e.reason}"
    except urllib.error.URLError as e:
        return False, f"No se pudo conectar con el endpoint de {prov.upper()}: {e.reason}"
    except Exception as e:
        return False, f"Fallo al conectar con {prov.upper()}: {str(e)}"

    return False, "Respuesta no concluyente del servidor del proveedor"

@app.post("/api/config/test-provider")
async def test_provider_endpoint(payload: TestProviderPayload):
    loop = asyncio.get_running_loop()
    valido, mensaje = await loop.run_in_executor(
        None,
        validar_conexion_proveedor,
        payload.provider,
        payload.api_key,
        payload.base_url or ""
    )
    if valido:
        return {"status": "ok", "message": mensaje}
    else:
        return JSONResponse(status_code=400, content={"status": "error", "message": mensaje})

def obtener_presupuesto_maximo() -> float:
    env_path = AGENTES_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRESUPUESTO_MAXIMO="):
                try:
                    return float(line.split("=", 1)[1].strip().strip('"').strip("'"))
                except Exception:
                    pass
    return 10.0

def enviar_alerta_telegram_presupuesto(gasto: float, limite: float):
    env_path = AGENTES_DIR / ".env"
    token = ""
    chat_id = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token or not chat_id:
        return
    try:
        import urllib.request
        msg = f"🚨 [AgenticOS] PARADA DURA ACTIVADA:\n\nLa tripulación ha alcanzado el límite mensual de presupuesto (${gasto:.2f} / ${limite:.2f} USD).\n\nLos agentes han sido detenidos automáticamente para proteger tu factura. Puedes ampliar el presupuesto o reiniciar el contador desde el panel de control."
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": msg}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception as e:
        print(f"Error enviando alerta Telegram presupuesto: {e}")

def detener_tripulacion_emergencia():
    try:
        subprocess.run(["docker", "compose", "stop"], cwd=str(AGENTES_DIR), capture_output=True, timeout=5)
    except Exception:
        pass
    try:
        current_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            if p.info['pid'] == current_pid:
                continue
            if 'python' in (p.info['name'] or '').lower():
                cmd = " ".join(p.info['cmdline'] or []).lower()
                if any(x in cmd for x in ['base_listener', 'luffy_agent', 'zoro_agent', 'sanji_agent', 'robin_agent', 'nami_agent']):
                    p.terminate()
    except Exception:
        pass

@app.post("/api/config/reset-costos")
async def reset_costos():
    from datetime import datetime
    mes_actual = datetime.now().strftime("%Y-%m")
    costos_path = BASE_DIR / "costos.json"
    default_costos = {
        "mes_activo": mes_actual,
        "tokens": 0,
        "costo": 0.0,
        "bloqueado_por_presupuesto": False,
        "presupuesto_maximo": obtener_presupuesto_maximo(),
        "agentes": {
            "luffy": {"tokens": 0, "costo": 0.0},
            "zoro": {"tokens": 0, "costo": 0.0},
            "sanji": {"tokens": 0, "costo": 0.0},
            "robin": {"tokens": 0, "costo": 0.0},
            "nami": {"tokens": 0, "costo": 0.0}
        },
        "historial_meses": {}
    }
    if costos_path.exists():
        try:
            curr = json.loads(costos_path.read_text(encoding="utf-8"))
            if isinstance(curr, dict) and "historial_meses" in curr:
                default_costos["historial_meses"] = curr["historial_meses"]
        except Exception:
            pass
    costos_path.write_text(json.dumps(default_costos, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "message": f"Contador de costos del mes {mes_actual} restablecido a $0.00"}

@app.post("/api/config/env")
async def update_env(config: EnvConfig):
    env_path = AGENTES_DIR / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    key_name = f"{config.provider.upper()}_API_KEY"
    new_lines = []
    key_found = False
    model_found = False
    provider_found = False
    for line in lines:
        if line.startswith(f"{key_name}="):
            new_lines.append(f"{key_name}={config.api_key}")
            key_found = True
        elif line.startswith("DEFAULT_MODEL="):
            new_lines.append(f"DEFAULT_MODEL={config.model}")
            model_found = True
        elif line.startswith("DEFAULT_PROVIDER="):
            new_lines.append(f"DEFAULT_PROVIDER={config.provider}")
            provider_found = True
        else:
            new_lines.append(line)
    if not key_found: new_lines.append(f"{key_name}={config.api_key}")
    if not model_found: new_lines.append(f"DEFAULT_MODEL={config.model}")
    if not provider_found: new_lines.append(f"DEFAULT_PROVIDER={config.provider}")
    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "success", "message": "Entorno actualizado"}

@app.delete("/api/config/env/{provider}")
async def delete_env_key(provider: str):
    env_path = AGENTES_DIR / ".env"
    if not env_path.exists():
        return {"status": "error", "message": "Archivo de entorno no encontrado"}
    lines = env_path.read_text(encoding="utf-8").splitlines()
    p_up = provider.upper()
    key_name = f"{p_up}_API_KEY"
    url_name = f"{p_up}_BASE_URL"
    new_lines = [line for line in lines if not line.startswith(f"{key_name}=") and not line.startswith(f"{url_name}=")]
    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    return {"status": "success", "message": f"Proveedor {p_up} eliminado"}

@app.post("/api/system/restart")
async def restart_system():
    try:
        bat_path = AGENTES_DIR / "reiniciar_tripulacion.bat"
        if bat_path.exists():
            subprocess.Popen([str(bat_path)], shell=True, cwd=str(AGENTES_DIR))
        else:
            subprocess.Popen("docker compose down && docker compose up -d", shell=True, cwd=str(AGENTES_DIR))
        return {"status": "success", "message": "Ejecutando script de reinicio de contenedor Docker..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------- REGISTRO Y GESTIÓN DE SEGURIDAD -----------------
@app.get("/api/seguridad/incidentes")
async def get_incidentes_seguridad():
    return {
        "incidentes": HISTORIAL_INTRUSIONES,
        "alerta_activa": ULTIMA_ALERTA_INTRUSION if (ULTIMA_ALERTA_INTRUSION and (time.time() - ULTIMA_ALERTA_INTRUSION.get("timestamp", 0) < 120)) else None
    }

@app.post("/api/seguridad/silenciar-alarma")
async def silenciar_alarma_seguridad():
    global ULTIMA_ALERTA_INTRUSION
    ULTIMA_ALERTA_INTRUSION = None
    return {"status": "ok", "message": "Alarma de intrusión silenciada"}

@app.delete("/api/seguridad/incidentes")
async def limpiar_incidentes_seguridad():
    global ULTIMA_ALERTA_INTRUSION, HISTORIAL_INTRUSIONES
    HISTORIAL_INTRUSIONES.clear()
    ULTIMA_ALERTA_INTRUSION = None
    try:
        INCIDENTES_SEGURIDAD_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass
    return {"status": "ok", "message": "Historial de incidentes borrado"}

# ----------------- MONITOREO Y CONTROL DE FLOTA REMOTA -----------------
FLOTA_REMOTA_DB = {}
COMANDOS_FILE = BASE_DIR / "comandos_remotos.json"
COMANDOS_PENDIENTES: Dict[str, List[dict]] = {}
HISTORIAL_COMANDOS: Dict[str, List[dict]] = {}

FLOTAS_REGISTRADAS_FILE = BASE_DIR / "flotas_registradas.json"
FLOTAS_REGISTRADAS: Dict[str, dict] = {}

def cargar_flotas_registradas():
    global FLOTAS_REGISTRADAS
    if FLOTAS_REGISTRADAS_FILE.exists():
        try:
            data = json.loads(FLOTAS_REGISTRADAS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                FLOTAS_REGISTRADAS = {f["id"]: f for f in data if isinstance(f, dict) and "id" in f}
            elif isinstance(data, dict):
                FLOTAS_REGISTRADAS = data
        except Exception:
            FLOTAS_REGISTRADAS = {}

def guardar_flotas_registradas():
    try:
        FLOTAS_REGISTRADAS_FILE.write_text(json.dumps(list(FLOTAS_REGISTRADAS.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

cargar_flotas_registradas()

if COMANDOS_FILE.exists():
    try:
        raw_cmd = json.loads(COMANDOS_FILE.read_text(encoding="utf-8"))
        COMANDOS_PENDIENTES = raw_cmd.get("pendientes", {})
        HISTORIAL_COMANDOS = raw_cmd.get("historial", {})
    except Exception:
        pass

def guardar_comandos():
    try:
        COMANDOS_FILE.write_text(json.dumps({
            "pendientes": COMANDOS_PENDIENTES,
            "historial": HISTORIAL_COMANDOS
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

class ReporteTelemetria(BaseModel):
    id: str
    nombre: str
    tipo: Optional[str] = "Nodo Remoto"
    ip: Optional[str] = "Remoto"
    version: Optional[str] = "v1.0"
    estado: Optional[str] = "activa" # activa | espera | error | desconectada
    agentes: Optional[dict] = None
    docker: Optional[dict] = None
    tarea_actual: Optional[str] = "En ejecución..."
    error_critico: Optional[str] = None
    tokens: Optional[int] = 0
    costo: Optional[float] = 0.0
    cpu: Optional[float] = 0.0
    ram: Optional[float] = 0.0
    logs: Optional[List[dict]] = None
    resultado_comando: Optional[dict] = None

class RegistrarFlotaPayload(BaseModel):
    nombre: str
    cliente: Optional[str] = "Cliente General"
    descripcion: Optional[str] = ""

class HandshakePayload(BaseModel):
    fleet_id: Optional[str] = None
    api_key: str
    timestamp: Optional[float] = None

class ComandoRemotoPayload(BaseModel):
    equipo_id: str
    accion: str
    parametros: Optional[dict] = {}

@app.post("/api/remoto/comando")
async def enviar_comando_remoto(payload: ComandoRemotoPayload):
    cmd_id = f"cmd-{int(time.time()*1000)}"
    nuevo_cmd = {
        "id": cmd_id,
        "accion": payload.accion,
        "parametros": payload.parametros or {},
        "creado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "pendiente"
    }
    if payload.equipo_id not in COMANDOS_PENDIENTES:
        COMANDOS_PENDIENTES[payload.equipo_id] = []
    COMANDOS_PENDIENTES[payload.equipo_id].append(nuevo_cmd)

    if payload.equipo_id not in HISTORIAL_COMANDOS:
        HISTORIAL_COMANDOS[payload.equipo_id] = []
    HISTORIAL_COMANDOS[payload.equipo_id].insert(0, {
        "id": cmd_id,
        "accion": payload.accion,
        "exito": None,
        "salida": "En cola de entrega para el próximo latido de la flota...",
        "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    guardar_comandos()
    return {
        "status": "ok",
        "message": f"Orden '{payload.accion}' encolada para el nodo {payload.equipo_id}",
        "comando": nuevo_cmd
    }

@app.get("/api/remoto/comandos/{equipo_id}")
async def get_comandos_remotos(equipo_id: str):
    return {
        "pendientes": COMANDOS_PENDIENTES.get(equipo_id, []),
        "historial": HISTORIAL_COMANDOS.get(equipo_id, [])
    }

# ----------------- REGISTRO Y CRIPTOGRAFÍA DE FLOTAS REMOTAS -----------------
@app.post("/api/flotas/registrar")
async def registrar_nueva_flota(payload: RegistrarFlotaPayload):
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', payload.nombre.lower().strip()).strip('-')
    if not slug:
        slug = "flota"
    rand_suffix = secrets.token_hex(3)
    fleet_id = f"flota-{slug}-{rand_suffix}"
    
    api_key = f"key_{secrets.token_urlsafe(24)}"
    secret_key = secrets.token_hex(32)
    session_token = f"tok_{secrets.token_urlsafe(32)}"
    expires_at = time.time() + 3600
    
    nueva_flota = {
        "id": fleet_id,
        "nombre": payload.nombre.strip(),
        "cliente": (payload.cliente or "Cliente General").strip(),
        "descripcion": (payload.descripcion or "").strip(),
        "api_key": api_key,
        "secret_key": secret_key,
        "session_token": session_token,
        "session_token_expires_at": expires_at,
        "creado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ultimo_reporte": None,
        "rotaciones_realizadas": 0,
        "estado": "pendiente_conexion"
    }
    
    FLOTAS_REGISTRADAS[fleet_id] = nueva_flota
    guardar_flotas_registradas()
    
    return {
        "status": "ok",
        "message": f"Flota '{payload.nombre}' registrada con éxito",
        "flota": nueva_flota
    }

@app.get("/api/flotas/lista")
async def listar_flotas_registradas():
    cargar_flotas_registradas()
    return {
        "status": "ok",
        "flotas": list(FLOTAS_REGISTRADAS.values())
    }

@app.delete("/api/flotas/eliminar/{fleet_id}")
async def eliminar_flota_registrada(fleet_id: str):
    cargar_flotas_registradas()
    if fleet_id in FLOTAS_REGISTRADAS:
        del FLOTAS_REGISTRADAS[fleet_id]
        guardar_flotas_registradas()
    if fleet_id in FLOTA_REMOTA_DB:
        del FLOTA_REMOTA_DB[fleet_id]
        equipos_path = BASE_DIR / "equipos_remotos.json"
        try:
            equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return {"status": "ok", "message": f"Flota {fleet_id} eliminada"}

@app.post("/api/flotas/handshake")
async def handshake_flota(payload: HandshakePayload, request: Request):
    cargar_flotas_registradas()
    if payload.fleet_id:
        flota = FLOTAS_REGISTRADAS.get(payload.fleet_id)
    else:
        flota = next((f for f in FLOTAS_REGISTRADAS.values() if f.get("api_key") == payload.api_key), None)

    if not flota:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Flota no registrada o clave API incorrecta"})
    
    if payload.api_key != flota.get("api_key"):
        return JSONResponse(status_code=401, content={"status": "error", "message": "API Key de flota inválida"})
    
    # Si viene con firma HMAC, verificarla
    sig_header = request.headers.get("x-fleet-signature")
    if sig_header:
        secret = flota.get("secret_key", "").encode("utf-8")
        ts = request.headers.get("x-fleet-timestamp", str(time.time()))
        msg_raw = f"{flota['id']}:{ts}".encode("utf-8")
        expected_sig = hmac.new(secret, msg_raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected_sig):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Firma HMAC inválida"})
    
    # Generar nuevo session token efímero
    nuevo_token = f"tok_{secrets.token_urlsafe(32)}"
    expires_at = time.time() + 3600
    flota["session_token"] = nuevo_token
    flota["session_token_expires_at"] = expires_at
    flota["estado"] = "vinculada"
    flota["ultimo_reporte"] = time.time()
    guardar_flotas_registradas()
    
    return {
        "status": "ok",
        "message": f"Handshake exitoso con {flota['nombre']}",
        "fleet_id": flota["id"],
        "session_token": nuevo_token,
        "expires_in": 3600
    }

@app.get("/api/flotas/estado/{fleet_id}")
async def obtener_estado_flota_registro(fleet_id: str):
    cargar_flotas_registradas()
    flota = FLOTAS_REGISTRADAS.get(fleet_id)
    if not flota:
        return {"status": "error", "message": "Flota no encontrada"}
    esta_vinculada = flota.get("estado") in ["vinculada", "activa"]
    return {
        "status": "ok",
        "id": fleet_id,
        "nombre": flota.get("nombre"),
        "estado": flota.get("estado", "pendiente_conexion"),
        "vinculada": esta_vinculada,
        "ultimo_reporte": flota.get("ultimo_reporte")
    }

@app.post("/api/flotas/emparejar/simular/{fleet_id}")
async def simular_emparejamiento_flota(fleet_id: str):
    cargar_flotas_registradas()
    flota = FLOTAS_REGISTRADAS.get(fleet_id)
    if not flota:
        return {"status": "error", "message": "Flota no encontrada"}
    flota["estado"] = "vinculada"
    flota["ultimo_reporte"] = time.time()
    guardar_flotas_registradas()
    return {"status": "ok", "message": f"Flota '{flota['nombre']}' vinculada con éxito"}

@app.post("/api/telemetria/reportar")
async def reportar_telemetria(data: ReporteTelemetria, request: Request):
    cargar_flotas_registradas()
    
    # 1. Verificar si corresponde a una Flota Registrada Criptográficamente
    bearer_token = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()
    
    fleet_id = request.headers.get("x-fleet-id") or data.id
    fleet_auth = FLOTAS_REGISTRADAS.get(fleet_id)
    new_token_to_send = None

    if fleet_auth:
        # Validar Token o API Key
        token_valido = False
        received = bearer_token or request.headers.get("x-api-key")
        if received in (fleet_auth.get("session_token"), fleet_auth.get("api_key")):
            token_valido = True
        
        # Validar por firma HMAC si se proveyó
        sig_header = request.headers.get("x-fleet-signature")
        if sig_header:
            secret = fleet_auth.get("secret_key", "").encode("utf-8")
            ts = request.headers.get("x-fleet-timestamp", "")
            expected_sig = hmac.new(secret, f"{fleet_id}:{ts}".encode("utf-8"), hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig_header, expected_sig):
                token_valido = True
        
        if not token_valido:
            return JSONResponse(
                status_code=401,
                content={"status": "error", "message": f"Acceso denegado a flota {fleet_id}: Token no válido o sesión expirada"}
            )
        
        # Rotación automática de sesión si faltan menos de 15 minutos de vigencia
        ahora_ts = time.time()
        expires_at = fleet_auth.get("session_token_expires_at", 0)
        if (expires_at - ahora_ts) < 900:
            nuevo_session_token = f"tok_{secrets.token_urlsafe(32)}"
            fleet_auth["session_token"] = nuevo_session_token
            fleet_auth["session_token_expires_at"] = ahora_ts + 3600
            fleet_auth["rotaciones_realizadas"] = fleet_auth.get("rotaciones_realizadas", 0) + 1
            new_token_to_send = nuevo_session_token
        
        fleet_auth["ultimo_reporte"] = ahora_ts
        fleet_auth["estado"] = "activa"
        guardar_flotas_registradas()
    else:
        # Validación legado de Token Secreto Global si está activo en .env
        env_path = AGENTES_DIR / ".env"
        expected_token = os.getenv("TELEMETRY_SECRET_TOKEN", "").strip()
        if not expected_token and env_path.exists():
            try:
                for l in env_path.read_text(encoding="utf-8").splitlines():
                    if l.strip().startswith("TELEMETRY_SECRET_TOKEN="):
                        expected_token = l.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
            except Exception:
                pass

        if expected_token:
            received_token = request.headers.get("x-telemetry-token") or request.headers.get("x-api-key")
            if not received_token and bearer_token:
                received_token = bearer_token
            
            if received_token != expected_token:
                return JSONResponse(
                    status_code=401,
                    content={"status": "error", "message": "Acceso denegado: Token secreto de telemetría no válido o ausente"}
                )

    ahora_ts = time.time()
    eq_dict = data.dict()
    eq_dict["ultimo_ping"] = ahora_ts
    FLOTA_REMOTA_DB[data.id] = eq_dict
    
    equipos_path = BASE_DIR / "equipos_remotos.json"
    try:
        equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    # Si el cliente reporta resultado de un comando ejecutado previamente
    if data.resultado_comando:
        cmd_res = data.resultado_comando
        if data.id not in HISTORIAL_COMANDOS:
            HISTORIAL_COMANDOS[data.id] = []
        # Actualizar en historial
        HISTORIAL_COMANDOS[data.id].insert(0, {
            "id": cmd_res.get("id"),
            "accion": cmd_res.get("accion", "comando"),
            "exito": cmd_res.get("exito", True),
            "salida": cmd_res.get("salida", "Comando ejecutado"),
            "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(HISTORIAL_COMANDOS[data.id]) > 30:
            HISTORIAL_COMANDOS[data.id].pop()
        guardar_comandos()

    # Extraer comandos pendientes para entregar a este nodo
    cmds_a_entregar = COMANDOS_PENDIENTES.pop(data.id, [])
    if cmds_a_entregar:
        guardar_comandos()

    res_data = {
        "status": "ok", 
        "message": f"Telemetría de {data.nombre} recibida",
        "comandos": cmds_a_entregar
    }
    if new_token_to_send:
        res_data["new_session_token"] = new_token_to_send
        res_data["expires_in"] = 3600
        
    return res_data

@app.post("/api/telemetria/simular")
async def simular_telemetria():
    ahora_ts = time.time()
    mock_nodes = [
        {
            "id": "cliente-alpha",
            "nombre": "Equipo Alpha • Cliente Retail",
            "tipo": "Servidor Cloud (AWS EC2)",
            "ip": "54.210.88.14",
            "version": "v1.2",
            "estado": "activa",
            "ultimo_ping": ahora_ts,
            "agentes": {
                "luffy": "activo", "zoro": "activo", "sanji": "espera", "robin": "espera", "nami": "activo"
            },
            "tarea_actual": "Sincronización automatizada de inventario y catálogo",
            "error_critico": None,
            "tokens": 142500,
            "costo": 0.285,
            "cpu": 18.4,
            "ram": 42.1
        },
        {
            "id": "cliente-beta",
            "nombre": "Equipo Beta • Finanzas y Auditoría",
            "tipo": "Servidor On-Premise",
            "ip": "192.168.10.45",
            "version": "v1.1",
            "estado": "error",
            "ultimo_ping": ahora_ts,
            "agentes": {
                "luffy": "activo", "zoro": "error", "sanji": "espera", "robin": "activo", "nami": "espera"
            },
            "tarea_actual": "Auditoría de balances fiscales trimestrales",
            "error_critico": "Error 429: OpenAI Rate Limit Exceeded en agente Zoro. Cuota diaria agotada.",
            "tokens": 389200,
            "costo": 0.778,
            "cpu": 64.2,
            "ram": 71.5
        }
    ]
    for m in mock_nodes:
        FLOTA_REMOTA_DB[m["id"]] = m
    
    equipos_path = BASE_DIR / "equipos_remotos.json"
    try:
        equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return {"status": "ok", "message": "Equipos de prueba simulados añadidos a la flota"}

@app.delete("/api/telemetria/eliminar/{equipo_id}")
async def eliminar_equipo_remoto(equipo_id: str):
    if equipo_id in FLOTA_REMOTA_DB:
        del FLOTA_REMOTA_DB[equipo_id]
        equipos_path = BASE_DIR / "equipos_remotos.json"
        try:
            equipos_path.write_text(json.dumps(list(FLOTA_REMOTA_DB.values()), indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return {"status": "ok", "message": f"Equipo {equipo_id} retirado"}

def obtener_estado_flota(local_activo, local_estado, local_pizarra, local_metrics, local_costos, local_logs):
    ahora_ts = time.time()
    
    # 1. Instancia local HQ
    error_local = None
    if local_logs:
        for l in reversed(local_logs[-10:]):
            texto = (l.get("mensaje") or "").lower()
            if any(k in texto for k in ["error crítico", "traceback", "exception:", "error code: 402", "error code: 429", "crash"]):
                error_local = l.get("mensaje")
                break

    ultimo_log_str = "Tripulación en reposo y a la espera de instrucciones"
    if local_logs:
        last_item = local_logs[-1]
        origen_tag = f"[{last_item.get('origen', 'LOG').upper()}] " if last_item.get("origen") else ""
        ultimo_log_str = origen_tag + (last_item.get("texto") or last_item.get("mensaje") or "")

    local_instance = {
        "id": "local-hq",
        "nombre": "Tripulación IA",
        "tipo": "",
        "ip": "",
        "version": "",
        "plugin_info": "Plugin: En vivo" if local_activo else "Plugin: Apagado",
        "estado": "activa" if local_activo else "desconectada",
        "ultimo_ping": ahora_ts,
        "ultimo_ping_relativo": "Plugin: En vivo" if local_activo else "Plugin: Apagado",
        "agentes": local_estado.get("agentes", {}),
        "tarea_actual": ultimo_log_str,
        "ultimo_log": ultimo_log_str,
        "logs": local_logs[-25:] if local_logs else [],
        "error_critico": error_local,
        "tokens": local_costos.get("tokens", 0),
        "costo": local_costos.get("costo", 0.0),
        "cpu": local_metrics.get("cpu", 0),
        "ram": local_metrics.get("ram", {}).get("percent", 0)
    }

    # Cargar equipos remotos persistidos
    equipos_path = BASE_DIR / "equipos_remotos.json"
    if equipos_path.exists():
        try:
            equipos_guardados = json.loads(equipos_path.read_text(encoding="utf-8"))
            if isinstance(equipos_guardados, list):
                for eq in equipos_guardados:
                    if isinstance(eq, dict) and eq.get("id") and eq.get("id") != "local-hq":
                        if eq["id"] not in FLOTA_REMOTA_DB:
                            FLOTA_REMOTA_DB[eq["id"]] = eq
        except Exception:
            pass

    flota = [local_instance]
    for eq_id, eq in FLOTA_REMOTA_DB.items():
        if eq_id == "local-hq":
            continue
        last_seen = eq.get("ultimo_ping", 0)
        seg_diff = int(ahora_ts - last_seen) if last_seen else 9999
        if seg_diff < 10:
            rel = "Hace unos segundos"
        elif seg_diff < 60:
            rel = f"Hace {seg_diff}s"
        elif seg_diff < 3600:
            rel = f"Hace {seg_diff // 60}m"
        else:
            rel = f"Hace {seg_diff // 3600}h"

        eq_copy = dict(eq)
        eq_copy["ultimo_ping_relativo"] = rel
        if seg_diff > 60 and eq_copy.get("estado") != "error":
            eq_copy["estado"] = "desconectada"
        flota.append(eq_copy)

    return flota

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = BASE_DIR / "static" / "index.html"
    content = index_file.read_text(encoding="utf-8")
    import re
    ts = str(int(time.time() * 1000))
    content = re.sub(r'script\.js\?v=[^\"]+', f'script.js?v={ts}', content)
    resp = HTMLResponse(content=content)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@app.get("/sw.js")
async def get_sw():
    content = "self.addEventListener('install', () => self.skipWaiting()); self.addEventListener('activate', () => self.registration.unregister());"
    resp = HTMLResponse(content=content, media_type="application/javascript")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# Utilidad para leer archivos de forma segura
def leer_archivo_json(ruta: Path):
    if ruta.exists():
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return []

def leer_archivo_texto(ruta: Path):
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    return ""

def check_docker_tripulacion():
    try:
        res = subprocess.run(["docker", "ps", "--filter", "status=running", "--format", "{{.Names}}"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            return True
    except Exception:
        pass
    return False

def check_procesos_tripulacion():
    try:
        current_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            if p.info['pid'] == current_pid:
                continue
            if 'python' in (p.info['name'] or '').lower():
                cmd = " ".join(p.info['cmdline'] or []).lower()
                if any(x in cmd for x in ['base_listener', 'luffy_agent', 'zoro_agent', 'sanji_agent', 'robin_agent', 'nami_agent']):
                    return True
    except Exception:
        pass
    return False

def calcular_estados_agentes(is_activo: bool, pizarra: list, logs_dir: Path) -> dict:
    agentes = ["luffy", "zoro", "sanji", "robin", "nami"]
    
    if not is_activo:
        return {ag: "off" for ag in agentes}
        
    estados = {}
    
    # 1. Identificar si hay agentes con tareas en progreso en la pizarra
    agentes_con_tarea = set()
    if isinstance(pizarra, list):
        for t in pizarra:
            if isinstance(t, dict):
                est = str(t.get("estado", "")).strip().upper()
                resp = str(t.get("responsable", "")).strip().lower()
                if est in ["EN_PROCESO", "EJECUTANDO", "TRABAJANDO", "PROCESANDO", "EN PROCESO", "NUEVO"]:
                    for ag in agentes:
                        if ag in resp:
                            agentes_con_tarea.add(ag)
                            
    # 2. Identificar procesos de python corriendo específicamente por agente
    procesos_por_agente = set()
    try:
        current_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            if p.info['pid'] == current_pid:
                continue
            if 'python' in (p.info['name'] or '').lower():
                cmd = " ".join(p.info['cmdline'] or []).lower()
                for ag in agentes:
                    if f"{ag}_agent" in cmd or (ag in cmd and "base_listener" in cmd):
                        procesos_por_agente.add(ag)
    except Exception:
        pass

    ahora = time.time()
    for ag in agentes:
        # A. Si el proceso de este agente está corriendo
        if ag in procesos_por_agente:
            estados[ag] = "activo"
            continue
            
        # B. Si tiene una tarea en proceso en la pizarra
        if ag in agentes_con_tarea:
            estados[ag] = "activo"
            continue
            
        # C. Analizar archivo de log del agente
        log_file = logs_dir / f"{ag.capitalize()}.log"
        if not log_file.exists():
            log_file = logs_dir / f"{ag}.log"
            
        if log_file.exists() and log_file.stat().st_size > 0:
            mtime = log_file.stat().st_mtime
            delta_seg = ahora - mtime
            
            # Si el log se modificó en los últimos 45 segundos
            if delta_seg <= 45:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        ultimas_lineas = [l.strip() for l in f.readlines() if l.strip()][-8:]
                    texto_reciente = " ".join(ultimas_lineas).lower()
                    
                    if any(err in texto_reciente for err in ["error crítico", "traceback", "exception:", "error code: 402", "error code: 429", "crash"]):
                        estados[ag] = "error"
                    else:
                        estados[ag] = "activo"
                    continue
                except Exception:
                    pass
                
        # D. Si la tripulación está activa pero el agente no tiene tarea activa ni log reciente
        estados[ag] = "espera"
        
    return estados

def obtener_metricas_costos() -> dict:
    from datetime import datetime
    mes_actual = datetime.now().strftime("%Y-%m")
    costos_path = BASE_DIR / "costos.json"
    default_costos = {
        "mes_activo": mes_actual,
        "tokens": 0,
        "costo": 0.0,
        "bloqueado_por_presupuesto": False,
        "presupuesto_maximo": obtener_presupuesto_maximo(),
        "agentes": {
            "luffy": {"tokens": 0, "costo": 0.0},
            "zoro": {"tokens": 0, "costo": 0.0},
            "sanji": {"tokens": 0, "costo": 0.0},
            "robin": {"tokens": 0, "costo": 0.0},
            "nami": {"tokens": 0, "costo": 0.0}
        },
        "historial_meses": {}
    }
    
    data = default_costos
    if costos_path.exists():
        try:
            raw = json.loads(costos_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except Exception:
            data = default_costos

    # 1. Asegurar campos base
    data.setdefault("tokens", 0)
    data.setdefault("costo", 0.0)
    data.setdefault("bloqueado_por_presupuesto", False)
    if "agentes" not in data or not isinstance(data["agentes"], dict):
        data["agentes"] = default_costos["agentes"]
    else:
        for ag in ["luffy", "zoro", "sanji", "robin", "nami"]:
            if ag not in data["agentes"]:
                data["agentes"][ag] = {"tokens": 0, "costo": 0.0}

    # 2. Verificar cambio de mes en el calendario (Rollover automático mensual)
    mes_registrado = data.get("mes_activo")
    if not mes_registrado:
        data["mes_activo"] = mes_actual
        mes_registrado = mes_actual

    necesita_guardar = False
    if mes_registrado != mes_actual:
        if "historial_meses" not in data or not isinstance(data["historial_meses"], dict):
            data["historial_meses"] = {}
        data["historial_meses"][mes_registrado] = {
            "costo": data.get("costo", 0.0),
            "tokens": data.get("tokens", 0)
        }
        data["mes_activo"] = mes_actual
        data["costo"] = 0.0
        data["tokens"] = 0
        data["bloqueado_por_presupuesto"] = False
        for ag in ["luffy", "zoro", "sanji", "robin", "nami"]:
            data["agentes"][ag] = {"tokens": 0, "costo": 0.0}
        necesita_guardar = True

    # 3. Límite de presupuesto mensual y Parada Dura
    presupuesto_max = obtener_presupuesto_maximo()
    if data.get("presupuesto_maximo") != presupuesto_max:
        data["presupuesto_maximo"] = presupuesto_max
        necesita_guardar = True
    costo_actual = float(data.get("costo", 0.0))

    if presupuesto_max > 0 and costo_actual >= presupuesto_max:
        if not data.get("bloqueado_por_presupuesto", False):
            data["bloqueado_por_presupuesto"] = True
            necesita_guardar = True
            detener_tripulacion_emergencia()
            enviar_alerta_telegram_presupuesto(costo_actual, presupuesto_max)
    else:
        if data.get("bloqueado_por_presupuesto", False):
            data["bloqueado_por_presupuesto"] = False
            necesita_guardar = True

    if necesita_guardar:
        try:
            costos_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return data

def obtener_ultimos_logs(max_lineas=40):
    lineas_combinadas = []
    
    # 1. Leer de archivos *.log en logs/
    logs_dir = AGENTES_DIR / "logs"
    if logs_dir.exists():
        for log_file in sorted(logs_dir.glob("*.log")):
            if log_file.is_file() and log_file.stat().st_size > 0:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                        for line in lines[-max_lineas:]:
                            origen = log_file.stem
                            texto = line
                            if line.startswith("[") and "]" in line:
                                origen = line[1:line.index("]")].strip()
                                texto = line[line.index("]")+1:].strip()
                            lineas_combinadas.append({"origen": origen, "texto": texto})
                except Exception:
                    pass

    # 2. Si no hay logs en disco, consultar logs del contenedor Docker (activo o recién detenido)
    if not lineas_combinadas:
        try:
            res = subprocess.run(
                ["docker", "logs", "--tail", str(max_lineas), "tripulacion_ia_v3"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1.5
            )
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line:
                        origen = "Tripulación"
                        texto = line
                        if line.startswith("[") and "]" in line:
                            origen = line[1:line.index("]")].strip()
                            texto = line[line.index("]")+1:].strip()
                        lineas_combinadas.append({"origen": origen, "texto": texto})
        except Exception:
            pass

    return lineas_combinadas[-max_lineas:]

async def obtener_metricas_sistema():
    cpu_usage = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ram_usage = mem.percent
    ram_used_gb = mem.used / (1024**3)
    ram_total_gb = mem.total / (1024**3)
    
    net = psutil.net_io_counters()
    
    gpu_info = []
    if GPUtil:
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            gpu_info.append({
                "name": gpu.name,
                "load": round(gpu.load * 100, 1),
                "temp": gpu.temperature,
                "memory_used": gpu.memoryUsed,
                "memory_total": gpu.memoryTotal
            })
            
    return {
        "cpu": cpu_usage,
        "ram": {
            "percent": ram_usage,
            "used_gb": round(ram_used_gb, 1),
            "total_gb": round(ram_total_gb, 1)
        },
        "gpu": gpu_info,
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv
        },
        "specs": {
            "system": platform.system(),
            "processor": platform.processor()
        }
    }



def limpiar_formato_md(txt: str) -> str:
    if not txt:
        return ""
    import re
    # Convertir wikilinks Obsidian [[algo|alias]] o [[algo]]
    txt = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', txt)
    # Convertir links standard markdown [texto](url)
    txt = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', txt)
    # Quitar negritas y cursivas
    txt = re.sub(r'\*\*(.*?)\*\*', r'\1', txt)
    txt = re.sub(r'\*(.*?)\*', r'\1', txt)
    # Quitar backticks
    txt = txt.replace('`', '')
    # Quitar listas o viñetas iniciales y guiones
    txt = re.sub(r'^\s*[-*•]\s*', '', txt)
    # Quitar espacios múltiples
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()

def extraer_id_y_titulo(titulo_raw: str):
    import re
    t_clean = limpiar_formato_md(titulo_raw)
    m = re.match(r'^(TKT-[A-Z0-9\-]+)[:\s\-]+(.*)$', t_clean, re.IGNORECASE)
    if m:
        return m.group(1).upper().strip(), m.group(2).strip()
    return None, t_clean

def parse_bitacora(ruta):
    if not ruta.exists(): return []
    content = ruta.read_text(encoding="utf-8")
    import re
    blocks = re.split(r'\n##\s+', '\n' + content)
    tareas = []
    for block in blocks[1:]:
        lines = block.split('\n')
        t_id, titulo = extraer_id_y_titulo(lines[0])
        responsable = "Luffy"
        estado = "Pendiente"
        desc = ""
        tarea_especifica = ""
        criterios = ""
        
        for line in lines[1:]:
            l_str = line.strip()
            if not l_str:
                continue
            if re.search(r'\*{0,2}Responsable:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Responsable:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                responsable = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Estado:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Estado:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                estado = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                desc = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Tarea:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Tarea:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                tarea_especifica = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                criterios = limpiar_formato_md(val)
        
        # Si el responsable dice Luffy pero el ID del ticket pertenece a un subagente (ej: TKT-SANJI-..., TKT-ROBIN-...)
        if t_id and responsable.lower() == "luffy":
            m_ag = re.match(r'^TKT-(ZORO|SANJI|ROBIN|NAMI)\b', t_id, re.IGNORECASE)
            if m_ag:
                responsable = m_ag.group(1).capitalize()

        tareas.append({
            "id": t_id,
            "titulo": titulo,
            "descripcion": desc or tarea_especifica or "Tarea en progreso...",
            "tarea": tarea_especifica,
            "criterios": criterios,
            "responsable": responsable,
            "estado": estado
        })
    return tareas

def parse_tickets_md(ruta):
    if not ruta.exists(): return []
    content = ruta.read_text(encoding="utf-8")
    tickets = []
    import re
    blocks = re.split(r'\n##\s+', '\n' + content)
    for block in blocks[1:]:
        lines = block.split('\n')
        t_id, titulo = extraer_id_y_titulo(lines[0])
        responsable = "Luffy"
        estado = "Completado"
        desc = ""
        tarea_especifica = ""
        criterios = ""
        
        for line in lines[1:]:
            l_str = line.strip()
            if not l_str:
                continue
            if re.search(r'\*{0,2}Responsable:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Responsable:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                responsable = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Estado:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Estado:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                estado = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Descripci[óo]n:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                desc = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Tarea:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Tarea:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                tarea_especifica = limpiar_formato_md(val)
            elif re.search(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, re.IGNORECASE):
                val = re.split(r'\*{0,2}Criterios(?:\s+de\s+aceptaci[óo]n)?:\*{0,2}', l_str, flags=re.IGNORECASE)[-1]
                criterios = limpiar_formato_md(val)
        
        # Ignorar encabezados que no sean tickets (ej: enlaces a memoria u Obsidian)
        if not t_id and not desc and not tarea_especifica:
            continue

        # Si el responsable dice Luffy pero el ID del ticket pertenece a un subagente (ej: TKT-SANJI-..., TKT-ROBIN-...)
        if t_id and responsable.lower() == "luffy":
            m_ag = re.match(r'^TKT-(ZORO|SANJI|ROBIN|NAMI)\b', t_id, re.IGNORECASE)
            if m_ag:
                responsable = m_ag.group(1).capitalize()

        tickets.append({
            "id": t_id,
            "titulo": titulo,
            "descripcion": desc or tarea_especifica or "Ticket archivado en memoria.",
            "tarea": tarea_especifica,
            "criterios": criterios,
            "responsable": responsable,
            "estado": estado or "Completado"
        })
    return tickets

TIEMPO_INICIO_CREW = None
tiempo_acumulado_trabajo = 0.0
ultimo_check_activo = time.time()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Guardar valores anteriores de red para calcular velocidad
        last_net = psutil.net_io_counters()
        
        while True:
            # 1. Hardware metrics
            metrics = await obtener_metricas_sistema()
            
            # Calcular velocidad de red rudimentaria (diferencia por segundo)
            current_net = psutil.net_io_counters()
            metrics["network"]["up_speed"] = current_net.bytes_sent - last_net.bytes_sent
            metrics["network"]["down_speed"] = current_net.bytes_recv - last_net.bytes_recv
            last_net = current_net
            
            
                        # 2. Pizarra de agentes (JSON array of tasks)
            pizarra_path = AGENTES_DIR / "Bitacora.md"
            pizarra = parse_bitacora(pizarra_path)
            
            # Tickets archivados
            tickets_path_md = AGENTES_DIR / "memoria" / "Tickets_Archivados.md"
            tickets_archivados = parse_tickets_md(tickets_path_md)
            
            # Tareas programadas
            programadas_path = Path(__file__).resolve().parent / "tareas_programadas.json"
            tareas_programadas = leer_archivo_json(programadas_path) if programadas_path.exists() else {"diarias":[], "semanales":[], "mensuales":[]}
            
            # 3. Chat de usuario y sesiones
            sincronizar_canal_activo_con_disco()
            canal_path = BASE_DIR / "canal_usuario.json"
            chat_raw = leer_archivo_json(canal_path)
            if isinstance(chat_raw, dict):
                chat = chat_raw.get("mensajes", [])
            elif isinstance(chat_raw, list):
                chat = chat_raw
            else:
                chat = []
            sesiones_chat = cargar_sesiones_index()
            
            # 4. Logs en vivo de la tripulacion
            logs = obtener_ultimos_logs()
            
            # 5. Costos/Tokens
            costos = obtener_metricas_costos()
            
            # 6. Estado de la tripulacion
            estado_path = LUFFY_DIR / "estado_tripulacion.json"
            estado_tripulacion = leer_archivo_json(estado_path) if estado_path.exists() else {"estado": "desconectada"}
            if not isinstance(estado_tripulacion, dict):
                estado_tripulacion = {"estado": "desconectada"}
            
            # Detectar si docker o los agentes estan activos
            docker_activo = check_docker_tripulacion()
            procesos_activos = check_procesos_tripulacion()
            is_activo = docker_activo or procesos_activos or (estado_tripulacion.get("estado") in ["activa", "activo", "conectada"])
            if costos.get("bloqueado_por_presupuesto"):
                is_activo = False
                estado_tripulacion["estado"] = "bloqueada_presupuesto"
            elif is_activo:
                estado_tripulacion["estado"] = "activa"
            else:
                estado_tripulacion["estado"] = "desconectada"
                
            estado_tripulacion["agentes"] = calcular_estados_agentes(is_activo, pizarra, AGENTES_DIR / "logs")
            
            # Rastrear tiempo de trabajo activo de los agentes
            global TIEMPO_INICIO_CREW, tiempo_acumulado_trabajo, ultimo_check_activo
            ahora_ts = time.time()
            dt = ahora_ts - ultimo_check_activo
            ultimo_check_activo = ahora_ts
            if dt < 0 or dt > 10:
                dt = 1.0

            if is_activo:
                if TIEMPO_INICIO_CREW is None:
                    TIEMPO_INICIO_CREW = ahora_ts
                tiempo_acumulado_trabajo += dt
            else:
                TIEMPO_INICIO_CREW = None

            horas_totales = int(tiempo_acumulado_trabajo // 3600)
            minutos_totales = int((tiempo_acumulado_trabajo % 3600) // 60)
            
            sesion_seg = int(ahora_ts - TIEMPO_INICIO_CREW) if TIEMPO_INICIO_CREW else 0
            sesion_min = int(sesion_seg // 60)
            
            tiempo_trabajo = {
                "segundos": int(tiempo_acumulado_trabajo),
                "formateado": f"{horas_totales}h {minutos_totales:02d}m",
                "sesion_minutos": sesion_min,
                "is_activo": is_activo
            }
            
            data = {
                "type": "update",
                "system": metrics,
                "pizarra": pizarra,
                "tickets_archivados": tickets_archivados,
                "tareas_programadas": tareas_programadas,
                "chat": chat,
                "sesiones_chat": sesiones_chat,
                "logs": logs,
                "costos": costos,
                "estado_tripulacion": estado_tripulacion,
                "tripulacion_activa": is_activo,
                "modelos": obtener_modelos_agentes(),
                "tiempo_trabajo": tiempo_trabajo,
                "flota_remota": obtener_estado_flota(is_activo, estado_tripulacion, pizarra, metrics, costos, logs),
                "alerta_intrusion": ULTIMA_ALERTA_INTRUSION if (ULTIMA_ALERTA_INTRUSION and (time.time() - ULTIMA_ALERTA_INTRUSION.get("timestamp", 0) < 180)) else None,
                "incidentes_seguridad": HISTORIAL_INTRUSIONES[:20],
                "comandos_remotos": {
                    "pendientes": COMANDOS_PENDIENTES,
                    "historial": HISTORIAL_COMANDOS
                }
            }
            
            await websocket.send_json(data)
            await asyncio.sleep(1) # Actualizar cada 1 segundo
            
    except WebSocketDisconnect:
        print("Cliente desconectado")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
