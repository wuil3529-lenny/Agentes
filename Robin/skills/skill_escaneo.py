"""
skill_escaneo.py — Habilidades de Escaneo Activo (Robin)
=========================================================
Herramientas para ejecutar comandos de auditoría de seguridad
sobre el ecosistema de agentes.

Herramientas disponibles:
  - ejecutar_pip_audit         : Escanear dependencias Python con CVEs conocidas
  - ejecutar_npm_audit         : Escanear dependencias Node.js con CVEs conocidas
  - verificar_puertos_locales  : Comprobar qué puertos están en escucha
  - verificar_auth_ngrok       : Detectar si ngrok corre sin autenticación
  - verificar_auth_n8n         : Comprobar configuración de seguridad de n8n
  - analizar_permisos_archivo  : Revisar permisos de archivos críticos
"""

import json
import subprocess
from pathlib import Path
from langchain_core.tools import tool


def _ejecutar_comando_seguro(comando: str, directorio: str = None, timeout: int = 60) -> dict:
    """Helper interno para ejecutar comandos de forma segura."""
    try:
        kwargs = {
            "shell": True,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "encoding": "utf-8",
            "errors": "replace"
        }
        if directorio:
            kwargs["cwd"] = directorio

        resultado = subprocess.run(comando, **kwargs)
        return {
            "exitcode": resultado.returncode,
            "stdout": resultado.stdout[:3000] if resultado.stdout else "",
            "stderr": resultado.stderr[:1500] if resultado.stderr else "",
            "ok": resultado.returncode == 0
        }
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
    con vulnerabilidades conocidas (CVEs). Requiere que pip-audit esté instalado.
    Si no está instalado, lo instala automáticamente.

    Args:
        directorio_proyecto: Ruta del proyecto Python a auditar.
    """
    # Verificar si pip-audit está disponible (usar módulo para evitar problemas de PATH en Windows)
    check = _ejecutar_comando_seguro("python -m pip_audit --version")
    if not check["ok"]:
        # Intentar instalarlo
        install = _ejecutar_comando_seguro("pip install pip-audit --quiet", timeout=90)
        if not install["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": "No se pudo instalar pip-audit. Instálalo manualmente: pip install pip-audit",
                "stderr": install["stderr"]
            })

    # Buscar requirements.txt en el proyecto
    ruta = Path(directorio_proyecto)
    req_file = ruta / "requirements.txt"

    if req_file.exists():
        cmd = f'python -m pip_audit -r "{req_file}" --format json'
    else:
        # Auditar el entorno actual
        cmd = "python -m pip_audit --format json"

    resultado = _ejecutar_comando_seguro(cmd, directorio=directorio_proyecto, timeout=120)

    # Parsear salida JSON de pip-audit
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
        "directorio": directorio_proyecto,
        "requirements_encontrado": req_file.exists(),
        "total_vulnerabilidades": len(vulnerabilidades),
        "nivel": nivel,
        "vulnerabilidades": vulnerabilidades[:20],
        "stderr": resultado["stderr"][:500] if resultado["stderr"] else ""
    }, ensure_ascii=False)


@tool
def ejecutar_npm_audit(directorio_proyecto: str) -> str:
    """
    Ejecuta npm audit en un proyecto Node.js para detectar dependencias
    con vulnerabilidades conocidas (CVEs).

    Args:
        directorio_proyecto: Ruta del proyecto Node.js que contiene package.json.
    """
    ruta = Path(directorio_proyecto)
    package_json = ruta / "package.json"

    if not package_json.exists():
        return json.dumps({
            "status": "error",
            "mensaje": f"No se encontró package.json en: {directorio_proyecto}"
        })

    resultado = _ejecutar_comando_seguro(
        "npm audit --json",
        directorio=directorio_proyecto,
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
        "directorio": directorio_proyecto,
        "resumen_vulnerabilidades": vulnerabilidades_resumen,
        "total_vulnerabilidades": total,
        "nivel": nivel,
        "salida_raw": resultado["stdout"][:1500] if resultado["stdout"] else "",
        "stderr": resultado["stderr"][:500] if resultado["stderr"] else ""
    }, ensure_ascii=False)


@tool
def verificar_puertos_locales() -> str:
    """
    Verifica qué puertos locales están actualmente en escucha.
    Detecta exposiciones de n8n (5678), Ollama (11434), ngrok, y otros servicios
    que podrían representar un riesgo si están accesibles desde la red.
    """
    resultado = _ejecutar_comando_seguro("netstat -an", timeout=15)

    puertos_criticos = {
        "5678": {"servicio": "n8n UI", "riesgo": "Workflows y credenciales expuestos si sin auth"},
        "11434": {"servicio": "Ollama API", "riesgo": "API de LLM sin restricción puede ser abusada"},
        "4040": {"servicio": "ngrok Inspector UI", "riesgo": "UI de inspección de ngrok accesible"},
        "3000": {"servicio": "App genérica / n8n alternativo", "riesgo": "Verificar qué servicio corre aquí"},
        "8080": {"servicio": "Servidor web genérico", "riesgo": "Verificar exposición"},
        "22": {"servicio": "SSH", "riesgo": "Acceso remoto — verificar configuración"},
    }

    puertos_activos = []
    alertas = []

    if resultado["stdout"]:
        lineas = resultado["stdout"].splitlines()
        for linea in lineas:
            if "LISTEN" in linea or "LISTENING" in linea:
                for puerto, info in puertos_criticos.items():
                    if f":{puerto}" in linea or f".{puerto}" in linea:
                        entrada = {
                            "puerto": puerto,
                            "servicio": info["servicio"],
                            "riesgo": info["riesgo"],
                            "linea": linea.strip()[:100]
                        }
                        puertos_activos.append(entrada)
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
        "nota": "Esta herramienta solo evalúa puertos de servicios conocidos del ecosistema."
    }, ensure_ascii=False)


@tool
def verificar_auth_ngrok(ruta_config_o_proceso: str = "") -> str:
    """
    Verifica si ngrok está corriendo con autenticación básica configurada.
    Revisa el archivo de configuración de ngrok, procesos activos y
    el archivo runner de ngrok del sistema.

    Args:
        ruta_config_o_proceso: Ruta opcional al archivo de configuración de ngrok
                               o al script que lo lanza (ej: ngrok_runner.js).
    """
    alertas = []
    hallazgos = []

    # 1. Verificar proceso ngrok activo
    proc = _ejecutar_comando_seguro("tasklist /FI \"IMAGENAME eq ngrok.exe\"", timeout=10)
    ngrok_activo = "ngrok.exe" in proc["stdout"]
    hallazgos.append({"check": "Proceso ngrok activo", "resultado": "SÍ" if ngrok_activo else "NO"})

    # 2. Leer archivo de config/script si se provee
    tiene_basic_auth = False
    if ruta_config_o_proceso:
        ruta = Path(ruta_config_o_proceso)
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
                    alertas.append("El script/config de ngrok no tiene --basic-auth configurado")
            except Exception as e:
                hallazgos.append({"check": "Lectura de config", "resultado": f"Error: {e}"})

    # 3. Verificar ngrok_runner.js del sistema
    runner_path = Path("/app/ngrok_runner.js")
    if runner_path.exists():
        try:
            contenido_runner = runner_path.read_text(encoding="utf-8", errors="replace")
            runner_tiene_auth = "basic-auth" in contenido_runner.lower()
            hallazgos.append({
                "check": "basic-auth en ngrok_runner.js del sistema",
                "resultado": "CONFIGURADO" if runner_tiene_auth else "NO ENCONTRADO"
            })
            if not runner_tiene_auth:
                alertas.append(
                    "ngrok_runner.js del sistema NO tiene --basic-auth. "
                    "El webhook de Nami podría estar expuesto públicamente sin protección."
                )
                tiene_basic_auth = False
        except Exception:
            pass

    nivel = "OK"
    if alertas:
        nivel = "ALTO" if ngrok_activo else "MEDIO"

    recomendacion = (
        "Añadir --basic-auth='usuario:password_segura' al comando ngrok. "
        "Ejemplo: ngrok http 5678 --basic-auth='robin:Str0ngP@ss!'"
        if alertas else "Configuración de ngrok correcta."
    )

    return json.dumps({
        "status": "success",
        "ngrok_activo": ngrok_activo,
        "checks_realizados": hallazgos,
        "alertas": alertas,
        "nivel": nivel,
        "recomendacion": recomendacion
    }, ensure_ascii=False)


@tool
def verificar_auth_n8n(ruta_env: str = "/app/.env") -> str:
    """
    Verifica que n8n esté configurado con autenticación básica.
    Lee el archivo .env del sistema para comprobar las variables
    N8N_BASIC_AUTH_ACTIVE, N8N_BASIC_AUTH_USER y N8N_BASIC_AUTH_PASSWORD.

    Args:
        ruta_env: Ruta al archivo .env del sistema (por defecto el del ecosistema).
    """
    hallazgos = []
    alertas = []

    ruta = Path(ruta_env)
    if not ruta.exists():
        return json.dumps({
            "status": "error",
            "mensaje": f"Archivo .env no encontrado en: {ruta_env}"
        })

    try:
        contenido = ruta.read_text(encoding="utf-8", errors="replace")
        lineas = contenido.splitlines()
        variables_n8n = {}

        for linea in lineas:
            linea = linea.strip()
            if linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            if "N8N" in clave.upper():
                # Enmascarar contraseñas
                valor_mostrar = valor.strip()
                if "PASSWORD" in clave.upper() or "PASS" in clave.upper():
                    valor_mostrar = valor_mostrar[:3] + "***" if len(valor_mostrar) > 3 else "***"
                variables_n8n[clave] = valor_mostrar

        # Verificar variables críticas
        auth_activa = variables_n8n.get("N8N_BASIC_AUTH_ACTIVE", "").lower() in ("true", "1", "yes")
        tiene_usuario = bool(variables_n8n.get("N8N_BASIC_AUTH_USER", "").strip())
        tiene_password = bool(variables_n8n.get("N8N_BASIC_AUTH_PASSWORD", "").strip())

        hallazgos.append({"check": "N8N_BASIC_AUTH_ACTIVE", "valor": str(auth_activa), "ok": auth_activa})
        hallazgos.append({"check": "N8N_BASIC_AUTH_USER configurado", "valor": str(tiene_usuario), "ok": tiene_usuario})
        hallazgos.append({"check": "N8N_BASIC_AUTH_PASSWORD configurado", "valor": str(tiene_password), "ok": tiene_password})

        if not auth_activa:
            alertas.append("N8N_BASIC_AUTH_ACTIVE no está en 'true'. La UI de n8n en :5678 es accesible sin contraseña.")
        if not tiene_usuario:
            alertas.append("N8N_BASIC_AUTH_USER no está configurado.")
        if not tiene_password:
            alertas.append("N8N_BASIC_AUTH_PASSWORD no está configurado.")

        nivel = "OK" if not alertas else ("ALTO" if not auth_activa else "MEDIO")

        return json.dumps({
            "status": "success",
            "archivo_env": str(ruta),
            "variables_n8n_encontradas": variables_n8n,
            "checks": hallazgos,
            "alertas": alertas,
            "nivel": nivel,
            "recomendacion": (
                "Añadir al .env:\n"
                "N8N_BASIC_AUTH_ACTIVE=true\n"
                "N8N_BASIC_AUTH_USER=admin\n"
                "N8N_BASIC_AUTH_PASSWORD=TuPasswordSegura123!"
                if alertas else "Configuración de n8n correcta."
            )
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas exportadas
HERRAMIENTAS_ESCANEO = [
    ejecutar_pip_audit,
    ejecutar_npm_audit,
    verificar_puertos_locales,
    verificar_auth_ngrok,
    verificar_auth_n8n,
]
