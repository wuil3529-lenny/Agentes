@echo off
echo ===================================================
echo   Reiniciando Contenedor Docker: Tripulacion IA
echo ===================================================
cd /d "%~dp0"

echo [1/2] Deteniendo contenedor actual...
docker compose down

echo [2/2] Levantando contenedor con nuevo entorno...
docker compose up -d

echo ===================================================
echo   Proceso de reinicio finalizado.
echo ===================================================
