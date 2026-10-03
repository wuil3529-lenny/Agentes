"""
skill_sentry.py — Monitoreo de Errores, Telemetría y Fallos Críticos
===================================================================
Habilidad del Agente Orquestador para auditar excepciones, buscar antecedentes
en Sentry y memoria vectorial (RAG), registrar recetas técnicas de hotfixes
y documentar fallos críticos en la Memoria Viva de Errores.
"""

import os
import sys
import json
import uuid
import datetime
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

# Inicialización segura de Sentry SDK si está disponible
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


def _obtener_raiz_proyecto() -> Path:
    """Encuentra la raíz del proyecto tanto en entorno local como en contenedor Docker."""
    actual = Path(__file__).resolve()
    for parent in actual.parents:
        if (parent / "Bitacora.md").exists() or (parent / "Agente_Orquestador").exists():
            return parent
    if Path("/app/Bitacora.md").exists():
        return Path("/app")
    return actual.parents[2]


def obtener_prompt_sentry() -> str:
    """
    System Prompt especializado y encapsulado para el modo de monitoreo
    de errores, observabilidad y resiliencia.
    """
    return """[🛑 HARD-STOP: MODO MONITOREO DE ERRORES Y OBSERVABILIDAD SENTRY ACTIVO 🛑]
Eres el Ingeniero de Observabilidad, Diagnóstico y Resiliencia del Agente Orquestador.
Tu misión es monitorizar excepciones, recuperar soluciones previas probadas y registrar fallos críticos para inmunizar el sistema mediante código.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA PREVIA ANTE EXCEPCIONES:
   - Ante cualquier fallo de comando, sintaxis o ejecución de API, invoca de inmediato `tool_consultar_sentry_errores` antes de improvisar parches a ciegas.
2. DOCUMENTACIÓN DE HOTFIXES (APRENDIZAJE CONTINUO):
   - Cuando soluciones un error no documentado, registra la receta técnica con `tool_registrar_solucion_error` para indexarla en la memoria vectorial (ChromaDB) y en Sentry.
3. CRITERIO ESTRICTO DE FALLO CRÍTICO:
   - Usa `tool_reportar_fallo_critico` ÚNICAMENTE ante bloqueos estructurales, bucles redundantes o rechazos triples de un auditor.
   - Los fallos menores o advertencias deben ser corregidos en caliente y no registrarse como fallos críticos en `Memoria_Viva_Errores.md`.
"""


@tool
def tool_consultar_sentry_errores(mensaje_error: str) -> str:
    """
    Busca antecedentes de un error específico en Sentry y en la base de conocimientos RAG.
    Usa esta herramienta de INMEDIATO cuando un comando o código falle, para ver cómo se solucionó antes.

    Args:
        mensaje_error: Mensaje de error, excepción o traza técnica ocurrida.
    """
    print(f"\n[Sentry] Consultando antecedentes para el error...")
    try:
        raiz = _obtener_raiz_proyecto()
        skills_path = raiz / "Agente_Orquestador" / "skills"
        if str(skills_path) not in sys.path:
            sys.path.insert(0, str(skills_path))

        from memoria_vectorial.skill_memoria_vectorial import tool_buscar_soluciones

        # Consultar soluciones similares en la memoria vectorial
        rag_result = tool_buscar_soluciones.invoke({
            "query_semantica": mensaje_error,
            "n_resultados": 2
        })

        try:
            resultados_parsed = json.loads(rag_result)
        except Exception:
            resultados_parsed = rag_result

        return json.dumps({
            "status": "success",
            "origen": "RAG_SENTRY_SYNC",
            "resultados_previos": resultados_parsed
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_registrar_solucion_error(error_log: str, como_se_soluciono: str) -> str:
    """
    Registra la receta técnica de cómo se solucionó un error inédito.
    Ejecuta esta herramienta en cuanto logres sobrepasar un obstáculo técnico para persistir la solución.

    Args:
        error_log: Mensaje de error crudo o excepción que arrojó el sistema.
        como_se_soluciono: Explicación técnica exacta y reproducible de qué se hizo para corregirlo.
    """
    print(f"\n[Sentry] Registrando solución técnica inédita...")
    try:
        # Enviar evento a Sentry SDK si está configurado
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("solucion_aplicada", como_se_soluciono)
                sentry_sdk.capture_message(f"Solucion Inedita Descubierta: {error_log[:60]}...", level="info")
        except Exception:
            pass

        raiz = _obtener_raiz_proyecto()
        skills_path = raiz / "Agente_Orquestador" / "skills"
        if str(skills_path) not in sys.path:
            sys.path.insert(0, str(skills_path))

        from memoria_vectorial.skill_memoria_vectorial import tool_guardar_solucion

        ticket_virtual = f"HOTFIX-{str(uuid.uuid4())[:8].upper()}"
        contenido = f"ERROR ORIGINAL:\n{error_log}\n\nSOLUCION APLICADA:\n{como_se_soluciono}"

        tool_guardar_solucion.invoke({
            "ticket_id": ticket_virtual,
            "descripcion": f"Hotfix - Resolución de error: {error_log[:50]}",
            "contenido": contenido,
            "evidencia_fisica": "N/A"
        })

        return json.dumps({
            "status": "success",
            "mensaje": f"Solución registrada exitosamente con ticket virtual {ticket_virtual} e indexada en ChromaDB."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


@tool
def tool_reportar_fallo_critico(titulo_fallo: str, contexto_agente: str) -> str:
    """
    Reporta un bloqueo severo o fallo crítico en la Memoria Viva de Errores.
    Usa esta herramienta EXCLUSIVAMENTE cuando un subagente colapse, falle repetitivamente,
    o cuando un auditor rechace su trabajo 3 veces.

    Args:
        titulo_fallo: Título descriptivo y concreto de la falla (ej: 'Subagente_Desarrollo: 3 rechazos en TKT-001').
        contexto_agente: Explicación técnica detallada de la causa raíz y las evidencias encontradas.
    """
    print(f"\n[Sentry] 🛑 Reportando fallo crítico a Memoria_Viva_Errores.md...")
    try:
        raiz = _obtener_raiz_proyecto()
        memoria_errores_path = raiz / "memoria" / "Memoria_Viva_Errores.md"

        if not memoria_errores_path.exists():
            return "Error: memoria/Memoria_Viva_Errores.md no existe en el proyecto."

        contenido = memoria_errores_path.read_text(encoding="utf-8")

        nueva_entrada = (
            f"\n* **[ERR-PENDIENTE] {titulo_fallo}**\n"
            f"  * **Causa Raíz Comportamental:** {contexto_agente}\n"
            f"  * **Solución Implementada por Código:** PENDIENTE DE DESARROLLO.\n"
            f"  * **Estado:** [Infección Activa - Requiere Inmunización]\n"
        )

        marcador = "## [ZONA DE RESTRICCIONES ACTIVAS - INMUNIZADAS]:"
        if marcador in contenido:
            partes = contenido.split(marcador)
            nuevo_contenido = partes[0] + marcador + "\n" + nueva_entrada + partes[1]
        else:
            nuevo_contenido = contenido + f"\n{marcador}\n" + nueva_entrada

        memoria_errores_path.write_text(nuevo_contenido, encoding="utf-8")

        return (
            f"Fallo crítico '{titulo_fallo}' reportado exitosamente en memoria/Memoria_Viva_Errores.md. "
            f"Instrucción inmediata: Actualiza el ticket correspondiente en Bitacora.md a estado ABORTADO "
            f"y formula el plan de inmunización por código."
        )
    except Exception as e:
        return f"Error al reportar fallo crítico: {str(e)}"


HERRAMIENTAS_SENTRY = [
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico
]

if __name__ == "__main__":
    print(tool_consultar_sentry_errores.invoke({"mensaje_error": "SyntaxError test"}))
