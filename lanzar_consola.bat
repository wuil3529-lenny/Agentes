@echo off
chcp 65001 > nul
title Consola de Pruebas - Tripulacion IA (Manos y Ojos)
cd /d "C:\Users\admin\Documents\Agentes"
color 0A
python consola_pruebas.py
echo.
echo ========================================================
echo Consola finalizada. Manteniendo ventana abierta para comandos libres.
echo ========================================================
cmd /k
