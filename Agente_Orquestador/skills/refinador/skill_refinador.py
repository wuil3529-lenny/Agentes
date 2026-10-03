"""
skill_refinador.py — Refinamiento Quirúrgico de Objetivos y Validación de Alcance (BLAST)
========================================================================================
Habilidad especializada del Agente Orquestador para pausar la delegación y solicitar
clarificación humana cuando una directiva es ambigua o carece de especificaciones críticas.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]


def obtener_prompt_refinador() -> str:
    """
    System Prompt especializado y encapsulado para la habilidad de Refinamiento
    Quirúrgico de Objetivos y Validación de Alcance (Framework BLAST).
    """
    return """[🛑 HARD-STOP: MODO REFINADOR DE OBJETIVOS Y VALIDACIÓN DE ALCANCE (BLAST) ACTIVO 🛑]
Eres el Director de Requisitos y Analista de Alcance (Scope & Requirements Lead).
Tu misión es analizar críticamente cada solicitud inicial del Usuario antes de crear tickets o delegar misiones, identificando ambigüedades, suposiciones no validadas o requerimientos difusos.

DIRECTIVAS INNEGOCIABLES DEL ROL:
1. DETECCIÓN TEMPRANA DE AMBIGÜEDAD:
   Si el Usuario realiza una petición general (ej. "crea una web", "optimiza el sistema", "conecta una API"), TIENES ESTRICTAMENTE PROHIBIDO improvisar detalles o crear tickets a ciegas en la Bitácora.
2. APLICACIÓN DEL FRAMEWORK BLAST:
   Cada misión debe contar con especificación suficiente en sus 5 ejes:
   - Blueprint: ¿Cuál es el resultado final exacto y medible esperado?
   - Links: ¿Qué dependencias, archivos, APIs o credenciales previas se requieren?
   - Architecture: ¿Qué diseño técnico, tecnologías y patrones se aplicarán?
   - Style: ¿Qué restricciones, normas de seguridad y límites operativos aplican?
   - Trigger: ¿Cuál es la Evidencia Física que confirmará el cierre definitivo?
3. PAUSA QUIRÚRGICA:
   Invoca `tool_validar_objetivo(pregunta_aclaratoria="...")` formulando una pregunta precisa, cortés y estructurada con opciones concretas para que el Usuario elija el camino deseado.
4. RETENCIÓN DE EJECUCIÓN:
   Tras invocar la herramienta, detén la delegación a los subagentes técnicos hasta que el Usuario proporcione las clarificaciones necesarias.
"""


@tool
def tool_validar_objetivo(pregunta_aclaratoria: str, contexto_adicional: Optional[str] = "") -> str:
    """
    Pausa la delegación y envía una pregunta directa al usuario para clarificar
    requisitos vagos antes de crear un ticket.
    
    Usa esta herramienta cuando el usuario pida algo genérico como "hazme una web"
    y necesites definir el Blueprint, Links y Architecture exactos (Framework BLAST).
    
    Args:
        pregunta_aclaratoria: La pregunta precisa y estructurada que le harás al usuario.
        contexto_adicional: Información de contexto o alternativas sugeridas para facilitar la decisión.
    """
    try:
        import sys
        
        # Resolución agnóstica de directorios (Docker vs Host)
        rutas_orquestador = [
            _APP_ROOT / "Agente_Orquestador",
            _APP_ROOT / "Luffy",
            Path("/app/Agente_Orquestador"),
            Path("/app/Luffy")
        ]
        
        for r in rutas_orquestador:
            if r.exists() and str(r) not in sys.path:
                sys.path.insert(0, str(r))
                break
                
        try:
            from memory import publicar_mensaje
        except ImportError:
            from Agente_Orquestador.memory import publicar_mensaje

        # Enviar el mensaje al canal del usuario para visualización directa
        contenido_mensaje = {
            "texto": pregunta_aclaratoria.strip(),
            "contexto": "Refinamiento Quirúrgico (BLAST)",
            "detalle": contexto_adicional.strip() if contexto_adicional else None
        }
        
        publicar_mensaje(
            de="Agente Orquestador",
            para="usuario",
            tipo="mensaje",
            contenido=contenido_mensaje
        )
        
        return json.dumps({
            "status": "pausado",
            "mensaje": "Se ha enviado la consulta aclaratoria al Usuario. Detén la delegación, NO crees tickets en la Bitácora todavía, y espera el feedback del Usuario."
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en validación de objetivo: {str(e)}"}, ensure_ascii=False)


# Alias de compatibilidad funcional
tool_refinar_objetivo = tool_validar_objetivo
