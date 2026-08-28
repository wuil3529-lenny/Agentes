"""
skill_refinador.py — Refinamiento Quirúrgico de Objetivos (Human-in-the-Loop)
============================================================================
Herramienta para que Luffy devuelva el turno al usuario si una instrucción
es muy ambigua, impidiendo que el agente inicie tareas sin un Blueprint claro.
"""

import json
from langchain_core.tools import tool

@tool
def tool_validar_objetivo(pregunta_aclaratoria: str) -> str:
    """
    Pausa la delegación y envía una pregunta directa al usuario para clarificar
    requisitos vagos antes de crear un ticket.
    
    Usa esta herramienta cuando el usuario pida algo genérico como "hazme una web"
    y necesites definir el Blueprint, Links y Architecture exactos (Framework BLAST).
    
    Args:
        pregunta_aclaratoria: La pregunta precisa que le harás al usuario.
    """
    try:
        import sys
        from pathlib import Path
        _APP_ROOT = Path(__file__).resolve().parents[2]
        if str(_APP_ROOT / "Luffy") not in sys.path:
            sys.path.insert(0, str(_APP_ROOT / "Luffy"))
            
        from memory import publicar_mensaje
        
        # Enviar el mensaje al canal del usuario para que lo vea en Telegram
        publicar_mensaje(
            de="Luffy",
            para="usuario",
            tipo="mensaje",
            contenido={
                "texto": pregunta_aclaratoria,
                "contexto": "Refinamiento Quirúrgico (BLAST)"
            }
        )
        
        # Devolver un estado que indique al LLM que debe detener la ejecución
        return json.dumps({
            "status": "pausado",
            "mensaje": "Se ha enviado la pregunta al usuario. Detén la delegación, NO crees el ticket todavía, y cambia el estado a ESPERANDO_FEEDBACK_USUARIO o simplemente despídete hasta que responda."
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})
