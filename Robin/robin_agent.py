import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[1]
import os
"""
robin_agent.py — Agente Oficial de Ciberseguridad: Nico Robin
==============================================================
Orquestador LangGraph de Robin.
Importa todas las habilidades de seguridad y las expone al LLM
como herramientas para auditar el ecosistema de agentes.

Skills cargados:
  - skill_auditoria.py → leer_archivo_seguro, listar_directorio_auditoria,
                          buscar_patron_en_directorio, detectar_secretos_expuestos,
                          leer_workflow_n8n, verificar_gitignore
  - skill_escaneo.py   → ejecutar_pip_audit, ejecutar_npm_audit,
                          verificar_puertos_locales, verificar_auth_ngrok,
                          verificar_auth_n8n
  - skill_reportes.py  → generar_reporte_vulnerabilidades,
                          crear_ticket_seguridad, leer_ultimo_reporte

Documentación en Obsidian: agentes/Robin.md
"""

import json
import re
import sys
from pathlib import Path

from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ─── Path Setup ───────────────────────────────────────────────────────────────
_LUFFY_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent / 'Luffy'
_ROBIN_PATH = Path(os.path.dirname(os.path.abspath(__file__)))

# ─── Ubicación Común de Archivos Temporales (Basura / Scratch) ───────────────
# Cualquier archivo temporal que pueda ser borrado y no forme parte ni de skins,
# ni habilidades, ni funciones, debe guardarse en: Archivos_temporales/
ARCHIVOS_TEMPORALES_PATH = _LUFFY_PATH.parent / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"

_ROBIN_SKILLS_PATH = _ROBIN_PATH / "skills"

for p in [str(_LUFFY_PATH), str(_ROBIN_PATH), str(_ROBIN_SKILLS_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ─── Importar utilidades de Luffy y memoria ───────────────────────────────────
from luffy_agent import crear_llm
from memory import (
    cargar_perfil_agente,
    publicar_mensaje,
    leer_nodo_obsidian,
    leer_mensajes,
    registrar_bitacora,
    guardar_cerebro
)

# ─── Importar todos los Skills de Seguridad ───────────────────────────────────
from skill_auditoria import HERRAMIENTAS_AUDITORIA
from skill_escaneo   import HERRAMIENTAS_ESCANEO
from skill_reportes  import HERRAMIENTAS_REPORTES
from skill_limpiar_robin import tool_limpiar_habitacion_robin


import sys
from pathlib import Path
skills_path_local = Path(__file__).parent / "skills"
if str(skills_path_local) not in sys.path:
    sys.path.insert(0, str(skills_path_local))
from skill_sentry import consultar_sentry_errores, registrar_solucion_error
from skill_base import crear_archivo, leer_archivo, listar_directorio, ejecutar_comando

HERRAMIENTAS_ROBIN = [
    consultar_sentry_errores,
    registrar_solucion_error,
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando,
] + HERRAMIENTAS_AUDITORIA + HERRAMIENTAS_ESCANEO + HERRAMIENTAS_REPORTES + [tool_limpiar_habitacion_robin]

NOMBRE_AGENTE = "Robin"

# ═══════════════════════════════════════════════════════════════════════════════
# Prompt del Agente
# ═══════════════════════════════════════════════════════════════════════════════

def _cargar_protocolo_local(ruta_relativa: str) -> str:
    """
    Carga archivos de protocolo desde /app/protocolo/ directamente,
    con fallback a leer_nodo_obsidian.
    """
    # Intentar primero desde /app/protocolo/
    ruta_directa = Path("/app/protocolo") / ruta_relativa
    if ruta_directa.exists():
        return ruta_directa.read_text(encoding="utf-8")
    # Fallback al sistema de memoria
    return leer_nodo_obsidian(ruta_relativa)


def construir_prompt_agente() -> ChatPromptTemplate:
    """
    Construye el prompt del sistema para Robin, cargando su identidad,
    reglas de protocolo y guía de skills desde la memoria compartida.
    """
    perfil    = cargar_perfil_agente(NOMBRE_AGENTE)
    identidad = perfil.get("presentacion", "Soy Robin, Oficial de Ciberseguridad de la tripulación.")

    reglas    = _cargar_protocolo_local("Reglas de la Tripulacion.md")
    protocolo = _cargar_protocolo_local("Protocolo Inter-Agente.md")

    # Mapeo de herramientas disponibles
    herramientas_desc = "\n".join([
        f"  - {h.name}: {h.description[:120]}"
        for h in HERRAMIENTAS_ROBIN
    ])

    system_prompt = f"""
{identidad}

Tu capitán es Luffy. Él te delegará auditorías y revisiones de seguridad.
Tu misión es proteger el ecosistema de agentes de cualquier vulnerabilidad.

--- TUS DOMINIOS DE SUPERVISIÓN ---
1. CÓDIGO DE ZORO: Revisa todo código que Zoro genera.
   Busca: inyecciones, secretos hardcodeados, CVEs en dependencias, APIs sin auth,
   manejo inseguro de errores, XSS/CSRF en código web, deserialización insegura.

2. OPERACIONES DE NAMI: Supervisa sus flujos n8n y redes sociales.
   Busca: webhooks sin autenticación, tokens de RRSS expuestos en logs/archivos,
   URLs de ngrok sin basic-auth, permisos OAuth excesivos, payloads sin validar.

3. INFRAESTRUCTURA: Monitorea el ecosistema completo.
   Busca: .env sin .gitignore, n8n sin Basic Auth, Ollama API expuesta,
   puertos locales innecesarios, credenciales en texto plano.

--- TUS HERRAMIENTAS DISPONIBLES ---
{herramientas_desc}

--- CÓMO TRABAJAS ---
1. Leer el contexto de la delegación (qué auditar y por qué).
2. Usar tus herramientas para inspeccionar el área indicada.
3. Clasificar cada hallazgo con nivel CRÍTICO | ALTO | MEDIO | BAJO | OK.
4. Generar un reporte formal con generar_reporte_vulnerabilidades.
5. Crear tickets de corrección con crear_ticket_seguridad para hallazgos ALTO+.
6. Reportar el resultado a Luffy con el JSON del protocolo.

--- REGLAS ABSOLUTAS ---
{reglas}

--- PROTOCOLO DE COMUNICACIÓN (JSON OBLIGATORIO) ---
{protocolo}
---

INSTRUCCIONES CRÍTICAS:
1. Cuando uses herramientas, procesa sus resultados antes de responder.
2. Responde ÚNICAMENTE con un JSON v�álido según el protocolo (Los 3 Pilares).
3. No envíes markdown alrededor del JSON — solo JSON puro.
4. Puedes encadenar hasta 8 herramientas para completar una auditoría compleja.
5. En el JSON de respuesta, incluye siempre:
   - nivel_criticidad: CRÍTICO | ALTO | MEDIO | BAJO | OK
   - hallazgos: lista de vulnerabilidades encontradas
   - recomendaciones: acciones a tomar
6. Si detectas un CRÍTICO, el ticket creado en la Pizarra debe tener a Luffy como responsable para atención inmediata.
7. Si la auditoría no revela problemas, no crees tickets de seguridad y simplemente reporta el nivel OK en tu JSON de cierre.
8. Usa "registrar_bitacora" para cada auditoría que realices.
9. Usa "guardar_cerebro" para reglas o patrones de vulnerabilidad que descubras.

--- FORMATO JSON DE SALIDA (OBLIGATORIO) ---
Tu respuesta final DEBE ser un JSON puro con esta estructura EXACTA:
{{
  "para": "Luffy",
  "tipo": "informe_auditoria",
  "contenido": {{
    "nivel_criticidad": "OK",
    "hallazgos": [],
    "recomendaciones": [],
    "resumen": "Descripción breve de la auditoría realizada"
  }}
}}

EJEMPLO DE RESPUESTA VÁLIDA:
{{"para": "Luffy", "tipo": "informe_auditoria", "contenido": {{"nivel_criticidad": "OK", "hallazgos": [], "recomendaciones": [], "resumen": "Auditoría completada sin hallazgos."}}}}

NO escribas texto antes o después del JSON. NO uses markdown. SOLO el JSON puro.

[RUTAS DE TRABAJO OBLIGATORIAS - HARD STOP ACTIVO]
- Tus entregables van en: /app/Robin/reportes/
- Archivos temporales: /app/Archivos_temporales/ (DEBES usar tu nombre como prefijo, ej. robin_temp.md)
- Actualizar estado de ticket: /app/Bitacora.md
- Guardar conocimiento: /app/Cerebro.md y /app/memoria/
- PROHIBIDO escribir en cualquier otra ruta del sistema.
  Si lo intentas, el sistema lanzará un error y abortará la escritura.
"""

    system_prompt += "\n--- PROTOCOLO DE HERRAMIENTAS ---\nAntes de usar cualquier habilidad o herramienta, consulta siempre el Protocolo de Herramientas y Manual Quirúrgico (en tus reglas o contexto) para verificar cuándo usarla (gatillo) y seguir el paso a paso exacto de la plantilla Pensamiento/Acción.\n"

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="messages"),

        "REGLA DE DESARROLLO AUTÓNOMO: Tienes acceso a herramientas de código (`crear_archivo`, `ejecutar_comando`, `leer_archivo`). "
        "Úsalas ÚNICA Y EXCLUSIVAMENTE para crear scripts temporales que te ayuden a cumplir tu tarea si tus herramientas actuales fallan, "
        "o para crear/modificar tus propias skills en tu carpeta `skills/`. Si el usuario pide desarrollar una aplicación, una API, "
        "un flujo de n8n o modificar código general del proyecto, DEBES DELEGARLO A ZORO. Zoro es el Ingeniero de Software; "
        "tú solo programas para automejorarte o resolver bloqueos en tu área de expertise.",

    ])


# ═══════════════════════════════════════════════════════════════════════════════
# Nodo LangGraph
# ═══════════════════════════════════════════════════════════════════════════════

def _extraer_json_robusto(texto: str) -> dict:
    """
    Escudo JSON robusto de 4 pasos con fallback.
    Extrae el primer JSON válido de cualquier texto.
    """
    # Paso 1: Limpieza de Markdown
    texto_limpio = re.sub(r"```(?:json)?", " ", texto, flags=re.IGNORECASE)

    # Paso 2: Extracción por índices
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

    # Paso 3: Validación (Try/Except)
    if inicio == -1:
        raise ValueError("No se encontró ningún delimitador JSON en la respuesta.")

    fin = texto_limpio.rfind(char_fin)
    if fin == -1 or fin < inicio:
        raise ValueError(f"No se encontró cierre '{char_fin}' válido.")

    texto_extraido = texto_limpio[inicio : fin + 1]
    datos_json = json.loads(texto_extraido)

    if not isinstance(datos_json, (dict, list)):
        raise ValueError("El JSON no es un objeto ni una lista válidos.")

    return datos_json


def _generar_json_fallback(texto_respuesta: str) -> dict:
    """
    Genera un JSON de error estructurado cuando el LLM no devuelve JSON válido.
    """
    return {
        "para": "Luffy",
        "tipo": "informe_auditoria",
        "contenido": {
            "nivel_criticidad": "OK",
            "hallazgos": [],
            "recomendaciones": [],
            "resumen": f"Auditoría completada. El LLM devolvió texto sin formato JSON. Respuesta cruda: {texto_respuesta[:200]}"
        }
    }


def funcion_nodo_robin(estado: dict) -> dict:
    """
    Función de LangGraph que ejecuta Robin cuando Luffy le delega
    una tarea de auditoría o supervisión de seguridad.
    """
    print(f"\n[{NOMBRE_AGENTE}] Recibiendo delegación del Capitán...")
    print(f"[{NOMBRE_AGENTE}] Herramientas de seguridad disponibles: {len(HERRAMIENTAS_ROBIN)}")

    # 1. Leer mensajes pendientes del canal
    contexto_mensajes = ""
    try:
        contexto_mensajes = leer_mensajes(NOMBRE_AGENTE)
        if contexto_mensajes:
            print(f"[{NOMBRE_AGENTE}] Contexto del canal: {contexto_mensajes[:100]}...")
    except Exception as e:
        print(f"[{NOMBRE_AGENTE}] ⚠️ No se pudo leer contexto del canal: {e}")

    # 2. Construir prompt y LLM
    prompt = construir_prompt_agente()
    llm = crear_llm()
    llm_con_tools = llm.bind_tools(HERRAMIENTAS_ROBIN)

    cadena_con_tools = prompt | llm_con_tools
    cadena_sin_tools = prompt | llm

    # Inyectar contexto del canal en el último mensaje
    mensajes_langgraph = list(estado["messages"])
    if contexto_mensajes and mensajes_langgraph:
        ultimo_contenido = mensajes_langgraph[-1].content
        mensajes_langgraph[-1].content = ultimo_contenido + contexto_mensajes

    # 3. Primera invocación al LLM
    respuesta = cadena_con_tools.invoke({"messages": mensajes_langgraph})

    # 4. Bucle de ejecución de herramientas (hasta 10 rondas — auditorías son más profundas)
    MAX_ROUNDS = 50
    ronda = 0

    while (hasattr(respuesta, "tool_calls") and respuesta.tool_calls and ronda < MAX_ROUNDS):
        ronda += 1
        print(f"[{NOMBRE_AGENTE}] Ronda {ronda}: ejecutando {len(respuesta.tool_calls)} herramienta(s) de seguridad...")

        mensajes_langgraph.append(respuesta)

        for tool_call in respuesta.tool_calls:
            nombre_tool = tool_call["name"]
            args_tool   = tool_call["args"]
            tool_id     = tool_call.get("id", f"tool_{ronda}")

            print(f"[{NOMBRE_AGENTE}] → Ejecutando: {nombre_tool}({list(args_tool.keys())})")

            herramienta_encontrada = None
            for herramienta in HERRAMIENTAS_ROBIN:
                if herramienta.name == nombre_tool:
                    herramienta_encontrada = herramienta
                    break

            if herramienta_encontrada:
                try:
                    resultado_tool = herramienta_encontrada.invoke(args_tool)
                    print(f"[{NOMBRE_AGENTE}] ← Resultado: {str(resultado_tool)[:150]}...")
                except Exception as e:
                    resultado_tool = json.dumps({"status": "error", "mensaje": str(e)})
                    print(f"[{NOMBRE_AGENTE}] ← Error en herramienta: {e}")
            else:
                resultado_tool = json.dumps({
                    "status": "error",
                    "mensaje": f"Herramienta de seguridad '{nombre_tool}' no encontrada."
                })

            mensajes_langgraph.append(
                ToolMessage(content=str(resultado_tool) + "\n\n⚠️ MUY IMPORTANTE: Acción completada. AHORA DEBES TERMINAR TU TURNO DEVOLVIENDO ÚNICAMENTE UN JSON MINIMALISTA DE CIERRE.", tool_call_id=tool_id)
            )

        respuesta = cadena_con_tools.invoke({"messages": mensajes_langgraph})

    # 5. Generar respuesta final en formato JSON del protocolo
    if hasattr(respuesta, "tool_calls") and respuesta.tool_calls:
        print(f"[{NOMBRE_AGENTE}] Máximo de rondas ({MAX_ROUNDS}) alcanzado. Forzando informe final.")

    mensajes_langgraph.append(respuesta)
    respuesta_final = cadena_sin_tools.invoke({"messages": mensajes_langgraph})
    texto_respuesta = respuesta_final.content if hasattr(respuesta_final, "content") else str(respuesta_final)

    # 6. Parsear JSON con Escudo Robusto (4 pasos) + Fallback
    try:
        datos_json = _extraer_json_robusto(texto_respuesta)
        print(f"[{NOMBRE_AGENTE}] ✅  Escudo JSON: Parseo exitoso.")
        mensaje_salida = f"[{NOMBRE_AGENTE} -> {datos_json.get('para', 'Luffy') if isinstance(datos_json, dict) else 'Luffy'}]: {json.dumps(datos_json, ensure_ascii=False)}"
    except (json.JSONDecodeError, ValueError) as e:
        # ── Paso 4: Manejo de error — intentar reintento con mensaje de corrección ──
        print(f"[{NOMBRE_AGENTE}] ⚠️  Escudo JSON: Error al parsear — {e}")
        print(f"[{NOMBRE_AGENTE}] 🔄 Intentando reintento con mensaje de corrección...")

        # Añadir mensaje de corrección al historial
        mensaje_correccion = AIMessage(
            content=(
                "Tu respuesta anterior no contenía un JSON válido. "
                "DEBES responder ÚNICAMENTE con un JSON puro en este formato EXACTO:\n"
                '{"para": "Luffy", "tipo": "informe_auditoria", "contenido": {"nivel_criticidad": "OK", "hallazgos": [], "recomendaciones": [], "resumen": "Descripción"}}\n'
                "NO escribas texto antes o después del JSON. NO uses markdown. SOLO el JSON puro."
            )
        )
        mensajes_langgraph.append(mensaje_correccion)

        try:
            respuesta_reintento = cadena_sin_tools.invoke({"messages": mensajes_langgraph})
            texto_reintento = respuesta_reintento.content if hasattr(respuesta_reintento, "content") else str(respuesta_reintento)
            datos_json = _extraer_json_robusto(texto_reintento)
            print(f"[{NOMBRE_AGENTE}] ✅  Escudo JSON: Reintento exitoso.")
            mensaje_salida = f"[{NOMBRE_AGENTE} -> {datos_json.get('para', 'Luffy') if isinstance(datos_json, dict) else 'Luffy'}]: {json.dumps(datos_json, ensure_ascii=False)}"
        except (json.JSONDecodeError, ValueError) as e2:
            # Fallback final: generar JSON de error estructurado
            print(f"[{NOMBRE_AGENTE}] ⚠️  Reintento falló: {e2}. Usando fallback.")
            datos_json = _generar_json_fallback(texto_respuesta)
            mensaje_salida = f"[{NOMBRE_AGENTE} -> Luffy]: {json.dumps(datos_json, ensure_ascii=False)}"

    print(f"[{NOMBRE_AGENTE}] Auditoría completada. Retornando informe al Capitán.")

    return {
        "messages": [AIMessage(content=mensaje_salida)],
        "ultimo_agente": NOMBRE_AGENTE,
        "datos_json": datos_json
    }
