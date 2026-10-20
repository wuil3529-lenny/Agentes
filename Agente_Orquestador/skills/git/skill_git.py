"""
skill_git.py — Gestión, Control de Versiones y Despliegue Git para Agente_Orquestador
====================================================================================
Permite al Agente Orquestador (Luffy) operar el repositorio Git con estándar profesional:
- Consultar estado del árbol de trabajo (git status).
- Visualizar diferencias (git diff y git diff --staged).
- Preparar cambios selectivamente (git add).
- Realizar commits con verificación obligatoria previa de seguridad (Pre-Commit Gate de Robin).
- Sincronizar con el repositorio remoto (git push y git pull).
- Consultar historial reciente (git log).
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Patrones estrictos de detección de fugas de seguridad (Pre-Commit Gate de Robin)
PATRONES_GATE_ROBIN = [
    (r'(?i)AIza[0-9A-Za-z-_]{35}', "Google API Key"),
    (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API Key"),
    (r'sk-proj-[a-zA-Z0-9_\-]{40,}', "OpenAI Project Key"),
    (r'sk-or-v1-[a-f0-9]{64}', "OpenRouter API Key"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Token (ghp)"),
    (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token (gho)"),
    (r'8615\d{6,}:[A-Za-z0-9_-]{30,}', "Telegram Bot Token"),
    (r'-{5}BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-{5}', "Clave Privada PEM/SSH"),
    (r'-{5}BEGIN CERTIFICATE-{5}', "Certificado Criptográfico PEM"),
    (r'\b[a-z]{4}\s+[a-z]{4}\s+[a-z]{4}\s+[a-z]{4}\b', "App Password Gmail (16 caracteres)"),
    (r'\b[A-Za-z0-9._%+-]+@(?:gmail|hotmail|yahoo|outlook)\.com\b', "Email Personal (PII no parametrizada)"),
]


def _ejecutar_git(args: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Ejecuta un comando de Git de forma controlada y segura."""
    directorio = cwd or str(_APP_ROOT)
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=directorio,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=40,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


@tool
def tool_git_status(directorio: str = "") -> dict:
    """
    Consulta el estado actual del árbol de trabajo de Git (archivos modificados, preparados y no rastreados).
    """
    code, stdout, stderr = _ejecutar_git(["status"], cwd=directorio or None)
    if code != 0:
        return {"status": "error", "mensaje": stderr or "Fallo al ejecutar git status"}
    return {
        "status": "success",
        "salida": stdout,
        "limpio": "nothing to commit, working tree clean" in stdout
    }


@tool
def tool_git_diff(en_staged: bool = False, archivo: str = "", directorio: str = "") -> dict:
    """
    Muestra las diferencias de los archivos modificados.
    - en_staged: si es True, muestra 'git diff --cached' (cambios preparados para commit).
    - archivo: ruta opcional para limitar el diff a un archivo específico.
    """
    args = ["diff"]
    if en_staged:
        args.append("--cached")
    if archivo:
        args.append(archivo)

    code, stdout, stderr = _ejecutar_git(args, cwd=directorio or None)
    if code != 0:
        return {"status": "error", "mensaje": stderr or "Fallo al ejecutar git diff"}
    
    lineas = stdout.splitlines()
    return {
        "status": "success",
        "en_staged": en_staged,
        "total_lineas": len(lineas),
        "extracto": "\n".join(lineas[:200]),
        "truncado": len(lineas) > 200
    }


@tool
def tool_git_add(archivos: list[str], directorio: str = "") -> dict:
    """
    Prepara archivos para el próximo commit ('git add').
    - archivos: lista de rutas relativas o nombres de archivo a preparar (ej. ['sistema/sistema.md']).
    """
    if not archivos:
        return {"status": "error", "mensaje": "Debe especificar al menos un archivo para git add."}

    args = ["add"] + archivos
    code, stdout, stderr = _ejecutar_git(args, cwd=directorio or None)
    if code != 0:
        return {"status": "error", "mensaje": stderr or "Error preparando archivos con git add"}

    return {"status": "success", "archivos_preparados": archivos, "mensaje": "Archivos preparados correctamente."}


@tool
def tool_git_commit(mensaje: str, forzar_sin_gate: bool = False, directorio: str = "") -> dict:
    """
    Crea un commit en el repositorio Git.
    INTEGRA EL GATE DE CIBERSEGURIDAD DE ROBIN:
    Antes de ejecutar el commit, escanea 'git diff --cached' buscando credenciales, tokens,
    claves privadas o datos de identidad expuestos. Si detecta alguna anomalía, ABORTA el commit
    para proteger el repositorio.
    - mensaje: mensaje descriptivo del commit (formato convencional, ej: 'feat(modulo): descripcion').
    - forzar_sin_gate: NUNCA recomendado, requiere autorización explícita del usuario.
    """
    if not mensaje or not mensaje.strip():
        return {"status": "error", "mensaje": "El mensaje de commit no puede estar vacío."}

    # 1. Ejecutar Gate de Seguridad de Robin sobre el diff staged
    if not forzar_sin_gate:
        code_diff, stdout_diff, _ = _ejecutar_git(["diff", "--cached"], cwd=directorio or None)
        if code_diff != 0 or not stdout_diff.strip():
            return {"status": "error", "mensaje": "No hay cambios preparados en staged para comitear (usa tool_git_add primero)."}

        hallazgos_gate = []
        for line in stdout_diff.splitlines():
            # Solo evaluamos líneas añadidas (+)
            if line.startswith("+") and not line.startswith("+++"):
                if "PATRONES_GATE_ROBIN" in line or "PATRONES_SECRETOS" in line or "r'-{5}BEGIN" in line or "App Password" in line or "Email Personal" in line:
                    continue
                for pat, tipo in PATRONES_GATE_ROBIN:
                    if re.search(pat, line):
                        hallazgos_gate.append({
                            "tipo": tipo,
                            "linea": line.strip()[:80]
                        })

        if hallazgos_gate:
            return {
                "status": "bloqueado_por_ciberseguridad",
                "mensaje": (
                    f"🛑 [GATE DE ROBIN ACTIVADO] Se abortó el commit porque se detectaron {len(hallazgos_gate)} "
                    f"posibles credenciales o datos sensibles en el diff preparado. Remedia los archivos antes de continuar."
                ),
                "hallazgos": hallazgos_gate[:5]
            }

    # 2. Ejecutar el Commit
    code_c, stdout_c, stderr_c = _ejecutar_git(["commit", "-m", mensaje.strip()], cwd=directorio or None)
    if code_c != 0:
        return {"status": "error", "mensaje": stderr_c or "Fallo al ejecutar git commit"}

    return {
        "status": "success",
        "mensaje_commit": mensaje.strip(),
        "salida": stdout_c,
        "gate_seguridad_robin": "APROBADO_LIMPIO"
    }


@tool
def tool_git_push(remoto: str = "origin", rama: str = "main", directorio: str = "") -> dict:
    """
    Envía los commits locales al repositorio remoto ('git push').
    - remoto: nombre del remoto (por defecto 'origin').
    - rama: rama de destino (por defecto 'main').
    """
    code, stdout, stderr = _ejecutar_git(["push", remoto, rama], cwd=directorio or None)
    if code != 0:
        return {"status": "error", "mensaje": stderr or "Fallo al ejecutar git push"}

    return {
        "status": "success",
        "remoto": remoto,
        "rama": rama,
        "salida": stdout or stderr or "Push completado con éxito."
    }


@tool
def tool_git_pull(remoto: str = "origin", rama: str = "main", directorio: str = "") -> dict:
    """
    Descarga y fusiona los cambios más recientes del repositorio remoto ('git pull').
    """
    code, stdout, stderr = _ejecutar_git(["pull", remoto, rama], cwd=directorio or None)
    if code != 0:
        return {"status": "error", "mensaje": stderr or "Fallo al ejecutar git pull"}

    return {
        "status": "success",
        "remoto": remoto,
        "rama": rama,
        "salida": stdout or "Pull completado con éxito."
    }


@tool
def tool_git_log(limite: int = 5, directorio: str = "") -> dict:
    """
    Muestra los últimos commits registrados en el historial de Git ('git log --oneline').
    - limite: cantidad de commits a mostrar (por defecto 5).
    """
    code, stdout, stderr = _ejecutar_git(["log", f"-n{limite}", "--oneline"], cwd=directorio or None)
    if code != 0:
        return {"status": "error", "mensaje": stderr or "Fallo al ejecutar git log"}

    commits = [line.strip() for line in stdout.splitlines() if line.strip()]
    return {
        "status": "success",
        "total_mostrados": len(commits),
        "commits": commits
    }


def obtener_prompt_git() -> str:
    """
    Retorna el System Prompt especializado para la habilidad de Git del Agente Orquestador.
    Lee dinámicamente el archivo Markdown cognitivo de la habilidad.
    """
    md_path = Path(__file__).resolve().parent / "Skill_Git_Agente_Orquestador.md"
    if md_path.exists():
        try:
            return md_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return """[🐙 DIRECTIVA OPERATIVA: GESTIÓN DE VERSIONES Y DESPLIEGUE GIT - AGENTE ORQUESTADOR]
Eres el Oficial de Control de Versiones y Despliegue Git de la Flota (Luffy).
Tu misión es gestionar el repositorio Git con rigor industrial:
1. INSPECCIÓN PREVIA: Siempre consulta `tool_git_status` y `tool_git_diff` antes de preparar cambios.
2. PREPARACIÓN SELECTIVA: Usa `tool_git_add` especificando únicamente los archivos modificados intencionalmente.
3. GATE DE CIBERSEGURIDAD DE ROBIN: Todo commit pasa automáticamente por la validación de Robin integrada en `tool_git_commit`. Si el gate detecta credenciales o tokens en el staged diff, el commit se abortará. NUNCA fuerces un commit con fallos de seguridad.
4. COMMITS CONVENCIONALES: Redacta mensajes claros siguiendo el estándar: 'feat(...)', 'fix(...)', 'docs(...)', 'refactor(...)'.
5. SINCRONIZACIÓN: Ejecuta `tool_git_push` únicamente tras confirmar commits limpios."""


HERRAMIENTAS_GIT = [
    tool_git_status,
    tool_git_diff,
    tool_git_add,
    tool_git_commit,
    tool_git_push,
    tool_git_pull,
    tool_git_log,
]
