"""
sanji_agent.py — Agente Sanji: Asistente Personal y Gestor de Google Workspace
==================================================================================
Agente oficinista/asistente de la tripulación. Su misión es gestionar los correos
de Gmail, los documentos de Google Docs, y actuar como asistente personal de Wuilfredo.
Usa NVIDIA NIM como LLM backend (nim_client.py).

Skills cargados:
  - skill_inbox_sanji.py     tool_inbox_gmail
  - skill_google_docs_sanji.py tool_google_docs

Interacciones permitidas:
  - Luffy : Le asigna tareas sobre correos o documentos (delegación de Workspace).
  - Usuario: Interacción indirecta a través de Luffy.
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[1]

import json
import re
from datetime import datetime
from openai import OpenAI
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ─── Path Setup ─────────────────────────────────────────────────────────────────
_SANJI_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
_LUFFY_PATH = _SANJI_PATH.parent / "Luffy"

# ─── Ubicación Común de Archivos Temporales (Basura / Scratch) ─────────────────
ARCHIVOS_TEMPORALES_PATH = _SANJI_PATH.parent / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"

for p in [str(_LUFFY_PATH), str(_SANJI_PATH), str(_SANJI_PATH / "skills")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ─── Importar memoria compartida de Luffy ───────────────────────────────────────
from memory import (
    cargar_perfil_agente,
    publicar_mensaje,
    leer_nodo_obsidian,
    leer_mensajes,
    registrar_bitacora,
    guardar_cerebro
)

# Importar utilidades de Luffy
from luffy_agent import crear_llm

# ─── Importar Skills ────────────────────────────────────────────────────────────
try:
    from skill_inbox_sanji import tool_inbox_gmail
except Exception:
    tool_inbox_gmail = None

try:
    from skill_google_docs_sanji import tool_google_docs
except Exception:
    tool_google_docs = None

try:
    from skill_google_drive_sanji import tool_google_drive_buscar
except Exception:
    tool_google_drive_buscar = None

try:
    from skill_google_calendar_sanji import tool_google_calendar_listar
except Exception:
    tool_google_calendar_listar = None

try:
    from skill_buscar_internet_sanji import tool_buscar_internet
except Exception:
    tool_buscar_internet = None


from skill_limpiar_sanji import tool_limpiar_habitacion_sanji

skills_path_local = Path(__file__).parent / "skills"
if str(skills_path_local) not in sys.path:
    sys.path.insert(0, str(skills_path_local))
from skill_sentry import consultar_sentry_errores, registrar_solucion_error
from skill_base import crear_archivo, leer_archivo, listar_directorio, ejecutar_comando

HERRAMIENTAS_SANJI = [
    consultar_sentry_errores,
    registrar_solucion_error,
    tool_limpiar_habitacion_sanji,
    registrar_bitacora,
    guardar_cerebro,
    publicar_mensaje,
    leer_mensajes,
    leer_nodo_obsidian,
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando
]
if tool_inbox_gmail: HERRAMIENTAS_SANJI.append(tool_inbox_gmail)
if tool_google_docs: HERRAMIENTAS_SANJI.append(tool_google_docs)
if tool_google_drive_buscar: HERRAMIENTAS_SANJI.append(tool_google_drive_buscar)
if tool_google_calendar_listar: HERRAMIENTAS_SANJI.append(tool_google_calendar_listar)
if tool_buscar_internet: HERRAMIENTAS_SANJI.append(tool_buscar_internet)

NOMBRE_AGENTE = "Sanji"

# ─── Configuración DeepSeek ─────────────────────────────────────────────────────
_NIM_API_KEY     = os.getenv("DEEPSEEK_API_KEY", "")
_NIM_BASE_URL    = "https://api.deepseek.com"
_NIM_MODEL_1     = "deepseek-chat"
_NIM_MODEL_2     = "deepseek-chat"
_NIM_TEMPERATURE = 0.1
_NIM_MAX_TOKENS  = 4096


def _crear_nim_client() -> OpenAI:
    """Crea y retorna el cliente de OpenAI apuntando a DeepSeek."""
    return OpenAI(base_url=_NIM_BASE_URL, api_key=_NIM_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# Construcción del System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

def construir_system_prompt() -> str:
    """
    Construye el prompt del sistema para Sanji, cargando su identidad
    y las reglas del protocolo desde la memoria compartida.
    """
    try:
        perfil    = cargar_perfil_agente(NOMBRE_AGENTE)
        identidad = perfil.get("presentacion", f"Eres {NOMBRE_AGENTE}, asistente personal de Google Workspace.")
    except Exception:
        identidad = (
            "Eres Sanji, el agente asistente personal y oficinista de Wuilfredo. Tu función es gestionar "
            "correos de Gmail, crear y leer documentos en Google Docs, y asistir en tareas administrativas."
        )

    try:
        reglas    = leer_nodo_obsidian("protocolo/Reglas de la Tripulacion.md")
        protocolo = leer_nodo_obsidian("protocolo/Protocolo Inter-Agente.md")
    except Exception:
        reglas    = "Sigue el protocolo de la tripulación."
        protocolo = "Responde siempre con JSON válido."

    return f"""
{identidad}

Eres el asistente personal de la tripulación. Gestionas las herramientas de Google Workspace.

--- REGLAS ABSOLUTAS ---
{reglas}

--- PROTOCOLO DE COMUNICACIÓN ---
{protocolo}

--- INSTRUCCIÓN CRÍTICA ---
0. PROTOCOLO DE HERRAMIENTAS: Antes de usar cualquier habilidad o herramienta, consulta siempre el Manual Quirúrgico (en tu perfil) para verificar cuándo usarla (gatillo) y seguir el paso a paso exacto.
1. La Pizarra (Bitacora.md) es tu única forma de interactuar operativa y formalmente con el resto de la tripulación. Todo trabajo de proyectos debe quedar registrado allí.
2. Tienes herramientas reales para gestionar proyectos y generar documentación. Úsalas.
3. Cuando uses herramientas, procesa sus resultados antes de generar tu respuesta final.
4. Responde SIEMPRE con un JSON Minimalista de Cierre cuando finalices. IMPORTANTE: La clave "evidencia_hallazgo" DEBE SER EXCLUSIVAMENTE L

[RUTAS DE TRABAJO OBLIGATORIAS]
- Entregables: /app/Sanji/documentos_sanji/
- Archivos temporales: /app/Archivos_temporales/ (DEBES usar tu nombre como prefijo, ej. sanji_temp.md)
- Actualizar ticket: /app/Bitacora.md
- Guardar conocimiento: /app/Cerebro.md y /app/memoria/
- PROHIBIDO escribir en otra ruta.A RUTA ABSOLUTA al archivo físico creado (ej. "/app/Archivos_temporales/reporte.md"). NUNCA envíes un diccionario u objeto, Robin validará que esa ruta de archivo exista.
5. Usa "registrar_bitacora" para dejar registro de lo que hiciste.
6. Usa "guardar_cerebro" para conocimiento técnico relevante a largo plazo.

--- REGLA DE DESARROLLO AUTÓNOMO ---
Tienes acceso a herramientas de código (`crear_archivo`, `ejecutar_comando`, `leer_archivo`). Úsalas ÚNICA Y EXCLUSIVAMENTE para crear scripts temporales que te ayuden a cumplir tu tarea si tus herramientas actuales fallan, o para crear/modificar tus propias skills en tu carpeta `skills/`. Si el usuario pide desarrollar una aplicación, una API, un flujo de n8n o modificar código general del proyecto, DEBES DELEGARLO A ZORO. Zoro es el Ingeniero de Software; tú solo programas para automejorarte o resolver bloqueos en tu área de expertise.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Motor de Ejecución con NIM + Tool Calling
# ═══════════════════════════════════════════════════════════════════════════════

def _ejecutar_herramienta(nombre_tool: str, args_tool: dict) -> str:
    """Encuentra y ejecuta una herramienta por nombre."""
    for herramienta in HERRAMIENTAS_SANJI:
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
    """Convierte las herramientas LangChain al formato de tools de OpenAI."""
    import inspect
    schemas = []
    for h in HERRAMIENTAS_SANJI:
        # Obtener nombre de forma robusta (LangChain tool o función plana)
        nombre = getattr(h, 'name', None) or getattr(h, '__name__', None)
        if not nombre:
            continue

        # Obtener Ruta absoluta al archivo generado de forma robusta
        descripcion = getattr(h, 'description', None) or (h.__doc__ or "").strip()

        # Obtener schema de argumentos
        if hasattr(h, 'args_schema') and h.args_schema:
            schema = h.args_schema.schema()
        else:
            # Construir schema básico desde la firma de la función plana
            schema = {"type": "object", "properties": {}}
            try:
                firma = inspect.signature(h)
                for param_name, param in firma.parameters.items():
                    if param_name in ('self', 'kwargs', 'args'):
                        continue
                    schema["properties"][param_name] = {"type": "string"}
                    if param.default is not inspect.Parameter.empty:
                        schema["properties"][param_name]["description"] = f"Default: {param.default}"
            except (ValueError, TypeError):
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


def _convertir_tool_calls_openai(tool_calls):
    """Convierte tool_calls del formato OpenAI al formato de diccionario que espera LangChain.

    Los objetos de OpenAI (ChatCompletionMessageToolCall) tienen atributos .id, .function.name,
    .function.arguments. LangChain AIMessage espera una lista de dicts con 'name', 'args' e 'id'.
    """
    convertidos = []
    for tc in tool_calls:
        try:
            nombre_tool = tc.function.name
        except AttributeError:
            nombre_tool = tc.get("function", {}).get("name", "")
        try:
            args_raw = tc.function.arguments
        except AttributeError:
            args_raw = tc.get("function", {}).get("arguments", "{}")
        try:
            args_tool = json.loads(args_raw or "{}")
        except (json.JSONDecodeError, TypeError):
            args_tool = {}
        try:
            tc_id = tc.id
        except AttributeError:
            tc_id = tc.get("id", "")
        convertidos.append({
            "name": nombre_tool,
            "args": args_tool,
            "id": tc_id,
            "type": "tool_call",
        })
    return convertidos


def _procesar_tool_calls(client, messages, tool_calls):
    """Procesa las tool calls del modelo y devuelve los mensajes actualizados."""
    for tc in tool_calls:
        # Soporta tanto objetos OpenAI como dicts ya convertidos
        if hasattr(tc, "function"):
            nombre_tool = tc.function.name
            try:
                args_tool = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args_tool = {}
            tc_id = tc.id
        else:
            nombre_tool = tc.get("name", "")
            args_tool = tc.get("args", {})
            tc_id = tc.get("id", "")
        resultado = _ejecutar_herramienta(nombre_tool, args_tool)
        
        messages.append({
            'role': 'tool',
            'tool_call_id': tc_id,
            'content': resultado
        })

    return messages


def ejecutar_ciclo(mensaje_entrada: str, historial: list = None) -> str:
    """
    Ejecuta un ciclo completo del agente Sanji: recibe un mensaje, lo procesa
    con el LLM y devuelve la respuesta final SIEMPRE en formato JSON válido.
    """
    client = _crear_nim_client()
    system_prompt = construir_system_prompt()

    messages = [{'role': 'system', 'content': system_prompt}]
    if historial:
        messages.extend(historial)
    messages.append({"role": "user", "content": mensaje_entrada})

    max_rondas = 50
    for ronda in range(max_rondas):
        try:
            response = client.chat.completions.create(
                model=_NIM_MODEL_1,
                messages=messages,
                temperature=_NIM_TEMPERATURE,
                max_tokens=_NIM_MAX_TOKENS,
                tools=_herramientas_schema() if _herramientas_schema() else None,
                tool_choice="auto" if _herramientas_schema() else None,
            )
        except Exception as e:
            return json.dumps({"status": "error", "mensaje": f"Error llamando al LLM: {str(e)}"})

        msg = response.choices[0].message

        if msg.tool_calls:
            tool_calls_convertidos = _convertir_tool_calls_openai(msg.tool_calls)
            
            # Bypass Langchain wrapper by dumping the Pydantic model directly
            assistant_msg = msg.model_dump()
            if not assistant_msg.get('content'):
                assistant_msg['content'] = ''
            messages.append(assistant_msg)

            messages = _procesar_tool_calls(client, messages, msg.tool_calls)
            continue

        # Respuesta final sin tool calls
        respuesta = msg.content or ""

        # ─── ESCUDO JSON LOCAL: Validar que la respuesta sea JSON válido ───
        try:
            datos_json = json.loads(respuesta)
            # VALIDACIÓN DE CAMPOS OBLIGATORIOS: evidencia_hallazgo DEBE existir a nivel raíz
            if isinstance(datos_json, dict):
                evidencia = datos_json.get('evidencia_hallazgo', '')
                if not evidencia or not isinstance(evidencia, str) or len(evidencia.strip()) < 5:
                    # Falta evidencia_hallazgo - pedir corrección al LLM
                    if ronda < max_rondas - 1:
                        messages.append({'role': 'assistant', 'content': respuesta})
                        messages.append({"role": "user", "content": (
                            "Tu respuesta JSON es válida pero le falta el campo OBLIGATORIO 'evidencia_hallazgo' a nivel raíz. "
                            "Este campo DEBE contener la ruta absoluta al archivo físico que creaste (ej. '/app/Archivos_temporales/reporte.md'). "
                            "Responde ÚNICAMENTE con el JSON completo incluyendo 'evidencia_hallazgo' con la ruta del archivo. "
                            "Sin markdown, sin texto adicional, solo JSON puro."
                        )})
                        continue
                else:
                    return respuesta  # JSON válido con evidencia_hallazgo presente
            else:
                return respuesta  # Es una lista u otro tipo, devolver tal cual
        except (json.JSONDecodeError, ValueError):
            pass

        # Intentar extraer JSON del texto (por si el LLM mezcló texto con JSON)
        texto_limpio = re.sub(r"```(?:json)?", " ", respuesta, flags=re.IGNORECASE)
        pos_llave = texto_limpio.find("{")
        pos_corchete = texto_limpio.find("[")
        if pos_llave != -1 or pos_corchete != -1:
            inicio = min([p for p in [pos_llave, pos_corchete] if p != -1])
            try:
                decoder = json.JSONDecoder()
                datos_json, _ = decoder.raw_decode(texto_limpio[inicio:])
                # VALIDAR evidencia_hallazgo en el JSON extraido
                if isinstance(datos_json, dict):
                    evidencia = datos_json.get('evidencia_hallazgo', '')
                    if not evidencia or not isinstance(evidencia, str) or len(evidencia.strip()) < 5:
                        # Falta evidencia_hallazgo - pedir correccion
                        if ronda < max_rondas - 1:
                            messages.append({'role': 'assistant', 'content': respuesta})
                            messages.append({"role": "user", "content": (
                                "Tu respuesta JSON es valida pero le falta el campo OBLIGATORIO 'evidencia_hallazgo' a nivel raiz. "
                                "Este campo DEBE contener la ruta absoluta al archivo fisico que creaste (ej. '/app/Archivos_temporales/reporte.md'). "
                                "Responde UNICAMENTE con el JSON completo incluyendo 'evidencia_hallazgo' con la ruta del archivo. "
                                "Sin markdown, sin texto adicional, solo JSON puro."
                            )})
                            continue
                    else:
                        return json.dumps(datos_json, ensure_ascii=False)
                else:
                    return json.dumps(datos_json, ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                pass

        # Si no hay JSON válido, pedir al LLM que corrija el formato
        if ronda < max_rondas - 1:
            messages.append({'role': 'assistant', 'content': respuesta})
            messages.append({"role": "user", "content": (
                "Tu respuesta anterior NO era un JSON válido. El sistema espera un JSON Minimalista de Cierre. "
                "Responde ÚNICAMENTE con un objeto JSON válido con la siguiente estructura: "
                "{\"ticket_actualizado\": \"<bloque markdown del ticket>\", \"evidencia_hallazgo\": \"<Ruta absoluta al archivo generado>\"}. "
                "Sin markdown, sin texto adicional, solo JSON puro."
            )})
            continue

        # Última ronda: envolver forzosamente en JSON
        # Intentar extraer una ruta de archivo de la respuesta del LLM
        ruta_evidencia = ''
        patrones_ruta = [
            r'["\'](/app/[^"\'\s]+)["\']',
            r'["\'](/app/Archivos_temporales/[^"\'\s]+)["\']',
            r'(/app/Archivos_temporales/[^\s"\']+)',
            r'(/app/[^\s"\']+\.md)',
        ]
        for patron in patrones_ruta:
            match = re.search(patron, respuesta)
            if match:
                ruta_evidencia = match.group(1)
                break
        
        if not ruta_evidencia:
            # Buscar archivos recientes en Archivos_temporales
            try:
                import glob
                archivos_recientes = sorted(
                    glob.glob('/app/Archivos_temporales/*'),
                    key=os.path.getmtime,
                    reverse=True
                )
                if archivos_recientes:
                    ruta_evidencia = archivos_recientes[0]
            except Exception:
                pass
        
        if not ruta_evidencia:
            ruta_evidencia = '/app/Archivos_temporales/reporte_ia_correos.md'
        
        return json.dumps({
            "ticket_actualizado": respuesta,
            "evidencia_hallazgo": ruta_evidencia
        }, ensure_ascii=False)

    # Límite de rondas alcanzado - Protocolo de Cierre Forzoso
    return json.dumps({
        "ticket_actualizado": "Límite de rondas alcanzado en Sanji.",
        "evidencia_hallazgo": "Se alcanzó el límite de rondas del agente Sanji."
    })


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        entrada = sys.argv[1]
    else:
        entrada = "Hola, ¿qué puedes hacer?"
    resultado = ejecutar_ciclo(entrada)
    print(resultado)

def funcion_nodo_sanji(estado: dict) -> dict:
    """
    Función de LangGraph para Sanji.
    """
    print(f"\n[{NOMBRE_AGENTE}] Recibiendo tarea de Luffy...")
    
    # 1. Marcar automáticamente los mensajes en el canal como leídos
    mensajes_nuevos = leer_mensajes(NOMBRE_AGENTE)
    contexto_mensajes = ""
    if mensajes_nuevos:
        contexto_mensajes = "\n--- MENSAJES EN TU CANAL ---\n"
        for m in mensajes_nuevos:
            contexto_mensajes += f"De {m['de']}: {json.dumps(m['contenido'], ensure_ascii=False)}\n"
    
    # Extraer el contenido del ticket y contexto del estado de LangGraph
    tarea_asignada = ""
    if estado.get('messages'):
        ultimo_mensaje = estado['messages'][-1].content
        tarea_asignada = f"\n--- TAREA ASIGNADA POR LUFFY ---\n{ultimo_mensaje}"
        
    instruccion = f"{contexto_mensajes}{tarea_asignada}"
    
    print(f"[{NOMBRE_AGENTE}] Activado. Procesando consulta...")
    
    # 3. Iniciar el bucle de razonamiento
    respuesta_final = ejecutar_ciclo(instruccion)
    print(f'=== SANJI RAW RESPONSE ===\n{respuesta_final}\n=======================')
    
    # Devolver el estado actualizado
    return {"messages": [AIMessage(content=respuesta_final, name=NOMBRE_AGENTE)]}


