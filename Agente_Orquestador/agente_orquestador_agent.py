"""
agente_orquestador_agent.py — Agente Orquestador (Director de Operaciones y Supervisor)
=====================================================================================
Arquitectura: LangGraph + langchain_openai + NVIDIA NIM / DeepSeek / OpenAI (Python 3.14 compatible)

El Agente Orquestador es el nodo supervisor (director) del sistema multi-agente.
Su rol es:
  - Recibir el objetivo o mensaje del usuario.
  - Ejecutar directamente sus propias herramientas especializadas cuando la tarea
    corresponda a su ámbito (planes, entrevistas, auditorías, higiene, memoria, sentry).
  - Delegar tareas especializadas a los subagentes mediante la Bitácora (Bitacora.md).
  - Consolidar resultados, mantener la higiene del sistema y responder al usuario.
"""

import os
import sys
import io
import re
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ─── RAÍZ Y ENTORNO ──────────────────────────────────────────────────────────
_APP_ROOT = Path(__file__).resolve().parents[1]
ROOT_ENV_PATH = _APP_ROOT / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)

# Ubicación centralizada de archivos temporales (exclusiva en raíz)
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"

# Memoria compartida y perfiles
MEMORIA_PATH = Path(
    os.getenv("SHARED_MEMORY_PATH", str(_APP_ROOT / ".memoria_compartida"))
)
_DIR_AGENTS = (Path(__file__).parent / "_agents") if (Path(__file__).parent / "_agents").exists() else (Path(__file__).parent / ".agents")
AGENTE_MD_FILE = _DIR_AGENTS / "agente.md"

MAX_ITERACIONES = 50

# ─── EXCEPCIONES ─────────────────────────────────────────────────────────────
class AgentLoopError(Exception):
    """Error emitido cuando se detecta un bucle infinito o alucinación repetitiva."""
    pass

# ─── CODIFICACIÓN UTF-8 ROBUSTA ──────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── RICH CONSOLE ────────────────────────────────────────────────────────────
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.rule import Rule

console = Console()

# ─── LANGCHAIN & LANGGRAPH ───────────────────────────────────────────────────
from typing import Annotated, TypedDict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from memory import (
    guardar_en_historial,
    cargar_historial,
    listar_perfiles_disponibles,
    construir_contexto_para_agente,
    cargar_perfil_agente,
    SHARED_MEMORY_PATH,
    registrar_bitacora,
    guardar_cerebro,
)

# ══════════════════════════════════════════════════════════════════════════════
# LLM FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def crear_llm(temperatura: float = 0.2, agente: str = "AGENTE_ORQUESTADOR"):
    """
    Crea y retorna una instancia del LLM configurado dinámicamente en el .env.
    Soporta DeepSeek, OpenAI, Gemini, Ollama o NVIDIA NIM.
    """
    agente_upper = (agente or "AGENTE_ORQUESTADOR").upper()
    model_name = (
        os.getenv(f"MODEL_{agente_upper}")
        or os.getenv("MODEL_LUFFY")
        or os.getenv("DEFAULT_MODEL")
        or "deepseek-chat"
    )
    provider = (
        os.getenv(f"PROVIDER_{agente_upper}")
        or os.getenv("PROVIDER_LUFFY")
        or os.getenv("DEFAULT_PROVIDER", "")
    ).lower()

    low_model = model_name.lower()
    if "deepseek" in low_model or provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = "https://api.deepseek.com"
    elif "gpt" in low_model or "o1" in low_model or "o3" in low_model or provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = "https://api.openai.com/v1"
    elif "gemini" in low_model or provider in ("google", "gemini"):
        api_key = os.getenv("GEMINI_API_KEY")
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    elif "llama" in low_model or provider == "ollama":
        api_key = "ollama"
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    elif os.getenv(f"NVIDIA_API_KEY_{agente_upper}") or os.getenv("NVIDIA_API_KEY_LUFFY"):
        api_key = os.getenv(f"NVIDIA_API_KEY_{agente_upper}") or os.getenv("NVIDIA_API_KEY_LUFFY")
        base_url = "https://integrate.api.nvidia.com/v1"
    else:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = "https://api.deepseek.com"

    callbacks = []
    try:
        from costos_tracker import TokenTrackerCallbackHandler
        callbacks.append(TokenTrackerCallbackHandler(agente=agente))
    except Exception:
        pass

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperatura,
        max_tokens=4096,
        timeout=120.0,
        callbacks=callbacks
    )

# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE PERFIL Y SYSTEM PROMPT BASE
# ══════════════════════════════════════════════════════════════════════════════

def cargar_prompt_orquestador() -> str:
    """
    Carga el System Prompt canónico desde _agents/agente.md.
    Si no existe, retorna una definición básica de respaldo.
    """
    if AGENTE_MD_FILE.exists():
        try:
            return AGENTE_MD_FILE.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[Agente_Orquestador] Advertencia al leer agente.md: {e}")
    return (
        "Eres el Agente_Orquestador, Director de Operaciones y Supervisor Supremo del ecosistema multi-agente. "
        "Tu responsabilidad es planificar, supervisar y mantener la coherencia del sistema utilizando Bitacora.md como SSOT."
    )

# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DEL PROMPT DEL SUPERVISOR
# ══════════════════════════════════════════════════════════════════════════════

def construir_prompt_supervisor(
    agentes_disponibles: list[str],
    perfiles_agentes: dict[str, dict] = None,
    modo: str = "pizarra"
) -> ChatPromptTemplate:
    """
    Construye el System Prompt base del Agente Orquestador.
    Carga agente.md como núcleo y añade información dinámica del entorno.
    """
    prompt_base = cargar_prompt_orquestador()

    bloque_agentes = ""
    if agentes_disponibles:
        opciones = ", ".join(f'"{a}"' for a in agentes_disponibles)
        bloque_agentes = f"\n\nSubagentes disponibles en el ecosistema para delegación especializada: {opciones}.\n"

    instruccion_modo = ""
    if modo == "chat":
        instruccion_modo = (
            "\n\n[MODO COMUNICACIÓN DIRECTA CON USUARIO]:\n"
            "1. Responde de forma clara, ejecutiva y natural. Si el usuario te llama por tu nombre asignado (ej. Luffy), responde bajo esa identidad.\n"
            "2. Si es una orden de trabajo que requiere abrir tareas, genera el bloque de ticket en Markdown para la Bitácora (`## TKT-...`) con Estado: PENDIENTE y Responsable correspondiente.\n"
            "3. Si la tarea entra dentro de tus propias herramientas, ejecútala directamente antes de responder."
        )
    else:
        instruccion_modo = (
            "\n\n[MODO OPERACIÓN POR PIZARRA (BITACORA.MD)]:\n"
            "1. La Bitácora es la única fuente de verdad (SSOT). Toda delegación a subagentes se realiza modificando Bitacora.md.\n"
            "2. Toda finalización de tarea requiere evidencia física verificable en disco (Zero-Trust).\n"
            "3. Al terminar tu turno, cede el control con el formato estructurado correspondiente."
        )

    system_prompt = "\n".join([prompt_base, bloque_agentes, instruccion_modo]).strip()

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS CANÓNICAS DEL AGENTE ORQUESTADOR (13 SKILLS)
# ══════════════════════════════════════════════════════════════════════════════

skills_path_local = Path(__file__).parent / "skills"
if str(skills_path_local) not in sys.path:
    sys.path.insert(0, str(skills_path_local))

from base.skill_base import crear_archivo, leer_archivo, listar_directorio, ejecutar_comando
from refinador.skill_refinador import tool_validar_objetivo, obtener_prompt_refinador
from entrevistador.skill_entrevistador import tool_gestionar_entrevista, obtener_prompt_estrategico_entrevista
from crear_plan.skill_crear_plan import tool_crear_plan, obtener_prompt_creador_plan
from memoria_vectorial.skill_memoria_vectorial import (
    tool_guardar_solucion,
    tool_buscar_soluciones,
    consultar_estado_ticket
)
from sentry.skill_sentry import (
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
    obtener_prompt_sentry
)
from buscar_en_internet.skill_buscar_en_internet import tool_buscar_en_internet, obtener_prompt_buscar_internet
from supervisor.skill_supervisor import tool_auditar_ssot, obtener_prompt_supervisor
from limpiar_pizarra.skill_limpiar_pizarra import tool_limpiar_pizarra, obtener_prompt_limpiar_pizarra
from limpiar_workspace.skill_limpiar_workspace import tool_limpiar_workspace, obtener_prompt_limpiar_workspace
from registrar_agente.skill_registrar_agente import tool_registrar_agente, obtener_prompt_registrar_agente
from crear_herramienta.skill_crear_herramienta import iniciar_creacion_skill, obtener_prompt_creador_herramienta
from auto_aprendizaje.skill_auto_aprendizaje import (
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    obtener_prompt_auto_aprendizaje
)

@tool
def tool_enviar_telegram(mensaje: str) -> str:
    """Envía un mensaje o reporte ejecutivo al usuario por Telegram y consola.
    REGLA: El mensaje DEBE ser limpio, conciso y en formato lista de seguimiento.
    PROHIBIDO incluir líneas de código, comandos grep, números de línea L218, exit codes ni detalles técnicos de bajo nivel."""
    print(f"\n[Agente_Orquestador] Ejecutando: tool_enviar_telegram(mensaje='{mensaje[:80]}...')")
    try:
        from telegram_bridge import enviar_mensaje_telegram
        res = enviar_mensaje_telegram(mensaje, remitente="Agente_Orquestador")
        return f"Telegram enviado: {res}"
    except Exception as e:
        return f"Error en Telegram bridge: {e}"

@tool
def tool_crear_skill_tripulacion(
    agente: str,
    nombre_skill: str,
    objetivo: str,
    entradas_salidas: str = "",
    hard_stops: str = "",
    codigo_python: str = "",
    cargo_mision_prompt: str = "",
    gatillos_activacion: str = "",
    ciclo_vida: str = "",
    ejemplo_practico: str = ""
) -> str:
    """
    Crea una nueva habilidad (.md y .py) bajo el estándar de oro para cualquier agente o subagente.
    Usa esto cuando se requiera dotar de una nueva capacidad técnica a un agente, O de forma
    AUTÓNOMA cuando analices un objetivo/tarea y detectes que ningún agente cuenta con la herramienta
    necesaria para resolver el problema, evitando bloqueos.
    Genera la documentación formal en 6 secciones, el script Python con tipado estricto, encapsula el
    System Prompt especializado y levanta el ticket de auditoría para el Subagente de Ciberseguridad.
    """
    print(f"\n[Agente_Orquestador] Ejecutando: tool_crear_skill_tripulacion para {agente}...")
    try:
        return iniciar_creacion_skill(
            agente=agente,
            nombre_skill=nombre_skill,
            objetivo=objetivo,
            entradas_salidas=entradas_salidas,
            hard_stops=hard_stops,
            codigo_python=codigo_python,
            cargo_mision_prompt=cargo_mision_prompt,
            gatillos_activacion=gatillos_activacion,
            ciclo_vida=ciclo_vida,
            ejemplo_practico=ejemplo_practico
        )
    except Exception as e:
        return f"Error al crear habilidad: {e}"

HERRAMIENTAS_ORQUESTADOR = [
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando,
    tool_validar_objetivo,
    tool_gestionar_entrevista,
    tool_crear_plan,
    tool_guardar_solucion,
    tool_buscar_soluciones,
    consultar_estado_ticket,
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
    tool_buscar_en_internet,
    tool_limpiar_workspace,
    tool_auditar_ssot,
    tool_enviar_telegram,
    tool_registrar_agente,
    tool_limpiar_pizarra,
    tool_crear_skill_tripulacion,
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
]

# ══════════════════════════════════════════════════════════════════════════════
# NODO DE EJECUCIÓN DEL AGENTE ORQUESTADOR (CON INYECCIÓN DINÁMICA DE PROMPTS)
# ══════════════════════════════════════════════════════════════════════════════

def funcion_nodo_agente_orquestador(estado: dict) -> dict:
    """
    Nodo LangGraph principal del Agente Orquestador.
    Aplica inyección dinámica de prompts según el modo y ejecuta el ciclo de herramientas.
    """
    print(f"\n[Agente_Orquestador] Analizando la situación operativa...")

    mensajes_langgraph = list(estado["messages"])
    ultimo_texto = (
        mensajes_langgraph[-1].content.lower()
        if mensajes_langgraph and hasattr(mensajes_langgraph[-1], "content")
        else ""
    )

    # ── LEER MODO DE OPERACIÓN SELECCIONADO (Auto, Entrevista, Plan, etc.) ──
    modo_file = (
        _APP_ROOT / "dashboard" / "modo_agente.json"
        if (_APP_ROOT / "dashboard" / "modo_agente.json").exists()
        else (_APP_ROOT / "modo_agente.json")
    )
    modo_seleccionado = "auto"
    if modo_file.exists():
        try:
            modo_seleccionado = json.loads(modo_file.read_text(encoding="utf-8")).get("modo", "auto").lower()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # INYECCIÓN DINÁMICA DE SYSTEM PROMPTS (ON-DEMAND PROMPT INJECTION)
    # Evita la sobrecarga del prompt base; inyecta directivas solo cuando se activan.
    # ══════════════════════════════════════════════════════════════════════════
    prompt_inyectado = ""

    # 1. Modo Entrevistador
    estado_entrevista_file = Path(__file__).resolve().parent / "estado_entrevista.json"
    gatillos_entrevista = ["entrevista", "entrevistar", "hazme preguntas", "pregúntame"]
    es_modo_entrevista = (modo_seleccionado == "entrevista") or any(g in ultimo_texto for g in gatillos_entrevista)

    if not es_modo_entrevista and estado_entrevista_file.exists():
        try:
            estado_entrevista_file.unlink()
        except Exception:
            pass

    if es_modo_entrevista:
        print("[Agente_Orquestador] 🎙️ Inyectando System Prompt especializado: Entrevistador.")
        try:
            prompt_inyectado += obtener_prompt_estrategico_entrevista(estado_entrevista_file)
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt entrevistador: {e}")

    # 2. Modo Creador de Planes
    gatillos_plan = [
        "crea un plan", "crear un plan", "crea el plan", "crear el plan",
        "preparemos un plan", "haz un plan", "prepara un plan", "armemos un plan",
        "actualiza el plan", "actualizar el plan", "modifica el plan"
    ]
    es_modo_plan = (modo_seleccionado == "plan") or any(g in ultimo_texto for g in gatillos_plan)
    if es_modo_plan and not es_modo_entrevista:
        print("[Agente_Orquestador] 📋 Inyectando System Prompt especializado: Creador de Planes.")
        try:
            prompt_inyectado += obtener_prompt_creador_plan()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt crear_plan: {e}")

    # 3. Modo Refinador de Objetivos
    gatillos_refinador = ["refina", "refinar", "valida el objetivo", "clarifica el requerimiento", "analiza el objetivo"]
    es_modo_refinador = any(g in ultimo_texto for g in gatillos_refinador)
    if es_modo_refinador and not es_modo_entrevista and not es_modo_plan:
        print("[Agente_Orquestador] 🎯 Inyectando System Prompt especializado: Refinador de Objetivos.")
        try:
            prompt_inyectado += obtener_prompt_refinador()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt refinador: {e}")

    # 4. Modo Auditoría y Supervisión SSOT
    gatillos_supervisor = ["audita la pizarra", "auditar ssot", "revisa la bitácora", "supervisar tickets"]
    es_modo_supervisor = any(g in ultimo_texto for g in gatillos_supervisor)
    if es_modo_supervisor:
        print("[Agente_Orquestador] 🛡️ Inyectando System Prompt especializado: Supervisor SSOT.")
        try:
            prompt_inyectado += obtener_prompt_supervisor()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt supervisor: {e}")

    # 5. Modo Sentry / Diagnóstico de Errores
    gatillos_sentry = ["error crítico", "sentry", "consultar error", "fallo crítico", "diagnóstico de error"]
    es_modo_sentry = any(g in ultimo_texto for g in gatillos_sentry)
    if es_modo_sentry:
        print("[Agente_Orquestador] 🚨 Inyectando System Prompt especializado: Sentry.")
        try:
            prompt_inyectado += obtener_prompt_sentry()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt sentry: {e}")

    # 6. Modo Auto-Aprendizaje y Playbooks
    gatillos_auto_aprendizaje = ["playbook", "blueprint", "memoria procedural", "auto-aprendizaje", "autoaprendizaje", "one-shot", "receta", "aprender"]
    es_modo_auto_aprendizaje = any(g in ultimo_texto for g in gatillos_auto_aprendizaje)
    if es_modo_auto_aprendizaje:
        print("[Agente_Orquestador] 🧬 Inyectando System Prompt especializado: Auto-Aprendizaje y Playbooks.")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_auto_aprendizaje()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt auto_aprendizaje: {e}")

    # Aplicar la inyección dinámica al último mensaje
    if prompt_inyectado and mensajes_langgraph:
        mensajes_langgraph[-1].content += f"\n\n{prompt_inyectado}"

    # ── Preparar LLM con herramientas ──
    llm = crear_llm(temperatura=0.2, agente="AGENTE_ORQUESTADOR")
    llm_con_tools = llm.bind_tools(HERRAMIENTAS_ORQUESTADOR)

    es_chat = any("telegram" in str(getattr(m, "content", "")).lower() for m in mensajes_langgraph)
    modo_actual = "chat" if es_chat else "pizarra"
    prompt = construir_prompt_supervisor(
        ["Subagente_Desarrollo", "Subagente_Diseno", "Subagente_Ciberseguridad", "Subagente_Asistencia"],
        modo=modo_actual
    )
    cadena = prompt | llm_con_tools

    # Invocación inicial
    respuesta = cadena.invoke({"messages": mensajes_langgraph})

    # ── Bucle de ejecución de herramientas ──
    MAX_ROUNDS = 50
    ronda = 0
    historial_tools = []

    while hasattr(respuesta, "tool_calls") and respuesta.tool_calls and ronda < MAX_ROUNDS:
        ronda += 1
        print(f"[Agente_Orquestador] Ronda {ronda}: ejecutando {len(respuesta.tool_calls)} herramienta(s)...")

        # 🛡️ HARD-STOP (ERR-010): Anti-Looping
        firma_ronda_actual = tuple(
            (tc["name"], json.dumps(tc["args"], sort_keys=True)) for tc in respuesta.tool_calls
        )
        historial_tools.append(firma_ronda_actual)

        if len(historial_tools) >= 3 and historial_tools[-1] == historial_tools[-2] == historial_tools[-3]:
            error_msg = f"SISTEMA (ERR-010): Bucle infinito detectado al ejecutar '{firma_ronda_actual[0][0]}' repetidamente."
            print(f"[Agente_Orquestador] 🛡️ HARD-STOP: {error_msg}")
            raise AgentLoopError(error_msg)

        mensajes_langgraph.append(respuesta)

        for tool_call in respuesta.tool_calls:
            nombre_tool = tool_call["name"]
            args_tool   = tool_call["args"]
            tool_id     = tool_call.get("id", f"tool_{ronda}")

            print(f"[Agente_Orquestador] → Ejecutando: {nombre_tool}({list(args_tool.keys())})")

            herramienta_encontrada = next((h for h in HERRAMIENTAS_ORQUESTADOR if h.name == nombre_tool), None)
            if herramienta_encontrada:
                resultado_tool = herramienta_encontrada.invoke(args_tool)
                print(f"[Agente_Orquestador] ← Resultado: {str(resultado_tool)[:120]}...")
            else:
                resultado_tool = json.dumps({"status": "error", "mensaje": f"Herramienta '{nombre_tool}' no encontrada."})

            mensajes_langgraph.append(
                ToolMessage(
                    content=str(resultado_tool) + "\n\nAcción completada. Continúa tu flujo o emite tu respuesta de cierre.",
                    tool_call_id=tool_id
                )
            )

        respuesta = cadena.invoke({"messages": mensajes_langgraph})

    if hasattr(respuesta, "tool_calls") and respuesta.tool_calls:
        print("[Agente_Orquestador] Límite de rondas alcanzado. Forzando respuesta final.")
        mensajes_langgraph.append(respuesta)
        for tc in respuesta.tool_calls:
            mensajes_langgraph.append(
                ToolMessage(
                    content="SISTEMA: Límite de rondas alcanzado. Por favor emite tu respuesta final.",
                    tool_call_id=tc.get("id", "dummy")
                )
            )
        respuesta_final = (prompt | llm).invoke({"messages": mensajes_langgraph})
        texto_respuesta = respuesta_final.content if hasattr(respuesta_final, "content") else str(respuesta_final)
    else:
        texto_respuesta = respuesta.content if hasattr(respuesta, "content") else str(respuesta)

    # ── Parseo con Escudo Robusto ──
    print(f"[DEBUG RAW OUTPUT]:\n{texto_respuesta}\n[END DEBUG]", flush=True)
    texto_limpio = re.sub(r"```(?:json)?", " ", texto_respuesta, flags=re.IGNORECASE)

    pos_llave    = texto_limpio.find("{")
    pos_corchete = texto_limpio.find("[")

    if pos_llave == -1 and pos_corchete == -1:
        inicio, char_inicio = -1, None
    elif pos_llave == -1:
        inicio, char_inicio = pos_corchete, "["
    elif pos_corchete == -1:
        inicio, char_inicio = pos_llave, "{"
    elif pos_llave < pos_corchete:
        inicio, char_inicio = pos_llave, "{"
    else:
        inicio, char_inicio = pos_corchete, "["

    char_fin = "}" if char_inicio == "{" else "]"

    try:
        if inicio == -1:
            raise ValueError("No se encontró delimitador JSON.")

        fin = texto_limpio.rfind(char_fin)
        if fin == -1 or fin < inicio:
            raise ValueError(f"No se encontró cierre '{char_fin}' válido.")

        datos_json = json.loads(texto_limpio[inicio : fin + 1])
        if not isinstance(datos_json, (dict, list)):
            raise ValueError("El JSON no es un objeto ni una lista.")

        if isinstance(datos_json, dict) and "ticket_actualizado" in datos_json:
            if not datos_json.get("evidencia_hallazgo"):
                import re as _re_eh
                m_eh = _re_eh.search(r'(?i)(?:###\s*🧾?\s*Evidencia de Hallazgo|evidencia_hallazgo)[:\*\s]*\n?(.*?)(?=\n(?:###|-?\s*\*\*)|$)', datos_json["ticket_actualizado"], _re_eh.DOTALL)
                if m_eh and len(m_eh.group(1).strip()) > 10:
                    datos_json["evidencia_hallazgo"] = m_eh.group(1).strip()
                elif datos_json.get("Evidencia_Fisica"):
                    datos_json["evidencia_hallazgo"] = f"Evidencia física verificada en disco: {datos_json['Evidencia_Fisica']}"

        mensaje_salida = f"[Agente_Orquestador -> Sistema]: {json.dumps(datos_json, ensure_ascii=False)}"

    except Exception:
        datos_json = {
            "para": "Usuario",
            "tipo": "conversacion",
            "contenido": {"texto": texto_respuesta.strip()}
        }
        mensaje_salida = f"[Agente_Orquestador -> Usuario]: {texto_respuesta.strip()}"

    return {
        "messages": [AIMessage(content=mensaje_salida)],
        "ultimo_agente": "Agente_Orquestador",
        "datos_json": datos_json
    }

# ══════════════════════════════════════════════════════════════════════════════
# CLASE ORQUESTADORA MULTI-AGENTE
# ══════════════════════════════════════════════════════════════════════════════

class EstadoSistema(TypedDict):
    """Estado compartido entre todos los nodos del grafo durante una misión."""
    messages:      Annotated[list[BaseMessage], add_messages]
    next:          str
    objetivo:      str
    iteraciones:   int
    ultimo_agente: str

class OrquestadorAgentes:
    """Orquesta el sistema multi-agente con Agente_Orquestador como supervisor."""

    def __init__(self):
        self.llm        = crear_llm()
        self._agentes:  dict[str, callable] = {}
        self._perfiles: dict[str, dict]     = {}
        self._grafo     = None
        self._memory    = MemorySaver()

        print("[Agente_Orquestador] Director de Operaciones inicializado.")
        print(f"[Agente_Orquestador] Memoria compartida: {SHARED_MEMORY_PATH}")

    def agregar_agente(self, nombre: str, funcion_nodo: callable) -> None:
        """Registra un subagente en el sistema."""
        self._agentes[nombre] = funcion_nodo
        self._grafo = None
        perfil = cargar_perfil_agente(nombre)
        if perfil:
            self._perfiles[nombre] = perfil
            print(f"[Agente_Orquestador] Agente '{nombre}' registrado con perfil.")
        else:
            print(f"[Agente_Orquestador] Agente '{nombre}' registrado.")

    def listar_agentes(self) -> list[str]:
        """Retorna los nombres de los subagentes registrados."""
        return list(self._agentes.keys())

    def ejecutar_mision(self, objetivo: str, thread_id: str = "sesion_principal") -> str:
        """Lanza una misión al sistema multi-agente."""
        contexto_memoria = construir_contexto_para_agente()
        contenido = objetivo
        if contexto_memoria:
            contenido += f"\n\n[Memoria de sesiones previas]\n{contexto_memoria}"

        estado_inicial: EstadoSistema = {
            "messages":      [HumanMessage(content=contenido)],
            "next":          "agente_orquestador",
            "objetivo":      objetivo,
            "iteraciones":   0,
            "ultimo_agente": "",
        }
        config = RunnableConfig(configurable={"thread_id": thread_id})
        
        # En ejecución directa por nodo
        res = funcion_nodo_agente_orquestador(estado_inicial)
        resultado = res["messages"][-1].content
        guardar_en_historial(objetivo, resultado, ["Agente_Orquestador"] + self.listar_agentes())
        return resultado

    def chat(self, mensaje: str, thread_id: str = "sesion_principal") -> str:
        """Modo conversacional directo."""
        return self.ejecutar_mision(mensaje, thread_id=thread_id)

# ══════════════════════════════════════════════════════════════════════════════
# INTERFAZ DE CONSOLA
# ══════════════════════════════════════════════════════════════════════════════

BANNER = """[bold cyan]
  █████╗  ██████╗ ███████╗███╗   ██╗████████╗███████╗
 ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██╔════╝
 ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   █████╗  
 ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  
 ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ███████╗
 ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝
       ██████╗ ██████╗  ██████╗ ██╗   ██╗███████╗███████╗████████╗██████╗  █████╗ ██████╗  ██████╗ ██████╗ 
      ██╔═══██╗██╔══██╗██╔═══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
      ██║   ██║██████╔╝██║   ██║██║   ██║█████╗  ███████╗   ██║   ██████╔╝███████║██║  ██║██║   ██║██████╔╝
      ██║   ██║██╔══██╗██║▄▄ ██║██║   ██║██╔══╝  ╚════██║   ██║   ██╔══██╗██╔══██║██║  ██║██║   ██║██╔══██╗
      ╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝███████╗███████║   ██║   ██║  ██║██║  ██║██████╔╝╚██████╔╝██║  ██║
       ╚═════╝ ╚═╝  ╚═╝ ╚══▀▀═╝  ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝[/bold cyan]
[bold white]                      Director de Operaciones y Supervisor del Sistema[/bold white]
"""

AYUDA = """[bold cyan]Comandos disponibles:[/bold cyan]
  [bold green]mision[/bold green]      Lanzar una nueva misión al sistema
  [bold green]historial[/bold green]   Ver el registro de misiones anteriores
  [bold green]estado[/bold green]      Ver agentes activos y estado del sistema
  [bold green]ayuda[/bold green]       Mostrar esta ayuda
  [bold green]salir[/bold green]       Cerrar el sistema
"""

def main() -> None:
    """Bucle principal de interacción de consola."""
    console.clear()
    console.print(BANNER)
    console.print(AYUDA)

    orquestador = OrquestadorAgentes()
    thread_id = f"sesion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    while True:
        try:
            entrada = Prompt.ask("\n[bold cyan]Usuario[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Sesión finalizada.[/dim]")
            break

        if not entrada:
            continue

        comando = entrada.lower()
        if comando in ("salir", "exit", "quit"):
            console.print("[dim]Sesión finalizada.[/dim]")
            break
        elif comando == "ayuda":
            console.print(AYUDA)
        elif comando == "historial":
            hist = cargar_historial()
            console.print(f"[bold]Historial ({len(hist)} entradas):[/bold]")
            for h in hist[-5:]:
                console.print(f" - {h.get('timestamp')}: {h.get('objetivo')[:50]}")
        else:
            console.print("\n[bold yellow]Agente Orquestador[/bold yellow] procesando...\n")
            try:
                res = orquestador.chat(entrada, thread_id=thread_id)
                console.print(Panel(res, title="[bold green]Respuesta[/bold green]", border_style="green"))
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
