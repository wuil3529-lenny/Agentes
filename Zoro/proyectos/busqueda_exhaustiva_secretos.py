#!/usr/bin/env python3
"""
busqueda_exhaustiva_secretos.py — Búsqueda exhaustiva de secretos hardcodeados
en todos los archivos .py del ecosistema.
"""
import re
import json
from pathlib import Path

APP_ROOT = Path("/app")

# Directorios a auditar
dirs_a_auditar = ["Luffy", "Sanji", "Zoro", "Nami", "Robin"]

# Patrones de secretos hardcodeados (valores literales, no os.getenv)
patrones_secretos = [
    # OpenAI / Anthropic / DeepSeek style keys
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI/DeepSeek API Key"),
    # Google API keys
    (r"AIza[A-Za-z0-9_-]{20,}", "Google API Key"),
    # GitHub tokens
    (r"ghp_[A-Za-z0-9]{20,}", "GitHub Token"),
    # Slack tokens
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack Token"),
    # AWS keys
    (r"AKIA[A-Z0-9]{16}", "AWS Access Key"),
    # NVIDIA NIM keys
    (r"nvapi-[A-Za-z0-9_-]{20,}", "NVIDIA NIM API Key"),
    # Telegram bot tokens
    (r"\d{8,10}:[A-Za-z0-9_-]{30,}", "Telegram Bot Token"),
    # JWT tokens
    (r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}", "JWT Token"),
    # xAI keys
    (r"xai-[A-Za-z0-9_-]{20,}", "xAI API Key"),
    # FAL keys
    (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{32}", "FAL Key"),
    # Ideogram keys
    (r"ysg4[A-Za-z0-9_-]{20,}", "Ideogram API Key"),
    # Gemini keys
    (r"AQ\.[A-Za-z0-9_-]{20,}", "Gemini API Key"),
    # Generic patterns
    (r"['\"](?:api[_-]?key|token|secret|password|auth[_-]?token|access[_-]?token|refresh[_-]?token)['\"]\s*[:=]\s*['\"][^'\"]{10,}['\"]", "Generic hardcoded secret"),
]

resultados = {}

for dir_name in dirs_a_auditar:
    dir_path = APP_ROOT / dir_name
    if not dir_path.exists():
        continue
    
    for py_file in dir_path.rglob("*.py"):
        try:
            contenido = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        
        lineas = contenido.split("\n")
        hallazgos = []
        
        for i, linea in enumerate(lineas, 1):
            # Saltar líneas que ya usan os.getenv / os.environ.get
            if "os.getenv" in linea or "os.environ.get" in linea:
                continue
            
            for patron, descripcion in patrones_secretos:
                matches = re.findall(patron, linea)
                if matches:
                    for m in matches:
                        # Enmascarar
                        if len(m) > 8:
                            enmascarado = m[:4] + "***" + m[-4:]
                        else:
                            enmascarado = "***"
                        hallazgos.append({
                            "linea": i,
                            "tipo": descripcion,
                            "valor_enmascarado": enmascarado,
                            "contenido": linea.strip()[:150]
                        })
        
        if hallazgos:
            resultados[str(py_file.relative_to(APP_ROOT))] = hallazgos

print(json.dumps({
    "ticket": "TKT-SEC-20260820064246",
    "secretos_hardcodeados_encontrados": resultados,
    "total_archivos_con_secretos": len(resultados),
    "total_secretos": sum(len(v) for v in resultados.values())
}, indent=2, ensure_ascii=False))


