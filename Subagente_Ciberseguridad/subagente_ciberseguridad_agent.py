"""
subagente_ciberseguridad_agent.py — Subagente de Ciberseguridad y Auditoría Preventiva
======================================================================================
Entidad canónica de la tripulación/flota para la auditoría estática de código (SAST),
análisis de vulnerabilidades en dependencias (CVEs), inspección perimetral de red,
blindaje de flujos n8n y emisión de reportes ejecutivos Zero-Trust.

Identidad Canónica: Subagente_Ciberseguridad
Identidad Conversacional / Alias: Robin
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

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_APP_ROOT / ".env")
except Exception:
    pass

# Ubicación centralizada de archivos temporales y reportes
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"
REPORTES_PATH = _SUBAGENTE_PATH / "reportes"
INFORMES_PATH = _SUBAGENTE_PATH / "informes"
REPORTES_PATH.mkdir(parents=True, exist_ok=True)
INFORMES_PATH.mkdir(parents=True, exist_ok=True)

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
    def guardar_cerebro(*args, **kwargs): return ""
try:
    from bucle_autocorreccion import interceptar_tool_call
except Exception:
    try:
        from Agente_Orquestador.bucle_autocorreccion import interceptar_tool_call
    except Exception:
        interceptar_tool_call = None

# ─── Carga Modular de las 8 Habilidades y sus Prompts Especializados ───────────
HERRAMIENTAS_CIBERSEGURIDAD = [
    registrar_bitacora,
    guardar_cerebro,
    publicar_mensaje,
    leer_mensajes,
    leer_nodo_obsidian
]

# 1. Base (SO y archivos seguros)
from Subagente_Ciberseguridad.skills.base.skill_base import (
    crear_archivo, leer_archivo, listar_directorio, ejecutar_comando, obtener_prompt_base
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([crear_archivo, leer_archivo, listar_directorio, ejecutar_comando])

# 2. Auditoría Estática (SAST & Secretos)
from Subagente_Ciberseguridad.skills.auditoria.skill_auditoria import (
    leer_archivo_seguro,
    listar_directorio_auditoria,
    buscar_patron_en_directorio,
    detectar_secretos_expuestos,
    leer_workflow_n8n,
    verificar_gitignore,
    obtener_prompt_auditoria
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    leer_archivo_seguro,
    listar_directorio_auditoria,
    buscar_patron_en_directorio,
    detectar_secretos_expuestos,
    leer_workflow_n8n,
    verificar_gitignore
])

# 3. Escaneo Dinámico (CVEs & Red)
from Subagente_Ciberseguridad.skills.escaneo.skill_escaneo import (
    ejecutar_pip_audit,
    ejecutar_npm_audit,
    verificar_puertos_locales,
    verificar_auth_ngrok,
    verificar_auth_n8n,
    analizar_permisos_archivo,
    obtener_prompt_escaneo
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    ejecutar_pip_audit,
    ejecutar_npm_audit,
    verificar_puertos_locales,
    verificar_auth_ngrok,
    verificar_auth_n8n,
    analizar_permisos_archivo
])

# 4. Reportes de Vulnerabilidad
from Subagente_Ciberseguridad.skills.reportes.skill_reportes import (
    generar_reporte_vulnerabilidades,
    crear_ticket_seguridad,
    leer_ultimo_reporte,
    obtener_prompt_reportes
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    generar_reporte_vulnerabilidades,
    crear_ticket_seguridad,
    leer_ultimo_reporte
])

# 5. Sentry & Observabilidad
from Subagente_Ciberseguridad.skills.sentry.skill_sentry import (
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
    obtener_prompt_sentry
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico
])

# 6. Limpieza Workspace
from Subagente_Ciberseguridad.skills.limpiar_workspace.skill_limpiar_workspace import (
    tool_limpiar_habitacion,
    tool_limpiar_workspace,
    obtener_prompt_limpiar_workspace
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    tool_limpiar_habitacion,
    tool_limpiar_workspace
])

# 7. Solicitar Soporte Pizarra
from Subagente_Ciberseguridad.skills.solicitar_soporte_pizarra.skill_solicitar_soporte_pizarra import (
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra,
    obtener_prompt_solicitar_soporte_pizarra
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra
])

# 8. Auto-Aprendizaje
from Subagente_Ciberseguridad.skills.auto_aprendizaje.skill_auto_aprendizaje import (
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    obtener_prompt_auto_aprendizaje
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria
])

# 9. Seguridad y Monitoreo del Dashboard (SOC Defensivo)
from Subagente_Ciberseguridad.skills.seguridad_dashboard.skill_seguridad_dashboard import (
    tool_consultar_incidentes_dashboard,
    tool_verificar_estado_alarma_dashboard,
    tool_gestionar_alarma_dashboard,
    tool_auditar_postura_dashboard,
    tool_bloquear_ip_dashboard,
    obtener_prompt_seguridad_dashboard
)
HERRAMIENTAS_CIBERSEGURIDAD.extend([
    tool_consultar_incidentes_dashboard,
    tool_verificar_estado_alarma_dashboard,
    tool_gestionar_alarma_dashboard,
    tool_auditar_postura_dashboard,
    tool_bloquear_ip_dashboard
])

# 10. Manos y Ojos (Navegación Web con Playwright y Control de PC con PyAutoGUI + Visión IA)
from Subagente_Ciberseguridad.skills.manos_y_ojos import (
    HERRAMIENTAS_MANOS_Y_OJOS,
    obtener_prompt_manos_y_ojos
)
HERRAMIENTAS_CIBERSEGURIDAD.extend(HERRAMIENTAS_MANOS_Y_OJOS)

NOMBRE_AGENTE = "Subagente_Ciberseguridad"
NOMBRE_AGENTE_ALIAS = "Robin"

# ═══════════════════════════════════════════════════════════════════════════════
# MAPA DE INYECCIÓN NIVEL 2: Herramienta -> (Nombre_Skill, Prompt_Getter)
# ═══════════════════════════════════════════════════════════════════════════════
MAPA_HERRAMIENTA_PROMPTS = {
    # 1. Base
    "crear_archivo": ("Operaciones Base de Archivos", obtener_prompt_base),
    "leer_archivo": ("Operaciones Base de Archivos", obtener_prompt_base),
    "listar_directorio": ("Operaciones Base de Archivos", obtener_prompt_base),
    "ejecutar_comando": ("Operaciones Base de Archivos", obtener_prompt_base),
    # 2. Auditoría Estática
    "leer_archivo_seguro": ("Auditoría Estática de Código", obtener_prompt_auditoria),
    "listar_directorio_auditoria": ("Auditoría Estática de Código", obtener_prompt_auditoria),
    "buscar_patron_en_directorio": ("Auditoría Estática de Código", obtener_prompt_auditoria),
    "detectar_secretos_expuestos": ("Auditoría Estática de Código", obtener_prompt_auditoria),
    "leer_workflow_n8n": ("Auditoría Estática de Código", obtener_prompt_auditoria),
    "verificar_gitignore": ("Auditoría Estática de Código", obtener_prompt_auditoria),
    # 3. Escaneo Dinámico
    "ejecutar_pip_audit": ("Escaneo Dinámico y Dependencias", obtener_prompt_escaneo),
    "ejecutar_npm_audit": ("Escaneo Dinámico y Dependencias", obtener_prompt_escaneo),
    "verificar_puertos_locales": ("Escaneo Dinámico y Dependencias", obtener_prompt_escaneo),
    "verificar_auth_ngrok": ("Escaneo Dinámico y Dependencias", obtener_prompt_escaneo),
    "verificar_auth_n8n": ("Escaneo Dinámico y Dependencias", obtener_prompt_escaneo),
    "analizar_permisos_archivo": ("Escaneo Dinámico y Dependencias", obtener_prompt_escaneo),
    # 4. Reportes de Vulnerabilidad
    "generar_reporte_vulnerabilidades": ("Reportes de Seguridad y Remediación", obtener_prompt_reportes),
    "crear_ticket_seguridad": ("Reportes de Seguridad y Remediación", obtener_prompt_reportes),
    "leer_ultimo_reporte": ("Reportes de Seguridad y Remediación", obtener_prompt_reportes),
    # 5. Sentry
    "tool_consultar_sentry_errores": ("Diagnóstico Sentry y Resiliencia", obtener_prompt_sentry),
    "tool_registrar_solucion_error": ("Diagnóstico Sentry y Resiliencia", obtener_prompt_sentry),
    "tool_reportar_fallo_critico": ("Diagnóstico Sentry y Resiliencia", obtener_prompt_sentry),
    # 6. Limpieza Workspace
    "tool_limpiar_habitacion": ("Higiene de Workspace", obtener_prompt_limpiar_workspace),
    "tool_limpiar_workspace": ("Higiene de Workspace", obtener_prompt_limpiar_workspace),
    # 7. Soporte Pizarra
    "tool_solicitar_ayuda_pizarra": ("Solicitud de Soporte en Pizarra", obtener_prompt_solicitar_soporte_pizarra),
    "tool_consultar_estado_ticket_pizarra": ("Solicitud de Soporte en Pizarra", obtener_prompt_solicitar_soporte_pizarra),
    # 8. Auto-Aprendizaje
    "tool_consultar_playbook_memoria": ("Auto-Aprendizaje Continuo", obtener_prompt_auto_aprendizaje),
    "tool_registrar_playbook_memoria": ("Auto-Aprendizaje Continuo", obtener_prompt_auto_aprendizaje),
    # 9. Seguridad Dashboard (SOC)
    "tool_consultar_incidentes_dashboard": ("Seguridad y SOC del Dashboard", obtener_prompt_seguridad_dashboard),
    "tool_verificar_estado_alarma_dashboard": ("Seguridad y SOC del Dashboard", obtener_prompt_seguridad_dashboard),
    "tool_gestionar_alarma_dashboard": ("Seguridad y SOC del Dashboard", obtener_prompt_seguridad_dashboard),
    "tool_auditar_postura_dashboard": ("Seguridad y SOC del Dashboard", obtener_prompt_seguridad_dashboard),
    "tool_bloquear_ip_dashboard": ("Seguridad y SOC del Dashboard", obtener_prompt_seguridad_dashboard),
    # 10. Manos y Ojos
    "tool_navegar_web": ("Navegación Web y Formularios", obtener_prompt_manos_y_ojos),
    "tool_rellenar_formulario_web": ("Navegación Web y Formularios", obtener_prompt_manos_y_ojos),
    "tool_hacer_clic_web": ("Navegación Web y Formularios", obtener_prompt_manos_y_ojos),
    "tool_extraer_informacion_web": ("Navegación Web y Formularios", obtener_prompt_manos_y_ojos),
    "tool_capturar_pantalla_web": ("Navegación Web y Formularios", obtener_prompt_manos_y_ojos),
    "tool_cerrar_navegador_web": ("Navegación Web y Formularios", obtener_prompt_manos_y_ojos),
    "tool_capturar_pantalla_pc": ("Visión y Control de Pantalla PC", obtener_prompt_manos_y_ojos),
    "tool_analizar_pantalla_pc": ("Visión y Control de Pantalla PC", obtener_prompt_manos_y_ojos),
    "tool_hacer_clic_pc": ("Visión y Control de Pantalla PC", obtener_prompt_manos_y_ojos),
    "tool_escribir_teclado_pc": ("Visión y Control de Pantalla PC", obtener_prompt_manos_y_ojos),
    "tool_presionar_teclas_pc": ("Visión y Control de Pantalla PC", obtener_prompt_manos_y_ojos),
    "tool_abrir_aplicacion_pc": ("Visión y Control de Pantalla PC", obtener_prompt_manos_y_ojos),
}

# ─── Configuración LLM ─────────────────────────────────────────────────────────
_DEFAULT_PROV = os.getenv("PROVIDER_SUBAGENTE_CIBERSEGURIDAD") or os.getenv("PROVIDER_ROBIN") or os.getenv("DEFAULT_PROVIDER", "deepseek").lower()
_LLM_API_KEY = os.getenv(f"{_DEFAULT_PROV.upper()}_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
_LLM_BASE_URL = "https://api.deepseek.com" if _DEFAULT_PROV == "deepseek" else None
_LLM_MODEL = os.getenv("MODEL_SUBAGENTE_CIBERSEGURIDAD") or os.getenv("MODEL_ROBIN") or os.getenv("DEFAULT_MODEL", "deepseek-chat")
_LLM_TEMPERATURE = 0.1
_LLM_MAX_TOKENS = 4096


def _crear_client() -> OpenAI:
    """Crea el cliente OpenAI compatible con el proveedor configurado."""
    return OpenAI(base_url=_LLM_BASE_URL, api_key=_LLM_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# Carga de Perfil Canónico e Inyección Dinámica de Prompts
# ═══════════════════════════════════════════════════════════════════════════════

AGENTE_MD_FILE = _SUBAGENTE_PATH / "_agents" / "agente.md"


def cargar_prompt_ciberseguridad() -> str:
    """
    Carga el System Prompt canónico desde _agents/agente.md.
    """
    if AGENTE_MD_FILE.exists():
        try:
            return AGENTE_MD_FILE.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[Subagente_Ciberseguridad] Advertencia al leer {AGENTE_MD_FILE.name}: {e}")
    return ""


def detectar_prompts_habilidad(texto: str) -> List[str]:
    """
    Nivel 1 Quirúrgico: Detecta la intención operativa de la instrucción
    y recopila los system prompts especializados de las habilidades correspondientes.
    """
    t = texto.lower()
    inyectados = []

    # Auditoría Estática / Secretos / n8n / Git
    if any(k in t for k in ["secreto", "token", "password", "clave", "api_key", "auditoria", "auditar", "sast", "workflow", "n8n", "gitignore"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Auditoría Estática.")
            inyectados.append(obtener_prompt_auditoria())
        except Exception:
            pass

    # Escaneo Dinámico / CVEs / Puertos / ngrok
    if any(k in t for k in ["escaneo", "escanear", "cve", "pip-audit", "npm-audit", "puerto", "netstat", "ngrok", "perimetro", "permisos"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Escaneo Dinámico.")
            inyectados.append(obtener_prompt_escaneo())
        except Exception:
            pass

    # Reportes de Seguridad / Tickets
    if any(k in t for k in ["reporte", "informe de seguridad", "vulnerabilidades", "ticket_seguridad", "remediacion", "remediación"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Reportes de Seguridad.")
            inyectados.append(obtener_prompt_reportes())
        except Exception:
            pass

    # Sentry / Excepciones
    if any(k in t for k in ["sentry", "error crítico", "fallo crítico", "tool_consultar_sentry", "diagnóstico de error"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Sentry.")
            inyectados.append(obtener_prompt_sentry())
        except Exception:
            pass

    # Limpiar Workspace / Habitación
    if any(k in t for k in ["limpiar", "limpieza", "purgar", "habitacion", "habitación", "borrar temporales", "temporales de workspace"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Limpieza Workspace.")
            inyectados.append(obtener_prompt_limpiar_workspace())
        except Exception:
            pass

    # Soporte Pizarra / Pausa Operativa
    if any(k in t for k in ["ayuda", "bloqueo", "soporte en pizarra", "auxilio", "pausa operativa", "solicitar_soporte"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Soporte Pizarra.")
            inyectados.append(obtener_prompt_solicitar_soporte_pizarra())
        except Exception:
            pass

    # Auto-Aprendizaje / Playbooks
    if any(k in t for k in ["playbook", "blueprint", "memoria procedural", "auto-aprendizaje", "autoaprendizaje", "one-shot", "receta"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Auto-Aprendizaje.")
            inyectados.append(obtener_prompt_auto_aprendizaje())
        except Exception:
            pass

    # Seguridad y Monitoreo del Dashboard / SOC / Alarmas
    if any(k in t for k in ["dashboard", "consola", "soc", "alarma", "intrusión", "intrusion", "intrusiones", "postura", "bloquear_ip", "ataque"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Seguridad del Dashboard (SOC).")
            inyectados.append(obtener_prompt_seguridad_dashboard())
        except Exception:
            pass

    # Manos y Ojos (Navegación Web con Playwright y Control de PC con PyAutoGUI + Visión IA)
    if any(k in t for k in [
        "navegar", "navegador", "formulario", "rellenar", "web", "pagina", "página",
        "pantalla", "captura", "screenshot", "clic", "click", "mouse", "teclado",
        "abrir app", "abrir aplicacion", "abrir aplicación", "manos", "ojos", "vision",
        "visión", "playwright", "pyautogui", "tool_navegar", "tool_capturar_pantalla"
    ]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Manos y Ojos (Navegación Web y Control PC).")
            inyectados.append(obtener_prompt_manos_y_ojos())
        except Exception:
            pass

    return inyectados


def construir_system_prompt(instruccion: str = "") -> str:
    """
    Construye el System Prompt completo combinando el SSOT canónico
    con las directivas especializadas detectadas en Nivel 1.
    """
    prompt_base = cargar_prompt_ciberseguridad()
    if not prompt_base:
        prompt_base = f"Eres {NOMBRE_AGENTE} (alias {NOMBRE_AGENTE_ALIAS}), Oficial de Ciberseguridad y Auditoría Preventiva."

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
    for herramienta in HERRAMIENTAS_CIBERSEGURIDAD:
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
    for h in HERRAMIENTAS_CIBERSEGURIDAD:
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


def _procesar_tool_calls(client, messages, tool_calls, objetivo_ticket: str = "", historial_firmas: list = None, conteo_fallos: dict = None):
    """
    Ejecuta las herramientas e inyecta dinámicamente las directivas de Nivel 2
    en el ToolMessage para guiar la siguiente ronda de razonamiento.
    Aplica QA Gherkin Universal, Filtro Anti-Bucle y Autocorrección de Causa Raíz.
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

        if interceptar_tool_call:
            resultado, exito, _ = interceptar_tool_call(
                nombre_tool=nombre_tool,
                args_tool=args_tool,
                func_ejecutar=_ejecutar_herramienta,
                objetivo_ticket=objetivo_ticket,
                nombre_agente=NOMBRE_AGENTE,
                historial_firmas=historial_firmas,
                conteo_fallos=conteo_fallos
            )
        else:
            resultado = _ejecutar_herramienta(nombre_tool, args_tool)

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
    Ejecuta un ciclo completo de razonamiento y ejecución para el Subagente de Ciberseguridad.
    Aplica el Escudo JSON con validación Zero-Trust de evidencia física en disco.
    Integra QA Gherkin Universal y Filtro Anti-Bucle en cada llamada de herramienta.
    """
    client = _crear_client()
    system_prompt = construir_system_prompt(instruccion=mensaje_entrada)

    messages = [{'role': 'system', 'content': system_prompt}]
    if historial:
        messages.extend(historial)
    messages.append({"role": "user", "content": mensaje_entrada})

    max_rondas = 50
    schemas = _herramientas_schema()
    historial_firmas = []
    conteo_fallos = {}

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
                registrar_consumo_tokens("subagente_ciberseguridad", in_t, out_t, _LLM_MODEL)
            except Exception:
                pass

        msg = response.choices[0].message

        if msg.tool_calls:
            assistant_msg = msg.model_dump()
            if not assistant_msg.get('content'):
                assistant_msg['content'] = ''
            messages.append(assistant_msg)
            messages = _procesar_tool_calls(
                client,
                messages,
                msg.tool_calls,
                objetivo_ticket=mensaje_entrada,
                historial_firmas=historial_firmas,
                conteo_fallos=conteo_fallos
            )
            continue

        # Procesar respuesta final
        respuesta = msg.content or ""

        # Validar JSON de cierre estricto
        try:
            datos_json = json.loads(respuesta)
            if isinstance(datos_json, dict):
                evidencia = datos_json.get('evidencia_hallazgo', '')
                if not evidencia or not isinstance(evidencia, str) or len(evidencia.strip()) < 5:
                    if ronda < max_rondas - 1:
                        messages.append({'role': 'assistant', 'content': respuesta})
                        messages.append({"role": "user", "content": (
                            "Tu respuesta JSON es válida pero le falta el campo OBLIGATORIO 'evidencia_hallazgo' a nivel raíz. "
                            "Este campo DEBE contener la ruta física al reporte generado en reportes/ o informes/. "
                            "Responde ÚNICAMENTE con el JSON completo."
                        )})
                        continue
                return respuesta
        except Exception:
            pass

        # Extracción de JSON embebido en Markdown
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

        # Envoltura de seguridad si se agotan las rondas
        reportes_existentes = sorted(REPORTES_PATH.glob("*.md"), reverse=True)
        ruta_evidencia = str(reportes_existentes[0]) if reportes_existentes else "/app/Subagente_Ciberseguridad/reportes/reporte_001.md"
        return json.dumps({
            "ticket_actualizado": respuesta,
            "evidencia_hallazgo": ruta_evidencia
        }, ensure_ascii=False)

    return json.dumps({
        "ticket_actualizado": "Límite de rondas alcanzado en Subagente_Ciberseguridad.",
        "evidencia_hallazgo": "Límite de rondas alcanzado."
    })


def funcion_nodo_subagente_ciberseguridad(estado: dict) -> dict:
    """
    Función de nodo para LangGraph en el flujo del Subagente de Ciberseguridad.
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
    print(f'=== SUBAGENTE_CIBERSEGURIDAD RESPONSE ===\n{respuesta_final}\n====================================')

    return {"messages": [AIMessage(content=respuesta_final, name=NOMBRE_AGENTE)]}


# Exportar alias de compatibilidad canónica
funcion_nodo_robin = funcion_nodo_subagente_ciberseguridad


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Audita el estado de seguridad de los proyectos actuales."
    print(ejecutar_ciclo(entrada))
