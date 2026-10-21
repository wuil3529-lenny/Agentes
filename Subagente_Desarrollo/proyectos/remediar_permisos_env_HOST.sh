#!/usr/bin/env bash
# =============================================================================
# remediar_permisos_env_HOST.sh
# TKT-SEC-20261020205030 — Remediación ALTO: /app/.env con permisos 0o444
#
# ⚠️  ESTE SCRIPT DEBE EJECUTARSE EN EL HOST (Windows/Linux), NO EN EL CONTENEDOR.
#
# DIAGNÓSTICO (verificado el 2026-10-20):
#   /app es un bind-mount 9p de Windows (drvfs) montado con uid=0;gid=0.
#   El archivo .env pertenece a root:root con modo 0o444.
#   El proceso de la flota corre como 'tripulacion' (uid 1001) SIN CAP_FOWNER,
#   por lo que `chmod` dentro del contenedor falla con EPERM:
#       chmod: changing permissions of '/app/.env': Operation not permitted
#   => La corrección es IMPOSIBLE desde dentro del contenedor. Debe hacerse
#      sobre el archivo real del host.
#
# RUTA REAL DEL ARCHIVO EN EL HOST:
#   C:\Users\admin\Documents\Agentes\.env
#   (mapeada a /app/.env por docker-compose.yml: volumes: source: . target: /app)
#
# USO:
#   Windows (PowerShell como Administrador):
#       icacls "C:\Users\admin\Documents\Agentes\.env" /inheritance:r /grant:r "$env:USERNAME:(R)"
#   Linux/macOS:
#       chmod 600 /ruta/al/Agentes/.env
# =============================================================================
set -euo pipefail

ENV_FILE="${1:-.env}"

echo "════════════════════════════════════════════════════════════════════════"
echo " TKT-SEC-20261020205030 — Remediación de permisos de .env (HOST)"
echo "════════════════════════════════════════════════════════════════════════"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "✗ ERROR: no se encontró '$ENV_FILE'."
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
    echo "✗ ERROR: chmod falló. Ejecuta con privilegios suficientes"
    echo "  (sudo en Linux/macOS, o PowerShell como Administrador en Windows)."
    exit 1
fi
