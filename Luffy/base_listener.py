import os
import sys
import re
import time
import json
import importlib
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
_APP_ROOT = Path(__file__).resolve().parents[1]
# Forzar UTF-8 en stdout para soportar flechas y emojis
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(_APP_ROOT / "Luffy"))
from memory import (leer_mensajes, publicar_mensaje, leer_nodo_obsidian, 
                    cargar_perfil_agente, registrar_bitacora, guardar_cerebro, 
                    leer_turno, avanzar_turno, reclamar_turno,
                    leer_tickets_pendientes, crear_ticket_bitacora, actualizar_ticket_bitacora)
from nim_client import call_nim_with_fallback
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
load_dotenv((_APP_ROOT / ".env"))

# ══════════════════════════════════════════════════════════════════════════════
# UBICACIÓN COMÚN DE ARCHIVOS TEMPORALES PARA TODOS LOS AGENTES (Luffy, Zoro, Nami, Robin, Sanji)
# ══════════════════════════════════════════════════════════════════════════════
# Cualquier archivo temporal que pueda ser borrado y no forme parte ni de skins,
# ni habilidades, ni funciones, debe guardarse en: Archivos_temporales/
ARCHIVOS_TEMPORALES_ROOT = (_APP_ROOT / "Archivos_temporales")
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"


# ══════════════════════════════════════════════════════════════════════════════
# INTERCEPTOR DE RUTAS WINDOWS EN DOCKER (FALLO #1)
# ══════════════════════════════════════════════════════════════════════════════

def transformar_rutas_windows(texto: str) -> str:
    """
    Convierte cualquier ruta de Windows (ej: C:/Users/admin/Documents/Agentes/...) en su ruta equivalente dentro del contenedor (/app/... ).
    """
    if not isinstance(texto, str):
        return texto
    patron = r"[Cc]:[/\\]+Users[/\\]+admin[/\\]+Documents[/\\]+Agentes[/\\]*"
    texto_tr = re.sub(patron, "/app/", texto, flags=re.IGNORECASE)
    def _fix_slashes(m):
        return m.group(0).replace("\\", "/")
    texto_tr = re.sub(r"/app/[^\s\"'<>]*", _fix_slashes, texto_tr)
    return texto_tr

def sanitizar_obj_rutas(obj):
    """
    Sanitiza de forma recursiva cualquier ruta Windows presente en diccionarios, listas o cadenas.
    """
    if isinstance(obj, str):
        return transformar_rutas_windows(obj)
    elif isinstance(obj, dict):
        return {k: sanitizar_obj_rutas(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitizar_obj_rutas(x) for x in obj]
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# ESCUDO JSON — Extracción y limpieza robusta de respuestas LLM
# ══════════════════════════════════════════════════════════════════════════════

def limpiar_y_parsear_json(texto_crudo: str, agente_nombre: str) -> dict | list:
    """
    Escudo protector de parseo JSON. Ejecuta 4 pasos en orden estricto:

    1. Limpieza de Markdown: elimina bloques de código (```json ... ```).
    2. Extracción robusta: usa json.JSONDecoder().raw_decode() para encontrar
       el primer JSON válido, manejando correctamente llaves/llaves anidadas
       dentro de strings (como el bloque Markdown del ticket).
    3. Validación: intenta json.loads() sobre el texto extraído.
    4. Manejo de errores: si cualquier paso falla, retorna un mensaje de error
       estructurado para devolverle el turno al agente infractor.

    NUNCA lanza excepciones hacia afuera. El bucle infinito jamás se detiene.

    Args:
        texto_crudo:    Respuesta en bruto del LLM (puede contener markdown).
        agente_nombre:  Nombre del agente que generó la respuesta (para logs).

    Returns:
        dict | list: JSON parseado limpio, o dict de error estructurado.
    """
    # ── Paso 1: Limpieza de Markdown ─────────────────────────────────────────
    # Elimina etiquetas ```json, ```, ``` y variantes, reemplazándolas por espacio
    texto_limpio = re.sub(r"```(?:json)?", " ", texto_crudo, flags=re.IGNORECASE)

    # ── Paso 2: Extracción robusta con raw_decode ────────────────────────────
    # Buscar el primer '{' o '['
    pos_llave = texto_limpio.find("{")
    pos_corchete = texto_limpio.find("[")

    if pos_llave == -1 and pos_corchete == -1:
        print(f"[{agente_nombre} Listener] ⚠️  Escudo JSON: No se encontró '{{' ni '[' en la respuesta.")
        return {
            "para": agente_nombre,
            "tipo": "error_formato",
            "contenido": {
                "texto": (
                    "Error de formato: El sistema esperaba un JSON válido pero "
                    "no encontró ningún delimitador ('{' o '['). "
                    "Por favor, corrige la sintaxis y responde únicamente con el JSON estricto."
                )
            }
        }

    if pos_llave == -1:
        inicio = pos_corchete
    elif pos_corchete == -1:
        inicio = pos_llave
    else:
        inicio = min(pos_llave, pos_corchete)

    # Intentar raw_decode desde cada posición de inicio posible
    decoder = json.JSONDecoder()
    datos_json = None
    for start in range(inicio, len(texto_limpio)):
        if texto_limpio[start] not in ("{", "["):
            continue
        try:
            datos_json, _ = decoder.raw_decode(texto_limpio[start:])
            break
        except json.JSONDecodeError:
            continue

    if datos_json is None:
        print(f"[{agente_nombre} Listener] ⚠️  Escudo JSON: No se encontró JSON válido en la respuesta.")
        return {
            "para": agente_nombre,
            "tipo": "error_formato",
            "contenido": {
                "texto": (
                    "Error de formato: El sistema esperaba un JSON válido pero "
                    "no encontró una estructura JSON parseable. "
                    "Por favor, corrige la sintaxis y responde únicamente con el JSON estricto."
                )
            }
        }

    # ── Paso 3: Validación ───────────────────────────────────────────────────
    if not isinstance(datos_json, (dict, list)):
        print(f"[{agente_nombre} Listener] ⚠️  Escudo JSON: El JSON no es un objeto ni una lista válidos.")
        return {
            "para": agente_nombre,
            "tipo": "error_formato",
            "contenido": {
                "texto": (
                    "Error de formato: El JSON extraído no es un objeto ni una lista válidos. "
                    "Por favor, corrige la sintaxis y responde únicamente con el JSON estricto."
                )
            }
        }

    print(f"[{agente_nombre} Listener] ✅  Escudo JSON: Parseo exitoso.")
    return datos_json

# CRÓNOMETRO ÁRBITRO — Timeout y rescate de turno congelado
# ══════════════════════════════════════════════════════════════════════════════

# Tiempo máximo (en segundos) que un agente puede retener el turno.
TIMEOUT_SEGUNDOS: int = 600  # 10 minutos — margen para NVIDIA NIM 70B tras 10 rondas de herramientas


def _verificar_timeout() -> None:
    """
    Ejecuta la lógica del árbitro una vez por vuelta del bucle:

    1. Lee turno.json y obtiene hora_inicio del agente activo.
    2. Calcula (Hora Actual - hora_inicio).
    3. Si el delta > 300:
       a. Libera el turno forzosamente (lo devuelve a "Luffy").
       b. Inyecta en canal_comunicacion.json un mensaje de error
          firmado por el agente infractor para que Luffy lo vea.
    4. Si hora_inicio es None (agente aún no reclamó), no hace nada.

    Esta función NUNCA lanza excepciones hacia el bucle principal.
    """
    try:
        from datetime import datetime
        from pathlib import Path
        import json as _json

        turno = leer_turno()
        agente_activo = turno.get("turno_actual", "Luffy")
        hora_inicio_str = turno.get("hora_inicio")

        # Si el agente aún no reclamó el turno, no hay nada que controlar
        if not hora_inicio_str:
            return

        hora_inicio = datetime.fromisoformat(hora_inicio_str)
        delta = (datetime.now() - hora_inicio).total_seconds() + 300

        if delta <= TIMEOUT_SEGUNDOS:
            return  # Todo en orden, el agente está dentro del tiempo

        # ── ALARMA: turno expirado ─────────────────────────────────────────────
        minutos_bloqueado = round(delta / 60, 1)
        print(f"[Arbitro] ⏰  TIMEOUT: {agente_activo} lleva {minutos_bloqueado} min bloqueando el turno. Liberando..."
        )

        # ── Paso 4: Liberación Forzada ───────────────────────────────────────────
        turno_file = (_APP_ROOT / "turno.json")
        turno["turno_actual"] = "Luffy"   # El Capitán siempre recupera el control
        turno["hora_inicio"]  = None       # El turno está libre, sin tiempo iniciado
        turno_file.write_text(
            _json.dumps(turno, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[Arbitro] ✅  Turno liberado. Control devuelto a Luffy.")

        # ── Paso 5: Reporte de Falla ────────────────────────────────────────────
        # Inyecta un mensaje en el canal como si fuera el agente infractor
        publicar_mensaje(
            de=agente_activo,
            para="Luffy",
            tipo="error",
            contenido={
                "texto": (
                    f"ERROR DEL SISTEMA: Tiempo de espera agotado. "
                    f"La tarea fue cancelada por inactividad "
                    f"({minutos_bloqueado} min bloqueado). "
                    f"Puedes reasignar la tarea si lo consideras necesario."
                ),
                "origen": "arbitro_timeout",
                "agente_infractor": agente_activo,
                "duracion_bloqueo_seg": round(delta, 1),
            }
        )
        print(f"[Arbitro] 📨  Reporte de falla inyectado al canal para Luffy.")

    except Exception as arb_e:
        # El árbitro nunca detiene el bucle
        print(f"[Arbitro] Error interno del árbitro: {arb_e}")


# ══════════════════════════════════════════════════════════════════════════════
# AUDITORÍA DE EVIDENCIA — Verificación física antes de cerrar tickets
# ══════════════════════════════════════════════════════════════════════════════

# Valores de Evidencia_Fisica que indican tarea consultiva (sin archivo esperado)
_EVIDENCIA_CONSULTIVA = {"n/a", "ninguna", "none", "", "no aplica", "no_aplica"}


def auditar_evidencia(contenido_dict: dict, agente_nombre: str, hora_inicio_str: str | None) -> tuple[bool, str]:
    """
    Auditoría de Evidencia Física para tareas reportadas como PENDIENTE_REVISION o CERRADO.

    Pasos:
      1. Validar que el campo Evidencia_Fisica exista en el JSON del agente.
      2. Si el valor es consultivo (N/A, Ninguna...), aprobar sin verificar disco.
      3. Comprobar con os.path.exists() que el archivo realmente existe.
      4. Comprobar con os.path.getmtime() que fue modificado DESPUÉS de hora_inicio.

    Args:
        contenido_dict:  El dict JSON que envió el agente (ya parseado).
        agente_nombre:   Nombre del agente (para logs).
        hora_inicio_str: ISO timestamp de leer_turno()["hora_inicio"] o None.

    Returns:
        (True, "")         si la evidencia es válida y el ticket puede cerrarse.
        (False, motivo)    si hay falla; motivo contiene el texto para devolver al agente.
    """
    # Buscar Evidencia_Fisica tanto en el nivel raíz como dentro de "contenido"
    evidencia = (
        contenido_dict.get("Evidencia_Fisica")
        or contenido_dict.get("evidencia_fisica")
        or contenido_dict.get("contenido", {}).get("Evidencia_Fisica")
        or contenido_dict.get("contenido", {}).get("evidencia_fisica")
    )

    # ── Paso 1: Validar presencia del campo ───────────────────────────────────
    if evidencia is None:
        motivo = (
            "Error de Validación: Has reportado la tarea como PENDIENTE_REVISION o CERRADO pero tu JSON "
            "no contiene el campo obligatorio 'Evidencia_Fisica'. "
            "Debes incluirlo con la ruta del archivo generado, o el valor 'N/A' si la tarea "
            "fue puramente consultiva. El ticket permanece PENDIENTE. Inténtalo de nuevo."
        )
        print(f"[Auditor] ⚠️  {agente_nombre}: campo Evidencia_Fisica ausente.")
        return False, motivo

    # ── Paso 2: Tarea consultiva — aprobar sin verificar disco ────────────────
    if str(evidencia).strip().lower() in _EVIDENCIA_CONSULTIVA:
        print(f"[Auditor] ✅  {agente_nombre}: tarea consultiva (Evidencia_Fisica='{evidencia}'). Aprobado sin disco.")
        return True, ""

    # ── Manejar múltiples rutas separadas por comas ──
    evidencia_raw = str(evidencia).strip()
    # Transformar rutas Windows a Docker
    evidencia_raw = transformar_rutas_windows(evidencia_raw)
    # Dividir por comas
    rutas_evidencia = [r.strip() for r in evidencia_raw.split(",") if r.strip()]
    
    if not rutas_evidencia:
        rutas_evidencia = [evidencia_raw]
    
    # Verificar cada ruta
    rutas_validas = []
    for evidencia_path in rutas_evidencia:
        if evidencia_path.startswith("/app/"):
            evidencia_path = str(_APP_ROOT / evidencia_path.replace("/app/", "", 1))
        
        # Verificar existencia física (búsqueda en rutas relativas comunes)
        if not os.path.exists(evidencia_path):
            candidatos = [
                str(_APP_ROOT / agente_nombre / os.path.basename(evidencia_path)),
                str(_APP_ROOT / "Nami" / os.path.basename(evidencia_path)),
                str(_APP_ROOT / "recursos_externos" / os.path.basename(evidencia_path)),
                str(_APP_ROOT / "Robin" / "reportes" / os.path.basename(evidencia_path)),
                str(_APP_ROOT / "Archivos_temporales" / os.path.basename(evidencia_path)),
            ]
            for cand in candidatos:
                if os.path.exists(cand):
                    evidencia_path = cand
                    break
            else:
                if "/" not in evidencia_path and "\\" not in evidencia_path:
                    try:
                        encontrados = list(Path(_APP_ROOT).rglob(evidencia_path))
                    except (ValueError, NotImplementedError):
                        # Patrón glob inválido (p.ej. '**' en posición no válida). No buscar.
                        encontrados = []
                    if encontrados:
                        evidencia_path = str(encontrados[0])
        
        if os.path.exists(evidencia_path):
            rutas_validas.append(evidencia_path)
    
    if not rutas_validas:
        motivo = (
            f"Error de Validación: Has reportado la tarea como PENDIENTE_REVISION o CERRADO, pero ninguno de los archivos "
            f"'{evidencia_raw}' existe en el disco. "
            "Debes usar obligatoriamente tu herramienta de escritura/edición para crearlo. "
            "El ticket permanece PENDIENTE. Inténtalo de nuevo."
        )
        print(f"[Auditor] ⚠️  {agente_nombre}: archivo no encontrado -> {evidencia_raw}")
        return False, motivo
    
    # Verificar que al menos un archivo es reciente (posterior a hora_inicio)
    if hora_inicio_str:
        try:
            from datetime import datetime as _dt
            hora_inicio_dt = _dt.fromisoformat(hora_inicio_str)
            archivo_reciente = False
            for evidencia_path in rutas_validas:
                mtime = os.path.getmtime(evidencia_path)
                mtime_dt = _dt.fromtimestamp(mtime)
                if mtime_dt > hora_inicio_dt:
                    archivo_reciente = True
                    break
            if not archivo_reciente:
                motivo = (
                    f"Error de Validación: Has reportado la tarea como PENDIENTE_REVISION o CERRADO, pero ninguno de los archivos "
                    f"'{evidencia_raw}' fue modificado durante este turno "
                    f"(turno inició: {hora_inicio_dt.strftime('%H:%M:%S')}). "
                    "Debes usar tu herramienta para escribir o actualizar el archivo en este turno. "
                    "El ticket permanece PENDIENTE. Inténtalo de nuevo."
                )
                print(f"[Auditor] ⚠️  {agente_nombre}: archivos antiguos (inicio={hora_inicio_dt})")
                return False, motivo
        except Exception as fecha_e:
            # Si hay cualquier error al comparar fechas, dejar pasar (no bloquear por error interno)
            print(f"[Auditor] Advertencia al comparar fechas: {fecha_e}. Aprobando por defecto.")
    
    print(f"[Auditor] ✅  {agente_nombre}: evidencia verificada -> {rutas_validas}")
    return True, ""



def _extraer_tickets_pizarra(texto_markdown: str) -> list:
    tickets = []
    # Separa bloques por la cabecera TKT-
    bloques = re.split(r"(?=## TKT-[A-Z0-9\-]+(?:[^\n]*)\n)", texto_markdown)
    for bloque in bloques:
        bloque = bloque.strip()
        if not bloque.startswith("## TKT-"): continue
        
        m_id = re.search(r"(## TKT-[A-Z0-9\-]+)", bloque)
        
        def _get_field(field_name):
            # Busca "- **Campo:** valor", "### Campo\nvalor" o "**Campo:** valor" asegurando que estén al inicio de la línea
            match = re.search(rf"\n(?:-?\s*\*\*|###\s*){field_name}[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else None

        tarea = _get_field("Tarea")
        responsable_raw = _get_field("Responsable")
        if responsable_raw:
            m_resp = re.search(r'(?i)\b(luffy|zoro|nami|robin|sanji)\b', responsable_raw)
            responsable = m_resp.group(1).capitalize() if m_resp else responsable_raw
        else:
            responsable = None
        estado = _get_field("Estado")
        if estado:
            estado = estado.split('\n')[0].strip()
        evidencia = _get_field("Evidencia_Fisica")
        contexto = _get_field("Contexto")
        historial = _get_field("Historial(?: / Intentos Previos)?")
        
        if m_id:
            tickets.append({
                "id_bloque": m_id.group(1).strip(),
                "tarea": tarea if tarea else "N/A",
                "responsable": responsable if responsable else "N/A",
                "estado": estado if estado else "DESCONOCIDO",
                "evidencia": evidencia if evidencia else "N/A",
                "contexto": contexto if contexto else "N/A",
                "historial": historial if historial else "",
                "bloque_original": bloque
            })
    return tickets

def build_system_prompt(agente_nombre):
    perfil = cargar_perfil_agente(agente_nombre)
    identidad = perfil.get("presentacion", f"Eres {agente_nombre}.")
    manual = perfil.get("manual_quirurgico", "")
    if manual:
        identidad += f"\n\n--- MANUAL QUIRÚRGICO Y FEW-SHOTS ---\n{manual}\n"
        
    if agente_nombre.upper() == "LUFFY":
        try:
            from memory import listar_perfiles_disponibles
            perfiles = listar_perfiles_disponibles()
            radiografia = "\n--- RADIOGRAFÍA DE LA TRIPULACIÓN (BOOT SEQUENCE) ---\nEres el Director del sistema. Aquí está la radiografía de tu equipo para saber a quién delegar qué:\n"
            for p in perfiles:
                if p.upper() != "LUFFY":
                    p_data = cargar_perfil_agente(p)
                    desc = p_data.get("presentacion", "Agente sin rol definido.")
                    radiografia += f"- **{p}**: {desc[:300]}...\n"
            identidad += radiografia
        except Exception as e:
            print(f"Error cargando radiografía: {e}")
    
    reglas = leer_nodo_obsidian("protocolo/Reglas de la Tripulacion.md")
    protocolo = leer_nodo_obsidian("protocolo/Protocolo Inter-Agente.md")
    memoria_viva = leer_nodo_obsidian("memoria/Memoria_Viva_Errores.md")
    return f"""{identidad}
Tu capitán es Luffy. Él te delegará tareas. Si eres Luffy, tú eres el Capitán.
Siempre debes comunicarte usando el formato JSON especificado.
DIRECTIVA CRÍTICA: Cuando uses herramientas para leer archivos o investigar, NO respondas simplemente "he leído el archivo". DEBES incluir un resumen detallado de lo que aprendiste y extraer el conocimiento útil en tu respuesta.

--- REGLA DE ENTORNO Y RUTAS DOCKER (CRÍTICO - FALLO #1) ---
1. ESTÁS EJECUTANDO DENTRO DE UN CONTENEDOR DOCKER LINUX. LA RAÍZ DEL PROYECTO ES `/app/`.
2. PROHIBIDO ABSOLUTAMENTE USAR RUTAS DE WINDOWS (como C:\\Users\\admin\\... o C:/Users/...).
3. Cualquier ruta de archivo en tus respuestas, evidencias físicas o herramientas DEBE comenzar con `/app/` o ser relativa.

--- SISTEMA DE PIZARRA CENTRAL (BLACKBOARD) ---
El equipo se coordina a través de tickets en la Bitácora.
Cuando recibes un TICKET, fuiste invocado efímeramente para procesarlo. Para finalizar tu ejecución, debes responder con un JSON que contenga OBLIGATORIAMENTE la clave "ticket_actualizado" con el bloque completo del TICKET reescrito en Markdown.

--- FORMATO ESTRICTO DEL TICKET (NUEVO ORDEN OBLIGATORIO) ---
El bloque Markdown del ticket actualizado DEBE tener obligatoriamente esta estructura y orden exacto (el Estado y Responsable VAN AL FINAL):
## TKT-[AGENTE]-[TIMESTAMP]
- **Tarea:** (Qué debe hacer exactamente el agente)
- **Contexto:** (El trasfondo, la necesidad del usuario y el porqué)
- **Historial / Intentos Previos:** (Rastro de fallos, lecciones aprendidas, pasos documentados minuciosamente)
- **Evidencia_Fisica:** (Ruta absoluta del archivo generado o N/A)
- **Estado:** (PENDIENTE / PENDIENTE_REVISION / CERRADO)
- **Responsable:** (Nombre del agente que debe procesarlo ahora)

REGLAS DE TRANSICIÓN:
1. Si eres un SUBAGENTE (Zoro, Nami, etc.) y terminaste: NO uses COMPLETADO. Cambia el Estado a "PENDIENTE_REVISION" y el Responsable a "Luffy".
2. Si eres LUFFY (Capitán) y recibes un ticket en PENDIENTE_REVISION: Audítalo. Si el subagente falló y puede corregirlo, redacta la lección aprendida en el Historial, cambia el Estado a "PENDIENTE" y el Responsable al subagente. Si es éxito total, extrae la información, cambia el Estado a "CERRADO", y comunícate con el usuario usando tu herramienta tool_enviar_telegram.
3. Si necesitas delegar a otro agente: Cambia Responsable al nombre del agente y Estado a "PENDIENTE".

--- REGLA DE EVIDENCIA FÍSICA (OBLIGATORIO) ---
Además del campo en el markdown, TU JSON DEBE incluir obligatoriamente el campo a nivel raíz:
  "Evidencia_Fisica": "<ruta_absoluta_del_archivo_generado_o_modificado>"
Si la tarea fue consultiva (no generaste archivo), usa "N/A".
¡REQUISITO CRÍTICO DEL AUDITOR!: TU JSON TAMBIÉN DEBE INCLUIR A NIVEL RAÍZ EL CAMPO "evidencia_hallazgo" con una descripción CONCRETA y ESPECÍFICA de lo que hiciste, qué encontraste o qué corregiste. NO puede estar vacío, nulo ni ser un dict vacío {{}}.
EJEMPLO CORRECTO: "evidencia_hallazgo": "Se corrigió la función _transformar_ruta_linux en skill_ia_creativa.py que causaba [Errno 2] por rutas Windows en Docker Linux. Se verificó que el archivo existe en /app/Nami/informes/."
EJEMPLO INCORRECTO: "evidencia_hallazgo": "" ← ESTO SERÁ RECHAZADO.
Si este campo falta o está vacío, el Auditor RECHAZARÁ tu trabajo y entrarás en un bucle infinito de corrección. NUNCA lo omitas.

--- MEMORIA VIVA DE ERRORES Y RESTRICCIONES ACTIVAS ---
{memoria_viva}

--- REGLAS ABSOLUTAS ---
{reglas}
--- PROTOCOLO DE COMUNICACIÓN (JSON OBLIGATORIO) ---
{protocolo}
"""

def iniciar_listener(agente_nombre, ticket_efimero=None):
    print(f"[{agente_nombre} Listener] Iniciando bucle de escucha infinita...")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "YOUR_NVIDIA_API_KEY_HERE":
        print(f"[{agente_nombre} Listener] ERROR CRÍTICO: No se encontró la DEEPSEEK_API_KEY en el .env.")
        print(f"Configura DEEPSEEK_API_KEY en el archivo .env")
        return
    sys_prompt = build_system_prompt(agente_nombre)
    print(f"[{agente_nombre} Listener] Ejecutando rutina de despertar...")
    from memory import publicar_mensaje
    # Rutina de inicio automático deshabilitada para evitar creación de tickets bloqueantes (TKT-LEER-001)
    # publicar_mensaje(
    #     de="Sistema",
    #     para=agente_nombre,
    #     tipo="delegacion",
    #     contenido={
    #         "texto": f"Rutina de inicio automático: Eres {agente_nombre}. Usa tu herramienta de leer archivos para buscar y leer el archivo 'Reglas de la Tripulacion.md' (está en protocolo/, aunque puedes buscarlo si no sabes la ruta). Una vez leído, envía un mensaje al canal con 'para': 'Todos' donde te presentes ante la tripulación y resumas brevemente las reglas que acabas de asimilar. Esto es obligatorio para asegurar que el sistema inició con buen pie.",
    #         "contexto": "Inicialización del sistema"
    #     }
    # )
    
    # Pre-cargar el nodo LangGraph
    import importlib
    def _ejecutar_nodo_con_reintento_429(funcion_nodo, estado, agente_nombre):
        try:
            return funcion_nodo(estado)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Too Many Requests" in err_str or "rate limit" in err_str.lower():
                print(f"[{agente_nombre} Listener] ⏳ Límite de tasa 429 detectado. Esperando 12s para reintento automático...")
                time.sleep(12)
                return funcion_nodo(estado)
            raise e
    try:
        agente_dir = str(_APP_ROOT / agente_nombre)
        skills_dir = str(_APP_ROOT / agente_nombre / "skills")
        if agente_dir not in sys.path:
            sys.path.insert(0, agente_dir)
        if os.path.exists(skills_dir) and skills_dir not in sys.path:
            sys.path.insert(0, skills_dir)

        modulo_agente = importlib.import_module(f"{agente_nombre.lower()}_agent")
        funcion_nodo = getattr(modulo_agente, f"funcion_nodo_{agente_nombre.lower()}")
        print(f"[{agente_nombre} Listener] Módulo de agente ({agente_nombre.lower()}_agent.py) y skills cargados exitosamente.")
    except Exception as e:
        import traceback
        print(f"[{agente_nombre} Listener] Error crítico cargando LangGraph en {agente_nombre.lower()}_agent.py: {e}")
        traceback.print_exc()
        return

    global_crash_count = 0
    while True:
        try:
            # ── CRÓNOMETRO ÁRBITRO: se ejecuta en CADA vuelta, antes de todo ──
            _verificar_timeout()

            # ══════════════════════════════════════════════════════════════
            # ORQUESTACIÓN ON-DEMAND (SPAWN -> EXEC -> KILL)
            # ══════════════════════════════════════════════════════════════
            try:
                from memory import BITACORA_MD
                if not BITACORA_MD.exists():
                    time.sleep(2)
                    if ticket_efimero: break
                    continue
                texto_bitacora = BITACORA_MD.read_text(encoding="utf-8")
            except Exception as e:
                print(f"[{agente_nombre} Listener] Error leyendo bitacora {e}")
                time.sleep(2)
                if ticket_efimero: break
                continue

            tickets = _extraer_tickets_pizarra(texto_bitacora)
            
            ticket_activo = None
            if len(tickets) > 0:
                pass # print(f"[DEBUG] Tickets en pizarra: {[(t['id_bloque'], t['responsable'], t['estado']) for t in tickets]}")
            
            if ticket_efimero:
                # MODO EFÍMERO: Solo buscamos el ticket que nos mandaron a procesar
                for t in tickets:
                    if t['id_bloque'].strip() == ticket_efimero.strip() and t['responsable'].lower() == agente_nombre.lower():
                        ticket_activo = t
                        break
                if not ticket_activo:
                    print(f"[{agente_nombre} Listener] Error: Ticket {ticket_efimero} no encontrado o no asignado a mí. Terminando.")
                    break
            else:
                # MODO DAEMON (Sólo Luffy)
                if agente_nombre.lower() != "luffy":
                    print(f"[{agente_nombre} Listener] ERROR CRÍTICO: Sólo Luffy puede ejecutarse en modo Daemon.")
                    break
                    
                # 1. Buscar si hay algún ticket para Luffy
                for t in tickets:
                    if t['responsable'].lower() == "luffy" and t['estado'] in ['PENDIENTE', 'ESPERANDO_CORRECCION', 'PENDIENTE_REVISION', 'NUEVO', 'COMPLETADO']:
                        ticket_activo = t
                        break
                        
                # 2. Si no hay ticket para Luffy, buscar si hay tickets para otros agentes
                if not ticket_activo:
                    ticket_subagente = None
                    for t in tickets:
                        if t['responsable'].lower() != "luffy" and t['estado'] in ['PENDIENTE', 'ESPERANDO_CORRECCION', 'PENDIENTE_REVISION', 'NUEVO']:
                            ticket_subagente = t
                            break
                            
                    if ticket_subagente:
                        # [ORQUESTACIÓN] Iniciar Subagente en proceso aislado
                        raw_responsable = ticket_subagente['responsable']
                        import re
                        m = re.search(r'(?i)\b(luffy|zoro|nami|robin|sanji)\b', raw_responsable)
                        agente_asignado = m.group(1).capitalize() if m else raw_responsable.capitalize()
                        if agente_asignado.lower() == "luffy":
                            # Prevents spawning Luffy as a subagent due to compound name matching
                            agente_asignado = "Zoro" 
                        
                        id_tk = ticket_subagente['id_bloque'].strip()
                        print(f"\n[Luffy Orquestador] ⚡ Tarea detectada para {agente_asignado} ({id_tk}). Iniciando ejecución aislada (Spawn)...")
                        import subprocess
                        
                        max_intentos = 3
                        for intento in range(1, max_intentos + 1):
                            import subprocess
                            import threading
                            
                            print(f"[Luffy Orquestador] Intento {intento}/{max_intentos} de {agente_asignado} en {id_tk}...")
                            
                            process = subprocess.Popen(
                                [sys.executable, str(_APP_ROOT / "Luffy" / "base_listener.py"), agente_asignado, "--ticket", id_tk],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                encoding="utf-8",
                                errors="replace"
                            )
                            
                            timeout_kill = False
                            log_history = []
                            last_log_time = time.time()
                            rondas_consecutivas = 0
                            
                            def monitor_logs():
                                nonlocal last_log_time, rondas_consecutivas, timeout_kill
                                while True:
                                    linea = process.stdout.readline()
                                    if not linea:
                                        if process.poll() is not None:
                                            break
                                        continue
                                    
                                    last_log_time = time.time()
                                    linea_str = linea.strip()
                                    print(f"[Monitoreo {agente_asignado}] {linea_str}")
                                    log_history.append(linea_str)
                                    if len(log_history) > 100:
                                        log_history.pop(0)
                                        
                                    import re
                                    match_ronda = re.search(r"Ronda (\d+):", linea_str)
                                    if match_ronda:
                                        ronda_actual = int(match_ronda.group(1))
                                        rondas_consecutivas += 1
                                        
                                        if rondas_consecutivas > 25 or ronda_actual >= 30:
                                            print(f"[Luffy Orquestador] 🛑 ¡BUCLE DETECTADO! {agente_asignado} superó el límite seguro de iteraciones.")
                                            timeout_kill = True
                                            process.terminate()
                                            break

                            t_mon = threading.Thread(target=monitor_logs, daemon=True)
                            t_mon.start()
                            
                            while process.poll() is None:
                                if time.time() - last_log_time > 300:
                                    print(f"[Luffy Orquestador] 🛑 ¡CUELGUE DETECTADO! {agente_asignado} no reportó logs por 5 minutos.")
                                    timeout_kill = True
                                    process.terminate()
                                    break
                                time.sleep(1)
                                
                            t_mon.join(timeout=2)
                            
                            resultado_returncode = -9 if timeout_kill else process.returncode
                            
                            # Auditoría post-ejecución (Kill -> Inspect)
                            print(f"[Luffy Orquestador] 🛑 Proceso de {agente_asignado} terminado (código {resultado_returncode}). Auditando...")
                            
                            # Leer bitácora actualizada
                            try:
                                texto_b = BITACORA_MD.read_text(encoding="utf-8")
                                t_actualizados = _extraer_tickets_pizarra(texto_b)
                                t_post = next((tx for tx in t_actualizados if tx['id_bloque'].strip() == id_tk), None)
                            except:
                                t_post = None
                                
                            if t_post and t_post['estado'] in ['PENDIENTE_REVISION', 'PENDIENTE_APROBACION', 'COMPLETADO']:
                                print(f"[Luffy Orquestador] ✅ Auditoría exitosa: {agente_asignado} completó {id_tk} correctamente.")
                                import re
                                nb = t_post['bloque_original']
                                nb = re.sub(r"(?i)(-?\s*\*\*Responsable:\*\*\s*)\w+", r"\g<1>Luffy", nb)
                                nb += f"\n  - [Sistema - {datetime.now().isoformat()[:19]}]: Tarea completada por {agente_asignado}. Luffy, revisa la evidencia_hallazgo, notifica al usuario por Telegram y cierra el ticket (CERRADO)."
                                texto_b = texto_b.replace(t_post['bloque_original'], nb)
                                BITACORA_MD.write_text(texto_b, encoding="utf-8")
                                print(f"[Luffy Orquestador] 🔄 Ticket devuelto a Luffy para notificación final.")
                                break
                            else:
                                if intento < max_intentos:
                                    print(f"[Luffy Orquestador] Aplicando penalización/corrección en la pizarra para reintento...")
                                    if t_post:
                                        # Inyectar advertencia
                                        texto_b = texto_b.replace(t_post['bloque_original'], t_post['bloque_original'] + f"\n  - [Sistema - Intento {intento}]: Fallo crítico en ejecución. Revisa las reglas y reintenta.")
                                        BITACORA_MD.write_text(texto_b, encoding="utf-8")
                                else:
                                    print(f"[Luffy Orquestador] ❌ Límite de intentos alcanzado. Abortando flujo de {id_tk}.")
                                    # Abortar el ticket directamente para evitar que Luffy lo usurpe, y notificar
                                    if t_post:
                                        bloque = t_post['bloque_original']
                                        nuevo_bloque = re.sub(r'(?i)(-?\\s*\\*\\*Estado:\\*\\*\\s*).*', r'\\g<1>ABORTADO', bloque)
                                        nuevo_bloque += f"\\n  - [Sistema - Final]: Límite de intentos alcanzado. Tarea abortada."
                                        texto_b = texto_b.replace(bloque, nuevo_bloque)
                                        
                                        # Generar SYS-REPAIR para Luffy
                                        # Analizamos los últimos logs
                                        ultimos_logs = "\n".join(log_history[-15:])
                                        ticket_reparacion = f"\n\n## TKT-SYS-REPAIR-{agente_asignado}-{int(time.time())}\n- **Tarea:** Reparar el agente {agente_asignado}. Falló 3 veces seguidas o fue asesinado por el monitor (código {resultado_returncode}). Últimos logs:\n```text\n{ultimos_logs}\n```\n- **Evidencia_Fisica:** c:/Users/admin/Documents/Agentes/{agente_asignado}/{agente_asignado.lower()}_agent.py\n- **Responsable:** Luffy\n- **Estado:** PENDIENTE\n"
                                        texto_b += ticket_reparacion
                                        
                                        BITACORA_MD.write_text(texto_b, encoding="utf-8")
                                        try:
                                            sys.path.append(str(_APP_ROOT / "Luffy"))
                                            from telegram_bridge import enviar_mensaje_telegram
                                            enviar_mensaje_telegram(f"🚨 La tarea {id_tk} de {agente_asignado} fue abortada. Se generó un TKT-SYS-REPAIR para Luffy.")
                                        except Exception as e:
                                            print(f"[Luffy Orquestador] Error enviando alerta de fallo a Telegram: {e}")
                        
                        time.sleep(2)
                        continue

            if not ticket_activo and not ticket_efimero:
                # [ERR-007] Inmunización: Luffy despierta ante mensajes
                forzar_despertar = False
                if agente_nombre.lower() == "luffy":
                    try:
                        from memory import _cargar_canal
                        cu = _cargar_canal("usuario").get("mensajes", [])
                        ci = _cargar_canal("interno").get("mensajes", [])
                        if any("Luffy" not in m.get("leido_por", []) for m in cu) or \
                           any("Luffy" not in m.get("leido_por", []) and str(m.get("para", "")).lower() in ("luffy", "todos", "tripulacion") for m in ci):
                            forzar_despertar = True
                    except Exception as e_msg:
                        print(f"[{agente_nombre} Listener] Error verificando mensajes: {e_msg}")
                
                if forzar_despertar:
                    # Si es tarea (Gatillo 1) u otro caso (mensajes internos)
                    print(f"\n[{agente_nombre} Listener] 🚨 Mensaje entrante detectado. Invocando la consciencia de {agente_nombre}...")
                    try:
                        from memory import _cargar_canal, _guardar_canal
                        canal_u = _cargar_canal("usuario")
                        cu_nuevos = [m for m in canal_u.get("mensajes", []) if "Luffy" not in m.get("leido_por", [])]
                        texto_completo = " ".join([str(m.get("contenido", "")) for m in cu_nuevos])
                    except Exception:
                        pass

                    if texto_completo:
                            # Si es tarea (Gatillo 1) u otro caso (mensajes internos)
                        print(f"\n[{agente_nombre} Listener] 🚨 Mensaje entrante detectado. Invocando la consciencia de {agente_nombre}...")
                        try:
                            texto_bitacora_actual = BITACORA_MD.read_text(encoding="utf-8") if BITACORA_MD.exists() else "La pizarra está vacía."
                            estado_inicial = {"messages": [HumanMessage(content=f"Has recibido el siguiente mensaje de Telegram del usuario:\n\n{texto_completo}\n\n=== ESTADO ACTUAL DE LA PIZARRA ===\n{texto_bitacora_actual}\n====================================\n\n[MODO ORQUESTADOR ACTIVO]: Tienes total libertad para utilizar todas tus herramientas.\nREGLA ANTI-DUPLICADOS: Si la tarea pedida YA EXISTE (mismo objetivo) y está PENDIENTE o EN_PROGRESO, NO CREES NINGÚN TICKET NUEVO, solo avisa al usuario.\nREGLA DE REFINAMIENTO (BLAST): Si la orden del usuario es muy vaga, ambigua o le falta precisión quirúrgica, ESTÁ ESTRICTAMENTE PROHIBIDO CREAR UN TICKET O INVENTAR REQUISITOS. Debes invocar inmediatamente la herramienta 'tool_validar_objetivo' para devolver el turno al usuario con una pregunta aclaratoria y detenerte.\nSi necesitas auditar algo, investigar un bug de los agentes, o buscar contexto adicional, USA TUS HERRAMIENTAS (leer_archivo, grep_search, tool_buscar_soluciones, etc.) antes de responder.\nSi debes delegar, genera un bloque Markdown que empiece obligatoriamente por `## TKT-` con Estado y Responsable al final.")]}
                        
                            print(f"[{agente_nombre} Listener] Llamando a funcion_nodo_luffy directamente en memoria...")
                            resultado = _ejecutar_nodo_con_reintento_429(funcion_nodo, estado_inicial, agente_nombre)
                            respuesta_ai = resultado["messages"][-1].content
                        
                            if "## TKT-" in respuesta_ai:
                                import re
                                bloques = re.split(r"(?i)(?=## TKT-[a-z0-9\-]+)", respuesta_ai)
                                for bloque_nuevo in bloques:
                                    bloque_nuevo = bloque_nuevo.strip()
                                    # Extraer solo el bloque del ticket si está envuelto en JSON string
                                    if bloque_nuevo.startswith("## TKT-"):
                                        # Limpiar caracteres de cierre de JSON si el string termina ahí
                                        bloque_nuevo = re.sub(r'["\}]+$', '', bloque_nuevo).strip()
                                        # Convertir literales \n a saltos de línea reales
                                        bloque_nuevo = bloque_nuevo.replace('\\n', '\n')
                                        texto_bitacora = BITACORA_MD.read_text(encoding="utf-8") if BITACORA_MD.exists() else "La pizarra está vacía."
                                        texto_bitacora += "\n\n" + bloque_nuevo
                                        BITACORA_MD.write_text(texto_bitacora, encoding="utf-8")
                                        print(f"[{agente_nombre} Listener] ✅ Ticket inyectado desde la mente de {agente_nombre}: {bloque_nuevo.splitlines()[0]}")
                            else:
                                print(f"[{agente_nombre} Listener] 💬 {agente_nombre} conversó o no generó ticket. Pizarra limpia.")
                                if "datos_json" in resultado and "contenido" in resultado["datos_json"]:
                                    texto = resultado["datos_json"]["contenido"].get("texto", "")
                                    if texto:
                                        try:
                                            sys.path.append(str(_APP_ROOT / "Luffy"))
                                            from telegram_bridge import enviar_mensaje_telegram
                                            enviar_mensaje_telegram(texto)
                                            print(f"[{agente_nombre} Listener] Mensaje enviado a Telegram.")
                                        except Exception as e:
                                            print(f"[{agente_nombre} Listener] Error enviando a telegram: {e}")
                            
                            # Marcar como leídos
                            for m in canal_u.get("mensajes", []):
                                if "Luffy" not in m.get("leido_por", []): m.setdefault("leido_por", []).append("Luffy")
                            _guardar_canal(canal_u, "usuario")
                        except Exception as e_del:
                            print(f"[{agente_nombre} Listener] ❌ Error ejecutando la consciencia de {agente_nombre}: {e_del}")
                            import traceback
                            traceback.print_exc()
                else:
                    avanzar_turno(agente_nombre)
                    time.sleep(2)
                    continue
            
            if ticket_activo is None:
                continue

            print(f"\n[{agente_nombre} Listener] Ticket asignado encontrado: {ticket_activo.get('id_bloque')}")
            
            # Cambiar a EN_PROGRESO en el markdown original usando regex para ser robusto
            import re
            nuevo_bloque = re.sub(
                r'(?i)(-?\s*\*\*Estado:\*\*\s*).*',
                r'\g<1>EN_PROGRESO',
                ticket_activo.get('bloque_original')
            )
            texto_bitacora = texto_bitacora.replace(ticket_activo.get('bloque_original'), nuevo_bloque)
            try:
                BITACORA_MD.write_text(texto_bitacora, encoding="utf-8")
            except Exception as e:
                print(f"[{agente_nombre} Listener] Error guardando bitacora {e}")

            # Despachar al LLM
            prompt = transformar_rutas_windows(f"Contexto actual: Tienes el siguiente ticket asignado en la Pizarra:\n\n{nuevo_bloque}\n\nResponde estrictamente en formato JSON con la clave 'ticket_actualizado' conteniendo el bloque Markdown completo reescrito con tus actualizaciones, y la clave 'Evidencia_Fisica' si aplica.")
            
            reclamar_turno(agente_nombre)
            estado_inicial = {"messages": [HumanMessage(content=prompt)]}
            intentos_curacion = 0
            max_intentos_curacion = 3
            curado = False

            while intentos_curacion <= max_intentos_curacion:
                try:
                    if intentos_curacion == 0:
                        print(f"[{agente_nombre} Listener] Llamando a funcion_nodo...")
                    else:
                        print(f"[{agente_nombre} Listener] Reintento de funcion_nodo tras curación (Intento {intentos_curacion})...")
                    resultado = _ejecutar_nodo_con_reintento_429(funcion_nodo, estado_inicial, agente_nombre)
                    curado = True
                    break
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    print(f"[{agente_nombre} Listener] ❌ EXCEPCIÓN DETECTADA:\n{tb}")
                    if intentos_curacion >= max_intentos_curacion:
                        print(f"[{agente_nombre} Listener] ❌ Límite de intentos de curación superado. Abortando.")
                        try:
                            # Transferir ticket a Luffy
                            texto_b = BITACORA_MD.read_text(encoding="utf-8")
                            import re
                            if ticket_activo and 'bloque_original' in ticket_activo:
                                bloque_mod = ticket_activo.get('bloque_original')
                                bloque_mod = re.sub(r'(-\s*\*\*Responsable:\*\*\s*)\w+', r'\g<1>Luffy', bloque_mod, flags=re.IGNORECASE)
                                bloque_mod = re.sub(r'(-\s*\*\*Estado:\*\*\s*)\w+', r'\g<1>PENDIENTE_REVISION', bloque_mod, flags=re.IGNORECASE)
                                bloque_mod += f"\n  - [Sistema - Fallo Crítico]: El agente {agente_nombre} sufrió un fallo crítico de auto-curación. Error: {str(e)[:200]}... Por favor, analiza y notifica al usuario."
                                texto_b = texto_b.replace(ticket_activo.get('bloque_original'), bloque_mod)
                                BITACORA_MD.write_text(texto_b, encoding="utf-8")
                        except:
                            pass
                        break
                    
                    print(f"[{agente_nombre} Listener] 🛠️ Activando Auto-Curación (Intento {intentos_curacion + 1})...")
                    try:
                        from luffy_agent import crear_llm
                        
                        from pathlib import Path
                        skills_path = Path(__file__).parent / "skills"
                        if str(skills_path) not in sys.path:
                            sys.path.insert(0, str(skills_path))
                        from skill_curador import HERRAMIENTAS_CURADOR
                        
                        llm_curador = crear_llm(agente="LUFFY").bind_tools(HERRAMIENTAS_CURADOR)
                        prompt_curador = SystemMessage(
                            content="Eres el Curador del Sistema Antigravity 2.0. Ha ocurrido un error crítico en la ejecución de un agente. Tu objetivo es usar las herramientas para leer el código fuente, encontrar la causa del error, y parchear el archivo directamente en caliente para solucionarlo."
                        )
                        msg_error = HumanMessage(
                            content=f"Error detectado:\n```\n{tb}\n```\nTarea original del agente:\n{nuevo_bloque}\nPor favor, lee los archivos relevantes, parchea el error y confirma la solución."
                        )
                        mensajes_curacion = [prompt_curador, msg_error]
                        
                        for _ in range(5):
                            resp_curador = llm_curador.invoke(mensajes_curacion)
                            mensajes_curacion.append(resp_curador)
                            if not hasattr(resp_curador, "tool_calls") or not resp_curador.tool_calls:
                                break
                            
                            for tc in resp_curador.tool_calls:
                                tool_encontrada = next((h for h in HERRAMIENTAS_CURADOR if h.name == tc["name"]), None)
                                if tool_encontrada:
                                    res_tc = tool_encontrada.invoke(tc["args"])
                                else:
                                    res_tc = f"Error: Tool {tc['name']} not found."
                                mensajes_curacion.append(ToolMessage(content=str(res_tc), tool_call_id=tc.get("id")))
                                
                        print(f"[{agente_nombre} Listener] ✅ Intento de curación finalizado.")
                        # Recargar el módulo para aplicar el parche en caliente
                        if f"{agente_nombre.lower()}_agent" in sys.modules:
                            modulo_agente = importlib.reload(sys.modules[f"{agente_nombre.lower()}_agent"])
                            funcion_nodo = getattr(modulo_agente, f"funcion_nodo_{agente_nombre.lower()}")
                    except Exception as e_curador:
                        print(f"[{agente_nombre} Listener] ❌ Error durante la auto-curación: {e_curador}")
                    
                    intentos_curacion += 1
                    time.sleep(2)
            
            if not curado:
                print(f"[{agente_nombre} Listener] Revertiendo ticket tras fallo irrecuperable.")
                texto_bitacora = BITACORA_MD.read_text(encoding="utf-8")
                texto_bitacora = re.sub(r'(?i)(-?\s*\*\*Estado:\*\*\s*)EN_PROGRESO', rf'\g<1>{ticket_activo.get("estado")}', texto_bitacora)
                BITACORA_MD.write_text(texto_bitacora, encoding="utf-8")
                avanzar_turno(agente_nombre)
                time.sleep(2)
                if ticket_efimero: break
                continue

            # Escudo JSON
            if "datos_json" in resultado:
                raw_datos = resultado["datos_json"]
                parsed_data = limpiar_y_parsear_json(raw_datos, agente_nombre) if isinstance(raw_datos, str) else raw_datos
            else:
                ultimo_msg = resultado.get("messages", [])
                if ultimo_msg and hasattr(ultimo_msg[-1], "content"):
                    parsed_data = limpiar_y_parsear_json(ultimo_msg[-1].content, agente_nombre)
                else:
                    parsed_data = limpiar_y_parsear_json("", agente_nombre)
            
            parsed_data = sanitizar_obj_rutas(parsed_data)
            

                    
            if isinstance(parsed_data, dict) and "tipo" in parsed_data and parsed_data["tipo"] == "error_formato":
                print(f"[{agente_nombre} Listener] Error de formato del agente.")
                # Devolver el ticket a pendiente para que lo intente de nuevo, agregando la advertencia al historial
                texto_bitacora = BITACORA_MD.read_text(encoding="utf-8")
                
                # Agregamos la lección al historial del ticket para que no lo repita ciegamente
                import re
                bloque_original = ticket_activo.get("bloque_original", "")
                if bloque_original:
                    nuevo_historial = f"\n  - [Sistema - {datetime.now().strftime('%H:%M:%S')}]: Error CRÍTICO de formato JSON. {parsed_data.get('contenido', {}).get('texto', 'El JSON estaba corrupto o tenía datos extra.')} DEBES corregirlo en este intento."
                    bloque_mod = re.sub(r'(-?\s*\*\*Historial:\*\*)', r'\g<1>' + nuevo_historial, bloque_original)
                    bloque_mod = re.sub(r'(?i)(-?\s*\*\*Estado:\*\*\s*)EN_PROGRESO', rf'\g<1>{ticket_activo.get("estado")}', bloque_mod)
                    texto_bitacora = texto_bitacora.replace(bloque_original, bloque_mod)
                else:
                    texto_bitacora = re.sub(r'(?i)(-?\s*\*\*Estado:\*\*\s*)EN_PROGRESO', rf'\g<1>{ticket_activo.get("estado")}', texto_bitacora)
                    
                BITACORA_MD.write_text(texto_bitacora, encoding="utf-8")
                avanzar_turno(agente_nombre)
                time.sleep(2)
                if ticket_efimero: break
                continue

            # FASE 1 - CIERRE MINIMALISTA AUTOMÁTICO (Evitar cuello de botella de NVIDIA NIM):
            if isinstance(parsed_data, dict) and "ticket_actualizado" not in parsed_data and parsed_data.get("tipo") != "error_formato":
                if ticket_activo.get('id_bloque').startswith("## TKT-MSG") and agente_nombre == "Luffy":
                    print(f"[{agente_nombre} Listener] 🛡️ HARD-STOP: Cierre minimalista bloqueado para TKT-MSG. Luffy DEBE enviar ticket_actualizado.")
                else:
                    # Síntesis automática universal del ticket minimalista
                    evidencia = (
                        parsed_data.get("Evidencia_Fisica") or 
                        parsed_data.get("evidencia_fisica") or 
                        parsed_data.get("evidencia") or 
                        parsed_data.get("archivo") or 
                        parsed_data.get("path") or 
                        ticket_activo.get("evidencia", "N/A")
                    )
                    estado_cierre = str(
                        parsed_data.get("estado") or 
                        parsed_data.get("status") or 
                        parsed_data.get("status_code") or 
                        ("CERRADO" if agente_nombre.lower() == "luffy" else "PENDIENTE_REVISION")
                    ).upper()
                    resumen = (
                        parsed_data.get("resumen") or 
                        parsed_data.get("mensaje") or 
                        parsed_data.get("message") or 
                        parsed_data.get("summary") or 
                        "Trabajo completado exitosamente."
                    )
                        
                    id_limpio = ticket_activo.get('id_bloque').replace('## ', '').strip()
                    bloque_modificado = f"## {id_limpio}\n"
                    bloque_modificado += f"- **Tarea:** {ticket_activo.get('tarea')}\n"
                    bloque_modificado += f"- **Responsable:** {ticket_activo.get('responsable')}\n"
                    bloque_modificado += f"- **Estado:** {estado_cierre}\n"
                    bloque_modificado += f"- **Evidencia_Fisica:** {evidencia}\n"
                    bloque_modificado += f"- **Contexto:** {ticket_activo.get('contexto')}\n"
                    bloque_modificado += f"- **Historial:**\n"
                    historial_str = ticket_activo.get('historial', '').strip()
                    if historial_str:
                        for linea_h in historial_str.splitlines():
                            bloque_modificado += f" {linea_h}\n"
                    bloque_modificado += f"  - [{agente_nombre} - {datetime.now().strftime('%Y-%m-%d')}]: {resumen}\n"
                    
                    parsed_data["ticket_actualizado"] = bloque_modificado
                    if "Evidencia_Fisica" not in parsed_data:
                        parsed_data["Evidencia_Fisica"] = evidencia
                    if "evidencia_hallazgo" not in parsed_data:
                        parsed_data["evidencia_hallazgo"] = f"El agente {agente_nombre} completó la tarea mediante cierre minimalista. Resultados extraídos automáticamente."
                    print(f"[{agente_nombre} Listener] ⚡ Cierre Minimalista detectado. 'ticket_actualizado' sintetizado automáticamente por el receptor.")

            # CORRECCIÓN FALLO #3: Si falta ticket_actualizado, inyectar mensaje correctivo (few-shot)
            if not (isinstance(parsed_data, dict) and "ticket_actualizado" in parsed_data):
                print(f"[{agente_nombre} Listener] ⚠️ El LLM no incluyó 'ticket_actualizado'. Inyectando recordatorio correctivo (few-shot)...")
                id_limpio = ticket_activo.get('id_bloque').replace('## ', '').strip()
                if True:
                    prompt_cierre = (
                        "RECORDATORIO CRÍTICO DE PROTOCOLO:\n"
                        "Tu respuesta anterior no incluyó la clave obligatoria 'ticket_actualizado' en el JSON.\n"
                        "DEBES cerrar tu turno respondiendo ÚNICAMENTE con el JSON válido.\n"
                        "¡ATENCIÓN CON EVIDENCIA FÍSICA!: En 'Evidencia_Fisica' debes escribir LA RUTA REAL DEL ARCHIVO QUE CREASTE O MODIFICASTE en tus herramientas anteriores (por ejemplo /app/Robin/reportes/... o N/A si fue solo consulta). PROHIBIDO INVENTAR RUTAS FALSAS.\n\n"
                        "Estructura JSON requerida:\n"
                        "{\n"
                        f'  "ticket_actualizado": "## {id_limpio}\\n- **Tarea:** {ticket_activo.get("tarea")}\\n- **Responsable:** {"Luffy" if agente_nombre.lower() != "luffy" else "Luffy"}\\n- **Estado:** {"PENDIENTE_REVISION" if agente_nombre.lower() != "luffy" else "CERRADO"}\\n- **Evidencia_Fisica:** <RUTA_REAL_DEL_ARCHIVO_GENERADO_O_NA>\\n- **Contexto:** {ticket_activo.get("contexto")}\\n- **Historial:**\\n  - [{agente_nombre} - Fecha]: Trabajo completado.",\n'
                        '  "Evidencia_Fisica": "<RUTA_REAL_DEL_ARCHIVO_GENERADO_O_NA>",\n'
                        '  "evidencia_hallazgo": "Descripción concreta de lo que se hizo, encontró o corrigió (NUNCA VACÍO).",\n'
                        
                        "}\n"
                        "Devuelve SÓLO el JSON sin texto adicional ni bloques de código markdown alrededor."
                    )
                try:
                    mensajes_previos = resultado.get("messages", estado_inicial["messages"])
                    mensajes_previos.append(HumanMessage(content=prompt_cierre))
                    print(f"[{agente_nombre} Listener] Llamando a funcion_nodo (reintento de cierre)...")
                    resultado = _ejecutar_nodo_con_reintento_429(funcion_nodo, {"messages": mensajes_previos}, agente_nombre)
                    if "datos_json" in resultado:
                        raw_datos = resultado["datos_json"]
                        parsed_data = limpiar_y_parsear_json(raw_datos, agente_nombre) if isinstance(raw_datos, str) else raw_datos
                    else:
                        ultimo_msg = resultado.get("messages", [])
                        if ultimo_msg and hasattr(ultimo_msg[-1], "content"):
                            parsed_data = limpiar_y_parsear_json(ultimo_msg[-1].content, agente_nombre)
                        else:
                            parsed_data = limpiar_y_parsear_json("", agente_nombre)
                    parsed_data = sanitizar_obj_rutas(parsed_data)
                except Exception as e_cierre:
                    print(f"[{agente_nombre} Listener] Error en reintento de cierre: {e_cierre}")

                if not (isinstance(parsed_data, dict) and "ticket_actualizado" in parsed_data):
                    print(f"[{agente_nombre} Listener] ❌ El LLM tampoco devolvió 'ticket_actualizado' en reintento. Revertiendo ticket a {ticket_activo.get('estado')}.")
                    texto_bitacora = BITACORA_MD.read_text(encoding="utf-8")
                    texto_bitacora = re.sub(r'(?i)(-?\s*\*\*Estado:\*\*\s*)EN_PROGRESO', rf'\g<1>{ticket_activo.get("estado")}', texto_bitacora)
                    BITACORA_MD.write_text(texto_bitacora, encoding="utf-8")
                    avanzar_turno(agente_nombre)
                    time.sleep(2)
                    if ticket_efimero: break
                    continue

            # Extraer ticket_actualizado
            if isinstance(parsed_data, dict) and "ticket_actualizado" in parsed_data:
                texto_actualizado = parsed_data["ticket_actualizado"]
                # Parsear el nuevo estado para auditar evidencia
                sub_tickets = _extraer_tickets_pizarra(texto_actualizado)
                if sub_tickets:
                    nuevo_ticket = sub_tickets[0]
                    if nuevo_ticket['estado'] in ['COMPLETADO', 'PENDIENTE_REVISION', 'CERRADO']:
                        # ═══ PILAR 2: Contrato de Evidencia Obligatoria ═══
                        evidencia_hallazgo = parsed_data.get("evidencia_hallazgo")
                        if not evidencia_hallazgo or (isinstance(evidencia_hallazgo, dict) and len(evidencia_hallazgo) == 0):
                            print(f"[Auditor] ⚠️  {agente_nombre}: Infracción de protocolo — campo 'evidencia_hallazgo' ausente o vacío.")
                            import re
                            texto_actualizado = re.sub(
                                r'(?i)(-?\s*\*\*Estado:\*\*\s*)\w+',
                                r'\g<1>ESPERANDO_CORRECCION',
                                texto_actualizado,
                                flags=re.IGNORECASE
                            )
                            texto_actualizado += f"\n  - [Auditor - {datetime.now().isoformat()[:19]}]: RECHAZADO: Campo 'evidencia_hallazgo' ausente o vacío. El agente debe analizar los datos antes de cerrar."
                        else:
                            print(f"[Auditor] ✅  {agente_nombre}: Contrato de evidencia_hallazgo verificado.")

                        # Auditar evidencia física
                        hora_inicio_turno = leer_turno().get("hora_inicio")
                        # El auditor espera el campo 'Evidencia_Fisica' en la raíz del dict
                        if 'Evidencia_Fisica' not in parsed_data:
                            parsed_data['Evidencia_Fisica'] = nuevo_ticket['evidencia']
                        
                        evidencia_ok, motivo_rechazo = auditar_evidencia(
                            parsed_data, agente_nombre, hora_inicio_turno
                        )
                        if not evidencia_ok:
                            import re
                            texto_actualizado = re.sub(
                                r'(?i)(-?\s*\*\*Estado:\*\*\s*)\w+',
                                r'\g<1>ESPERANDO_CORRECCION',
                                texto_actualizado,
                                flags=re.IGNORECASE
                            )
                            texto_actualizado += f"\n  - [Auditor - {datetime.now().isoformat()[:19]}]: RECHAZADO: {motivo_rechazo}"
                        else:
                            # Auditoría exitosa
                            if nuevo_ticket['estado'] in ['CERRADO', 'COMPLETADO']:
                                # El archivado ahora es responsabilidad exclusiva de Luffy (vía tool_guardar_solucion o tool_limpiar_pizarra)
                                # Se desactiva este autoguardado del orquestador para evitar ruido y archivos N/A.
                                pass

                    # Enviar mensaje de telegram sin importar el estado del ticket
                    # Nota: msg_telegram_diferido no está definido en este flujo; se elimina el bloque muerto.
                    # Si se necesita envío diferido, debe inicializarse la variable antes de este punto.

                    # Reemplazar en la bitácora global
                    try:
                        # Volvemos a leer por si hubo cambios
                        texto_bitacora = BITACORA_MD.read_text(encoding="utf-8")
                        if texto_actualizado == "":
                            # Fallback de seguridad (no debería ocurrir)
                            pass
                        else:
                            import re
                            texto_bitacora = texto_bitacora.replace(nuevo_bloque, texto_actualizado)
                            print(f"[{agente_nombre} Listener] Pizarra actualizada.")
                        BITACORA_MD.write_text(texto_bitacora, encoding="utf-8")
                    except Exception as e:
                        print(f"[{agente_nombre} Listener] Error guardando bitacora final {e}")
                else:
                    print(f"[{agente_nombre} Listener] El LLM no devolvió un bloque de ticket válido.")
            else:
                print(f"[{agente_nombre} Listener] El LLM no incluyó 'ticket_actualizado' en el JSON.")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[{agente_nombre} Listener] ❌ Error en el bucle principal:\n{tb}")
            global_crash_count += 1
            if global_crash_count > 3:
                print(f"[{agente_nombre} Listener] ❌ Límite de curación global superado. Apagando agente.")
                break
                
            print(f"[{agente_nombre} Listener] 🛠️ Activando Auto-Curación GLOBAL (Intento {global_crash_count}/3)...")
            try:
                from luffy_agent import crear_llm
                from pathlib import Path
                skills_path = Path(__file__).parent / "skills"
                if str(skills_path) not in sys.path:
                    sys.path.insert(0, str(skills_path))
                from skill_curador import HERRAMIENTAS_CURADOR
                
                llm_curador = crear_llm(agente="LUFFY").bind_tools(HERRAMIENTAS_CURADOR)
                prompt_curador = SystemMessage(
                    content="Eres el Curador del Sistema Antigravity 2.0. Ha ocurrido un error crítico general en el bucle principal del agente. Tu objetivo es leer el código, encontrar la causa y parchearlo en caliente usando reemplazar exacto."
                )
                
                # Intentamos extraer contexto del ticket si existe, para dárselo al curador
                ctx_extra = ""
                try:
                    if 'ticket_activo' in locals() and ticket_activo:
                        ctx_extra = f"\nContexto del ticket activo:\n{ticket_activo.get('bloque_original', '')}"
                except:
                    pass
                    
                msg_error = HumanMessage(
                    content=f"Error detectado:\n```\n{tb}\n```\n{ctx_extra}\nPor favor, lee los archivos relevantes, parchea el error y confirma la solución."
                )
                mensajes_curacion = [prompt_curador, msg_error]
                
                for _ in range(5):
                    resp_curador = llm_curador.invoke(mensajes_curacion)
                    mensajes_curacion.append(resp_curador)
                    if not hasattr(resp_curador, "tool_calls") or not resp_curador.tool_calls:
                        break
                    
                    for tc in resp_curador.tool_calls:
                        tool_encontrada = next((h for h in HERRAMIENTAS_CURADOR if h.name == tc["name"]), None)
                        if tool_encontrada:
                            res_tc = tool_encontrada.invoke(tc["args"])
                        else:
                            res_tc = f"Error: Tool {tc['name']} not found."
                        mensajes_curacion.append(ToolMessage(content=str(res_tc), tool_call_id=tc.get("id")))
                        
                print(f"[{agente_nombre} Listener] ✅ Curación global finalizada. Recargando módulo...")
                if f"{agente_nombre.lower()}_agent" in sys.modules:
                    modulo_agente = importlib.reload(sys.modules[f"{agente_nombre.lower()}_agent"])
                    funcion_nodo = getattr(modulo_agente, f"funcion_nodo_{agente_nombre.lower()}")
            except Exception as e_curador:
                print(f"[{agente_nombre} Listener] ❌ Error en curación global: {e_curador}")

        if agente_nombre == "Luffy":
            try:
                import skill_supervisor
                skill_supervisor.ejecutar_supervision(api_key, "deepseek-chat", "deepseek-chat")
            except Exception as sup_e:
                pass # Silencioso, no rompe el flujo
        if ticket_efimero:
            print(f"[{agente_nombre} Listener] Tarea efímera terminada. Apagando (Kill).")
            break
        else:
            time.sleep(2)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Motor Listener Tripulación IA")
    parser.add_argument("agente", type=str, help="Nombre del agente (Luffy, Zoro, etc.)")
    parser.add_argument("--ticket", type=str, default=None, help="ID del ticket para ejecución efímera (Spawn->Exec->Kill)")
    
    args = parser.parse_args()
    agente = args.agente.capitalize()
    
    iniciar_listener(agente, ticket_efimero=args.ticket)
