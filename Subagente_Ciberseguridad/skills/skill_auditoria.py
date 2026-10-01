"""
skill_auditoria.py — Habilidades de Auditoría de Seguridad (Robin)
==================================================================
Herramientas de lectura e inspección para revisar código de Zoro
y flujos de Nami en busca de vulnerabilidades.

Herramientas disponibles:
  - leer_archivo_seguro        : Leer un archivo con contexto de seguridad
  - listar_directorio_auditoria: Mapear la estructura de un proyecto a revisar
  - buscar_patron_en_directorio: Buscar texto/expresiones en múltiples archivos
  - detectar_secretos_expuestos: Escanear en busca de tokens, claves y credenciales
  - leer_workflow_n8n          : Leer y analizar un workflow JSON de n8n
  - verificar_gitignore        : Comprobar que .env y secretos están protegidos
"""

import json
import re
from pathlib import Path
from langchain_core.tools import tool


# ══════════════════════════════════════════════════════════════════════════════
# Patrones de secretos conocidos
# ══════════════════════════════════════════════════════════════════════════════

PATRONES_SECRETOS = [
    # Genéricos
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{4,})["\']?', "Contraseña hardcodeada"),
    (r'(?i)(secret|api_secret|client_secret)\s*[:=]\s*["\']?([^\s"\']{4,})["\']?', "Secret hardcodeado"),
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([^\s"\']{8,})["\']?', "API Key hardcodeada"),
    (r'(?i)(token|access_token|auth_token)\s*[:=]\s*["\']?([^\s"\']{8,})["\']?', "Token hardcodeado"),
    # Redes sociales (Nami)
    (r'(?i)(twitter|x).*?(bearer|token|key|secret)\s*[:=]\s*["\']?([^\s"\']{8,})', "Token de Twitter/X"),
    (r'(?i)(instagram|ig).*?(token|key|secret)\s*[:=]\s*["\']?([^\s"\']{8,})', "Token de Instagram"),
    (r'(?i)(linkedin).*?(token|key|secret)\s*[:=]\s*["\']?([^\s"\']{8,})', "Token de LinkedIn"),
    (r'(?i)(facebook|fb).*?(token|key|secret)\s*[:=]\s*["\']?([^\s"\']{8,})', "Token de Facebook"),
    # Claves de infraestructura
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
    (r'xoxb-[0-9]+-[a-zA-Z0-9]+', "Slack Bot Token"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
    (r'(?i)ngrok.*?authtoken\s*[:=]\s*([^\s"\']{10,})', "ngrok Auth Token"),
    # Credenciales de base de datos
    (r'(?i)(db_pass|database_password|postgres.*pass|mysql.*pass)\s*[:=]\s*["\']?([^\s"\']{4,})["\']?', "Contraseña de base de datos"),
    # URLs con credenciales embebidas
    (r'(https?|postgresql|mysql|mongodb):\/\/[^:]+:[^@]+@', "URL con credenciales embebidas"),
]

EXTENSIONES_CODIGO = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".env",
                       ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ".bat", ".ps1"}

ARCHIVOS_IGNORAR = {"__pycache__", ".git", "node_modules", ".venv", "venv", "dist", "build"}


# ══════════════════════════════════════════════════════════════════════════════
# Herramientas
# ══════════════════════════════════════════════════════════════════════════════

@tool
def leer_archivo_seguro(ruta_absoluta: str) -> str:
    """
    Lee el contenido de un archivo de código para su auditoría de seguridad.
    Incluye metadatos relevantes para el análisis (tamaño, extensión, líneas).

    Args:
        ruta_absoluta: Ruta completa del archivo a revisar.
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            ruta_fallback = Path("/app/protocolo") / Path(ruta_absoluta).name
            if ruta_fallback.exists():
                ruta = ruta_fallback
            else:
                return json.dumps({"status": "error", "mensaje": f"Archivo no encontrado: {ruta_absoluta}"})
        if not ruta.is_file():
            return json.dumps({"status": "error", "mensaje": f"La ruta no es un archivo: {ruta_absoluta}"})

        contenido = ruta.read_text(encoding="utf-8", errors="replace")
        lineas = contenido.splitlines()

        return json.dumps({
            "status": "success",
            "archivo": str(ruta),
            "extension": ruta.suffix,
            "tamaño_bytes": ruta.stat().st_size,
            "total_lineas": len(lineas),
            "contenido": contenido[:8000],  # Limitar a 8000 chars para el LLM
            "truncado": len(contenido) > 8000
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def listar_directorio_auditoria(ruta_absoluta: str) -> str:
    """
    Mapea la estructura de un directorio para identificar todos los archivos
    a auditar. Excluye directorios irrelevantes (node_modules, __pycache__, etc.).

    Args:
        ruta_absoluta: Ruta del directorio raíz a mapear.
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta_absoluta}"})

        archivos_encontrados = []
        for item in sorted(ruta.rglob("*")):
            # Ignorar directorios excluidos
            if any(parte in ARCHIVOS_IGNORAR for parte in item.parts):
                continue
            if item.is_file():
                archivos_encontrados.append({
                    "ruta_relativa": str(item.relative_to(ruta)),
                    "extension": item.suffix,
                    "bytes": item.stat().st_size,
                    "es_codigo": item.suffix in EXTENSIONES_CODIGO
                })

        total = len(archivos_encontrados)
        archivos_codigo = [a for a in archivos_encontrados if a["es_codigo"]]

        return json.dumps({
            "status": "success",
            "ruta_raiz": str(ruta),
            "total_archivos": total,
            "archivos_auditables": len(archivos_codigo),
            "archivos": archivos_encontrados[:80]  # Limitar listado
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def buscar_patron_en_directorio(ruta_absoluta: str, patron: str, extensiones: str = ".py,.js,.ts,.json") -> str:
    """
    Busca un patrón de texto (puede ser regex) en todos los archivos de código
    de un directorio. Útil para rastrear el uso de funciones inseguras,
    imports peligrosos, o texto específico.

    Args:
        ruta_absoluta: Directorio raíz donde buscar.
        patron: Texto o expresión regular a buscar.
        extensiones: Extensiones a revisar, separadas por coma (ej: ".py,.js,.env").
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta_absoluta}"})

        exts = {e.strip() for e in extensiones.split(",")}
        regex = re.compile(patron, re.IGNORECASE)
        coincidencias = []

        for archivo in sorted(ruta.rglob("*")):
            if any(parte in ARCHIVOS_IGNORAR for parte in archivo.parts):
                continue
            if archivo.is_file() and archivo.suffix in exts:
                try:
                    contenido = archivo.read_text(encoding="utf-8", errors="replace")
                    for num, linea in enumerate(contenido.splitlines(), 1):
                        if regex.search(linea):
                            coincidencias.append({
                                "archivo": str(archivo.relative_to(ruta)),
                                "linea": num,
                                "contenido": linea.strip()[:200]
                            })
                            if len(coincidencias) >= 50:
                                break
                except Exception:
                    continue
            if len(coincidencias) >= 50:
                break

        return json.dumps({
            "status": "success",
            "patron_buscado": patron,
            "total_coincidencias": len(coincidencias),
            "coincidencias": coincidencias
        })
    except re.error as e:
        return json.dumps({"status": "error", "mensaje": f"Expresión regular inválida: {e}"})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def detectar_secretos_expuestos(ruta_absoluta: str) -> str:
    """
    Escanea un directorio completo en busca de credenciales hardcodeadas,
    tokens de API, contraseñas y otros secretos expuestos en el código fuente.
    Cubre patrones de Twitter, Instagram, LinkedIn, Facebook, OpenAI, GitHub, ngrok, etc.

    Args:
        ruta_absoluta: Directorio raíz a escanear (ej: C:/Users/admin/Documents/Agentes/Zoro).
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta_absoluta}"})

        hallazgos = []

        for archivo in sorted(ruta.rglob("*")):
            if any(parte in ARCHIVOS_IGNORAR for parte in archivo.parts):
                continue
            if not archivo.is_file():
                continue
            if archivo.suffix not in EXTENSIONES_CODIGO:
                continue

            try:
                contenido = archivo.read_text(encoding="utf-8", errors="replace")
                lineas = contenido.splitlines()

                for num, linea in enumerate(lineas, 1):
                    linea_limpia = linea.strip()
                    if not linea_limpia or linea_limpia.startswith("#"):
                        continue

                    for patron_regex, tipo_secreto in PATRONES_SECRETOS:
                        match = re.search(patron_regex, linea)
                        if match:
                            # Enmascarar el valor encontrado para el reporte
                            valor_raw = match.group(0)
                            valor_mask = valor_raw[:15] + "***" if len(valor_raw) > 15 else "***"
                            hallazgos.append({
                                "tipo": tipo_secreto,
                                "archivo": str(archivo.relative_to(ruta)),
                                "linea": num,
                                "extracto": valor_mask,
                                "nivel": "CRÍTICO" if "Key" in tipo_secreto or "Token" in tipo_secreto else "ALTO"
                            })
                            break  # Un hallazgo por línea

                    if len(hallazgos) >= 30:
                        break
            except Exception:
                continue

            if len(hallazgos) >= 30:
                break

        nivel_global = "OK"
        if hallazgos:
            niveles = [h["nivel"] for h in hallazgos]
            nivel_global = "CRÍTICO" if "CRÍTICO" in niveles else "ALTO"

        return json.dumps({
            "status": "success",
            "directorio_escaneado": str(ruta),
            "total_hallazgos": len(hallazgos),
            "nivel_global": nivel_global,
            "hallazgos": hallazgos
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def leer_workflow_n8n(ruta_absoluta: str) -> str:
    """
    Lee y analiza un archivo JSON de workflow de n8n, extrayendo
    información relevante para la auditoría de seguridad:
    webhooks expuestos, credenciales almacenadas, URLs, nodos con acceso externo.

    Args:
        ruta_absoluta: Ruta al archivo JSON del workflow de n8n.
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Archivo no encontrado: {ruta_absoluta}"})

        contenido_raw = ruta.read_text(encoding="utf-8", errors="replace")
        workflow = json.loads(contenido_raw)

        nodos = workflow.get("nodes", [])
        analisis_nodos = []
        webhooks = []
        credenciales_en_uso = []
        urls_externas = []

        for nodo in nodos:
            tipo = nodo.get("type", "")
            nombre = nodo.get("name", "Sin nombre")
            params = nodo.get("parameters", {})

            info_nodo = {"nombre": nombre, "tipo": tipo, "alertas": []}

            # Detectar webhooks
            if "webhook" in tipo.lower() or "trigger" in tipo.lower():
                path = params.get("path", "N/A")
                auth_type = params.get("authentication", "none")
                webhooks.append({
                    "nodo": nombre,
                    "path": path,
                    "autenticacion": auth_type,
                    "alerta": "SIN AUTENTICACIÓN" if auth_type in ("none", "", None) else "OK"
                })
                if auth_type in ("none", "", None):
                    info_nodo["alertas"].append("Webhook sin autenticación configurada")

            # Detectar credenciales referenciadas
            credentials = nodo.get("credentials", {})
            if credentials:
                for cred_tipo, cred_data in credentials.items():
                    credenciales_en_uso.append({
                        "nodo": nombre,
                        "tipo_credencial": cred_tipo,
                        "nombre_credencial": cred_data.get("name", "N/A")
                    })

            # Detectar URLs externas en parámetros
            params_str = json.dumps(params)
            urls = re.findall(r'https?://[^\s"\'<>]+', params_str)
            for url in urls:
                if "localhost" not in url and "127.0.0.1" not in url:
                    urls_externas.append({"nodo": nombre, "url": url[:120]})

            # Detectar posibles secrets en parámetros directos
            for clave, valor in params.items():
                if isinstance(valor, str) and any(
                    kw in clave.lower() for kw in ("token", "key", "secret", "password", "pass")
                ):
                    if len(valor) > 4 and not valor.startswith("={{"):
                        info_nodo["alertas"].append(f"Valor sensible directo en parámetro '{clave}'")

            if info_nodo["alertas"]:
                analisis_nodos.append(info_nodo)

        return json.dumps({
            "status": "success",
            "workflow_nombre": workflow.get("name", "Sin nombre"),
            "total_nodos": len(nodos),
            "webhooks_detectados": webhooks,
            "credenciales_en_uso": credenciales_en_uso,
            "urls_externas": urls_externas[:15],
            "nodos_con_alertas": analisis_nodos,
            "resumen_seguridad": {
                "webhooks_sin_auth": sum(1 for w in webhooks if w["alerta"] == "SIN AUTENTICACIÓN"),
                "credenciales_expuestas": len([n for n in analisis_nodos if any("sensible" in a for a in n["alertas"])]),
                "nivel": "ALTO" if any(w["alerta"] == "SIN AUTENTICACIÓN" for w in webhooks) else "MEDIO"
            }
        }, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({"status": "error", "mensaje": f"El archivo no es un JSON válido: {e}"})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def verificar_gitignore(ruta_absoluta: str) -> str:
    """
    Verifica que los archivos sensibles (.env, claves, credenciales) están
    correctamente protegidos por .gitignore en un proyecto.
    También comprueba si existe un repositorio git inicializado.

    Args:
        ruta_absoluta: Directorio raíz del proyecto a verificar.
    """
    try:
        ruta = Path(ruta_absoluta)
        if not ruta.exists():
            return json.dumps({"status": "error", "mensaje": f"Directorio no encontrado: {ruta_absoluta}"})

        # Verificar si hay repositorio git
        tiene_git = (ruta / ".git").exists()

        # Buscar archivos .gitignore
        gitignore_files = list(ruta.rglob(".gitignore"))
        contenido_gitignore = ""
        for gi in gitignore_files:
            try:
                contenido_gitignore += gi.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # Archivos sensibles que DEBEN estar en .gitignore
        archivos_sensibles_esperados = [
            (".env", ".env" in contenido_gitignore or "*.env" in contenido_gitignore),
            (".env.local", ".env.local" in contenido_gitignore),
            (".env.*", "*.env" in contenido_gitignore or ".env.*" in contenido_gitignore),
            ("*.key", "*.key" in contenido_gitignore),
            ("*.pem", "*.pem" in contenido_gitignore),
            ("secrets.json", "secrets.json" in contenido_gitignore),
            ("credentials.json", "credentials.json" in contenido_gitignore),
        ]

        # Buscar archivos .env reales en el proyecto
        env_files_encontrados = [
            str(f.relative_to(ruta))
            for f in ruta.rglob("*.env")
            if not any(p in ARCHIVOS_IGNORAR for p in f.parts)
        ] + [
            str(f.relative_to(ruta))
            for f in ruta.rglob(".env*")
            if f.is_file() and not any(p in ARCHIVOS_IGNORAR for p in f.parts)
        ]

        alertas = []
        for nombre, protegido in archivos_sensibles_esperados:
            if not protegido:
                alertas.append(f"'{nombre}' NO está cubierto por .gitignore")

        nivel = "OK"
        if alertas and tiene_git:
            nivel = "ALTO"
        elif alertas:
            nivel = "MEDIO"

        return json.dumps({
            "status": "success",
            "directorio": str(ruta),
            "tiene_repositorio_git": tiene_git,
            "gitignore_encontrados": [str(g.relative_to(ruta)) for g in gitignore_files],
            "archivos_env_encontrados": env_files_encontrados,
            "cobertura_gitignore": [
                {"archivo": n, "protegido": p}
                for n, p in archivos_sensibles_esperados
            ],
            "alertas": alertas,
            "nivel": nivel
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas exportadas
HERRAMIENTAS_AUDITORIA = [
    leer_archivo_seguro,
    listar_directorio_auditoria,
    buscar_patron_en_directorio,
    detectar_secretos_expuestos,
    leer_workflow_n8n,
    verificar_gitignore,
]
