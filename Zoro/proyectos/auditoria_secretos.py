#!/usr/bin/env python3
"""
auditoria_secretos.py — Audita los archivos afectados por el ticket TKT-SEC-20260820064246
para detectar API Keys y tokens hardcodeados en las líneas específicas.
"""
import re
import json
from pathlib import Path

APP_ROOT = Path("/app")

# Archivos y líneas afectadas según el ticket
archivos_afectados = {
    "Luffy/base_listener.py": [488],
    "Luffy/luffy_agent.py": [103, 108],
    "Luffy/skills/telegram_bridge.py": [10, 28],
    "Luffy/telegram_bridge.py": [10, 28],
    "Sanji/sanji_agent.py": [108, 118],
    "Sanji/skills/skill_google_sanji.py": [276, 288],
    "Zoro/skills/skill_n8n.py": [53],
    "Zoro/skills/skill_ngrok.py": [48],
}

# Patrones de secretos hardcodeados
patrones_secretos = [
    r"sk-[A-Za-z0-9]{20,}",
    r"AIza[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"AKIA[A-Z0-9]{16}",
    r"Bearer\s+[A-Za-z0-9._-]{20,}",
    r"api[_-]?key\s*[=:]\s*['\"][^'\"]{10,}['\"]",
    r"token\s*[=:]\s*['\"][^'\"]{10,}['\"]",
    r"password\s*[=:]\s*['\"][^'\"]{6,}['\"]",
    r"secret\s*[=:]\s*['\"][^'\"]{6,}['\"]",
    r"client[_-]?secret\s*[=:]\s*['\"][^'\"]{6,}['\"]",
    r"access[_-]?token\s*[=:]\s*['\"][^'\"]{10,}['\"]",
    r"refresh[_-]?token\s*[=:]\s*['\"][^'\"]{10,}['\"]",
    r"auth[_-]?token\s*[=:]\s*['\"][^'\"]{10,}['\"]",
]

resultados = {}

for ruta_rel, lineas in archivos_afectados.items():
    ruta_abs = APP_ROOT / ruta_rel
    if not ruta_abs.exists():
        resultados[ruta_rel] = {"error": "Archivo no encontrado"}
        continue
    
    contenido = ruta_abs.read_text(encoding="utf-8", errors="replace")
    lineas_contenido = contenido.split("\n")
    
    hallazgos = []
    for num_linea in lineas:
        if num_linea - 1 < len(lineas_contenido):
            linea_texto = lineas_contenido[num_linea - 1]
            # Buscar secretos en la línea
            secretos_encontrados = []
            for patron in patrones_secretos:
                matches = re.findall(patron, linea_texto, re.IGNORECASE)
                if matches:
                    # Enmascarar el secreto
                    for m in matches:
                        if len(m) > 8:
                            enmascarado = m[:4] + "***" + m[-4:]
                        else:
                            enmascarado = "***"
                        secretos_encontrados.append({"patron": patron, "valor_enmascarado": enmascarado})
            
            hallazgos.append({
                "linea": num_linea,
                "contenido": linea_texto.strip()[:120],
                "secretos": secretos_encontrados,
                "usa_os_getenv": "os.getenv" in linea_texto or "os.environ.get" in linea_texto,
                "usa_os_environ": "os.environ" in linea_texto,
            })
    
    resultados[ruta_rel] = hallazgos

# Verificar el .env para ver qué variables existen
env_path = APP_ROOT / ".env"
env_vars = []
if env_path.exists():
    env_content = env_path.read_text(encoding="utf-8", errors="replace")
    for line in env_content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=")[0].strip()
            env_vars.append(key)

resultado_final = {
    "ticket": "TKT-SEC-20260820064246",
    "archivos_auditados": resultados,
    "variables_env_existentes": env_vars,
    "resumen": "Auditoría de secretos hardcodeados completada"
}

print(json.dumps(resultado_final, indent=2, ensure_ascii=False))


