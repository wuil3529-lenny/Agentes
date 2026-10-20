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
_ORQUESTADOR_PATH = Path(__file__).resolve().parent
for p in [str(_APP_ROOT), str(_ORQUESTADOR_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

ROOT_ENV_PATH = _APP_ROOT / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)

# Ubicación centralizada de archivos temporales (exclusiva en raíz)
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"

# Memoria compartida y perfiles
MEMORIA_PATH = Path(
    os.getenv("SHARED_MEMORY_PATH", str(_APP_ROOT / "memoria"))
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

try:
    from bucle_autocorreccion import interceptar_tool_call
except Exception:
    try:
        from Agente_Orquestador.bucle_autocorreccion import interceptar_tool_call
    except Exception:
        interceptar_tool_call = None

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
            "2. Si es una orden de trabajo puntual que requiere abrir tareas, genera el bloque de ticket en Markdown para la Bitácora (`## TKT-...`) con Estado: PENDIENTE y Responsable correspondiente.\n"
            "3. Si el usuario solicita CUALQUIER TAREA REPETITIVA, REACTIVA POR EVENTO O DE MONITOREO (ej. cuando entre un correo nuevo catalogarlo, monitorear base de datos/API/archivos, o generar contenido periódico), PROHIBIDO programar despertares periódicos del LLM para consultar si hay cambios (desperdicio de tokens). Usa un GATILLO ZERO-TOKEN (`gatillo_correo`, `gatillo_sql`, `gatillo_archivo`, o crea un sensor a medida en Python puro con `tool_crear_gatillo_sensor_python` + `gatillo_script_python`) que vigile con 0 tokens y SOLO despierte al subagente cuando el evento real ocurra, o `reloj_programado` si es creación por horario fijo.\n"
            "4. Si la tarea entra dentro de tus propias herramientas, ejecútala directamente antes de responder."
        )
    else:
        instruccion_modo = (
            "\n\n[MODO OPERACIÓN POR PIZARRA (BITACORA.MD)]:\n"
            "1. La Bitácora es la única fuente de verdad (SSOT). Toda delegación a subagentes se realiza modificando Bitacora.md.\n"
            "2. Toda finalización de tarea requiere evidencia física verificable en disco (Zero-Trust).\n"
            "3. Para tickets disparados por gatillo o reloj (`TKT-REC-...`): si contiene un `[PIPELINE MULTI-AGENTE]` cuya etapa secundaria aún no se ha ejecutado, delega la siguiente etapa al subagente secundario con `Estado: PENDIENTE`. Al concluir, notifica por `tool_enviar_telegram` según la regla de notificación y cierra el ticket (`CERRADO`).\n"
            "4. Al terminar tu turno, cede el control con el formato estructurado correspondiente."
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
    tool_iniciar_aprendizaje_tarea,
    tool_registrar_paso_aprendizaje,
    tool_finalizar_aprendizaje_tarea,
    tool_guardar_procedimiento_aprendido,
    tool_ejecutar_tarea_aprendida,
    tool_listar_tareas_aprendidas,
    tool_eliminar_tarea_aprendida,
    obtener_prompt_auto_aprendizaje,
    HERRAMIENTAS_PROCEDIMIENTOS
)
from tareas_programadas.skill_tareas_programadas import (
    tool_crear_gatillo_sensor_python,
    tool_programar_tarea_repetitiva,
    tool_listar_tareas_repetitivas,
    tool_modificar_estado_tarea_repetitiva,
    obtener_prompt_tareas_programadas
)
from voz.skill_voz import (
    tool_enviar_nota_voz,
    tool_hablar_por_cornetas,
    tool_escuchar_microfono,
    obtener_prompt_voz,
    escuchar_microfono_pc,
    hablar_por_cornetas_pc,
    obtener_estado_voz,
    guardar_estado_voz,
)
from manos_y_ojos.skill_manos_y_ojos import (
    HERRAMIENTAS_MANOS_Y_OJOS,
    obtener_prompt_manos_y_ojos,
)
from grafo_obsidian.skill_grafo_obsidian import (
    HERRAMIENTAS_GRAFO_OBSIDIAN,
    obtener_prompt_grafo_obsidian,
    tool_auditar_grafo_obsidian,
    tool_sincronizar_grafo_canonico,
    tool_capturar_verificar_grafo_obsidian,
)
from scout_laboral.skill_scout_laboral import (
    tool_scout_laboral_multiplataforma,
    tool_evaluar_compatibilidad_vacante,
    obtener_prompt_scout_laboral,
)
from git.skill_git import (
    HERRAMIENTAS_GIT,
    obtener_prompt_git,
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
def tool_enviar_foto_telegram(ruta_foto: str, caption: str = "") -> str:
    """Envía una foto o captura de pantalla física directamente al chat de Telegram del usuario y la espejea en consola.
    Úsalo obligatoriamente cuando el usuario te pida ver una captura de pantalla, gráfico, diagrama o evidencia visual.
    Args:
        ruta_foto: Ruta local o relativa de la imagen (.png, .jpg, .jpeg, .webp), ej: 'Archivos_temporales/pc_screen_123.png'.
        caption: Texto explicativo o resumen ejecutivo que acompañará a la imagen en Telegram.
    """
    print(f"\n[Agente_Orquestador] Ejecutando: tool_enviar_foto_telegram(ruta='{ruta_foto}', caption='{caption[:60]}...')")
    try:
        from telegram_bridge import enviar_foto_telegram
        res = enviar_foto_telegram(ruta_foto, caption=caption, remitente="Agente_Orquestador")
        return f"Foto enviada por Telegram: {res}"
    except Exception as e:
        return f"Error enviando foto por Telegram: {e}"

@tool
def tool_enviar_documento_telegram(ruta_documento: str, caption: str = "") -> str:
    """Envía un archivo o documento (PDF, Markdown, DOCX, ZIP, JSON, informe) directamente al Telegram del usuario.
    Args:
        ruta_documento: Ruta del archivo a enviar (ej: 'Agente_Orquestador/informes/reporte.md').
        caption: Texto explicativo que acompaña al archivo en Telegram.
    """
    print(f"\n[Agente_Orquestador] Ejecutando: tool_enviar_documento_telegram(ruta='{ruta_documento}', caption='{caption[:60]}...')")
    try:
        from telegram_bridge import enviar_documento_telegram
        res = enviar_documento_telegram(ruta_documento, caption=caption, remitente="Agente_Orquestador")
        return f"Documento enviado por Telegram: {res}"
    except Exception as e:
        return f"Error enviando documento por Telegram: {e}"

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
    tool_enviar_foto_telegram,
    tool_enviar_documento_telegram,
    tool_registrar_agente,
    tool_limpiar_pizarra,
    tool_crear_skill_tripulacion,
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    tool_crear_gatillo_sensor_python,
    tool_programar_tarea_repetitiva,
    tool_listar_tareas_repetitivas,
    tool_modificar_estado_tarea_repetitiva,
    tool_enviar_nota_voz,
    tool_hablar_por_cornetas,
    tool_escuchar_microfono,
    tool_scout_laboral_multiplataforma,
    tool_evaluar_compatibilidad_vacante,
] + HERRAMIENTAS_MANOS_Y_OJOS + HERRAMIENTAS_PROCEDIMIENTOS + HERRAMIENTAS_GRAFO_OBSIDIAN + HERRAMIENTAS_GIT


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

    # 6. Modo Auto-Aprendizaje, Playbooks y Repetición de Procedimientos Guiados
    gatillos_auto_aprendizaje = [
        "playbook", "blueprint", "memoria procedural", "auto-aprendizaje", "autoaprendizaje",
        "one-shot", "receta", "aprender", "aprenda", "aprende", "te voy a enseñar", "enseñar",
        "enseña", "paso a paso", "repite", "repetir", "repetirlo", "grabar tarea", "modo maestro",
        "tarea aprendida", "procedimiento", "hacer como te enseñé", "reproducir tarea", "como te enseñé",
        "como te ensene", "primera vez", "hacer cosas", "procedimientos", "tarea_aprendida"
    ]
    es_modo_auto_aprendizaje = any(g in ultimo_texto for g in gatillos_auto_aprendizaje)
    if es_modo_auto_aprendizaje:
        print("[Agente_Orquestador] 🧬 Inyectando System Prompt especializado: Auto-Aprendizaje y Procedimientos Guiados.")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_auto_aprendizaje()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt auto_aprendizaje: {e}")


    # 7. Modo Tareas Programadas, Repetitivas y Monitoreo Continuo
    gatillos_tareas_programadas = [
        "repetitiva", "repetitivas", "diariamente", "diario", "cada correo",
        "cada nuevo correo", "bandeja de entrada", "catalogar", "monitorear",
        "monitorea", "monitoreo", "cada hora", "cada minuto", "todos los días",
        "todos los dias", "programar tarea", "tarea programada", "tareas programadas",
        "cada vez que", "avísame si", "avisame si", "avisarme", "cae por debajo",
        "stock", "cron", "recurrente", "periódica", "periodica", "tkt-rec-", "rec-"
    ]
    es_modo_tareas_programadas = any(g in ultimo_texto for g in gatillos_tareas_programadas)
    if es_modo_tareas_programadas:
        print("[Agente_Orquestador] ⏱️ Inyectando System Prompt especializado: Tareas Programadas y Monitoreo Continuo.")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_tareas_programadas()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt tareas_programadas: {e}")

    # 8. Modo Voz, Micrófono, Cornetas y Notas de Voz
    gatillos_voz = [
        "nota de voz", "notas de voz", "audio", "mándame un audio", "mandame un audio",
        "envíame un audio", "enviame un audio", "háblame", "hablame", "cornetas",
        "altavoces", "micrófono", "microfono", "por voz", "con tu voz"
    ]
    es_modo_voz = any(g in ultimo_texto for g in gatillos_voz)
    if es_modo_voz:
        print("[Agente_Orquestador] 🎙️ Inyectando System Prompt especializado: Sistema de Voz y Notas de Voz.")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_voz()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt voz: {e}")

    # 9. Modo Manos y Ojos (Navegación Web con Playwright y Control de PC con PyAutoGUI + Visión IA)
    gatillos_manos_ojos = [
        "navegar", "navegador", "formulario", "rellenar", "web", "pagina", "página",
        "pantalla", "captura", "screenshot", "clic", "click", "mouse", "teclado",
        "abrir app", "abrir aplicacion", "abrir aplicación", "manos", "ojos", "vision",
        "visión", "playwright", "pyautogui", "tool_navegar", "tool_capturar_pantalla",
        "video", "reproducir", "reproduce", "play", "pausar", "pausa", "pantalla completa",
        "fullscreen", "maximizar", "minimizar", "restaurar", "ventana", "ventanas",
        "pestaña", "pestañas", "youtube", "media"
    ]
    es_modo_manos_ojos = any(g in ultimo_texto for g in gatillos_manos_ojos)
    if es_modo_manos_ojos:
        print("[Agente_Orquestador] 👁️🖐️ Inyectando System Prompt especializado: Manos y Ojos (Navegación Web y Control PC).")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_manos_y_ojos()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt manos_y_ojos: {e}")

    # 10. Modo Gestión y Auditoría del Grafo de Obsidian
    gatillos_grafo_obsidian = [
        "grafo", "gráfico", "grafico", "obsidian", "rec-obs-001", "sync_cerebro",
        "vista gráfica", "vista grafica", "madeja", "erizo", "nodos huérfanos",
        "nodos huerfanos", "arreglar gráfico", "arreglar grafico", "limpiar gráfico",
        "limpiar grafico", "saneamiento del grafo", "topología", "topologia"
    ]
    es_modo_grafo_obsidian = any(g in ultimo_texto for g in gatillos_grafo_obsidian)
    if es_modo_grafo_obsidian:
        print("[Agente_Orquestador] 🗺️ Inyectando System Prompt especializado: Arquitecto y Auditor del Grafo de Obsidian.")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_grafo_obsidian()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt grafo_obsidian: {e}")

    # 11. Modo Scouting Laboral Multiplataforma
    gatillos_scout = [
        "scout", "scouting", "buscar empleo", "ofertas de empleo", "vacantes",
        "get on board", "getonbrd", "linkedin jobs", "postulación laboral",
        "postulacion laboral", "rec-scout-001"
    ]
    es_modo_scout = any(g in ultimo_texto for g in gatillos_scout)
    if es_modo_scout:
        print("[Agente_Orquestador] 🎯 Inyectando System Prompt especializado: Scout Laboral Multiplataforma.")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_scout_laboral()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt scout_laboral: {e}")

    # 12. Modo Gestión de Versiones y Despliegue Git (con Pre-Commit Gate de Robin)
    gatillos_git = [
        "git", "commit", "push", "pull", "repositorio", "rama", "versión", "version",
        "subir a git", "desplegar", "staged", "historial de commits", "tool_git"
    ]
    es_modo_git = any(g in ultimo_texto for g in gatillos_git)
    if es_modo_git:
        print("[Agente_Orquestador] 🐙 Inyectando System Prompt especializado: Gestión y Despliegue Git (Pre-Commit Gate).")
        try:
            prompt_inyectado += "\n\n" + obtener_prompt_git()
        except Exception as e:
            print(f"[Agente_Orquestador] Error al cargar prompt git: {e}")

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
    historial_tools_firmas = []
    conteo_fallos = {}

    def _ejecutar_tool_orquestador(n_tool, a_tool):
        h = next((h for h in HERRAMIENTAS_ORQUESTADOR if h.name == n_tool), None)
        if h:
            return h.invoke(a_tool)
        return json.dumps({"status": "error", "mensaje": f"Herramienta '{n_tool}' no encontrada."})

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

            if interceptar_tool_call:
                resultado_tool, exito, _ = interceptar_tool_call(
                    nombre_tool=nombre_tool,
                    args_tool=args_tool,
                    func_ejecutar=_ejecutar_tool_orquestador,
                    objetivo_ticket=str(mensajes_langgraph[0].content) if mensajes_langgraph else "",
                    nombre_agente="Agente_Orquestador",
                    historial_firmas=historial_tools_firmas,
                    conteo_fallos=conteo_fallos
                )
            else:
                resultado_tool = _ejecutar_tool_orquestador(nombre_tool, args_tool)

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
  [bold green]voz[/bold green]         Modo conversación continua en vivo (Micrófono PC -> Cornetas PC)
  [bold green]mic[/bold green]         Hablar una orden por el micrófono de la PC y escuchar respuesta por cornetas
  [bold green]nota[/bold green]        Grabar o enviar nota de voz (Consola + Telegram)
  [bold green]cornetas[/bold green]    Activar/desactivar lectura automática por las cornetas de la PC
  [bold green]historial[/bold green]   Ver el registro de misiones anteriores
  [bold green]ayuda[/bold green]       Mostrar esta ayuda
  [bold green]salir[/bold green]       Cerrar el sistema
"""

def main() -> None:
    """Bucle principal de interacción de consola (Texto + Micrófono + Cornetas + Notas de Voz)."""
    console.clear()
    console.print(BANNER)
    console.print(AYUDA)

    orquestador = OrquestadorAgentes()
    thread_id = f"sesion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cornetas_activas = obtener_estado_voz().get("cornetas_activas", False)

    while True:
        try:
            etiqueta = "[bold cyan]Usuario (🔊 Cornetas ON)[/bold cyan]" if cornetas_activas else "[bold cyan]Usuario[/bold cyan]"
            entrada = Prompt.ask(f"\n{etiqueta}").strip()
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
        elif comando in ("cornetas", "altavoces"):
            cornetas_activas = not cornetas_activas
            guardar_estado_voz(cornetas_activas=cornetas_activas)
            estado_str = "ACTIVADAS 🔊" if cornetas_activas else "DESACTIVADAS 🔇"
            console.print(f"[bold magenta]Cornetas de la computadora:[/bold magenta] {estado_str}")
        elif comando in ("mic", "microfono", "hablar"):
            res_mic = escuchar_microfono_pc(duracion_max_segundos=15)
            texto_usuario = res_mic.get("texto", "").strip()
            if not texto_usuario:
                console.print(f"[bold red]Micrófono:[/bold red] {res_mic.get('mensaje', 'No se detectó voz.')}")
                continue
            console.print(f"[bold cyan]🎙️ Tú dijiste:[/bold cyan] {texto_usuario}")
            console.print("\n[bold yellow]Agente Orquestador[/bold yellow] procesando...\n")
            try:
                res = orquestador.chat(texto_usuario, thread_id=thread_id)
                console.print(Panel(res, title="[bold green]Respuesta (Reproduciendo en Cornetas 🔊)[/bold green]", border_style="green"))
                hablar_por_cornetas_pc(res, bloquear=True)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
        elif comando in ("voz", "conversacion"):
            console.print("[bold magenta]🎙️ MODO CONVERSACIÓN EN VIVO ACTIVADO (Micrófono PC <-> Cornetas PC)[/bold magenta]")
            console.print("[dim]Di 'salir de voz' o 'detener voz' (o presiona Ctrl+C) para volver al teclado.[/dim]")
            while True:
                try:
                    res_mic = escuchar_microfono_pc(duracion_max_segundos=15)
                    texto_usuario = res_mic.get("texto", "").strip()
                    if not texto_usuario:
                        continue
                    console.print(f"[bold cyan]🎙️ Tú:[/bold cyan] {texto_usuario}")
                    if any(k in texto_usuario.lower() for k in ["salir de voz", "detener voz", "apagar voz", "terminar conversación"]):
                        console.print("[bold yellow]Saliendo del modo conversación en vivo...[/bold yellow]")
                        hablar_por_cornetas_pc("Entendido, saliendo del canal de voz.", bloquear=True)
                        break
                    res = orquestador.chat(texto_usuario, thread_id=thread_id)
                    console.print(Panel(res, title="[bold green]Agente Orquestador 🔊[/bold green]", border_style="green"))
                    hablar_por_cornetas_pc(res, bloquear=True)
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Modo conversación en vivo detenido.[/bold yellow]")
                    break
        elif comando.startswith("nota"):
            partes = entrada.split(" ", 1)
            if len(partes) > 1 and partes[1].strip():
                texto_orden = partes[1].strip()
            else:
                res_mic = escuchar_microfono_pc(duracion_max_segundos=15)
                texto_orden = res_mic.get("texto", "").strip()
            if not texto_orden:
                console.print("[bold red]No se capturó texto para la nota de voz.[/bold red]")
                continue
            console.print(f"\n[bold yellow]Agente Orquestador[/bold yellow] procesando y generando nota de voz...\n")
            try:
                res = orquestador.chat(f"{texto_orden}\n[Responde y envía también nota de voz]", thread_id=thread_id)
                console.print(Panel(res, title="[bold green]Respuesta + Nota de Voz 🎙️[/bold green]", border_style="green"))
                from telegram_bridge import enviar_nota_voz_telegram
                enviar_nota_voz_telegram(res, caption=res[:800], remitente="Agente_Orquestador", espejear_en_consola=True)
                if cornetas_activas:
                    hablar_por_cornetas_pc(res, bloquear=True)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
        else:
            console.print("\n[bold yellow]Agente Orquestador[/bold yellow] procesando...\n")
            try:
                res = orquestador.chat(entrada, thread_id=thread_id)
                console.print(Panel(res, title="[bold green]Respuesta[/bold green]", border_style="green"))
                if cornetas_activas:
                    hablar_por_cornetas_pc(res, bloquear=False)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
