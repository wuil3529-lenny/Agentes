"""
subagente_asistencia_agent.py — Subagente de Asistencia Ejecutiva y Automatización
==================================================================================
Entidad canónica de la tripulación/flota para la gestión de Google Workspace,
triaje inteligente de correos, agenda ejecutiva, maquetación de documentos,
análisis de archivos PDF y asistencia operativa de Wuilfredo.

Identidad Canónica: Subagente_Asistencia
Identidad Conversacional / Alias: Sanji
"""

import os
import sys
import re
import json
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

# Ubicación centralizada de archivos temporales y entregables
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"
DOCUMENTOS_ASISTENCIA_PATH = _SUBAGENTE_PATH / "documentos_asistencia"
DOCUMENTOS_ASISTENCIA_PATH.mkdir(parents=True, exist_ok=True)

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

try:
    from luffy_agent import crear_llm
except Exception:
    try:
        from agente_orquestador_agent import crear_llm
    except Exception:
        crear_llm = None

# ─── Carga Modular de las 11 Habilidades y sus Prompts Especializados ──────────
HERRAMIENTAS_ASISTENCIA = [
    registrar_bitacora,
    guardar_cerebro,
    publicar_mensaje,
    leer_mensajes,
    leer_nodo_obsidian
]

# 1. Base (SO y archivos)
from Subagente_Asistencia.skills.base.skill_base import (
    crear_archivo, leer_archivo, listar_directorio, ejecutar_comando, obtener_prompt_base
)
HERRAMIENTAS_ASISTENCIA.extend([crear_archivo, leer_archivo, listar_directorio, ejecutar_comando])

# 2. Clima
from Subagente_Asistencia.skills.obtener_clima.skill_obtener_clima import (
    tool_obtener_clima, obtener_prompt_obtener_clima
)
HERRAMIENTAS_ASISTENCIA.append(tool_obtener_clima)

# 3. Leer PDF
from Subagente_Asistencia.skills.leer_pdf.skill_leer_pdf import (
    tool_leer_pdf_texto, tool_leer_pdf_pagina, tool_leer_pdf_metadatos, obtener_prompt_leer_pdf
)
HERRAMIENTAS_ASISTENCIA.extend([tool_leer_pdf_texto, tool_leer_pdf_pagina, tool_leer_pdf_metadatos])

# 4. Buscar Internet
from Subagente_Asistencia.skills.buscar_internet.skill_buscar_internet import (
    tool_buscar_internet, obtener_prompt_buscar_internet
)
HERRAMIENTAS_ASISTENCIA.append(tool_buscar_internet)

# 5. Limpiar Workspace
from Subagente_Asistencia.skills.limpiar_workspace.skill_limpiar_workspace import (
    tool_limpiar_workspace, obtener_prompt_limpiar_workspace
)
HERRAMIENTAS_ASISTENCIA.append(tool_limpiar_workspace)

# 6. Sentry
from Subagente_Asistencia.skills.sentry.skill_sentry import (
    tool_consultar_sentry_errores, tool_registrar_solucion_error, tool_reportar_fallo_critico, obtener_prompt_sentry
)
HERRAMIENTAS_ASISTENCIA.extend([tool_consultar_sentry_errores, tool_registrar_solucion_error, tool_reportar_fallo_critico])

# 7 & 8. Google Docs
from Subagente_Asistencia.skills.google_docs.skill_google_docs import (
    tool_google_docs, obtener_prompt_google_docs
)
HERRAMIENTAS_ASISTENCIA.append(tool_google_docs)

# 9. Google Calendar
from Subagente_Asistencia.skills.google_calendar.skill_google_calendar import (
    tool_google_calendar_listar, tool_google_calendar_agendar, obtener_prompt_google_calendar
)
HERRAMIENTAS_ASISTENCIA.extend([tool_google_calendar_listar, tool_google_calendar_agendar])

# 10. Google Drive
from Subagente_Asistencia.skills.google_drive.skill_google_drive import (
    tool_google_drive_buscar, tool_google_drive_recientes, obtener_prompt_google_drive
)
HERRAMIENTAS_ASISTENCIA.extend([tool_google_drive_buscar, tool_google_drive_recientes])

# 11. Inbox & Triaje en Tiempo Real
from Subagente_Asistencia.skills.inbox.skill_inbox import (
    tool_inbox_analizar_nuevos_correos, tool_inbox_clasificar_correo, tool_inbox_resumen_estado, tool_inbox_gmail, obtener_prompt_inbox
)
HERRAMIENTAS_ASISTENCIA.extend([tool_inbox_analizar_nuevos_correos, tool_inbox_clasificar_correo, tool_inbox_resumen_estado])

NOMBRE_AGENTE = "Subagente_Asistencia"
NOMBRE_AGENTE_ALIAS = "Sanji"

# ─── Mapeo de Herramientas a sus System Prompts Especializados ─────────────────
MAPA_HERRAMIENTA_PROMPTS = {
    # 1. Base
    "crear_archivo": ("Base del Sistema", obtener_prompt_base),
    "leer_archivo": ("Base del Sistema", obtener_prompt_base),
    "listar_directorio": ("Base del Sistema", obtener_prompt_base),
    "ejecutar_comando": ("Base del Sistema", obtener_prompt_base),
    # 2. Clima
    "tool_obtener_clima": ("Clima y Variables Ambientales", obtener_prompt_obtener_clima),
    # 3. PDF
    "tool_leer_pdf_texto": ("Lectura y OCR de PDFs", obtener_prompt_leer_pdf),
    "tool_leer_pdf_pagina": ("Lectura y OCR de PDFs", obtener_prompt_leer_pdf),
    "tool_leer_pdf_metadatos": ("Lectura y OCR de PDFs", obtener_prompt_leer_pdf),
    # 4. Buscar Internet
    "tool_buscar_internet": ("Búsqueda en Internet", obtener_prompt_buscar_internet),
    # 5. Limpieza Workspace
    "tool_limpiar_workspace": ("Higiene de Workspace", obtener_prompt_limpiar_workspace),
    # 6. Sentry
    "tool_consultar_sentry_errores": ("Diagnóstico de Errores Sentry", obtener_prompt_sentry),
    "tool_registrar_solucion_error": ("Diagnóstico de Errores Sentry", obtener_prompt_sentry),
    "tool_reportar_fallo_critico": ("Diagnóstico de Errores Sentry", obtener_prompt_sentry),
    # 8. Google Docs
    "tool_google_docs": ("Google Docs Editorial", obtener_prompt_google_docs),
    # 9. Google Calendar
    "tool_google_calendar_listar": ("Google Calendar", obtener_prompt_google_calendar),
    "tool_google_calendar_agendar": ("Google Calendar", obtener_prompt_google_calendar),
    # 10. Google Drive
    "tool_google_drive_buscar": ("Google Drive", obtener_prompt_google_drive),
    "tool_google_drive_recientes": ("Google Drive", obtener_prompt_google_drive),
    # 11. Inbox
    "tool_inbox_analizar_nuevos_correos": ("Triaje de Correos Gmail", obtener_prompt_inbox),
    "tool_inbox_clasificar_correo": ("Triaje de Correos Gmail", obtener_prompt_inbox),
    "tool_inbox_resumen_estado": ("Triaje de Correos Gmail", obtener_prompt_inbox),
    "tool_inbox_gmail": ("Triaje de Correos Gmail", obtener_prompt_inbox),
}

# ─── Configuración LLM ─────────────────────────────────────────────────────────
_DEFAULT_PROV = os.getenv("PROVIDER_SUBAGENTE_ASISTENCIA") or os.getenv("PROVIDER_SANJI") or os.getenv("DEFAULT_PROVIDER", "deepseek").lower()
_LLM_API_KEY = os.getenv(f"{_DEFAULT_PROV.upper()}_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
_LLM_BASE_URL = "https://api.deepseek.com" if _DEFAULT_PROV == "deepseek" else None
_LLM_MODEL = os.getenv("MODEL_SUBAGENTE_ASISTENCIA") or os.getenv("MODEL_SANJI") or os.getenv("DEFAULT_MODEL", "deepseek-chat")
_LLM_TEMPERATURE = 0.1
_LLM_MAX_TOKENS = 4096


def _crear_client() -> OpenAI:
    """Crea el cliente OpenAI compatible con el proveedor configurado."""
    return OpenAI(base_url=_LLM_BASE_URL, api_key=_LLM_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# Carga de Perfil Canónico e Inyección Dinámica de Prompts
# ═══════════════════════════════════════════════════════════════════════════════

AGENTE_MD_FILE = _SUBAGENTE_PATH / "_agents" / "agente.md"


def cargar_prompt_asistencia() -> str:
    """
    Carga el System Prompt canónico desde _agents/agente.md.
    """
    if AGENTE_MD_FILE.exists():
        try:
            return AGENTE_MD_FILE.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[Subagente_Asistencia] Advertencia al leer {AGENTE_MD_FILE.name}: {e}")
    return ""


def detectar_prompts_habilidad(texto: str) -> List[str]:
    """
    Detecta la intención operativa de la instrucción del usuario y recopila
    los system prompts especializados de las habilidades correspondientes.
    """
    t = texto.lower()
    inyectados = []

    # Inbox / Gmail
    if any(k in t for k in ["correo", "email", "inbox", "gmail", "bandeja de entrada", "triaje", "tool_inbox"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Inbox/Gmail.")
            inyectados.append(obtener_prompt_inbox())
        except Exception:
            pass

    # Google Docs
    if any(k in t for k in ["google doc", "google docs", "gdocs", "prodocbuilder", "tool_google_docs"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Google Docs.")
            inyectados.append(obtener_prompt_google_docs())
        except Exception:
            pass

    # Google Calendar
    if any(k in t for k in ["calendario", "calendar", "google calendar", "agendar", "tool_google_calendar"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Google Calendar.")
            inyectados.append(obtener_prompt_google_calendar())
        except Exception:
            pass

    # Google Drive
    if any(k in t for k in ["google drive", "gdrive", "archivos en drive", "tool_google_drive"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Google Drive.")
            inyectados.append(obtener_prompt_google_drive())
        except Exception:
            pass

    # PDF / OCR
    if any(k in t for k in ["pdf", "documento pdf", "leer pdf", "ocr", "tool_leer_pdf"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Leer PDF.")
            inyectados.append(obtener_prompt_leer_pdf())
        except Exception:
            pass

    # Clima
    if any(k in t for k in ["clima", "meteorol", "pronostico", "pronóstico", "temperatura actual", "tool_obtener_clima"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Clima.")
            inyectados.append(obtener_prompt_obtener_clima())
        except Exception:
            pass

    # Buscar en Internet
    if any(k in t for k in ["buscar en internet", "busca en la web", "buscar en la red", "duckduckgo", "tool_buscar_internet"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Búsqueda Internet.")
            inyectados.append(obtener_prompt_buscar_internet())
        except Exception:
            pass

    # Limpiar Workspace
    if any(k in t for k in ["limpiar workspace", "limpieza de workspace", "tool_limpiar_workspace", "purgar temporales"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Limpieza Workspace.")
            inyectados.append(obtener_prompt_limpiar_workspace())
        except Exception:
            pass

    # Sentry
    if any(k in t for k in ["sentry", "error crítico", "fallo crítico", "tool_consultar_sentry", "tool_reportar_fallo"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Sentry.")
            inyectados.append(obtener_prompt_sentry())
        except Exception:
            pass

    # Base / Shell
    if any(k in t for k in ["ejecutar comando", "terminal", "bash", "powershell"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Operaciones Base.")
            inyectados.append(obtener_prompt_base())
        except Exception:
            pass

    return inyectados


def construir_system_prompt(instruccion: str = "") -> str:
    """
    Construye el System Prompt dinámico para el Subagente de Asistencia.
    Prioriza la especificación canónica en _agents/agente.md y añade
    las directivas especializadas de la habilidad en foco.
    """
    prompt_base = cargar_prompt_asistencia()
    if not prompt_base:
        prompt_base = (
            f"Eres {NOMBRE_AGENTE} (alias {NOMBRE_AGENTE_ALIAS}), el Subagente de Asistencia Ejecutiva y Automatización."
        )

    # Inyección de directivas preventivas según intención detectada
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
    for herramienta in HERRAMIENTAS_ASISTENCIA:
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
    import inspect
    schemas = []
    for h in HERRAMIENTAS_ASISTENCIA:
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
    especializado de la habilidad en el contexto de respuesta.
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

        # Inyección dinámica del System Prompt de la habilidad que se acaba de usar
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
    Ejecuta un ciclo completo de razonamiento y ejecución para el Subagente de Asistencia.
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
                registrar_consumo_tokens("subagente_asistencia", in_t, out_t, _LLM_MODEL)
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

        # Validar JSON de cierre
        try:
            datos_json = json.loads(respuesta)
            if isinstance(datos_json, dict):
                evidencia = datos_json.get('evidencia_hallazgo', '')
                if not evidencia or not isinstance(evidencia, str) or len(evidencia.strip()) < 5:
                    if ronda < max_rondas - 1:
                        messages.append({'role': 'assistant', 'content': respuesta})
                        messages.append({"role": "user", "content": (
                            "Tu respuesta JSON es válida pero le falta el campo OBLIGATORIO 'evidencia_hallazgo' a nivel raíz. "
                            "Este campo DEBE contener la ruta física al archivo que creaste o consultaste. "
                            "Responde ÚNICAMENTE con el JSON completo."
                        )})
                        continue
                return respuesta
        except Exception:
            pass

        # Extracción de JSON embebido
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
        ruta_evidencia = "/app/Subagente_Asistencia/documentos_asistencia/registro_asistencia.md"
        return json.dumps({
            "ticket_actualizado": respuesta,
            "evidencia_hallazgo": ruta_evidencia
        }, ensure_ascii=False)

    return json.dumps({
        "ticket_actualizado": "Límite de rondas alcanzado en Subagente_Asistencia.",
        "evidencia_hallazgo": "Límite de rondas alcanzado."
    })


def funcion_nodo_subagente_asistencia(estado: dict) -> dict:
    """
    Función de nodo para LangGraph en el flujo del Subagente de Asistencia.
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
    print(f"[{NOMBRE_AGENTE}] Activado. Procesando tarea...")

    respuesta_final = ejecutar_ciclo(instruccion)
    print(f'=== SUBAGENTE_ASISTENCIA RESPONSE ===\n{respuesta_final}\n====================================')

    return {"messages": [AIMessage(content=respuesta_final, name=NOMBRE_AGENTE)]}


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cuáles son tus habilidades operativas actuales?"
    print(ejecutar_ciclo(entrada))
