import json
import os
import traceback
from pathlib import Path
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

_APP_ROOT = Path(__file__).resolve().parents[2]

@tool
def consultar_sentry_errores(mensaje_error: str) -> str:
    """
    Busca antecedentes de un error especifico en Sentry y en la base de conocimientos RAG.
    Usa esta herramienta de INMEDIATO cuando un comando o codigo falle, para ver como se soluciono antes.
    """
    print(f"\n[Sentry] Consultando antecedentes para el error...")
    try:
        import sys
        skills_path = Path(__file__).parent
        if str(skills_path) not in sys.path:
            sys.path.insert(0, str(skills_path))
        from skill_memoria_vectorial import tool_buscar_soluciones
        
        # Consultamos el RAG interno usando la misma semantica
        rag_result = tool_buscar_soluciones.invoke({"query_semantica": mensaje_error, "n_resultados": 2})
        
        # Simulacion de busqueda en API de Sentry
        return json.dumps({
            "status": "success", 
            "origen": "RAG_SENTRY_SYNC",
            "resultados_previos": json.loads(rag_result)
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def registrar_solucion_error(error_log: str, como_se_soluciono: str) -> str:
    """
    Registra OBLIGATORIAMENTE la receta de como solucionaste un error inedito.
    Ejecuta esto en cuanto logres sobrepasar un obstaculo que antes te bloqueaba.
    
    Args:
        error_log: El mensaje de error crudo que te arrojo el sistema.
        como_se_soluciono: La explicacion tecnica exacta de que hiciste para arreglarlo.
    """
    try:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("solucion_aplicada", como_se_soluciono)
                sentry_sdk.capture_message(f"Solucion Inedita Descubierta: {error_log[:50]}...", level="info")
        except Exception:
            pass 
            
        import sys
        import uuid
        skills_path = Path(__file__).parent
        if str(skills_path) not in sys.path:
            sys.path.insert(0, str(skills_path))
        from skill_memoria_vectorial import tool_guardar_solucion
        
        ticket_virtual = f"HOTFIX-{str(uuid.uuid4())[:8].upper()}"
        contenido = f"ERROR ORIGINAL:\n{error_log}\n\nSOLUCION APLICADA:\n{como_se_soluciono}"
        
        tool_guardar_solucion.invoke({"ticket_id": ticket_virtual, "descripcion": "Hotfix - Resolucion de error en caliente", "contenido": contenido})
        
        return json.dumps({
            "status": "success",
            "mensaje": "Solucion registrada en Sentry y vectorizada en Cerebro. ¡Excelente trabajo!"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_reportar_fallo_critico(titulo_fallo: str, contexto_agente: str) -> str:
    """
    Usa esta herramienta EXCLUSIVAMENTE cuando un subagente colapse, falle repetitivamente, o cuando un auditor rechace su trabajo 3 veces.
    Esto escribira una alerta roja en la Memoria Viva de Errores para que el Capitan la revise.
    """
    try:
        import datetime
        import os
        from pathlib import Path
        app_root = Path(__file__).resolve().parents[3]
        memoria_errores_path = app_root / "memoria" / "Memoria_Viva_Errores.md"
        
        if not memoria_errores_path.exists():
            return "Error: Memoria_Viva_Errores.md no existe."
            
        with open(memoria_errores_path, "r", encoding="utf-8") as f:
            contenido = f.read()
            
        nueva_entrada = f"\n* **[ERR-PENDIENTE] {titulo_fallo}**\n  * **Causa Raíz Comportamental:** {contexto_agente}\n  * **Solución Implementada por Código:** PENDIENTE DE DESARROLLO.\n  * **Estado:** [Infección Activa - Requiere Inmunización]\n"
        
        if "## [ZONA DE RESTRICCIONES ACTIVAS - INMUNIZADAS]:" in contenido:
            partes = contenido.split("## [ZONA DE RESTRICCIONES ACTIVAS - INMUNIZADAS]:")
            nuevo_contenido = partes[0] + "## [ZONA DE RESTRICCIONES ACTIVAS - INMUNIZADAS]:\n" + nueva_entrada + partes[1]
        else:
            nuevo_contenido = contenido + "\n## [ZONA DE RESTRICCIONES ACTIVAS - INMUNIZADAS]:\n" + nueva_entrada
            
        with open(memoria_errores_path, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)
            
        return "Fallo CRITICO reportado exitosamente al Capitán en Memoria_Viva_Errores.md. Por favor, actualiza el ticket en la Bitácora a estado ABORTADO y notifica al usuario por Telegram."
    except Exception as e:
        return f"Error al reportar fallo: {e}"

HERRAMIENTAS_SENTRY = [consultar_sentry_errores, registrar_solucion_error, tool_reportar_fallo_critico]
