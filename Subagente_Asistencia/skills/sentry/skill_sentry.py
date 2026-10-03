"""
skill_sentry.py — Monitoreo de Errores, Diagnóstico y Resiliencia Sentry
========================================================================
Habilidad del Subagente de Asistencia para auditar excepciones, buscar antecedentes
técnicos en Sentry y memoria vectorial (RAG), registrar recetas de hotfixes aprendidos
y reportar bloqueos críticos en la Memoria Viva de Errores.

Herramientas disponibles:
  - tool_consultar_sentry_errores : Busca antecedentes de errores y recetas previas en RAG/Sentry.
  - tool_registrar_solucion_error : Registra la receta técnica de una solución inédita descubierta.
  - tool_reportar_fallo_critico   : Documenta un bloqueo o bug recurrente en Memoria_Viva_Errores.md.
  - obtener_prompt_sentry         : System Prompt especializado para inyección bajo demanda.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

# Inicialización segura de Sentry SDK si está configurado en .env
try:
    import sentry_sdk
    dsn = os.getenv("SENTRY_DSN", "")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=1.0,
        )
except ImportError:
    pass

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["sanji", "subagente_asistencia"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Asistencia"


def obtener_prompt_sentry() -> str:
    """
    System Prompt especializado y encapsulado para el modo de diagnóstico y resiliencia Sentry.
    """
    return """[🛑 HARD-STOP: MODO DIAGNÓSTICO DE ERRORES Y OBSERVABILIDAD SENTRY ACTIVO 🛑]
Eres el Especialista en Diagnóstico Técnico y Resiliencia del Subagente de Asistencia.
Tu misión es monitorizar excepciones, recuperar soluciones técnicas previas y registrar fallos críticos para inmunizar el sistema mediante código.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PREVIA ANTE EXCEPCIONES:
   - Ante cualquier fallo de comando, sintaxis, API de Google o procesamiento de documentos, invoca de inmediato `tool_consultar_sentry_errores` antes de improvisar cambios a ciegas.
2. DOCUMENTACIÓN DE RECETAS TÉCNICAS:
   - Cuando soluciones un error no documentado o superes un bloqueo, registra la receta con `tool_registrar_solucion_error` para indexarla en la base de conocimiento RAG.
3. CRITERIO DE FALLO CRÍTICO:
   - Utiliza `tool_reportar_fallo_critico` ÚNICAMENTE ante bloqueos insuperables, tokens de API revocados o anomalías estructurales repetitivas.
   - Las advertencias o errores menores que se resuelven en el flujo normal deben ser corregidos en caliente y no registrarse como fallos críticos en `Memoria_Viva_Errores.md`.
"""


def _conectar_rag_vectorial():
    """
    Conecta de forma resiliente con la memoria vectorial del ecosistema.
    """
    try:
        memoria_path = _APP_ROOT / "Agente_Orquestador" / "skills" / "memoria_vectorial"
        if str(memoria_path) not in sys.path:
            sys.path.insert(0, str(memoria_path))
        from skill_memoria_vectorial import tool_buscar_soluciones, tool_guardar_solucion
        return tool_buscar_soluciones, tool_guardar_solucion
    except Exception as e:
        return None, None


@tool
def tool_consultar_sentry_errores(mensaje_error: str) -> str:
    """
    Busca antecedentes de un error específico en Sentry y en la base de conocimiento vectorial (RAG).
    Usa esta herramienta cuando una operación o llamada a API falle, para conocer cómo se solucionó antes.

    Args:
        mensaje_error: Texto crudo del error o excepción capturada.
    """
    if not mensaje_error or not mensaje_error.strip():
        return json.dumps({"status": "error", "mensaje": "Se requiere un mensaje de error para consultar."}, ensure_ascii=False)

    try:
        tool_buscar, _ = _conectar_rag_vectorial()
        resultados_rag = []
        if tool_buscar:
            try:
                res = tool_buscar.invoke({"query_semantica": mensaje_error.strip(), "n_resultados": 2})
                resultados_rag = json.loads(res) if isinstance(res, str) and res.startswith("[") or res.startswith("{") else res
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "origen": "SENTRY_RAG_DIAGNOSTICO",
            "error_consultado": mensaje_error[:120],
            "antecedentes_encontrados": resultados_rag if resultados_rag else "No se encontraron soluciones previas idénticas. Procede con análisis técnico."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_registrar_solucion_error(error_log: str, como_se_soluciono: str) -> str:
    """
    Registra formalmente la receta técnica de cómo se solucionó un error inédito.
    Ejecuta esto tras resolver un problema bloqueante para inmunizar al equipo ante fallos repetitivos.

    Args:
        error_log: El mensaje de error original que arrojó el sistema o API.
        como_se_soluciono: Explicación técnica de la corrección aplicada.
    """
    try:
        # Notificar a Sentry si está activo
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("solucion_aplicada", como_se_soluciono)
                sentry_sdk.capture_message(f"Solución Inédita: {error_log[:60]}...", level="info")
        except Exception:
            pass

        _, tool_guardar = _conectar_rag_vectorial()
        ticket_virtual = f"HOTFIX-ASIST-{str(uuid.uuid4())[:8].upper()}"
        contenido = f"ERROR ORIGINAL:\n{error_log}\n\nSOLUCIÓN APLICADA:\n{como_se_soluciono}"

        if tool_guardar:
            try:
                tool_guardar.invoke({
                    "ticket_id": ticket_virtual,
                    "descripcion": "Resolución de error técnico en Subagente de Asistencia",
                    "contenido": contenido
                })
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "ticket": ticket_virtual,
            "mensaje": "Receta técnica registrada en Sentry y archivada en la base de conocimientos."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_reportar_fallo_critico(modulo_afectado: str, error_log: str, descripcion_bloqueo: str) -> str:
    """
    Documenta un fallo crítico o bloqueo insuperable en la Memoria Viva de Errores (Memoria_Viva_Errores.md).
    Úsalo ÚNICAMENTE ante bloqueos graves donde no puedas continuar sin intervención humana o del Orquestador.

    Args:
        modulo_afectado: Nombre del script o módulo con fallo (ej: 'skill_inbox.py', 'google_api').
        error_log: Mensaje o traza del fallo.
        descripcion_bloqueo: Explicación del bloqueo y acciones recomendadas.
    """
    try:
        ruta_errores = _APP_ROOT / "Memoria_Viva_Errores.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bloque = f"""
### [CRÍTICO - {timestamp}] Fallo en {modulo_afectado} (Subagente_Asistencia)
- **Módulo:** `{modulo_afectado}`
- **Descripción:** {descripcion_bloqueo}
- **Log / Excepción:**
```text
{error_log.strip()}
```
- **Estado:** Pendiente de revisión por Agente Orquestador.
---
"""
        if ruta_errores.exists():
            contenido_actual = ruta_errores.read_text(encoding="utf-8")
            ruta_errores.write_text(contenido_actual + "\n" + bloque, encoding="utf-8")
        else:
            ruta_errores.write_text("# Memoria Viva de Errores\n" + bloque, encoding="utf-8")

        return json.dumps({
            "status": "success",
            "mensaje": f"Fallo crítico registrado exitosamente en {ruta_errores.name} para revisión del Orquestador."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"No se pudo registrar fallo crítico: {str(e)}"}, ensure_ascii=False)


# Alias de compatibilidad histórica
consultar_sentry_errores = tool_consultar_sentry_errores
registrar_solucion_error = tool_registrar_solucion_error

HERRAMIENTAS_SENTRY = [
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
]

__all__ = [
    "tool_consultar_sentry_errores",
    "tool_registrar_solucion_error",
    "tool_reportar_fallo_critico",
    "consultar_sentry_errores",
    "registrar_solucion_error",
    "HERRAMIENTAS_SENTRY",
    "obtener_prompt_sentry",
]
