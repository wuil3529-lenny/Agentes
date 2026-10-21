"""
skill_escaneo.py — Habilidades de Escaneo Dinámico, CVEs y Exposición de Red
============================================================================
Herramientas activas para escanear vulnerabilidades en dependencias (Python/Node),
puertos locales en escucha y configuraciones perimetrales (n8n, ngrok y permisos).

Herramientas disponibles:
  - ejecutar_pip_audit        : Escanear dependencias Python con CVEs conocidas
  - ejecutar_npm_audit        : Escanear dependencias Node.js con CVEs conocidas
  - verificar_puertos_locales : Inspeccionar puertos en escucha y servicios expuestos
  - verificar_auth_ngrok      : Comprobar autenticación en túneles ngrok
  - verificar_auth_n8n        : Comprobar autenticación básica en n8n
  - analizar_permisos_archivo : Revisar permisos y atributos de archivos sensibles
"""

import os
import sys
import json
import stat
import shlex
import subprocess
from pathlib import Path
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["robin", "subagente_ciberseguridad"] else _CURRENT.parents[2]


def obtener_prompt_escaneo() -> str:
    """
    Retorna el System Prompt especializado para la habilidad de Escaneo Dinámico.
    """
    return """[🛡️ DIRECTIVA OPERATIVA: MODO ESCANEO DINÁMICO, DEPENDENCIAS Y PERÍMETRO]
Eres el Especialista en Detección de Vulnerabilidades y Análisis Perimetral de la tripulación.
Tu función es auditar activamente el estado de dependencias de terceros, servicios en ejecución en la red local y túneles de comunicación expuestos.

PAUTAS CRÍTICAS DE ESCANEO:
1. AUDITORÍA DE DEPENDENCIAS (CVEs):
   - Ejecuta `ejecutar_pip_audit` sobre proyectos Python con `requirements.txt` para identificar librerías vulnerables o desactualizadas.
   - Ejecuta `ejecutar_npm_audit` sobre proyectos Node/React con `package.json` para detectar vulnerabilidades en el árbol de dependencias.
2. ANÁLISIS DE PUERTOS Y SERVICIOS EXPUESTOS:
   - Utiliza `verificar_puertos_locales` para auditar qué procesos están escuchando conexiones (ej. n8n en :5678, Ollama en :11434, Webhooks).
3. CONFIGURACIONES PERIMETRALES Y AUTENTICACIÓN:
   - Utiliza `verificar_auth_ngrok` para evitar que túneles públicos queden abiertos sin bandera `--basic-auth`.
   - Utiliza `verificar_auth_n8n` para validar que `N8N_BASIC_AUTH_ACTIVE=true` esté activo en el `.env`.
   - Utiliza `analizar_permisos_archivo` para verificar que claves y variables de entorno no tengan permisos excesivos de lectura global.
"""


# ─── SEC-H02: Utilidades de saneamiento de comandos ──────────────────────────
# Operadores de shell que solo tienen sentido con shell=True. Su presencia es
# señal de intento de encadenamiento/inyección y se rechaza explícitamente.
_METACARACTERES_SHELL = ("&&", "||", ";", "|", "`", "$(", "${", ">", "<", "&>", ">>")

# Binarios permitidos para las herramientas de escaneo (lista blanca determinística).
_BINARIOS_PERMITIDOS = {
    "python", "python3", "py", "pip", "pip3",
    "npm", "npx", "node",
    "netstat", "ss", "tasklist", "lsof",
}


def _tokenizar_comando_seguro(comando) -> list:
    """
    Normaliza un comando a una lista de argumentos SIN invocar una shell.

    Acepta tanto una lista/tupla ya tokenizada como una cadena, que se divide
    con shlex.split(). Rechaza operadores de shell y binarios fuera de la
    lista blanca.

    Raises:
        ValueError: si el comando contiene metacaracteres de shell, no puede
                    tokenizarse o el binario no está permitido.
    """
    if isinstance(comando, (list, tuple)):
        argv = [str(a) for a in comando]
        texto_control = " ".join(argv)
    elif isinstance(comando, str):
        if not comando.strip():
            raise ValueError("Comando vacío o inválido.")
        texto_control = comando
        try:
            argv = shlex.split(comando, posix=(os.name != "nt"))
        except ValueError as e:
            raise ValueError(f"Comando no tokenizable de forma segura: {e}")
    else:
        raise ValueError(f"Tipo de comando no soportado: {type(comando).__name__}")

    if not argv:
        raise ValueError("Comando vacío tras tokenizar.")

    # 1. Rechazo de operadores de encadenamiento / redirección / sustitución
    for op in _METACARACTERES_SHELL:
        if op in texto_control:
            raise ValueError(
                f"Operador de shell '{op}' no permitido (ejecución sin shell intermedio). "
                "Emite un único comando por invocación."
            )

    # 2. Validación del binario base contra la lista blanca
    binario = Path(argv[0]).name.lower()
    if binario.endswith(".exe"):
        binario = binario[:-4]
    if binario not in _BINARIOS_PERMITIDOS:
        raise ValueError(
            f"Binario '{binario}' no está en la lista blanca de permitidos: "
            f"{', '.join(sorted(_BINARIOS_PERMITIDOS))}"
        )

    return argv


def _ejecutar_comando_seguro(comando, directorio: str = None, timeout: int = 60) -> dict:
    """
    Helper interno para ejecutar comandos de escaneo de forma segura.

    SEC-H02: ejecuta SIEMPRE con shell=False sobre una lista de argumentos
    (tokenizada con shlex.split() si recibe una cadena), eliminando la
    superficie de inyección de comandos por interpolación de variables.
    """
    try:
        argv = _tokenizar_comando_seguro(comando)

        kwargs = {
            "shell": False,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "encoding": "utf-8",
            "errors": "replace"
        }
        if directorio:
            kwargs["cwd"] = directorio

        resultado = subprocess.run(argv, **kwargs)
        return {
            "exitcode": resultado.returncode,
            "stdout": resultado.stdout[:3000] if resultado.stdout else "",
            "stderr": resultado.stderr[:1500] if resultado.stderr else "",
            "ok": resultado.returncode == 0
        }
    except ValueError as e:
        return {"exitcode": -1, "stdout": "", "stderr": f"Comando rechazado por política de seguridad: {e}", "ok": False}
    except subprocess.TimeoutExpired:
        return {"exitcode": -1, "stdout": "", "stderr": "Timeout: comando superó el límite de tiempo.", "ok": False}
    except FileNotFoundError:
        return {"exitcode": -1, "stdout": "", "stderr": "Comando no encontrado en el sistema.", "ok": False}
    except Exception as e:
        return {"exitcode": -1, "stdout": "", "stderr": str(e), "ok": False}


# ══════════════════════════════════════════════════════════════════════════════
# Herramientas
# ══════════════════════════════════════════════════════════════════════════════

@tool
def ejecutar_pip_audit(directorio_proyecto: str) -> str:
    """
    Ejecuta pip-audit en un proyecto Python para detectar dependencias
    con vulnerabilidades conocidas (CVEs).
    """
    check = _ejecutar_comando_seguro(["python", "-m", "pip_audit", "--version"])
    if not check["ok"]:
        install = _ejecutar_comando_seguro(["pip", "install", "pip-audit", "--quiet"], timeout=90)
        if not install["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": "No se pudo instalar pip-audit en el entorno.",
                "stderr": install["stderr"]
            }, ensure_ascii=False)

    ruta = Path(directorio_proyecto)
    if not ruta.is_absolute():
        ruta = _APP_ROOT / directorio_proyecto.lstrip("/\\")

    req_file = ruta / "requirements.txt"
    if req_file.exists():
        cmd = ["python", "-m", "pip_audit", "-r", str(req_file), "--format", "json"]
    else:
        cmd = ["python", "-m", "pip_audit", "--format", "json"]

    resultado = _ejecutar_comando_seguro(cmd, directorio=str(ruta), timeout=120)

    vulnerabilidades = []
    try:
        if resultado["stdout"]:
            datos = json.loads(resultado["stdout"])
            vulnerabilidades = datos if isinstance(datos, list) else datos.get("vulnerabilities", [])
    except (json.JSONDecodeError, ValueError):
        pass

    nivel = "OK"
    if vulnerabilidades:
        criticas = [v for v in vulnerabilidades if any(
            "critical" in str(v).lower() or "high" in str(v).lower()
        )]
        nivel = "CRÍTICO" if criticas else "ALTO"

    return json.dumps({
        "status": "success",
        "directorio": str(ruta),
        "requirements_encontrado": req_file.exists(),
        "total_vulnerabilidades": len(vulnerabilidades),
        "nivel": nivel,
        "vulnerabilidades": vulnerabilidades[:20],
        "stderr": resultado["stderr"][:500] if resultado["stderr"] else ""
    }, ensure_ascii=False)


@tool
def ejecutar_npm_audit(directorio_proyecto: str) -> str:
    """
    Ejecuta npm audit en un proyecto Node.js / React para detectar dependencias
    con vulnerabilidades conocidas (CVEs).
    """
    ruta = Path(directorio_proyecto)
    if not ruta.is_absolute():
        ruta = _APP_ROOT / directorio_proyecto.lstrip("/\\")

    package_json = ruta / "package.json"
    if not package_json.exists():
        return json.dumps({
            "status": "error",
            "mensaje": f"No se encontró package.json en: {ruta}"
        }, ensure_ascii=False)

    resultado = _ejecutar_comando_seguro(
        ["npm", "audit", "--json"],
        directorio=str(ruta),
        timeout=90
    )

    vulnerabilidades_resumen = {}
    try:
        if resultado["stdout"]:
            datos = json.loads(resultado["stdout"])
            vulnerabilidades_resumen = datos.get("metadata", {}).get("vulnerabilities", {})
    except (json.JSONDecodeError, ValueError):
        pass

    total = sum(vulnerabilidades_resumen.values()) if vulnerabilidades_resumen else 0
    nivel = "OK"
    if vulnerabilidades_resumen.get("critical", 0) > 0:
        nivel = "CRÍTICO"
    elif vulnerabilidades_resumen.get("high", 0) > 0:
        nivel = "ALTO"
    elif total > 0:
        nivel = "MEDIO"

    return json.dumps({
        "status": "success",
        "directorio": str(ruta),
        "resumen_vulnerabilidades": vulnerabilidades_resumen,
        "total_vulnerabilidades": total,
        "nivel": nivel,
        "salida_raw": resultado["stdout"][:1500] if resultado["stdout"] else "",
        "stderr": resultado["stderr"][:500] if resultado["stderr"] else ""
    }, ensure_ascii=False)


@tool
def verificar_puertos_locales() -> str:
    """
    Verifica qué puertos locales están actualmente en escucha en el sistema.
    Detecta exposiciones de n8n (5678), Ollama (11434), ngrok (4040) y servicios web.
    """
    resultado = _ejecutar_comando_seguro(["netstat", "-an"], timeout=15)

    puertos_criticos = {
        "5678": {"servicio": "n8n UI", "riesgo": "Workflows y credenciales expuestos si no tiene autenticación"},
        "11434": {"servicio": "Ollama API", "riesgo": "API de LLM sin restricción de acceso"},
        "4040": {"servicio": "ngrok Inspector UI", "riesgo": "Inspección de tráfico HTTP expuesta"},
        "3000": {"servicio": "App Node / React dev server", "riesgo": "Verificar superficie expuesta"},
        "8000": {"servicio": "FastAPI / Uvicorn backend", "riesgo": "Verificar endpoints y auth"},
        "8080": {"servicio": "Servidor web HTTP", "riesgo": "Verificar exposición"},
        "22": {"servicio": "SSH", "riesgo": "Acceso remoto por consola"},
    }

    puertos_activos = []
    alertas = []

    if resultado["stdout"]:
        lineas = resultado["stdout"].splitlines()
        for linea in lineas:
            if "LISTEN" in linea or "LISTENING" in linea:
                for puerto, info in puertos_criticos.items():
                    if f":{puerto}" in linea or f".{puerto}" in linea:
                        puertos_activos.append({
                            "puerto": puerto,
                            "servicio": info["servicio"],
                            "riesgo": info["riesgo"],
                            "linea": linea.strip()[:100]
                        })
                        alertas.append(f"Puerto {puerto} ({info['servicio']}) en escucha — {info['riesgo']}")

    nivel = "OK"
    if alertas:
        nivel = "ALTO" if any("n8n" in a or "Ollama" in a for a in alertas) else "MEDIO"

    return json.dumps({
        "status": "success",
        "puertos_criticos_activos": puertos_activos,
        "total_alertas": len(alertas),
        "nivel": nivel,
        "alertas": alertas,
        "nota": "Auditoría de puertos críticos completada."
    }, ensure_ascii=False)


@tool
def verificar_auth_ngrok(ruta_config_o_proceso: str = "") -> str:
    """
    Verifica si ngrok está corriendo con autenticación básica (--basic-auth).
    Revisa archivos de configuración, procesos activos y scripts de túnel.
    """
    alertas = []
    hallazgos = []

    proc = _ejecutar_comando_seguro(
        ["tasklist", "/FI", "IMAGENAME eq ngrok.exe"],
        timeout=10
    )
    ngrok_activo = "ngrok.exe" in proc["stdout"].lower()
    hallazgos.append({"check": "Proceso ngrok activo", "resultado": "SÍ" if ngrok_activo else "NO"})

    tiene_basic_auth = False
    if ruta_config_o_proceso:
        ruta = Path(ruta_config_o_proceso)
        if not ruta.is_absolute():
            ruta = _APP_ROOT / ruta_config_o_proceso.lstrip("/\\")
        if ruta.exists():
            try:
                contenido = ruta.read_text(encoding="utf-8", errors="replace")
                tiene_basic_auth = (
                    "basic-auth" in contenido.lower() or
                    "basicauth" in contenido.lower() or
                    "basic_auth" in contenido.lower()
                )
                hallazgos.append({
                    "check": "basic-auth en config/script",
                    "resultado": "CONFIGURADO" if tiene_basic_auth else "NO ENCONTRADO"
                })
                if not tiene_basic_auth:
                    alertas.append("El script o config de ngrok carece de --basic-auth")
            except Exception as e:
                hallazgos.append({"check": "Lectura de config", "resultado": f"Error: {e}"})

    runner_path = _APP_ROOT / "ngrok_runner.js"
    if runner_path.exists():
        try:
            contenido_runner = runner_path.read_text(encoding="utf-8", errors="replace")
            runner_tiene_auth = "basic-auth" in contenido_runner.lower()
            hallazgos.append({
                "check": "basic-auth en ngrok_runner.js",
                "resultado": "CONFIGURADO" if runner_tiene_auth else "NO ENCONTRADO"
            })
            if not runner_tiene_auth:
                alertas.append("ngrok_runner.js no implementa --basic-auth obligatoria.")
        except Exception:
            pass

    nivel = "OK"
    if alertas:
        nivel = "ALTO" if ngrok_activo else "MEDIO"

    return json.dumps({
        "status": "success",
        "ngrok_activo": ngrok_activo,
        "checks_realizados": hallazgos,
        "alertas": alertas,
        "nivel": nivel,
        "recomendacion": "Añadir --basic-auth='usuario:password' al invocar túneles ngrok." if alertas else "OK"
    }, ensure_ascii=False)


@tool
def verificar_auth_n8n(ruta_env: str = "") -> str:
    """
    Verifica que la instancia de n8n esté protegida con autenticación básica.
    Lee el archivo .env comprobando N8N_BASIC_AUTH_ACTIVE, N8N_BASIC_AUTH_USER y N8N_BASIC_AUTH_PASSWORD.
    """
    hallazgos = []
    alertas = []

    target_env = Path(ruta_env) if ruta_env else (_APP_ROOT / ".env")
    if not target_env.exists():
        return json.dumps({
            "status": "error",
            "mensaje": f"Archivo .env no encontrado en: {target_env}"
        }, ensure_ascii=False)

    try:
        contenido = target_env.read_text(encoding="utf-8", errors="replace")
        variables_n8n = {}

        for linea in contenido.splitlines():
            linea = linea.strip()
            if linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            if "N8N" in clave.upper():
                valor_mostrar = valor.strip()
                if "PASSWORD" in clave.upper() or "PASS" in clave.upper():
                    valor_mostrar = valor_mostrar[:3] + "***" if len(valor_mostrar) > 3 else "***"
                variables_n8n[clave] = valor_mostrar

        auth_activa = variables_n8n.get("N8N_BASIC_AUTH_ACTIVE", "").lower() in ("true", "1", "yes")
        tiene_usuario = bool(variables_n8n.get("N8N_BASIC_AUTH_USER", "").strip())
        tiene_password = bool(variables_n8n.get("N8N_BASIC_AUTH_PASSWORD", "").strip())

        hallazgos.append({"check": "N8N_BASIC_AUTH_ACTIVE", "valor": str(auth_activa), "ok": auth_activa})
        hallazgos.append({"check": "N8N_BASIC_AUTH_USER configurado", "valor": str(tiene_usuario), "ok": tiene_usuario})
        hallazgos.append({"check": "N8N_BASIC_AUTH_PASSWORD configurado", "valor": str(tiene_password), "ok": tiene_password})

        if not auth_activa:
            alertas.append("N8N_BASIC_AUTH_ACTIVE no está activo. La UI en :5678 es accesible sin contraseña.")
        if not tiene_usuario:
            alertas.append("N8N_BASIC_AUTH_USER no configurado.")
        if not tiene_password:
            alertas.append("N8N_BASIC_AUTH_PASSWORD no configurado.")

        nivel = "OK" if not alertas else ("ALTO" if not auth_activa else "MEDIO")

        return json.dumps({
            "status": "success",
            "archivo_env": str(target_env),
            "variables_n8n": variables_n8n,
            "checks": hallazgos,
            "alertas": alertas,
            "nivel": nivel
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def analizar_permisos_archivo(ruta_archivo: str) -> str:
    """
    Revisa los permisos de lectura, escritura y ejecución de un archivo sensible (.env, certificados, llaves).
    Detecta permisos excesivos o inseguros en entornos Linux/Docker o Windows.
    """
    try:
        p = Path(ruta_archivo)
        if not p.is_absolute():
            p = _APP_ROOT / ruta_archivo.lstrip("/\\")

        if not p.exists():
            return json.dumps({"status": "error", "mensaje": f"Archivo no encontrado: {ruta_archivo}"})

        stat_info = p.stat()
        modo = stat_info.st_mode
        es_inseguro = False
        alertas = []

        # En sistemas POSIX (Docker Linux), verificar si tiene escritura pública o lectura excesiva
        if hasattr(os, "stat"):
            perm_octal = oct(stat.S_IMODE(modo))
            if modo & stat.S_IWOTH:
                es_inseguro = True
                alertas.append("El archivo sensible tiene permisos de escritura pública (World Writable).")
            elif (modo & stat.S_IROTH) and perm_octal not in ["0o444", "0o400", "0o644", "0o600"]:
                es_inseguro = True
                alertas.append("El archivo sensible tiene permisos excesivos de lectura para otros usuarios.")
        else:
            perm_octal = "N/A (Windows)"

        nivel = "ALTO" if es_inseguro else "OK"

        return json.dumps({
            "status": "success",
            "archivo": str(p),
            "permisos_octal": perm_octal,
            "tamaño_bytes": stat_info.st_size,
            "es_inseguro": es_inseguro,
            "alertas": alertas,
            "nivel": nivel
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_ESCANEO = [
    ejecutar_pip_audit,
    ejecutar_npm_audit,
    verificar_puertos_locales,
    verificar_auth_ngrok,
    verificar_auth_n8n,
    analizar_permisos_archivo,
]
