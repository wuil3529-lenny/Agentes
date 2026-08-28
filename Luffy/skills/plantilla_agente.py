"""
plantilla_agente.py — Plantilla Base para crear a Zoro, Nami o Robin
=====================================================================
Instrucciones de uso:
1. Copia este archivo y renómbralo (ej. zoro_agent.py).
2. Reemplaza 'NOMBRE_AGENTE' por el nombre de tu agente (ej. 'Zoro').
3. Asegúrate de haber creado memoria_compartida/perfiles/zoro_perfil.json
4. En main.py, importa `funcion_nodo_zoro` y regístralo:
   tripulacion.agregar_agente("Zoro", funcion_nodo_zoro)
"""

import json
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Importamos utilidades de Luffy y la memoria
from luffy_agent import crear_llm
from memory import (
    cargar_perfil_agente, 
    publicar_mensaje, 
    leer_nodo_obsidian,
    leer_mensajes,
    registrar_bitacora,
    guardar_cerebro
)

NOMBRE_AGENTE = "Zoro"  # <-- CAMBIAR AQUÍ

def construir_prompt_agente() -> ChatPromptTemplate:
    """
    Construye el prompt del sistema para este agente, cargando
    sus reglas e identidad desde la memoria compartida.
    """
    # 1. Cargar el perfil del agente
    perfil = cargar_perfil_agente(NOMBRE_AGENTE)
    identidad = perfil.get("presentacion", f"Eres {NOMBRE_AGENTE}, un agente de la tripulación.")
    
    # 2. Cargar las reglas de protocolo desde Obsidian
    reglas = leer_nodo_obsidian("protocolo/Reglas de la Tripulacion.md")
    protocolo = leer_nodo_obsidian("protocolo/Protocolo Inter-Agente.md")

    # 3. Construir el system prompt
    system_prompt = f"""
{identidad}

Tu capitán es Luffy. Él te delegará tareas.
Cuando recibas una tarea, debes procesarla usando tus habilidades.

--- REGLAS ABSOLUTAS ---
{reglas}

--- PROTOCOLO DE COMUNICACIÓN (JSON OBLIGATORIO) ---
{protocolo}
"""
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

def funcion_nodo_zoro(estado: dict) -> dict:
    """
    Esta es la función que ejecuta LangGraph cuando Luffy delega
    una tarea a este agente.
    """
    print(f"[{NOMBRE_AGENTE}] Procesando tarea...")
    llm = crear_llm()
    prompt = construir_prompt_agente()
    
    # --- LECTURA AUTOMÁTICA DE MENSAJES ---
    # El agente lee si tiene mensajes pendientes en el canal antes de actuar
    mensajes_nuevos = leer_mensajes(agente=NOMBRE_AGENTE)
    contexto_mensajes = ""
    if mensajes_nuevos:
        contexto_mensajes = "\n--- MENSAJES EN TU CANAL ---\n"
        for m in mensajes_nuevos:
            contexto_mensajes += f"De {m['de']}: {json.dumps(m['contenido'])}\n"
    # --------------------------------------

    # Preparar el invocador uniendo el estado de LangGraph + Mensajes de Memoria
    cadena = prompt | llm
    
    # Modificamos temporalmente el último mensaje del usuario para inyectarle
    # los mensajes del canal si los hay, para que el LLM los tenga en cuenta.
    mensajes_langgraph = estado["messages"]
    if contexto_mensajes and mensajes_langgraph:
        ultimo_mensaje = mensajes_langgraph[-1].content
        mensajes_langgraph[-1].content = ultimo_mensaje + contexto_mensajes

    try:
        respuesta_ia = cadena.invoke({"messages": mensajes_langgraph})
        texto_respuesta = respuesta_ia.content
        
        print(f"\n--- RESPUESTA RAW DE {NOMBRE_AGENTE} ---\n{texto_respuesta}\n---------------------------")

        # Intentar extraer el JSON de la respuesta del LLM
        json_str = texto_respuesta
        if "```json" in texto_respuesta:
            json_str = texto_respuesta.split("```json")[1].split("```")[0].strip()
            
        datos_json = json.loads(json_str)
        
        if isinstance(datos_json, dict):
            # Enviar el mensaje al canal compartido
            publicar_mensaje(
                de=NOMBRE_AGENTE,
                para=datos_json.get("para", "Luffy"),
                tipo=datos_json.get("tipo", "resultado"),
                contenido=datos_json.get("contenido", {"texto": texto_respuesta})
            )
            
            # --- MOTOR DE ACCIONES DE MEMORIA (Los 3 Pilares) ---
            acciones = datos_json.get("acciones_memoria", {})
            
            if "registrar_bitacora" in acciones:
                entrada = acciones["registrar_bitacora"]
                print(f"[{NOMBRE_AGENTE}] Escribiendo en bitácora...")
                registrar_bitacora(NOMBRE_AGENTE, entrada)
                
            if "guardar_cerebro" in acciones:
                for cerebro_entry in acciones["guardar_cerebro"]:
                    print(f"[{NOMBRE_AGENTE}] Guardando en cerebro: {cerebro_entry.get('tema')}")
                    guardar_cerebro(
                        agente=NOMBRE_AGENTE,
                        tema=cerebro_entry.get("tema", "Sin título"),
                        contenido=cerebro_entry.get("contenido", ""),
                        ruta_local=cerebro_entry.get("ruta_local")
                    )
            # ------------------------------------
            
            # Formatear el mensaje para que LangGraph (y Luffy) lo entiendan en el siguiente ciclo
            mensaje_salida = f"[{NOMBRE_AGENTE} -> Luffy]: {json.dumps(datos_json, ensure_ascii=False)}"
        else:
            raise ValueError("No se encontró JSON en la respuesta")
            
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[{NOMBRE_AGENTE}] Error parseando JSON: {e}")
        # Notificar error en el canal (Pilar 1)
        publicar_mensaje(
            de=NOMBRE_AGENTE, para="Luffy", tipo="error",
            contenido={"texto": f"Fallo al generar JSON estructurado: {e}", "datos": {"raw": texto_respuesta}}
        )
        mensaje_salida = f"[{NOMBRE_AGENTE} -> Luffy]: Error de formato. Dijo: {texto_respuesta}"

    return {"messages": [AIMessage(content=mensaje_salida)]}
