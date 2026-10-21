#!/usr/bin/env bash
# =============================================================================
# remediar_permisos_env.sh
# TKT-SEC-20261020190613 — Remediación del hallazgo H-01 (ALTO)
#
# OBJETIVO: Restringir /app/.env (bind-mount del host) a permisos 0600.
#
# CONTEXTO TÉCNICO:
#   El archivo .env vive en el HOST y se monta en el contenedor vía
#   `docker-compose.yml` (volumes: type: bind, source: ., target: /app).
#   Dentro del contenedor el proceso corre como 'tripulacion' (uid 1001),
#   pero el archivo pertenece a 'root:root'. Por eso `chmod` desde dentro
#   del contenedor falla con "Operation not permitted" (falta CAP_FOWNER).
#
#   => La corrección DEBE ejecutarse en el HOST, no en el contenedor.
#
# USO:
#   Linux / macOS  :  bash remediar_permisos_env.sh
#   Windows (PowerShell como Administrador):
#       icacls .env /inheritance:r /grant:r "$env:USERNAME:(R)"
#
# =============================================================================
set -euo pipefail

ENV_FILE="${1:-.env}"

echo "════════════════════════════════════════════════════════════════════"
echo " TKT-SEC-20261020190613 — Remediación de permisos de .env"
echo "════════════════════════════════════════════════════════════════════"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "✗ ERROR: no se encontró '$ENV_FILE' en el directorio actual."
    echo "  Ejecuta este script desde la raíz del proyecto (donde vive .env)."
    exit 1
fi

MODO_ANTES="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE")"
PROPIETARIO="$(stat -c '%U:%G' "$ENV_FILE" 2>/dev/null || echo 'n/a')"

echo "  Archivo     : $ENV_FILE"
echo "  Permisos    : $MODO_ANTES"
echo "  Propietario : $PROPIETARIO"
echo ""

if [[ "$MODO_ANTES" == "600" ]]; then
    echo "✓ Los permisos YA son 0600. No se requiere acción."
    exit 0
fi

echo "→ Aplicando chmod 600 ..."
if chmod 600 "$ENV_FILE"; then
    MODO_DESPUES="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE")"
    echo "✓ Permisos corregidos: $MODO_ANTES -> $MODO_DESPUES"
    echo ""
    echo "  RECUERDA: reinicia la flota para que el contenedor relea el archivo:"
    echo "      docker compose restart"
    exit 0
else
    echo "✗ ERROR: chmod falló. Ejecuta este script con privilegios suficientes"
    echo "  (sudo en Linux/macOS, o PowerShell como Administrador en Windows)."
    exit 1
fi
