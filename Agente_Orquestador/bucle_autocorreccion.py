import json
import re
import sys
import io

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import TypedDict, Sequence, Annotated, List, Any
import operator
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END


# ══════════════════════════════════════════════════════════════════════════════
# Clasificador de Causa Raíz de Errores
# ══════════════════════════════════════════════════════════════════════════════

def _clasificar_error(stderr_o_resultado: str) -> str:
    """
    Analiza el stderr o resultado de error y devuelve una instrucción de corrección
    específica basada en la causa raíz detectada.

    Categorías:
      - ModuleNotFoundError / ImportError   → instalar paquete con pip
      - Port / Address already in use        → cambiar o liberar el puerto
      - PermissionError / Permission denied  → verificar rutas y permisos
      - FileNotFoundError / No such file     → verificar existencia con listar_directorio
      - SyntaxError / IndentationError       → corregir sintaxis del script
      - Timeout                              → aumentar timeout o verificar red
      - JSONDecodeError / json.decoder       → el archivo no es JSON válido
      - ConnectionError / ECONNREFUSED       → el servicio no está corriendo
      - exit code distinto de 0 (genérico)  → leer traceback completo y corregir
    """
    texto = str(stderr_o_resultado).lower()

    # ── ModuleNotFoundError / ImportError ────────────────────────────────────
    m = re.search(r"no module named '?([\w\-\.]+)'?", texto)
    if m or "importerror" in texto or "modulenotfounderror" in texto:
        modulo = m.group(1) if m else "<módulo desconocido>"
        return (
            f"### CAUSA RAÍZ: Módulo Python faltante — '{modulo}' ###\n"
            f"INSTRUCCIÓN OBLIGATORIA: Usa la herramienta `python_pip_instalar` con "
            f"paquetes='{modulo}' y el directorio del proyecto ANTES de volver a ejecutar el script.\n"
            f"Ejemplo: python_pip_instalar(paquetes='{modulo}', directorio_proyecto='/app/Subagente_Desarrollo/proyectos/')"
        )

    # ── Puerto ocupado ────────────────────────────────────────────────────────
    if re.search(r"address already in use|port.*in use|eaddrinuse|bind.*failed", texto):
        return (
            "### CAUSA RAÍZ: Puerto ya ocupado ###\n"
            "INSTRUCCIÓN OBLIGATORIA: Identifica qué proceso usa el puerto con "
            "`ejecutar_comando('netstat -tulpn | grep <puerto>', '/app/')` y "
            "cámbialo en el script o detén el proceso ocupando el puerto antes de reintentar."
        )

    # ── Permisos ──────────────────────────────────────────────────────────────
    if re.search(r"permission denied|permissionerror|access denied|errno 13", texto):
        return (
            "### CAUSA RAÍZ: Error de permisos ###\n"
            "INSTRUCCIÓN OBLIGATORIA: Verifica que la ruta de destino esté dentro de "
            "'/app/Subagente_Desarrollo/' o '/app/Archivos_temporales/'. Rutas fuera de estos directorios "
            "están bloqueadas. Si la ruta es correcta, usa `ejecutar_comando('ls -la <dir>', '/app/')` "
            "para inspeccionar los permisos reales."
        )

    # ── Archivo no encontrado ─────────────────────────────────────────────────
    if re.search(r"filenotfounderror|no such file|no existe|not found.*file|errno 2", texto):
        return (
            "### CAUSA RAÍZ: Archivo o directorio no encontrado ###\n"
            "INSTRUCCIÓN OBLIGATORIA: Usa `listar_directorio` para verificar que la ruta "
            "existe ANTES de intentar leer o ejecutar. Si el archivo no existe, créalo "
            "primero con `crear_archivo`."
        )

    # ── Error de sintaxis Python ──────────────────────────────────────────────
    if re.search(r"syntaxerror|indentationerror|invalid syntax|unexpected indent", texto):
        return (
            "### CAUSA RAÍZ: Error de sintaxis en el script Python ###\n"
            "INSTRUCCIÓN OBLIGATORIA: Lee el traceback completo, localiza el número de línea "
            "exacto donde está el error, y usa `crear_archivo` para reescribir el script "
            "completo con la sintaxis corregida antes de volver a ejecutar."
        )

    # ── Timeout ───────────────────────────────────────────────────────────────
    if re.search(r"timeout|timed out|time.?out|superado.*seg", texto):
        return (
            "### CAUSA RAÍZ: Timeout de ejecución ###\n"
            "INSTRUCCIÓN OBLIGATORIA: El comando tardó demasiado. Verifica conexión de red "
            "si es una llamada HTTP, o simplifica el script si es un proceso de larga duración. "
            "Si es una instalación de pip, puede necesitar un timeout mayor."
        )

    # ── JSON inválido ─────────────────────────────────────────────────────────
    if re.search(r"jsondecode|json.*error|invalid.*json|expecting.*value", texto):
        return (
            "### CAUSA RAÍZ: JSON con sintaxis inválida ###\n"
            "INSTRUCCIÓN OBLIGATORIA: Lee el contenido del archivo con `leer_archivo`, "
            "identifica la línea con error de sintaxis (coma extra, comilla sin cerrar, etc.), "
            "y usa `crear_archivo` para reescribirlo con JSON válido."
        )

    # ── Servicio no disponible / Conexión rechazada ───────────────────────────
    if re.search(r"connection refused|econnrefused|no está accesible|connectionerror|failed to connect", texto):
        return (
            "### CAUSA RAÍZ: Servicio no disponible o conexión rechazada ###\n"
            "INSTRUCCIÓN OBLIGATORIA: El servicio destino no está corriendo. "
            "Si es n8n, usa `n8n_iniciar()` primero y espera a que el healthcheck responda. "
            "Si es otro servicio, verifica que el puerto y host sean correctos en las variables de entorno."
        )

    # ── Error genérico (exit code != 0) ──────────────────────────────────────
    return (
        "### CAUSA RAÍZ: Error de ejecución (causa no categorizada) ###\n"
        "PROTOCOLO DE AUTO-DIAGNÓSTICO OBLIGATORIO:\n"
        "  1. Lee el traceback COMPLETO del campo 'stderr' del resultado anterior.\n"
        "  2. Identifica la línea EXACTA que falló.\n"
        "  3. Determina si es un problema de: datos, lógica, red, dependencias o permisos.\n"
        "  4. Aplica UNA corrección específica y reintenta.\n"
        "PROHIBIDO: adivinar soluciones al azar o repetir el mismo comando sin cambios."
    )

def agregar_mensajes(left: list, right: list):
    """Función reducer para acumular mensajes en el estado de LangGraph."""
    return left + right

class EstadoAgente(TypedDict):
    messages: Annotated[list[BaseMessage], agregar_mensajes]
    ultimo_agente: str
    datos_json: dict
    intentos_fallidos: int
    historial_errores: Annotated[list[str], operator.add]
    objetivo_ticket: str
    requiere_reflexion: bool
    historial_herramientas: Annotated[list[str], operator.add]  # Pilar 3: Anti-Bucle

def crear_grafo_agente(nombre_agente: str, herramientas: list, llm, prompt, funcion_qa_gherkin=None, max_reintentos: int = 3):
    """
    Construye un StateGraph (Bucle Interno) reutilizable para cualquier agente de la tripulación.
    Implementa el patrón de Reflexión/LATS con Nodo_Ejecutor y Nodo_Reflexion.
    """
    llm_con_tools = llm.bind_tools(herramientas)
    llm_sin_tools = llm

    def _ejecutar_herramienta(nombre_tool, args_tool, herramientas_disponibles):
        for h in herramientas_disponibles:
            if h.name == nombre_tool:
                try:
                    return h.invoke(args_tool)
                except Exception as e:
                    return json.dumps({"status": "error", "mensaje": f"Excepción interna: {str(e)}"})
        return json.dumps({"status": "error", "mensaje": f"Herramienta '{nombre_tool}' no encontrada."})

    def nodo_ejecutor(state: EstadoAgente):
        print(f"\n[{nombre_agente} - Nodo_Ejecutor] Analizando situación...")
        mensajes = state["messages"]
        intentos = state.get("intentos_fallidos", 0)
        historial_tools = state.get("historial_herramientas", [])
        
        # Invocamos al LLM con las herramientas disponibles
        cadena = prompt | llm_con_tools
        respuesta_llm = cadena.invoke({"messages": mensajes})
        
        if hasattr(respuesta_llm, "tool_calls") and respuesta_llm.tool_calls:
            nuevos_mensajes = [respuesta_llm]
            hubo_error = False
            mensajes_error = []
            nuevas_firmas = []
            
            for tool_call in respuesta_llm.tool_calls:
                nombre_tool = tool_call["name"]
                args_tool = tool_call["args"]
                tool_id = tool_call.get("id", "tool_id")
                
                # ═══ PILAR 3: Filtro Anti-Bucle ═══
                firma = f"{nombre_tool}:{json.dumps(args_tool, sort_keys=True, default=str)}"
                if firma in historial_tools:
                    print(f"[{nombre_agente}] 🧊 Anti-Bucle: {nombre_tool} CONGELADA por redundancia.")
                    msg_congelar = (
                        f"### ALERTA DE REDUNDANCIA (ANTI-BUCLE) ###\n"
                        f"Ya ejecutaste '{nombre_tool}' con los mismos parámetros y obtuviste datos.\n"
                        f"Tienes PROHIBIDO volver a llamar esa herramienta.\n"
                        f"INSTRUCCIÓN OBLIGATORIA: Lee los datos que ya tienes en tu historial de mensajes, "
                        f"analízalos en detalle, extrae la información solicitada por el usuario, "
                        f"y procede a emitir tu JSON de cierre con los campos 'resumen' (describiendo "
                        f"el hallazgo real) y 'evidencia_hallazgo' (con los datos extraídos).\n"
                        f"Objetivo original: {state.get('objetivo_ticket', 'Ejecutar orden del Capitán')}"
                    )
                    # Generar ToolMessages de placeholder para cada tool_call del AIMessage
                    # para que el AIMessage con tool_calls siempre esté seguido de ToolMessages
                    # (requisito obligatorio de la API de OpenAI: todo tool_call debe tener su ToolMessage)
                    nuevos_mensajes = [respuesta_llm]
                    for tc in respuesta_llm.tool_calls:
                        tc_id = tc.get("id", "tool_id")
                        nuevos_mensajes.append(ToolMessage(
                            content=f"Herramienta '{tc['name']}' CONGELADA por redundancia (Anti-Bucle). No se ejecutó.",
                            tool_call_id=tc_id,
                            name=tc['name']
                        ))
                    from langchain_core.messages import HumanMessage
                    nuevos_mensajes.append(HumanMessage(content=msg_congelar))
                    
                    return {
                        "messages": nuevos_mensajes,
                        "requiere_reflexion": False
                    }
                
                print(f"[{nombre_agente}] -> Ejecutando: {nombre_tool}({list(args_tool.keys())})")
                resultado = _ejecutar_herramienta(nombre_tool, args_tool, herramientas)
                res_str = str(resultado)
                print(f"[{nombre_agente}] ← Resultado: {res_str[:120]}...")
                
                nuevos_mensajes.append(ToolMessage(content=res_str, tool_call_id=tool_id, name=nombre_tool))
                
                # Evaluación de error
                es_error = False
                try:
                    res_dict = json.loads(res_str) if isinstance(resultado, str) else resultado
                    if isinstance(res_dict, dict) and res_dict.get("status") in ["error", "warning"]:
                        es_error = True
                except Exception:
                    # Si no es JSON y contiene palabras de error
                    if re.search(r"error|exception|fail|fallo", res_str, re.IGNORECASE):
                        es_error = True
                
                # Evaluación adicional con QA Gherkin (Doble Validación)
                if not es_error and funcion_qa_gherkin:
                    _TOOLS_EVALUABLES = {
                        "n8n_api_call", "n8n_guardar_workflow", "crear_archivo", "git_commit",
                        "ejecutar_comando", "python_ejecutar_script"  # Fase 3: Cobertura extendida
                    }
                    if nombre_tool in _TOOLS_EVALUABLES:
                        if not funcion_qa_gherkin(resultado, objetivo_ticket=state.get("objetivo_ticket", ""), nombre_agente=nombre_agente):
                            es_error = True
                
                if es_error:
                    hubo_error = True
                    mensajes_error.append(f"Fallo en {nombre_tool}: {res_str}")
                else:
                    # SOLO registramos la firma si la herramienta tuvo éxito
                    # Así, si falla, el LLM puede volver a intentarlo con los mismos parámetros
                    nuevas_firmas.append(firma)

            if hubo_error:
                # Si falló, preparamos la bandera para ir a reflexión
                return {
                    "messages": nuevos_mensajes,
                    "intentos_fallidos": intentos + 1,
                    "historial_errores": [f"Intento {intentos+1}: " + " | ".join(mensajes_error)],
                    "requiere_reflexion": True,
                    "historial_herramientas": nuevas_firmas
                }
            else:
                # Éxito en las herramientas
                print(f"[{nombre_agente}] ✅ Herramientas ejecutadas con éxito.")
                # Devolvemos el control al LLM para que lea el resultado de las herramientas y decida su siguiente paso.
                return {
                    "messages": nuevos_mensajes,
                    "requiere_reflexion": False,
                    "historial_herramientas": nuevas_firmas
                }
        else:
            # No llamó a herramientas, simplemente respondió con texto
            return {"messages": [respuesta_llm]}

    def nodo_reflexion(state: EstadoAgente):
        intentos = state.get("intentos_fallidos", 0)
        errores = state.get("historial_errores", [])
        print(f"\n[{nombre_agente} - Nodo_Reflexion] ⚠️ Fallo detectado (Intento {intentos}/{max_reintentos}).")
        
        if intentos >= max_reintentos:
            print(f"[{nombre_agente} - Nodo_Reflexion] ❌ Límite de reintentos alcanzado. Escalando a Agente_Orquestador.")
            ultimo_error = errores[-1] if errores else "Error desconocido"
            msg_error = (
                f"Has alcanzado el límite máximo de {max_reintentos} intentos. "
                "Genera INMEDIATAMENTE un JSON estricto dirigido a Agente_Orquestador explicando que fallaste y adjunta el traceback: "
                f"{ultimo_error}"
            )
            return {"messages": [HumanMessage(content=msg_error)]}
        else:
            ultimo_error = errores[-1] if errores else "Error desconocido"
            # ═══ PROTOCOLO DE AUTO-DIAGNÓSTICO: Clasificar causa raíz antes de reflexionar ═══
            instruccion_especifica = _clasificar_error(ultimo_error)
            prompt_reflexion = (
                f"### INSTRUCCIÓN DE AUTOCORRECCIÓN (Intento {intentos}/{max_reintentos}) ###\n"
                f"Objetivo original: {state.get('objetivo_ticket', 'Ejecutar orden del Capitán')}\n\n"
                f"DIAGNÓSTICO DEL SISTEMA:\n"
                f"Traceback/Stderr completo: {ultimo_error}\n\n"
                f"{instruccion_especifica}\n\n"
                f"Te quedan {max_reintentos - intentos} intento(s). "
                f"Aplica la corrección específica indicada arriba y reintenta.\n"
                f"PROHIBIDO repetir el mismo comando sin cambios."
            )
            return {"messages": [HumanMessage(content=prompt_reflexion)]}

    def determinar_siguiente_nodo(state: EstadoAgente) -> str:
        mensajes = state["messages"]
        if not mensajes:
            return END
        
        ultimo_mensaje = mensajes[-1]
        
        # Si el último mensaje es de Reflexión (SystemMessage), vamos al Ejecutor
        if isinstance(ultimo_mensaje, SystemMessage):
            return "Nodo_Ejecutor"
            
        # Si el último mensaje es AIMessage y NO tiene tool_calls, significa que ya concluyó
        if isinstance(ultimo_mensaje, AIMessage) and not hasattr(ultimo_mensaje, "tool_calls"):
            return END
        if isinstance(ultimo_mensaje, AIMessage) and not ultimo_mensaje.tool_calls:
            return END
            
        # Si el último es un ToolMessage, verificamos si requiere reflexión por fallo
        if isinstance(ultimo_mensaje, ToolMessage):
            if state.get("requiere_reflexion", False):
                return "Nodo_Reflexion"
            else:
                # Si tuvo éxito, vuelve al ejecutor para que el LLM lea el output
                return "Nodo_Ejecutor"
                
        return END

    # Construir el Grafo
    workflow = StateGraph(EstadoAgente)
    
    workflow.add_node("Nodo_Ejecutor", nodo_ejecutor)
    workflow.add_node("Nodo_Reflexion", nodo_reflexion)
    
    workflow.set_entry_point("Nodo_Ejecutor")
    
    workflow.add_conditional_edges(
        "Nodo_Ejecutor",
        determinar_siguiente_nodo,
        {
            "Nodo_Reflexion": "Nodo_Reflexion",
            "Nodo_Ejecutor": "Nodo_Ejecutor",
            END: END
        }
    )
    
    workflow.add_edge("Nodo_Reflexion", "Nodo_Ejecutor")
    
    return workflow.compile()


# ══════════════════════════════════════════════════════════════════════════════
# Interceptor Universal de Herramientas (Para bucles OpenAI Function Calling)
# ══════════════════════════════════════════════════════════════════════════════

def interceptar_tool_call(
    nombre_tool: str,
    args_tool: dict,
    func_ejecutar: Any,
    objetivo_ticket: str = "",
    nombre_agente: str = "Agente",
    historial_firmas: list = None,
    conteo_fallos: dict = None,
    max_reintentos: int = 3,
) -> tuple[str, bool, str]:
    """
    Interceptor Universal de Herramientas para la Tripulación IA.
    Ejecuta y valida cualquier tool call bajo:
      1. Filtro Anti-Bucle (Pilar 3: Congelamiento si se repite con idénticos argumentos).
      2. Ejecución controlada con captura de excepciones.
      3. QA Gherkin Universal (Capa 1: Red/Infraestructura + Capa 2: Contenido/Cumplimiento).
      4. Clasificador de Causa Raíz (_clasificar_error) y diagnóstico de autocorrección.

    Retorna:
      (contenido_salida: str, es_exito: bool, firma: str)
    """
    firma = f"{nombre_tool}:{json.dumps(args_tool, sort_keys=True, default=str)}"

    # ─── 1. PILAR 3: Filtro Anti-Bucle ──────────────────────────────────────────
    if historial_firmas is not None and firma in historial_firmas:
        print(f"[{nombre_agente}] [Anti-Bucle] Herramienta '{nombre_tool}' CONGELADA por redundancia.")
        msg_congelar = (
            f"### ALERTA DE REDUNDANCIA (ANTI-BUCLE) ###\n"
            f"La herramienta '{nombre_tool}' ha sido CONGELADA por el sistema anti-bucle.\n"
            f"Ya ejecutaste esta herramienta con exactamente los mismos parámetros y obtuviste datos.\n"
            f"Tienes PROHIBIDO volver a llamar '{nombre_tool}' con estos argumentos repetidos.\n"
            f"INSTRUCCIÓN OBLIGATORIA: Lee la información que ya obtuviste en tu contexto, "
            f"analízala minuciosamente y procede con la entrega o cierre del ticket.\n"
            f"Objetivo: {objetivo_ticket or 'Completar tarea asignada'}"
        )
        return msg_congelar, False, firma

    # ─── 2. Ejecución de la herramienta ─────────────────────────────────────────
    print(f"[{nombre_agente}] -> Ejecutando: {nombre_tool}({list(args_tool.keys())})")
    try:
        resultado = func_ejecutar(nombre_tool, args_tool)
    except Exception as exc:
        resultado = json.dumps({"status": "error", "mensaje": f"Excepción en ejecución: {str(exc)}"})

    res_str = str(resultado)

    # ─── 3. Detección base de fallos ────────────────────────────────────────────
    es_error = False
    motivo_error = ""
    try:
        res_dict = json.loads(res_str) if isinstance(resultado, str) else resultado
        if isinstance(res_dict, dict) and str(res_dict.get("status", "")).lower() in ["error", "warning"]:
            es_error = True
            motivo_error = str(res_dict.get("mensaje", res_str))
    except Exception:
        if re.search(r"\b(error|exception|traceback|syntaxerror|importerror|filenotfounderror)\b", res_str, re.IGNORECASE):
            es_error = True
            motivo_error = res_str

    # ─── 4. Doble Validación QA Gherkin ─────────────────────────────────────────
    if not es_error:
        try:
            try:
                from qa_gherkin import evaluar_qa_gherkin
            except Exception:
                from Agente_Orquestador.qa_gherkin import evaluar_qa_gherkin
            gherkin_aprobado = evaluar_qa_gherkin(
                resultado_operacion=resultado,
                objetivo_ticket=objetivo_ticket,
                nombre_agente=nombre_agente
            )
            if not gherkin_aprobado:
                es_error = True
                motivo_error = "QA Gherkin rechazó el resultado: contenido insuficiente o fallo de infraestructura."
        except Exception as qae:
            print(f"[{nombre_agente}] Aviso al evaluar QA Gherkin: {qae}")

    # ─── 5. Clasificador de Causa Raíz y Autocorrección ─────────────────────────
    if es_error:
        if conteo_fallos is not None:
            conteo_fallos[nombre_tool] = conteo_fallos.get(nombre_tool, 0) + 1
            intento = conteo_fallos[nombre_tool]
        else:
            intento = 1

        diagnostico = _clasificar_error(res_str if not motivo_error else f"{motivo_error}\n{res_str}")
        contenido_salida = (
            f"### FALLO DETECTADO EN {nombre_tool} (Intento {intento}/{max_reintentos}) ###\n"
            f"Resultado devuelto:\n{res_str[:400]}\n\n"
            f"{diagnostico}\n"
        )
        if intento >= max_reintentos:
            contenido_salida += (
                f"\n[ALERTA] LÍMITE DE REINTENTOS ({max_reintentos}) ALCANZADO PARA {nombre_tool}.\n"
                f"Escala este ticket inmediatamente al Agente_Orquestador con el resumen del error."
            )
        return contenido_salida, False, firma
    else:
        # Éxito confirmado
        print(f"[{nombre_agente}] [OK] Herramienta '{nombre_tool}' validada y aprobada.")
        if historial_firmas is not None:
            historial_firmas.append(firma)
        return res_str, True, firma
