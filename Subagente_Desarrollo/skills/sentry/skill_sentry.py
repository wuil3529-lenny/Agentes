"""
skill_sentry.py — Monitoreo de Errores, Diagnóstico y Resiliencia Sentry
========================================================================
Habilidad del Subagente de Desarrollo para auditar excepciones, buscar antecedentes
técnicos en Sentry y memoria vectorial (RAG ChromaDB), registrar recetas de hotfixes
y reportar bloqueos críticos.

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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"


def obtener_prompt_sentry() -> str:
    """
    System Prompt especializado y encapsulado para el modo de diagnóstico y resiliencia Sentry.
    """
    return """[🛑 HARD-STOP: MODO DIAGNÓSTICO DE ERRORES Y OBSERVABILIDAD SENTRY ACTIVO 🛑]
Eres el Especialista en Diagnóstico Técnico y Resiliencia del Subagente de Desarrollo.
Tu misión es monitorizar excepciones, recuperar soluciones técnicas previas y registrar fallos críticos para inmunizar el sistema mediante código.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PREVIA ANTE EXCEPCIONES:
   - Ante cualquier fallo de compilación, script, API, dependencias o tooling, invoca de inmediato `tool_consultar_sentry_errores` antes de improvisar cambios a ciegas.
2. DOCUMENTACIÓN DE RECETAS TÉCNICAS:
   - Cuando soluciones un error no documentado o superes un bloqueo, registra la receta con `tool_registrar_solucion_error` para indexarla en la base de conocimiento vectorial RAG.
3. CRITERIO DE FALLO CRÍTICO:
   - Utiliza `tool_reportar_fallo_critico` ÚNICAMENTE ante bloqueos insuperables o anomalías estructurales repetitivas.
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
    except Exception:
        return None, None


@tool
def tool_consultar_sentry_errores(mensaje_error: str) -> str:
    """
    Busca antecedentes de un error específico en Sentry y en la base de conocimiento vectorial (RAG).
    Usa esta herramienta cuando una operación o comando falle, para conocer cómo se solucionó antes.

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
                resultados_rag = json.loads(res) if isinstance(res, str) and (res.startswith("[") or res.startswith("{")) else res
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "origen": "SENTRY_RAG_DIAGNOSTICO",
            "error_consultado": mensaje_error[:150],
            "antecedentes_encontrados": resultados_rag if resultados_rag else "No se encontraron soluciones previas idénticas. Procede con análisis técnico."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_registrar_solucion_error(error_log: str, como_se_soluciono: str) -> str:
    """
    Registra la receta técnica de cómo se solucionó un error inédito para indexarlo en el Cerebro RAG.

    Args:
        error_log: El mensaje de error crudo que arrojó el sistema.
        como_se_soluciono: La explicación técnica exacta de los pasos aplicados para corregirlo.
    """
    if not error_log or not como_se_soluciono:
        return json.dumps({"status": "error", "mensaje": "Debes proporcionar tanto el error_log como la explicación en como_se_soluciono."}, ensure_ascii=False)

    try:
        solucion_id = f"SOL-{_AGENTE}-{uuid.uuid4().hex[:8].upper()}"
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        _, tool_guardar = _conectar_rag_vectorial()
        rag_guardado = False
        if tool_guardar:
            try:
                res = tool_guardar.invoke({
                    "id_error": solucion_id,
                    "descripcion_problema": error_log.strip(),
                    "solucion": como_se_soluciono.strip()
                })
                rag_guardado = True
            except Exception:
                pass

        # Notificar a Sentry SDK si está inicializado
        try:
            import sentry_sdk
            if sentry_sdk.Hub.current.client:
                sentry_sdk.capture_message(f"[{_AGENTE} Solución Registrada] {error_log[:80]}: {como_se_soluciono[:120]}", level="info")
        except Exception:
            pass

        return json.dumps({
            "status": "success",
            "solucion_id": solucion_id,
            "indexado_rag": rag_guardado,
            "fecha": fecha_str,
            "mensaje": f"Receta registrada exitosamente en la base de conocimientos RAG ({solucion_id})."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_reportar_fallo_critico(mensaje_fallo: str, detalles_tecnicos: str) -> str:
    """
    Registra un fallo crítico o bloqueo insuperable en la Memoria Viva de Errores y envía alerta a Sentry.

    Args:
        mensaje_fallo: Título sintético del fallo crítico.
        detalles_tecnicos: Trazas de error completas, comandos fallidos y diagnóstico.
    """
    try:
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_id = f"ERR-CRIT-{_AGENTE}-{uuid.uuid4().hex[:6].upper()}"

        try:
            import sentry_sdk
            if sentry_sdk.Hub.current.client:
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("agente", _AGENTE)
                    scope.set_extra("detalles", detalles_tecnicos)
                    sentry_sdk.capture_message(f"[{_AGENTE} CRÍTICO] {mensaje_fallo}", level="error")
        except Exception:
            pass

        # Registrar en Memoria_Viva_Errores.md
        memoria_errores_file = _APP_ROOT / "contexto" / "Memoria_Viva_Errores.md"
        if not memoria_errores_file.exists():
            memoria_errores_file = _APP_ROOT / "Memoria_Viva_Errores.md"

        entrada_md = f"\n\n### [{fecha_str}] {error_id}: {mensaje_fallo}\n- **Agente:** {_AGENTE}\n- **Detalles:**\n```\n{detalles_tecnicos.strip()[:1500]}\n```\n"

        if memoria_errores_file.exists():
            with open(memoria_errores_file, "a", encoding="utf-8") as f:
                f.write(entrada_md)

        return json.dumps({
            "status": "success",
            "error_id": error_id,
            "mensaje": f"Fallo crítico registrado formalmente bajo identificador {error_id}."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


# Aliases de compatibilidad
consultar_sentry_errores = tool_consultar_sentry_errores
registrar_solucion_error = tool_registrar_solucion_error

HERRAMIENTAS_SENTRY = [
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico
]
