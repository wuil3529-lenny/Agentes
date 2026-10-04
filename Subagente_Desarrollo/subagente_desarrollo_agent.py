"""
subagente_desarrollo_agent.py — Subagente de Desarrollo de Software Full-Stack
==============================================================================
Entidad canónica de la tripulación para el desarrollo de software backend,
frontend (React, HTML5), aplicaciones móviles (Expo, React Native), control de
versiones con Git, andamiaje UI/UX y flujos de automatización n8n.

Identidad Canónica: Subagente_Desarrollo
Identidad Conversacional / Alias: Zoro
"""

import os
import sys
import re
import json
import inspect
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from openai import OpenAI
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

# ─── Path & Environment Setup ───────────────────────────────────────────────────
_CURRENT_FILE = Path(__file__).resolve()
_SUBAGENTE_PATH = _CURRENT_FILE.parent
_APP_ROOT = _SUBAGENTE_PATH.parent
_ORQUESTADOR_PATH = _APP_ROOT / "Agente_Orquestador"

# SEC-005: Carga de variables de entorno desde .env sin valores en texto plano
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_APP_ROOT / ".env")
except Exception:
    pass

# Directorios de trabajo y salida
PROYECTOS_PATH = _SUBAGENTE_PATH / "proyectos"
PROYECTOS_PATH.mkdir(parents=True, exist_ok=True)
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES_PATH.mkdir(parents=True, exist_ok=True)
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"

# Registrar rutas prioritarias en sys.path
for p in [str(_APP_ROOT), str(_ORQUESTADOR_PATH), str(_SUBAGENTE_PATH), str(_SUBAGENTE_PATH / "skills")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ─── Memoria y Utilidades de la Flota ──────────────────────────────────────────
try:
    from memory import (
        cargar_perfil_agente,
        publicar_mensaje,
        leer_nodo_obsidian,
        leer_mensajes,
        registrar_bitacora,
        guardar_cerebro
    )
except Exception:
    def cargar_perfil_agente(*args, **kwargs): return {}
    def publicar_mensaje(*args, **kwargs): return ""
    def leer_nodo_obsidian(*args, **kwargs): return ""
    def leer_mensajes(*args, **kwargs): return []
    def registrar_bitacora(*args, **kwargs): return ""
    def guardar_cerebro(*args, **kwargs): return ""

# ─── Carga Modular de las 20 Habilidades y sus Prompts Especializados ──────────
from Subagente_Desarrollo.skills import (
    HERRAMIENTAS_DESARROLLO,
    MAPA_HABILIDADES,
    MAPA_HERRAMIENTA_PROMPTS,
    detectar_prompts_habilidad,
)

HERRAMIENTAS_AGENTE = [
    registrar_bitacora,
    guardar_cerebro,
    publicar_mensaje,
    leer_mensajes,
    leer_nodo_obsidian
] + HERRAMIENTAS_DESARROLLO

NOMBRE_AGENTE = "Subagente_Desarrollo"
NOMBRE_AGENTE_ALIAS = "Zoro"

# ─── Configuración LLM ─────────────────────────────────────────────────────────
_DEFAULT_PROV = os.getenv("PROVIDER_SUBAGENTE_DESARROLLO") or os.getenv("PROVIDER_ZORO") or os.getenv("DEFAULT_PROVIDER", "deepseek").lower()
_LLM_API_KEY = os.getenv(f"{_DEFAULT_PROV.upper()}_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
_LLM_BASE_URL = "https://api.deepseek.com" if _DEFAULT_PROV == "deepseek" else None
_LLM_MODEL = os.getenv("MODEL_SUBAGENTE_DESARROLLO") or os.getenv("MODEL_ZORO") or os.getenv("DEFAULT_MODEL", "deepseek-chat")
_LLM_TEMPERATURE = 0.1
_LLM_MAX_TOKENS = 4096


def _crear_client() -> OpenAI:
    """Crea el cliente OpenAI compatible con el proveedor configurado."""
    return OpenAI(base_url=_LLM_BASE_URL, api_key=_LLM_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# Carga de Perfil Canónico e Inyección Dinámica de Prompts
# ═══════════════════════════════════════════════════════════════════════════════

AGENTE_MD_FILE = _SUBAGENTE_PATH / "_agents" / "agente.md"


def cargar_prompt_desarrollo() -> str:
    """
    Carga el System Prompt canónico desde _agents/agente.md.
    """
    if AGENTE_MD_FILE.exists():
        try:
            return AGENTE_MD_FILE.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[{NOMBRE_AGENTE}] Advertencia al leer {AGENTE_MD_FILE.name}: {e}")
    return ""


def construir_system_prompt(instruccion: str = "") -> str:
    """
    Construye el System Prompt dinámico para el Subagente de Desarrollo.
    Prioriza la especificación canónica en _agents/agente.md y añade
    las directivas especializadas de la habilidad en foco (Nivel 1).
    """
    prompt_base = cargar_prompt_desarrollo()
    if not prompt_base:
        prompt_base = (
            f"Eres {NOMBRE_AGENTE} (alias {NOMBRE_AGENTE_ALIAS}), el Subagente de Desarrollo de Software Full-Stack."
        )

    # Inyección de directivas preventivas según intención detectada (Nivel 1 Quirúrgico)
    if instruccion:
        prompts_especificos = detectar_prompts_habilidad(instruccion)
        if prompts_especificos:
            prompt_base += "\n\n" + "\n\n".join(prompts_especificos)

    return prompt_base


# ═══════════════════════════════════════════════════════════════════════════════
# Motor de Invocación y Ejecución de Herramientas
# ═══════════════════════════════════════════════════════════════════════════════

def _ejecutar_herramienta(nombre_tool: str, args_tool: dict) -> str:
    """Localiza y ejecuta la herramienta adecuada."""
    for herramienta in HERRAMIENTAS_AGENTE:
        nombre = getattr(herramienta, 'name', None) or getattr(herramienta, '__name__', None)
        if nombre == nombre_tool:
            try:
                if hasattr(herramienta, 'invoke'):
                    resultado = herramienta.invoke(args_tool)
                else:
                    resultado = herramienta(**args_tool)
                return str(resultado)
            except Exception as e:
                return json.dumps({"status": "error", "mensaje": str(e)})
    return json.dumps({"status": "error", "mensaje": f"Herramienta '{nombre_tool}' no encontrada."})


def _herramientas_schema() -> list:
    """Genera el schema para function calling de OpenAI."""
    schemas = []
    for h in HERRAMIENTAS_AGENTE:
        nombre = getattr(h, 'name', None) or getattr(h, '__name__', None)
        if not nombre:
            continue
        descripcion = getattr(h, 'description', None) or (h.__doc__ or "").strip()

        if hasattr(h, 'args_schema') and h.args_schema:
            try:
                schema = h.args_schema.model_json_schema() if hasattr(h.args_schema, 'model_json_schema') else h.args_schema.schema()
            except Exception:
                schema = {"type": "object", "properties": {}}
        else:
            schema = {"type": "object", "properties": {}}
            try:
                firma = inspect.signature(h)
                for param_name, param in firma.parameters.items():
                    if param_name in ('self', 'kwargs', 'args'):
                        continue
                    schema["properties"][param_name] = {"type": "string"}
                    if param.default is not inspect.Parameter.empty:
                        schema["properties"][param_name]["description"] = f"Default: {param.default}"
            except Exception:
                pass

        schemas.append({
            "type": "function",
            "function": {
                "name": nombre,
                "description": descripcion,
                "parameters": schema
            }
        })
    return schemas


def _procesar_tool_calls(client, messages, tool_calls):
    """
    Ejecuta las llamadas a herramientas, inyectando el System Prompt
    especializado de la habilidad en el contexto de respuesta (Inyección Nivel 2).
    """
    for tc in tool_calls:
        if hasattr(tc, "function"):
            nombre_tool = tc.function.name
            try:
                args_tool = json.loads(tc.function.arguments or "{}")
            except Exception:
                args_tool = {}
            tc_id = tc.id
        else:
            nombre_tool = tc.get("name", "")
            args_tool = tc.get("args", {})
            tc_id = tc.get("id", "")

        resultado = _ejecutar_herramienta(nombre_tool, args_tool)

        # Inyección dinámica Nivel 2: System Prompt de la habilidad ejecutada
        contenido_tool = resultado
        if nombre_tool in MAPA_HERRAMIENTA_PROMPTS:
            nombre_skill, func_prompt = MAPA_HERRAMIENTA_PROMPTS[nombre_tool]
            try:
                prompt_skill = func_prompt()
                print(f"[{NOMBRE_AGENTE}] 💉 Inyectando directivas de {nombre_skill} tras ejecutar {nombre_tool}.")
                contenido_tool += f"\n\n--- [DIRECTIVAS OPERATIVAS VIVAS DE {nombre_skill.upper()}] ---\n{prompt_skill}"
            except Exception as pe:
                print(f"[{NOMBRE_AGENTE}] Error al inyectar prompt de {nombre_skill}: {pe}")

        messages.append({
            'role': 'tool',
            'tool_call_id': tc_id,
            'content': contenido_tool
        })
    return messages


def ejecutar_ciclo(mensaje_entrada: str, historial: list = None) -> str:
    """
    Ejecuta un ciclo completo de razonamiento y desarrollo de software.
    Garantiza la inyección del prompt canónico y de los prompts especializados de skills.
    """
    client = _crear_client()
    system_prompt = construir_system_prompt(instruccion=mensaje_entrada)

    messages = [{'role': 'system', 'content': system_prompt}]
    if historial:
        messages.extend(historial)
    messages.append({"role": "user", "content": mensaje_entrada})

    max_rondas = 50
    schemas = _herramientas_schema()

    for ronda in range(max_rondas):
        try:
            response = client.chat.completions.create(
                model=_LLM_MODEL,
                messages=messages,
                temperature=_LLM_TEMPERATURE,
                max_tokens=_LLM_MAX_TOKENS,
                tools=schemas if schemas else None,
                tool_choice="auto" if schemas else None,
            )
        except Exception as e:
            return json.dumps({"status": "error", "mensaje": f"Error llamando al LLM: {str(e)}"})

        if hasattr(response, "usage") and response.usage:
            try:
                from costos_tracker import registrar_consumo_tokens
                in_t = getattr(response.usage, "prompt_tokens", 0) or 0
                out_t = getattr(response.usage, "completion_tokens", 0) or 0
                registrar_consumo_tokens("subagente_desarrollo", in_t, out_t, _LLM_MODEL)
            except Exception:
                pass

        msg = response.choices[0].message

        if msg.tool_calls:
            assistant_msg = msg.model_dump()
            if not assistant_msg.get('content'):
                assistant_msg['content'] = ''
            messages.append(assistant_msg)
            messages = _procesar_tool_calls(client, messages, msg.tool_calls)
            continue

        # Procesar respuesta final
        respuesta = msg.content or ""

        # Validar JSON de cierre y verificación física (Zero-Trust)
        try:
            datos_json = json.loads(respuesta)
            if isinstance(datos_json, dict):
                evidencia = datos_json.get('evidencia_hallazgo', '')
                if not evidencia or not isinstance(evidencia, str) or len(evidencia.strip()) < 5:
                    if ronda < max_rondas - 1:
                        messages.append({'role': 'assistant', 'content': respuesta})
                        messages.append({"role": "user", "content": (
                            "Tu respuesta JSON es válida pero le falta el campo OBLIGATORIO 'evidencia_hallazgo' a nivel raíz. "
                            "Este campo DEBE contener la ruta física al archivo de software o proyecto que creaste o consultaste. "
                            "Responde ÚNICAMENTE con el JSON completo."
                        )})
                        continue
                return respuesta
        except Exception:
            pass

        # Extracción de JSON embebido si vino con Markdown
        texto_limpio = re.sub(r"```(?:json)?", " ", respuesta, flags=re.IGNORECASE)
        pos_llave = texto_limpio.find("{")
        if pos_llave != -1:
            try:
                decoder = json.JSONDecoder()
                datos_json, _ = decoder.raw_decode(texto_limpio[pos_llave:])
                if isinstance(datos_json, dict):
                    return json.dumps(datos_json, ensure_ascii=False)
            except Exception:
                pass

        if ronda < max_rondas - 1:
            messages.append({'role': 'assistant', 'content': respuesta})
            messages.append({"role": "user", "content": (
                "Tu respuesta anterior NO era un JSON válido. "
                "Responde ÚNICAMENTE con un JSON válido con la siguiente estructura: "
                "{\"ticket_actualizado\": \"<markdown>\", \"evidencia_hallazgo\": \"<ruta_al_archivo>\"}."
            )})
            continue

        # Envoltura forzosa si se agotan rondas
        ruta_evidencia = "/app/Subagente_Desarrollo/proyectos/registro_desarrollo.md"
        return json.dumps({
            "ticket_actualizado": respuesta,
            "evidencia_hallazgo": ruta_evidencia
        }, ensure_ascii=False)

    return json.dumps({
        "ticket_actualizado": "Límite de rondas alcanzado en Subagente_Desarrollo.",
        "evidencia_hallazgo": "Límite de rondas alcanzado."
    })


def funcion_nodo_subagente_desarrollo(estado: dict) -> dict:
    """
    Función de nodo para LangGraph en el flujo del Subagente de Desarrollo.
    """
    print(f"\n[{NOMBRE_AGENTE}] Recibiendo tarea del Orquestador...")

    mensajes_nuevos = leer_mensajes(NOMBRE_AGENTE) or leer_mensajes(NOMBRE_AGENTE_ALIAS)
    contexto_mensajes = ""
    if mensajes_nuevos:
        contexto_mensajes = "\n--- MENSAJES EN TU CANAL ---\n"
        for m in mensajes_nuevos:
            contexto_mensajes += f"De {m['de']}: {json.dumps(m['contenido'], ensure_ascii=False)}\n"

    tarea_asignada = ""
    if estado.get('messages'):
        ultimo_mensaje = estado['messages'][-1].content
        tarea_asignada = f"\n--- TAREA ASIGNADA POR EL ORQUESTADOR ---\n{ultimo_mensaje}"

    instruccion = f"{contexto_mensajes}{tarea_asignada}"
    print(f"[{NOMBRE_AGENTE}] Activado. Procesando tarea de desarrollo...")

    respuesta_final = ejecutar_ciclo(instruccion)
    print(f'=== SUBAGENTE_DESARROLLO RESPONSE ===\n{respuesta_final}\n====================================')

    return {"messages": [AIMessage(content=respuesta_final, name=NOMBRE_AGENTE)]}


# Compatibilidad histórica
funcion_nodo_zoro = funcion_nodo_subagente_desarrollo

if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cuáles son tus habilidades operativas actuales?"
    print(ejecutar_ciclo(entrada))
