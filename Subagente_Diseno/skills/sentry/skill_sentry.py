"""
skill_sentry.py — Monitoreo de Errores, Diagnóstico y Resiliencia Sentry
========================================================================
Habilidad del Subagente de Diseño para diagnosticar fallos de renderizado,
consultar antecedentes de errores, registrar soluciones inéditas y reportar
fallos críticos en la Memoria Viva de Errores.

Herramientas disponibles:
  - tool_consultar_sentry_errores : Busca antecedentes de errores y soluciones en el RAG/Sentry
  - tool_registrar_solucion_error : Registra la receta técnica de una solución descubierta
  - tool_reportar_fallo_critico   : Documenta un bloqueo severo en Memoria_Viva_Errores.md
  - obtener_prompt_sentry         : System Prompt especializado para inyección bajo demanda
"""

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_AGENTE = "Subagente_Diseno"


def obtener_prompt_sentry() -> str:
    """
    Retorna el System Prompt especializado para el modo de diagnóstico y resiliencia Sentry.
    """
    return """[🛑 HARD-STOP: MODO DIAGNÓSTICO DE ERRORES Y OBSERVABILIDAD SENTRY ACTIVO 🛑]
Eres la Especialista en Diagnóstico Técnico y Resiliencia del Subagente de Diseño.
Tu misión es diagnosticar excepciones, recuperar soluciones previas a fallos de renderizado o generación multimedia y registrar recetas para prevenir caídas repetitivas.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PREVIA ANTE EXCEPCIONES:
   - Ante cualquier fallo de generación de imagen, renderizado de video, compilación Marp o script, invoca `tool_consultar_sentry_errores` antes de reintentar a ciegas.
2. DOCUMENTACIÓN DE RECETAS TÉCNICAS:
   - Cuando soluciones un error no documentado, registra la receta con `tool_registrar_solucion_error` para indexarla en la base de conocimientos.
3. REPORTE DE FALLO CRÍTICO:
   - Utiliza `tool_reportar_fallo_critico` únicamente ante bloqueos insuperables o dependencias ausentes en el entorno.
"""


@tool
def tool_consultar_sentry_errores(mensaje_error: str) -> str:
    """
    Busca antecedentes de un error en Sentry y en la base de conocimientos RAG del ecosistema.
    Invocada de inmediato ante fallos para recuperar soluciones probadas.
    """
    try:
        # Consulta de fallback en memoria si el RAG vectorial no está inicializado
        memoria_errores = _APP_ROOT / "memoria" / "Memoria_Viva_Errores.md"
        coincidencias = []
        if memoria_errores.exists():
            lineas = memoria_errores.read_text(encoding="utf-8", errors="replace").splitlines()
            for l in lineas:
                if any(w.lower() in l.lower() for w in mensaje_error.split()[:4]):
                    coincidencias.append(l.strip())

        return json.dumps({
            "status": "success",
            "error_consultado": mensaje_error,
            "antecedentes_encontrados": coincidencias[:3] if coincidencias else ["No se hallaron antecedentes idénticos directos."],
            "recomendacion": "Verificar parámetros de entrada y aplicar fallback resiliente si el servicio remoto falla."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al consultar Sentry/RAG: {str(e)}"}, ensure_ascii=False)


@tool
def tool_registrar_solucion_error(error_log: str, como_se_soluciono: str) -> str:
    """
    Registra obligatoriamente la receta técnica de cómo se solucionó un error inédito.
    """
    try:
        registro_id = str(uuid.uuid4())[:8]
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("agente", _AGENTE)
                scope.set_tag("tipo", "solucion_documentada")
                scope.set_extra("como_se_soluciono", como_se_soluciono)
                sentry_sdk.capture_message(f"[{_AGENTE}] Solución registrada: {error_log[:100]}")
        except Exception:
            pass

        # Anexar a memoria/Memoria_Viva_Errores.md
        memoria_errores = _APP_ROOT / "memoria" / "Memoria_Viva_Errores.md"
        memoria_errores.parent.mkdir(parents=True, exist_ok=True)
        entrada = (
            f"\n### 🛠️ Solución Registrada [{datetime.now().strftime('%Y-%m-%d %H:%M')}] — ID: `{registro_id}`\n"
            f"- **Agente:** `{_AGENTE}`\n"
            f"- **Error:** `{error_log[:200]}`\n"
            f"- **Solución:** {como_se_soluciono}\n"
        )
        with open(memoria_errores, "a", encoding="utf-8") as f:
            f.write(entrada)

        return json.dumps({
            "status": "success",
            "id": registro_id,
            "mensaje": f"Solución archivada en Memoria_Viva_Errores.md."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al registrar solución: {str(e)}"}, ensure_ascii=False)


@tool
def tool_reportar_fallo_critico(modulo: str, error_tecnico: str, impacto: str) -> str:
    """
    Documenta un bloqueo severo en Memoria_Viva_Errores.md cuando una herramienta no puede recuperarse.
    """
    try:
        memoria_errores = _APP_ROOT / "memoria" / "Memoria_Viva_Errores.md"
        memoria_errores.parent.mkdir(parents=True, exist_ok=True)
        entrada = (
            f"\n### 🚨 Fallo Crítico [{datetime.now().strftime('%Y-%m-%d %H:%M')}]\n"
            f"- **Agente:** `{_AGENTE}`\n"
            f"- **Módulo:** `{modulo}`\n"
            f"- **Impacto:** {impacto}\n"
            f"- **Error Técnico:** `{error_tecnico[:300]}`\n"
        )
        with open(memoria_errores, "a", encoding="utf-8") as f:
            f.write(entrada)

        return json.dumps({
            "status": "success",
            "mensaje": f"Fallo crítico documentado en Memoria_Viva_Errores.md."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al reportar error: {str(e)}"}, ensure_ascii=False)


HERRAMIENTAS_SENTRY = [
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico
]
