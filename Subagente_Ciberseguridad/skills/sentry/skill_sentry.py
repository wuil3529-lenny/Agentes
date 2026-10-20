"""
skill_sentry.py — Monitoreo de Errores, Diagnóstico y Resiliencia Sentry
========================================================================
Habilidad del Subagente de Ciberseguridad para auditar excepciones, buscar antecedentes
técnicos en Sentry y memoria vectorial (RAG), registrar recetas de hotfixes aprendidos
y documentar fallos críticos en la Memoria Viva de Errores.

Herramientas disponibles:
  - tool_consultar_sentry_errores : Busca antecedentes de errores y recetas previas en RAG/Sentry
  - tool_registrar_solucion_error : Registra la receta técnica de una solución inédita descubierta
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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["robin", "subagente_ciberseguridad"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Ciberseguridad"


def obtener_prompt_sentry() -> str:
    """
    System Prompt especializado y encapsulado para el modo de diagnóstico y resiliencia Sentry.
    """
    return """[🛑 HARD-STOP: MODO DIAGNÓSTICO DE ERRORES Y OBSERVABILIDAD SENTRY ACTIVO 🛑]
Eres el Especialista en Diagnóstico Técnico y Resiliencia del Subagente de Ciberseguridad.
Tu misión es monitorizar excepciones, recuperar soluciones técnicas previas y registrar fallos críticos para inmunizar el sistema mediante código.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PREVIA ANTE EXCEPCIONES:
   - Ante cualquier fallo de comando, sintaxis, escáner de red o script de auditoría, invoca de inmediato `tool_consultar_sentry_errores` antes de improvisar cambios a ciegas.
2. DOCUMENTACIÓN DE RECETAS TÉCNICAS:
   - Cuando soluciones un error no documentado o superes un bloqueo, registra la receta con `tool_registrar_solucion_error` para indexarla en la base de conocimiento RAG.
3. CRITERIO DE FALLO CRÍTICO:
   - Utiliza `tool_reportar_fallo_critico` ÚNICAMENTE ante bloqueos insuperables, dependencias rotas del sistema o excepciones recurrentes que impidan auditar.
"""


def _conectar_rag_vectorial():
    """Conecta de forma resiliente con la memoria vectorial del ecosistema."""
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
    Busca antecedentes de un error específico en Sentry y en la base de conocimientos RAG (ChromaDB).
    Usa esta herramienta DE INMEDIATO cuando un escaneo, comando o script falle.
    """
    print(f"\n[Sentry - Ciberseguridad] Consultando antecedentes para: {mensaje_error[:80]}...")
    try:
        tool_buscar, _ = _conectar_rag_vectorial()
        antecedentes_rag = []
        if tool_buscar:
            try:
                res_rag = tool_buscar.invoke({"query_semantica": mensaje_error, "n_resultados": 2})
                if isinstance(res_rag, str):
                    try:
                        antecedentes_rag = json.loads(res_rag)
                    except Exception:
                        antecedentes_rag = [{"texto": res_rag}]
            except Exception as e:
                print(f"[Sentry RAG Error] {e}")

        # Buscar también en Memoria_Viva_Errores.md
        memoria_viva_path = _APP_ROOT / "memoria" / "Memoria_Viva_Errores.md"
        coincidencias_viva = []
        if memoria_viva_path.exists():
            try:
                contenido_viva = memoria_viva_path.read_text(encoding="utf-8", errors="replace")
                palabras_clave = [p.lower() for p in mensaje_error.split() if len(p) > 4]
                bloques = contenido_viva.split("### Error:")
                for b in bloques[1:]:
                    b_lower = b.lower()
                    if any(kw in b_lower for kw in palabras_clave):
                        coincidencias_viva.append(b.strip()[:600])
            except Exception:
                pass

        return json.dumps({
            "status": "success",
            "origen": "RAG_SENTRY_SYNC",
            "resultados_rag": antecedentes_rag,
            "coincidencias_memoria_viva": coincidencias_viva[:2]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_registrar_solucion_error(error_log: str, como_se_soluciono: str) -> str:
    """
    Registra la receta técnica de cómo se solucionó un error inédito.
    Indexa la solución en ChromaDB para inmunizar a toda la tripulación.
    """
    print(f"\n[Sentry - Ciberseguridad] Registrando solución para: {error_log[:60]}...")
    try:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("agente", _AGENTE)
                scope.set_extra("solucion_aplicada", como_se_soluciono)
                sentry_sdk.capture_message(f"Solución registrada: {error_log[:100]}", level="info")
        except Exception:
            pass

        _, tool_guardar = _conectar_rag_vectorial()
        rag_guardado = False
        if tool_guardar:
            try:
                res = tool_guardar.invoke({
                    "tema": "Inmunización de Ciberseguridad",
                    "problema": error_log,
                    "solucion": como_se_soluciono
                })
                rag_guardado = True
            except Exception as e:
                print(f"[Sentry Guardar RAG Error] {e}")

        # Guardar en memoria/Memoria_Viva_Errores.md
        memoria_viva_path = _APP_ROOT / "memoria" / "Memoria_Viva_Errores.md"
        memoria_viva_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        registro_md = f"\n\n### Error: {error_log[:120]}\n"
        registro_md += f"- **Fecha:** {timestamp}\n"
        registro_md += f"- **Agente:** {_AGENTE}\n"
        registro_md += f"- **Solución Aplicada:** {como_se_soluciono}\n"
        registro_md += f"- **Estado:** INMUNIZADO POR CÓDIGO\n"

        with open(memoria_viva_path, "a", encoding="utf-8") as f:
            f.write(registro_md)

        return json.dumps({
            "status": "success",
            "mensaje": "Solución registrada e indexada en RAG y Memoria Viva.",
            "rag_guardado": rag_guardado
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_reportar_fallo_critico(modulo: str, error: str, traceback_str: str = "") -> str:
    """
    Reporta un fallo crítico insuperable en Memoria_Viva_Errores.md y emite telemetría Sentry.
    """
    try:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("agente", _AGENTE)
                scope.set_tag("modulo", modulo)
                scope.set_extra("traceback", traceback_str)
                sentry_sdk.capture_exception(Exception(f"[{modulo}] {error}"))
        except Exception:
            pass

        memoria_viva_path = _APP_ROOT / "memoria" / "Memoria_Viva_Errores.md"
        memoria_viva_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        registro_md = f"\n\n### 🚨 FALLO CRÍTICO: [{modulo}] {error[:120]}\n"
        registro_md += f"- **Fecha:** {timestamp}\n"
        registro_md += f"- **Agente:** {_AGENTE}\n"
        registro_md += f"- **Traceback:** `{traceback_str[:300]}`\n"
        registro_md += f"- **Estado:** BLOQUEO REGISTRADO\n"

        with open(memoria_viva_path, "a", encoding="utf-8") as f:
            f.write(registro_md)

        return json.dumps({
            "status": "success",
            "mensaje": f"Fallo crítico reportado en Memoria_Viva_Errores.md para [{modulo}]."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_SENTRY = [
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
]
