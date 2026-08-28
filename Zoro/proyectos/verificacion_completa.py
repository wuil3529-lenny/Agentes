#!/usr/bin/env python3
"""
verificacion_completa.py — Verificación completa de secretos hardcodeados
en TODOS los archivos del ecosistema (no solo .py).
"""
import re
import json
from pathlib import Path

APP_ROOT = Path("/app")

# Extensiones a auditar
exts = [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".cfg", ".conf", ".ini", ".sh", ".env.example"]

# Patrones de secretos hardcodeados
patrones_secretos = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI/DeepSeek API Key"),
    (r"AIza[A-Za-z0-9_-]{20,}", "Google API Key"),
    (r"ghp_[A-Za-z0-9]{20,}", "GitHub Token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack Token"),
    (r"AKIA[A-Z0-9]{16}", "AWS Access Key"),
    (r"nvapi-[A-Za-z0-9_-]{20,}", "NVIDIA NIM API Key"),
    (r"\d{8,10}:[A-Za-z0-9_-]{30,}", "Telegram Bot Token"),
    (r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}", "JWT Token"),
    (r"xai-[A-Za-z0-9_-]{20,}", "xAI API Key"),
    (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{32}", "FAL Key"),
    (r"ysg4[A-Za-z0-9_-]{20,}", "Ideogram API Key"),
    (r"AQ\.[A-Za-z0-9_-]{20,}", "Gemini API Key"),
]

# Directorios a excluir
excluir = [".git", "node_modules", ".venv", "__pycache__", "logs", "Archivos_temporales", ".obsidian"]

resultados = {}

for ext in exts:
    for py_file in APP_ROOT.rglob(f"*{ext}"):
        # Excluir directorios
        rel = py_file.relative_to(APP_ROOT)
        if any(part in excluir for part in rel.parts):
            continue
        
        # Excluir el .env principal (es el archivo de configuración, no código)
        if py_file.name == ".env":
            continue
        
        try:
            contenido = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        
        lineas = contenido.split("\n")
        hallazgos = []
        
        for i, linea in enumerate(lineas, 1):
            # Saltar líneas que ya usan os.getenv / os.environ.get / os.environ
            if "os.getenv" in linea or "os.environ.get" in linea or "os.environ[" in linea:
                continue
            
            for patron, descripcion in patrones_secretos:
                matches = re.findall(patron, linea)
                if matches:
                    for m in matches:
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
            resultados[str(rel)] = hallazgos

print(json.dumps({
    "ticket": "TKT-SEC-20260820064246",
    "secretos_hardcodeados_encontrados": resultados,
    "total_archivos_con_secretos": len(resultados),
    "total_secretos": sum(len(v) for v in resultados.values())
}, indent=2, ensure_ascii=False))


