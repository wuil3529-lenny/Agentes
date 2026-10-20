#!/bin/bash
# =============================================================================
# remediar_permisos_root.sh
# TKT-SEC-20261019181510 — Remediación de permisos 0o777 (H-01, H-02)
#
# PROPÓSITO:
#   Completa la remediación de los 2 objetivos que NO pudieron aplicarse desde
#   el contexto del Subagente_Desarrollo (uid=1001 tripulacion, CapEff=0x0):
#     - /app/.env                              -> 0600
#     - /app/Agente_Orquestador/data/          -> 0700
#
#   Ambos son propiedad de root:root. Un proceso no-root NO puede:
#     * chmod sobre archivos/dirs ajenos (requiere CAP_FOWNER o ser owner)
#     * renombrar/reemplazar el directorio data/ (requiere escritura en el padre
#       /app/Agente_Orquestador/, que es root:root 0755)
#
# EJECUCIÓN (requiere root):
#   docker exec -u 0 <contenedor> bash /app/Subagente_Desarrollo/proyectos/remediacion_permisos_TKT-SEC-20261019181510/remediar_permisos_root.sh
#   — o —
#   sudo bash /app/Subagente_Desarrollo/proyectos/remediacion_permisos_TKT-SEC-20261019181510/remediar_permisos_root.sh
#
# IDEMPOTENTE: puede ejecutarse múltiples veces sin efectos adversos.
# =============================================================================

set -euo pipefail

ENV_FILE="/app/.env"
DATA_DIR="/app/Agente_Orquestador/data"
CRED_FILE="${DATA_DIR}/credentials.json"
TOKEN_FILE="${DATA_DIR}/token.json"

log() { echo "[remediar_permisos] $*"; }
fail() { echo "[remediar_permisos][ERROR] $*" >&2; exit 1; }

# ── 0. Verificación de privilegios ───────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    fail "Este script DEBE ejecutarse como root (uid 0). Actual: $(id -u) ($(id -un))."
fi

log "Ejecutando como root (uid 0). Iniciando remediación..."

# ── 1. Backup de seguridad (HS-01 ZERO-LOSS) ─────────────────────────────────
BACKUP_DIR="/app/Archivos_temporales/desarrollo_backup_permisos_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
[ -f "$ENV_FILE" ]   && cp -p "$ENV_FILE"   "$BACKUP_DIR/.env.bak"
[ -f "$CRED_FILE" ]  && cp -p "$CRED_FILE"  "$BACKUP_DIR/credentials.json.bak"
[ -f "$TOKEN_FILE" ] && cp -p "$TOKEN_FILE" "$BACKUP_DIR/token.json.bak"
log "Backup creado en: $BACKUP_DIR"

# ── 2. Remediación de /app/.env -> 0600 ──────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    chmod 600 "$ENV_FILE"
    log "OK  $ENV_FILE -> $(stat -c '%a' "$ENV_FILE")"
else
    log "SKIP $ENV_FILE no existe"
fi

# ── 3. Remediación de credenciales OAuth -> 0600 ─────────────────────────────
for f in "$CRED_FILE" "$TOKEN_FILE"; do
    if [ -f "$f" ]; then
        chmod 600 "$f"
        log "OK  $f -> $(stat -c '%a' "$f")"
    else
        log "SKIP $f no existe"
    fi
done

# ── 4. Remediación del directorio data/ -> 0700 ──────────────────────────────
if [ -d "$DATA_DIR" ]; then
    chmod 700 "$DATA_DIR"
    log "OK  $DATA_DIR -> $(stat -c '%a' "$DATA_DIR")"
else
    log "SKIP $DATA_DIR no existe"
fi

# ── 5. Verificación final ────────────────────────────────────────────────────
log "─── VERIFICACIÓN FINAL ───"
RC=0
check() {
    local path="$1" expected="$2"
    if [ -e "$path" ]; then
        local actual
        actual=$(stat -c '%a' "$path")
        if [ "$actual" = "$expected" ]; then
            log "PASS $path = $actual (esperado $expected)"
        else
            log "FAIL $path = $actual (esperado $expected)"
            RC=1
        fi
    fi
}

check "$ENV_FILE"   "600"
check "$CRED_FILE"  "600"
check "$TOKEN_FILE" "600"
check "$DATA_DIR"   "700"

if [ "$RC" -eq 0 ]; then
    log "✅ REMEDIACIÓN COMPLETA — todos los permisos conformes."
else
    log "❌ REMEDIACIÓN INCOMPLETA — revisar los FAIL anteriores."
fi

exit "$RC"
