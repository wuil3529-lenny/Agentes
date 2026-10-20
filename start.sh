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

log() { echo -e "${CYAN}[start.sh]${NC} $*"; }
ok()  { echo -e "${GREEN}[start.sh ✓]${NC} $*"; }
warn(){ echo -e "${YELLOW}[start.sh ⚠]${NC} $*"; }
err() { echo -e "${RED}[start.sh ✗]${NC} $*" >&2; }

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
    2>&1 | while IFS= read -r line; do echo "[Agente_Orquestador] $line" | tee -a /app/logs/Agente_Orquestador.log; done &
PID_LUFFY=$!
ok "Agente_Orquestador (Daemon) iniciado con PID $PID_LUFFY"

# Pequeña pausa para que el listener arranque
sleep 2

# ── Lanzar telegram_bridge.py ────────────────────────────────────────────────
if [[ "$BRIDGE_DISABLED" == "false" ]]; then
    log "Iniciando puente Telegram: telegram_bridge.py ..."
    python -u /app/Agente_Orquestador/telegram_bridge.py \
        2>&1 | while IFS= read -r line; do echo "[telegram_bridge] $line" | tee -a /app/logs/Agente_Orquestador.log; done &
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
# revisión de correos de valor en el buzón Wuil3529@gmail.com:
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
    if timeout 60 python3 "$HOOK_CORREOS" 2>&1 | while IFS= read -r line; do echo "[hook-correos] $line" | tee -a /app/logs/hook_arranque_correos.log; done; then
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
    if timeout 60 python3 "$HOOK_SEGURIDAD" 2>&1 | while IFS= read -r line; do echo "[hook-seguridad] $line" | tee -a /app/logs/hook_arranque_seguridad.log; done; then
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
    if timeout 90 python3 "$HOOK_OBSIDIAN" 2>&1 | while IFS= read -r line; do echo "[hook-obsidian] $line" | tee -a /app/logs/hook_arranque_obsidian.log; done; then
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
