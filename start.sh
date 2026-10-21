#!/bin/bash
# =============================================================================
# start.sh — Script de arranque del ecosistema multiagente dentro del contenedor
#
# Estrategia:
#   - Lanza base_listener.py (motor principal de Luffy) en background.
#   - Lanza telegram_bridge.py (puente Telegram↔Canal) en background.
#   - Ejecuta el HOOK DE ARRANQUE de revisión de correos de valor (Zero-Token):
#       * Reanuda el vigilante REC-VIGILANTED-003 si quedó PAUSADO.
#       * Dispara una evaluación única del sensor v2.1 al encender la flota.
#     El hook es idempotente y tolerante a fallos: NUNCA aborta el arranque.
#   - El proceso `wait` del final mantiene el contenedor vivo y captura
#     la señal de salida de CUALQUIERA de los dos procesos.
#   - Si uno muere, el contenedor sale con código != 0 → Docker lo reinicia
#     automáticamente gracias a `restart: unless-stopped`.
#
# TKT-DEV-20261014002 — Hook de arranque de revisión de correos.
# =============================================================================

set -euo pipefail

# ── Configurar Zona Horaria Local (America/Caracas -04:00) ───────────────────
export TZ="${TZ:-America/Caracas}"

# ── [TKT-SEC-20261019181510] Hardening de permisos (H-01/H-02) ────────────────
# umask 077: todo archivo/directorio creado por la flota nace restringido
# (0600 archivos / 0700 directorios). Evita que credenciales, tokens OAuth,
# .env o logs con secretos nazcan world-readable/writable.
umask 077
# ─────────────────────────────────────────────────────────────────────────────

# ── Colores para logs legibles en docker compose logs ────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'   # No Color

ts() { date "+%Y-%m-%d %H:%M:%S"; }

log()  { echo -e "${CYAN}[$(ts)] [start.sh]${NC} $*"; }
ok()   { echo -e "${GREEN}[$(ts)] [start.sh ✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(ts)] [start.sh ⚠]${NC} $*"; }
err()  { echo -e "${RED}[$(ts)] [start.sh ✗]${NC} $*" >&2; }

# ═════════════════════════════════════════════════════════════════════════════
# 🔐 [TKT-SEC-20261020151813] AUTO-SANEO DE PERMISOS DE ARCHIVOS SENSIBLES 🔐
#
# Mitiga el hallazgo H-01 (ALTO): /app/.env con permisos 0o777.
# Bloque IDEMPOTENTE y TOLERANTE A FALLOS: intenta restringir a 0600 los
# archivos con secretos en cada arranque. Si el archivo es un bind-mount del
# host (root:root) y el usuario del contenedor no puede cambiarlo, emite una
# ALERTA CRÍTICA VISIBLE (fail-loud) con la acción requerida en el host,
# la persiste en /app/logs/seguridad_permisos.log y NO aborta el arranque.
# [TKT-SEC-20261020190613] Endurecido: alerta ya NO es silenciosa.
# ═════════════════════════════════════════════════════════════════════════════
endurecer_permisos() {
    local archivo="$1"
    local modo_deseado="${2:-600}"

    [[ -e "$archivo" ]] || return 0

    local modo_actual
    modo_actual="$(stat -c '%a' "$archivo" 2>/dev/null || echo '???')"

    # [TKT-SEC-20261020205030] FIX BUG LOGICO: solo el modo exacto deseado (0600)
    # se considera seguro. Los modos 444/400/644 son world-readable y NO deben
    # aceptarse como "seguros": eso anulaba el hardening y dejaba el hallazgo H-01
    # (ALTO) vivo entre reinicios. Si el modo no coincide, se INTENTA el chmod.
    if [[ "$modo_actual" == "$modo_deseado" ]]; then
        ok "Permisos seguros ($modo_actual): $archivo"
        return 0
    fi

    if chmod "$modo_deseado" "$archivo" 2>/dev/null; then
        ok "Permisos corregidos ($modo_actual -> $modo_deseado): $archivo"
        return 0
    fi

    # ── FALLO: no se pudo restringir (bind-mount del host / otro propietario) ──
    local propietario
    propietario="$(stat -c '%U:%G' "$archivo" 2>/dev/null || echo 'desconocido')"

    # [TKT-SEC-20261020190613] ALERTA CRÍTICA VISIBLE — NO silenciosa.
    err "════════════════════════════════════════════════════════════════════"
    err "🔴 ALERTA DE SEGURIDAD CRÍTICA — PERMISOS INSEGUROS NO REMEDIABLES"
    err "════════════════════════════════════════════════════════════════════"
    err "  Archivo   : $archivo"
    err "  Permisos  : $modo_actual (esperado: $modo_deseado)"
    err "  Propietario: $propietario  |  Proceso: $(id -un):$(id -gn)"
    err ""
    err "  CAUSA: El archivo es un BIND-MOUNT del host y pertenece a otro"
    err "         usuario (root). El proceso del contenedor corre como"
    err "         'tripulacion' (uid 1001) SIN CAP_FOWNER, por lo que chmod"
    err "         falla con 'Operation not permitted'."
    err ""
    err "  RIESGO: Exfiltración y ENVENENAMIENTO de credenciales de la flota"
    err "          (API keys LLM, N8N_API_KEY, N8N_BASIC_AUTH_PASSWORD, OAuth)."
    err ""
    err "  ACCIÓN REQUERIDA EN EL HOST (ejecutar como Administrador):"
    err "    Linux/macOS : chmod 600 <ruta_host>/.env"
    err "    Windows     : icacls .env /inheritance:r /grant:r \"%USERNAME%:R\""
    err "    Ver script : /app/Subagente_Desarrollo/proyectos/remediar_permisos_env.sh"
    err "════════════════════════════════════════════════════════════════════"

    # Persistir el hallazgo para auditoría del Subagente_Ciberseguridad
    local log_sec="/app/logs/seguridad_permisos.log"
    mkdir -p /app/logs 2>/dev/null || true
    {
        echo "[$(ts)] ALERTA_CRITICA archivo=$archivo modo=$modo_actual esperado=$modo_deseado propietario=$propietario proceso=$(id -un) causa=bind_mount_root chmod=EPERM"
    } >> "$log_sec" 2>/dev/null || true

    return 0
}

log "Aplicando hardening de permisos a archivos sensibles..."
endurecer_permisos "/app/.env" 600 || true
endurecer_permisos "/app/Agente_Orquestador/data/credentials.json" 600 || true
endurecer_permisos "/app/Agente_Orquestador/data/token.json" 600 || true

# ═══════════════════════════════════════════════════════════════════════════════
# 🔒 [TKT-SEC-20261021085734] GUARD ESTRICTO DE PERMISOS .env (FAIL-CLOSED) 🔒
#
# Complementa endurecer_permisos(): si tras el auto-saneo /app/.env conserva
# bits de acceso para grupo u otros (world-readable/writable/executable),
# el arranque ABORTA con código 78 (EX_CONFIG) para evitar operar con
# credenciales de la flota expuestas o envenenables.
# Idempotente: no se duplica si ya existe el marcador.
# ═══════════════════════════════════════════════════════════════════════════════
verificar_permisos_env_estricto() {
    local archivo="/app/.env"
    [[ -e "$archivo" ]] || return 0

    local modo_actual
    modo_actual="$(stat -c '%a' "$archivo" 2>/dev/null || echo '???')"

    # Modo octal de 3 dígitos: el tercer dígito son los bits de "otros".
    # Rechazamos cualquier modo != 600 (grupo/otros con acceso).
    if [[ "$modo_actual" == "600" ]]; then
        ok "GUARD .env: permisos estrictos confirmados (600)."
        return 0
    fi

    err "════════════════════════════════════════════════════════════════════════"
    err "🔴 ARRANQUE ABORTADO — /app/.env CON PERMISOS EXCESIVOS"
    err "════════════════════════════════════════════════════════════════════════"
    err "  Archivo    : $archivo"
    err "  Modo actual: $modo_actual  (requerido: 600)"
    err "  Propietario: $(stat -c '%U:%G' "$archivo" 2>/dev/null || echo 'desconocido')"
    err "  Proceso    : $(id -un):$(id -gn) (uid=$(id -u))"
    err ""
    err "  El archivo concentra credenciales de TODA la flota (LLM API keys,"
    err "  N8N_API_KEY, N8N_BASIC_AUTH_PASSWORD, OAuth Gmail, SUPABASE, NGROK)."
    err "  Operar con acceso de grupo/otros permite exfiltración y envenenamiento."
    err ""
    err "  ACCIÓN REQUERIDA:"
    err "    chmod 600 /app/.env"
    err "    (o en el HOST si es bind-mount: chmod 600 <ruta_host>/.env)"
    err "════════════════════════════════════════════════════════════════════════"

    mkdir -p /app/logs 2>/dev/null || true
    echo "[$(ts)] ARRANQUE_ABORTADO motivo=permisos_env_excesivos modo=$modo_actual requerido=600" \
        >> /app/logs/seguridad_permisos.log 2>/dev/null || true

    exit 78
}

verificar_permisos_env_estricto
# ═══════════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════════

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   🏴‍☠️  Tripulación IA — Sandbox Docker        ║"
echo "  ║   Motor: base_listener.py (Luffy)            ║"
echo "  ║   Puente: telegram_bridge.py                 ║"
echo "  ║   Hook: revisión de correos al arranque      ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# ── Verificar directorio de trabajo ──────────────────────────────────────────
log "Directorio de trabajo: $(pwd)"
log "Contenido de /app:"
ls /app | head -20

# ── Verificar que existan los archivos clave ─────────────────────────────────
LISTENER="/app/Agente_Orquestador/base_listener.py"
BRIDGE="/app/Agente_Orquestador/telegram_bridge.py"

if [[ ! -f "$LISTENER" ]]; then
    err "No se encontró base_listener.py en $LISTENER"
    err "Verifica que el volumen bind-mount esté configurado correctamente."
    exit 1
fi

if [[ ! -f "$BRIDGE" ]]; then
    # Fallback: buscar en skills/
    BRIDGE_FALLBACK="/app/Agente_Orquestador/skills/telegram_bridge.py"
    if [[ -f "$BRIDGE_FALLBACK" ]]; then
        warn "telegram_bridge.py no está en raíz. Usando fallback: $BRIDGE_FALLBACK"
        # Copiar al lugar correcto para que start.sh lo encuentre siempre
        cp "$BRIDGE_FALLBACK" "$BRIDGE"
        BRIDGE_DISABLED=false
    else
        warn "No se encontró telegram_bridge.py en $BRIDGE ni en skills/. El puente Telegram NO se iniciará."
        BRIDGE_DISABLED=true
    fi
else
    BRIDGE_DISABLED=false
fi

# ── Verificar variables de entorno críticas ──────────────────────────────────
if [[ -z "${NVIDIA_API_KEY_LUFFY:-}" ]]; then
    warn "NVIDIA_API_KEY_LUFFY no está definida en el entorno."
    warn "Asegúrate de que el archivo .env esté en C:\\Users\\admin\\Documents\\Agentes\\"
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    warn "TELEGRAM_BOT_TOKEN no definida. El puente Telegram no podrá autenticarse."
fi

# ── Trampa de señales para limpieza al salir ─────────────────────────────────
# Cuando el contenedor recibe SIGTERM (docker compose down), matamos
# todos los procesos hijos antes de salir.
cleanup() {
    log "Señal de parada recibida. Deteniendo procesos..."
    # Matar los grupos de procesos de cada PID registrado
    [[ -n "${PID_LUFFY:-}" ]] && kill -TERM "$PID_LUFFY" 2>/dev/null || true
    [[ -n "${PID_ZORO:-}" ]] && kill -TERM "$PID_ZORO" 2>/dev/null || true
    [[ -n "${PID_NAMI:-}" ]] && kill -TERM "$PID_NAMI" 2>/dev/null || true
    [[ -n "${PID_ROBIN:-}" ]] && kill -TERM "$PID_ROBIN" 2>/dev/null || true
    [[ -n "${PID_SANJI:-}" ]] && kill -TERM "$PID_SANJI" 2>/dev/null || true
    [[ -n "${BRIDGE_PID:-}" ]]   && kill -TERM "$BRIDGE_PID"   2>/dev/null || true
    wait
    log "Tripulación detenida. ¡Hasta la próxima!"
    exit 0
}
trap cleanup SIGTERM SIGINT

# Asegurar que exista la carpeta de logs
mkdir -p /app/logs

# 🚀 Lanzar base_listener.py (Orquestador como Daemon principal) 🚀
log "Iniciando motor principal: base_listener.py para Agente_Orquestador..."
python -u /app/Agente_Orquestador/base_listener.py Agente_Orquestador \
    2>&1 | while IFS= read -r line; do echo "[$(ts)] [Agente_Orquestador] $line" | tee -a /app/logs/Agente_Orquestador.log; done &
PID_LUFFY=$!
ok "Agente_Orquestador (Daemon) iniciado con PID $PID_LUFFY"

# Pequeña pausa para que el listener arranque
sleep 2

# ── Lanzar telegram_bridge.py ────────────────────────────────────────────────
if [[ "$BRIDGE_DISABLED" == "false" ]]; then
    log "Iniciando puente Telegram: telegram_bridge.py ..."
    python -u /app/Agente_Orquestador/telegram_bridge.py \
        2>&1 | while IFS= read -r line; do echo "[$(ts)] [telegram_bridge] $line" | tee -a /app/logs/Agente_Orquestador.log; done &
    BRIDGE_PID=$!
    ok "telegram_bridge.py iniciado con PID $BRIDGE_PID"
else
    BRIDGE_PID=""
    warn "Puente Telegram deshabilitado (archivo no encontrado)."
fi

# ═════════════════════════════════════════════════════════════════════════════
# 🔔 HOOK DE ARRANQUE — REVISIÓN DE CORREOS DE VALOR (Zero-Token) 🔔
# TKT-DEV-20261014002
#
# Garantiza que CADA VEZ que se encienda la flota se ejecute UNA SOLA VEZ una
# revisión de correos de valor en el buzón configurado (EMAIL_REMITENTE):
#   (1) Reanuda el vigilante REC-VIGILANTED-003 si quedó PAUSADO tras el reinicio.
#   (2) Dispara una evaluación inmediata del sensor v2.1 (Python puro, 0 tokens).
#       Si detecta correos importantes, inyecta el ticket en Bitacora.md para
#       Subagente_Asistencia.
#
# El hook es IDEMPOTENTE y TOLERANTE A FALLOS: se ejecuta con `timeout` duro y
# captura de error, de modo que si el sensor o IMAP fallan (o no hay red), el
# arranque de la flota CONTINÚA normalmente sin abortar.
# ═════════════════════════════════════════════════════════════════════════════
HOOK_CORREOS="/app/Subagente_Desarrollo/proyectos/hook_arranque_revision_correos.py"

if [[ -f "$HOOK_CORREOS" ]]; then
    log "Ejecutando hook de arranque: revisión de correos de valor (Zero-Token)..."
    # `timeout 60` protege el arranque; el `if` captura el fallo sin abortar
    # el contenedor (compatible con `set -e`).
    if timeout 60 python3 "$HOOK_CORREOS" 2>&1 | while IFS= read -r line; do echo "[$(ts)] [hook-correos] $line" | tee -a /app/logs/hook_arranque_correos.log; done; then
        ok "Hook de revisión de correos completado."
    else
        warn "El hook de revisión de correos falló o excedió el timeout. El arranque continúa."
    fi
else
    warn "Hook de revisión de correos no encontrado en $HOOK_CORREOS. Se omite."
fi

# ═════════════════════════════════════════════════════════════════════════════
# 🛡️ HOOK DE ARRANQUE — AUDITORÍA DE SEGURIDAD PREVENTIVA (Robin) 🛡️
#
# Garantiza que CADA VEZ que se encienda o reinicie la flota se ejecute una
# inspección preventiva de seguridad (SAST, detección de secretos, permisos):
#   - Inyecta el ticket TKT-SEC-BOOT-... en Bitacora.md para Subagente_Ciberseguridad.
#   - El listener de Luffy lo detecta e invoca a Robin en modo Spawn efímero.
#   - El hook es IDEMPOTENTE y TOLERANTE A FALLOS: NUNCA bloquea el arranque.
# ═════════════════════════════════════════════════════════════════════════════
HOOK_SEGURIDAD="/app/Subagente_Ciberseguridad/skills/auditoria/hook_arranque_auditoria_seguridad.py"

if [[ -f "$HOOK_SEGURIDAD" ]]; then
    log "Ejecutando hook de arranque: auditoría de seguridad preventiva (Robin)..."
    if timeout 60 python3 "$HOOK_SEGURIDAD" 2>&1 | while IFS= read -r line; do echo "[$(ts)] [hook-seguridad] $line" | tee -a /app/logs/hook_arranque_seguridad.log; done; then
        ok "Hook de auditoría de seguridad completado."
    else
        warn "El hook de auditoría de seguridad falló o excedió el timeout. El arranque continúa."
    fi
else
    warn "Hook de seguridad no encontrado en $HOOK_SEGURIDAD. Se omite."
fi

# ═════════════════════════════════════════════════════════════════════════════
# 🧠 HOOK DE ARRANQUE — LIMPIEZA Y SINCRONIZACIÓN DEL GRAFO DE OBSIDIAN 🧠
#
# Garantiza que en CADA ARRANQUE o reinicio de la flota se purguen enlaces
# residuales y se normalice la topología canónica de Obsidian (13 nodos):
#   - Ejecuta /app/Agente_Orquestador/sync_cerebro.py
#   - El hook es IDEMPOTENTE y TOLERANTE A FALLOS: NUNCA bloquea el arranque.
# ═════════════════════════════════════════════════════════════════════════════
HOOK_OBSIDIAN="/app/Agente_Orquestador/sync_cerebro.py"

if [[ -f "$HOOK_OBSIDIAN" ]]; then
    log "Ejecutando hook de arranque: limpieza y sincronización del grafo de Obsidian..."
    if timeout 90 python3 "$HOOK_OBSIDIAN" 2>&1 | while IFS= read -r line; do echo "[$(ts)] [hook-obsidian] $line" | tee -a /app/logs/hook_arranque_obsidian.log; done; then
        ok "Hook de sincronización del grafo de Obsidian completado."
    else
        warn "El hook de Obsidian falló o excedió el timeout. El arranque continúa."
    fi
else
    warn "Script de Obsidian no encontrado en $HOOK_OBSIDIAN. Se omite."
fi

echo ""
ok "Ecosistema activo. Esperando a los procesos..."
echo "  • PID Luffy (Daemon) : $PID_LUFFY"
[[ -n "$BRIDGE_PID" ]] && echo "  • PID telegram_bridge: $BRIDGE_PID"
echo ""

# ── wait -n: el contenedor sale en cuanto UNO de los procesos termine ────────
wait -n $PID_LUFFY ${BRIDGE_PID:-}
EXIT_CODE=$?

err "Uno de los procesos terminó inesperadamente (código: $EXIT_CODE)."
err "Docker reiniciará el contenedor según la política restart: unless-stopped."
exit $EXIT_CODE
