#!/bin/bash
# =============================================================================
# start.sh — Script de arranque del ecosistema multiagente dentro del contenedor
#
# Estrategia:
#   - Lanza base_listener.py (motor principal de Luffy) en background.
#   - Lanza telegram_bridge.py (puente Telegram↔Canal) en background.
#   - El proceso `wait` del final mantiene el contenedor vivo y captura
#     la señal de salida de CUALQUIERA de los dos procesos.
#   - Si uno muere, el contenedor sale con código != 0 → Docker lo reinicia
#     automáticamente gracias a `restart: unless-stopped`.
# =============================================================================

set -euo pipefail

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

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   🏴‍☠️  Tripulación IA — Sandbox Docker        ║"
echo "  ║   Motor: base_listener.py (Luffy)            ║"
echo "  ║   Puente: telegram_bridge.py                 ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# ── Verificar directorio de trabajo ──────────────────────────────────────────
log "Directorio de trabajo: $(pwd)"
log "Contenido de /app:"
ls /app | head -20

# ── Verificar que existan los archivos clave ──────────────────────────────────
LISTENER="/app/Luffy/base_listener.py"
BRIDGE="/app/Luffy/telegram_bridge.py"

if [[ ! -f "$LISTENER" ]]; then
    err "No se encontró base_listener.py en $LISTENER"
    err "Verifica que el volumen bind-mount esté configurado correctamente."
    exit 1
fi

if [[ ! -f "$BRIDGE" ]]; then
    # Fallback: buscar en skills/
    BRIDGE_FALLBACK="/app/Luffy/skills/telegram_bridge.py"
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

# ── Verificar variables de entorno críticas ───────────────────────────────────
if [[ -z "${NVIDIA_API_KEY_LUFFY:-}" ]]; then
    warn "NVIDIA_API_KEY_LUFFY no está definida en el entorno."
    warn "Asegúrate de que el archivo .env esté en C:\\Users\\admin\\Documents\\Agentes\\"
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    warn "TELEGRAM_BOT_TOKEN no definida. El puente Telegram no podrá autenticarse."
fi

# ── Trampa de señales para limpieza al salir ──────────────────────────────────
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

# 🚀 Lanzar base_listener.py (Luffy como Daemon principal) 🚀
log "Iniciando motor principal: base_listener.py para Luffy..."
python /app/Luffy/base_listener.py luffy \
    2>&1 | while IFS= read -r line; do echo "[Luffy] $line"; done &
PID_LUFFY=$!
ok "Luffy (Daemon) iniciado con PID $PID_LUFFY"

# Pequeña pausa para que el listener arranque
sleep 2

# ── Lanzar telegram_bridge.py ─────────────────────────────────────────────────
if [[ "$BRIDGE_DISABLED" == "false" ]]; then
    log "Iniciando puente Telegram: telegram_bridge.py ..."
    python /app/Luffy/telegram_bridge.py \
        2>&1 | while IFS= read -r line; do echo "[telegram_bridge] $line"; done &
    BRIDGE_PID=$!
    ok "telegram_bridge.py iniciado con PID $BRIDGE_PID"
else
    BRIDGE_PID=""
    warn "Puente Telegram deshabilitado (archivo no encontrado)."
fi

echo ""
ok "Ecosistema activo. Esperando a los procesos..."
echo "  • PID Luffy (Daemon) : $PID_LUFFY"
[[ -n "$BRIDGE_PID" ]] && echo "  • PID telegram_bridge: $BRIDGE_PID"
echo ""

# ── wait -n: el contenedor sale en cuanto UNO de los procesos termine ─────────
wait -n $PID_LUFFY ${BRIDGE_PID:-}
EXIT_CODE=$?

err "Uno de los procesos terminó inesperadamente (código: $EXIT_CODE)."
err "Docker reiniciará el contenedor según la política restart: unless-stopped."
exit $EXIT_CODE
