"""
skill_manos_y_ojos.py — Habilidad 'Manos y Ojos' para la Flota de Agentes
===========================================================================
Permite a los agentes (Luffy, Sanji, Zoro, Robin, Nami):
  1. OJOS: Capturar y analizar visualmente la pantalla de la PC y páginas web con IA Multimodal (VLM).
  2. MANOS: Navegar por páginas web visibles en tiempo real, rellenar formularios, hacer clics,
     mover el ratón, escribir con el teclado en la PC y abrir aplicaciones del sistema.
"""

import os
import sys
import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_core.tools import tool

# Endpoint del puente en el host
HOST_BRIDGE_URL = os.getenv("HOST_BRIDGE_URL", "http://127.0.0.1:8000")
DOCKER_BRIDGE_URL = "http://host.docker.internal:8000"


def _hacer_peticion_puente(endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Envía petición al host bridge con fallback entre localhost y host.docker.internal,
    o importación directa si se ejecuta en el host Windows.
    """
    # 1. Si estamos en Windows host directamente (con pantalla nativa y PyAutoGUI real), ejecutar en proceso
    if sys.platform == "win32":
        try:
            from dashboard.puente_manos_ojos import GestorNavegadorWeb, GestorControlEscritorio, GestorVisionIA
            res = None
            if endpoint == "/api/manos_ojos/web/navegar":
                res = GestorNavegadorWeb.obtener_instancia().navegar(data.get("url", ""), data.get("visible", True))
            elif endpoint == "/api/manos_ojos/web/rellenar":
                res = GestorNavegadorWeb.obtener_instancia().rellenar_formulario(data.get("campos", {}), data.get("selector_envio"))
            elif endpoint == "/api/manos_ojos/web/clic":
                res = GestorNavegadorWeb.obtener_instancia().hacer_clic(data.get("selector_o_texto", ""))
            elif endpoint == "/api/manos_ojos/web/extraer":
                res = GestorNavegadorWeb.obtener_instancia().extraer_contenido(data.get("selector"))
            elif endpoint == "/api/manos_ojos/web/capturar":
                res = GestorNavegadorWeb.obtener_instancia().capturar_pantalla()
            elif endpoint == "/api/manos_ojos/web/cerrar":
                res = GestorNavegadorWeb.obtener_instancia().cerrar()
            elif endpoint == "/api/manos_ojos/pc/capturar":
                res = GestorControlEscritorio.capturar_pantalla_pc()
            elif endpoint == "/api/manos_ojos/pc/analizar":
                res = GestorVisionIA.analizar_pantalla(data.get("instruccion", ""), data.get("ruta_imagen"))
            elif endpoint == "/api/manos_ojos/pc/clic":
                res = GestorControlEscritorio.clic_pantalla(data.get("x", 0), data.get("y", 0), data.get("tipo", "izquierdo"), data.get("doble", False))
            elif endpoint == "/api/manos_ojos/pc/escribir":
                res = GestorControlEscritorio.escribir_texto(data.get("texto", ""), data.get("enter", False))
            elif endpoint == "/api/manos_ojos/pc/tecla":
                res = GestorControlEscritorio.presionar_tecla(data.get("combinacion", ""))
            elif endpoint == "/api/manos_ojos/pc/app":
                res = GestorControlEscritorio.abrir_aplicacion(data.get("comando", ""))
            elif endpoint == "/api/manos_ojos/web/media":
                res = GestorNavegadorWeb.obtener_instancia().controlar_media(data.get("accion", "reproducir"))
            elif endpoint == "/api/manos_ojos/web/pestanas":
                res = GestorNavegadorWeb.obtener_instancia().gestionar_pestanas(data.get("accion", "listar"), data.get("url", ""), data.get("indice", 0))
            elif endpoint == "/api/manos_ojos/pc/ventanas":
                res = GestorControlEscritorio.gestionar_ventanas(data.get("accion", "listar"), data.get("titulo_o_proceso", ""))

            if res is not None and res.get("status") != "error":
                return res
        except Exception:
            pass

    # 2. Vía HTTP hacia el servidor FastAPI del host (imprescindible cuando se corre desde Docker)
    payload_bytes = json.dumps(data or {}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    candidate_urls = [
        "http://host.docker.internal:8000",
        "http://172.17.0.1:8000",
        HOST_BRIDGE_URL,
    ] if sys.platform != "win32" else [
        HOST_BRIDGE_URL,
        "http://127.0.0.1:8000",
        "http://host.docker.internal:8000",
    ]

    for base_url in candidate_urls:
        try:
            url = base_url.rstrip("/") + endpoint
            req = urllib.request.Request(url, data=payload_bytes, headers=headers)
            with opener.open(req, timeout=65) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue

    return {"status": "error", "mensaje": f"No fue posible contactar el Puente de Manos y Ojos en {endpoint}."}


def obtener_prompt_manos_y_ojos() -> str:
    return """[✋👁️ MODO MANOS Y OJOS ACTIVADO — CONTROL WEB Y DE ESCRITORIO]
Tienes acceso a ojos visuales y manos de automatización sobre la PC y el navegador:

🌐 PUERTO Y ENTORNO EXCLUSIVO DE LA FLOTA:
- Tu navegador oficial es la ventana de Microsoft Edge conectada exclusivamente al puerto TCP 9222 (perfil aislado 'browser_visible_profile').
- La ventana personal de Edge del Capitán (donde tiene Gemini, Telegram, Dashboard) NO tiene puerto CDP y NUNCA debe ser alterada ni cerrada.
- En tu ventana de Edge (puerto 9222), tienes TOTAL LIBERTAD MULTI-PESTAÑA: puedes abrir cuantas pestañas necesites para explorar ofertas, comparar vacantes o seguir flujos en paralelo.
- PROTOCOLO DE VISIBILIDAD Y ORDEN:
  1. Cada vez que abras o trabajes en una pestaña, usa `tool_gestionar_pestanas_web(accion="cambiar", indice=X)` para traerla al frente (bring_to_front). Esto garantiza que el Capitán siempre vea con total claridad en pantalla lo que estás haciendo en tiempo real.
  2. Puedes usar `tool_gestionar_pestanas_web(accion="listar")` para supervisar tus pestañas activas.
  3. Higiene ordenada: cuando termines la postulación o tarea de una vacante concreta, CIERRA esa pestaña (`tool_gestionar_pestanas_web(accion="cerrar", indice=X)`) para mantener la barra ordenada y no saturar el navegador.

1. CONTROL DE VIDEOS Y REPRODUCTORES EN LA WEB (YouTube, etc.):
   - Para reproducir o dar play a un video: usa `tool_controlar_media_web(accion="reproducir")`.
   - Para pausar un video: usa `tool_controlar_media_web(accion="pausar")`.
   - Para poner el video en PANTALLA COMPLETA: usa `tool_controlar_media_web(accion="pantalla_completa")`.
   - Para alternar play/pausa: usa `tool_controlar_media_web(accion="alternar")`.
   - Para silenciar/desmutear: usa `tool_controlar_media_web(accion="silenciar")`.
2. CONTROL DE PESTAÑAS DEL NAVEGADOR (PUERTO 9222):
   - Para ver qué pestañas tienes abiertas: usa `tool_gestionar_pestanas_web(accion="listar")`.
   - Para abrir una pestaña nueva: usa `tool_gestionar_pestanas_web(accion="nueva", url="https://...")`.
   - Para cambiar entre pestañas y traer al frente: usa `tool_gestionar_pestanas_web(accion="cambiar", indice=0)`.
   - Para cerrar una pestaña concluida: usa `tool_gestionar_pestanas_web(accion="cerrar", indice=0)`.
   - Para cerrar pestañas redundantes dejando la actual: usa `tool_gestionar_pestanas_web(accion="cerrar_otras")`.
3. CONTROL DE VENTANAS Y APLICACIONES DE LA PC (Los 3 botones de control y cambio de apps):
   - Para maximizar una ventana: usa `tool_gestionar_ventanas_pc(accion="maximizar", titulo_o_proceso="Edge")`.
   - Para minimizar una ventana: usa `tool_gestionar_ventanas_pc(accion="minimizar", titulo_o_proceso="Edge")`.
   - Para restaurar el tamaño original de una ventana: usa `tool_gestionar_ventanas_pc(accion="restaurar", titulo_o_proceso="Edge")`.
   - Para cerrar una ventana/aplicación: usa `tool_gestionar_ventanas_pc(accion="cerrar", titulo_o_proceso="Notepad")`.
   - Para traer al frente una ventana: usa `tool_gestionar_ventanas_pc(accion="enfocar", titulo_o_proceso="Discord")`.
   - Para ver todas las ventanas abiertas en pantalla: usa `tool_gestionar_ventanas_pc(accion="listar")`.
4. NAVEGACIÓN Y FORMULARIOS WEB:
   - Para abrir o visitar una página: usa `tool_navegar_web(url, visible=True)`. La ventana se abrirá en pantalla visible para que el usuario observe.
   - Para rellenar formularios: usa `tool_rellenar_formulario_web(campos_json, boton_enviar)`.
   - Para hacer clic en botones, enlaces o pestañas: usa `tool_hacer_clic_web(selector_o_texto)`.
   - Para extraer información y ver qué formularios existen: usa `tool_extraer_informacion_web()`.
5. OJOS Y VISIÓN DE LA PC (MULTIMODAL VLM):
   - Para tomar una captura de pantalla completa de la PC: usa `tool_capturar_pantalla_pc()`.
   - Para analizar visualmente lo que se ve en la pantalla o encontrar coordenadas de botones: usa `tool_analizar_pantalla_pc(instruccion)`.
6. CONTROL DEL ESCRITORIO DE LA PC:
   - Para hacer clic en un punto de la pantalla: usa `tool_hacer_clic_pc(x, y)`.
   - Para escribir texto en la aplicación activa: usa `tool_escribir_teclado_pc(texto, presionar_enter)`.
   - Para presionar teclas o atajos (Enter, Tab, Ctrl+C, Win+R): usa `tool_presionar_teclas_pc(combinacion)`.
   - Para abrir programas de la PC (Notepad, Excel, Calc): usa `tool_abrir_aplicacion_pc(nombre)`.
"""


# ─── HERRAMIENTAS WEB (MANOS WEB) ─────────────────────────────────────────────

@tool
def tool_navegar_web(url: str, visible: bool = True) -> str:
    """
    Abre el navegador Chromium en la PC y navega a la URL especificada.
    Por defecto se abre de forma VISIBLE (headful) en la pantalla para que el usuario pueda ver la navegación.

    Args:
        url: La dirección web a visitar (ej: 'https://google.com', 'https://sunat.gob.pe').
        visible: True para mostrar la ventana del navegador en la pantalla, False para segundo plano.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/navegar", {"url": url, "visible": visible})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_rellenar_formulario_web(campos_json: str, boton_enviar: str = "") -> str:
    """
    Rellena automáticamente campos de un formulario en la página web abierta.
    Detecta inputs por texto visible, etiquetas (label), placeholders, nombres o selectores CSS.

    Args:
        campos_json: JSON con pares campo: valor. Ej: '{"Nombre": "Juan", "Email": "usuario@example.com", "#terminos": true}'
        boton_enviar: Texto visible o selector del botón de envío a presionar tras rellenar (opcional).
    """
    try:
        campos = json.loads(campos_json) if isinstance(campos_json, str) else campos_json
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"campos_json inválido: {str(e)}"})

    res = _hacer_peticion_puente("/api/manos_ojos/web/rellenar", {
        "campos": campos,
        "selector_envio": boton_enviar if boton_enviar else None
    })
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_hacer_clic_web(selector_o_texto: str) -> str:
    """
    Hace clic en un elemento de la página web abierta, buscando por texto visible del botón/enlace o selector CSS.

    Args:
        selector_o_texto: Texto del botón o enlace (ej: 'Iniciar sesión', 'Buscar', 'Enviar') o selector CSS ('#btn-submit').
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/clic", {"selector_o_texto": selector_o_texto})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_extraer_informacion_web(selector: str = "") -> str:
    """
    Extrae el texto legible principal y detecta todos los formularios e inputs presentes en la página web abierta.

    Args:
        selector: Selector CSS opcional si se desea extraer una sección concreta (ej: '#tabla-datos'). Dejar vacío para todo.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/extraer", {"selector": selector if selector else None})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_capturar_pantalla_web() -> str:
    """
    Toma una captura de pantalla de la página web abierta actualmente y genera la imagen de evidencia.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/capturar")
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_cerrar_navegador_web() -> str:
    """
    Cierra la sesión del navegador web Chromium en la PC.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/cerrar")
    return json.dumps(res, ensure_ascii=False)


# ─── HERRAMIENTAS PC Y ESCRITORIO (MANOS PC) ──────────────────────────────────

@tool
def tool_capturar_pantalla_pc() -> str:
    """
    Toma una captura de pantalla completa del escritorio de la PC (Windows) en tiempo real.
    Retorna la ruta física del archivo guardado y la URL local para el Dashboard.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/capturar")
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_analizar_pantalla_pc(instruccion: str = "¿Qué elementos, ventanas o formularios se ven en la pantalla?") -> str:
    """
    OJOS VISUALES POR IA (VLM): Captura la pantalla actual de la PC y la analiza con un modelo de visión multimodal.
    Describe qué ventanas están abiertas, dónde están los botones o formularios, qué textos se leen y qué errores hay.

    Args:
        instruccion: Pregunta o instrucción específica sobre lo que se desea ver o encontrar en la pantalla.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/analizar", {"instruccion": instruccion})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_hacer_clic_pc(x: int, y: int, tipo_clic: str = "izquierdo", doble_clic: bool = False) -> str:
    """
    Mueve el ratón suavemente en la pantalla de la PC y hace clic en las coordenadas especificadas (x, y).

    Args:
        x: Coordenada horizontal en píxeles.
        y: Coordenada vertical en píxeles.
        tipo_clic: 'izquierdo' o 'derecho'.
        doble_clic: True para realizar doble clic.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/clic", {
        "x": int(x),
        "y": int(y),
        "tipo": tipo_clic,
        "doble": doble_clic
    })
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_escribir_teclado_pc(texto: str, presionar_enter: bool = False) -> str:
    """
    Escribe texto en la aplicación activa de la PC simulando pulsaciones de teclado humano.

    Args:
        texto: El texto o número a ingresar en el campo o ventana activa.
        presionar_enter: True para presionar Enter después de escribir.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/escribir", {"texto": texto, "enter": presionar_enter})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_presionar_teclas_pc(combinacion: str) -> str:
    """
    Presiona una tecla o atajo de teclado en la PC Windows.

    Args:
        combinacion: Nombre de la tecla o atajo (ej: 'enter', 'tab', 'escape', 'ctrl+c', 'ctrl+v', 'win+r', 'alt+tab').
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/tecla", {"combinacion": combinacion})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_abrir_aplicacion_pc(nombre_o_comando: str) -> str:
    """
    Lanza una aplicación o programa en la PC Windows.

    Args:
        nombre_o_comando: Comando o ejecutable a iniciar (ej: 'notepad', 'calc', 'chrome', 'explorer', 'excel').
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/app", {"comando": nombre_o_comando})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_controlar_media_web(accion: str = "reproducir") -> str:
    """
    Controla la reproducción de video o audio en el navegador web (YouTube, Netflix, etc.):
    - 'reproducir' o 'play': Inicia la reproducción del video.
    - 'pausar' o 'pause': Pausa el video.
    - 'pantalla_completa' o 'fullscreen': Activa o desactiva la pantalla completa del video.
    - 'alternar' o 'toggle': Alterna entre play y pause.
    - 'silenciar' o 'mute': Activa o silencia el sonido.
    - 'adelantar': Avanza 10 segundos.
    - 'retroceder': Retrocede 10 segundos.

    Args:
        accion: 'reproducir', 'pausar', 'pantalla_completa', 'alternar', 'silenciar'.
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/media", {"accion": accion})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_gestionar_pestanas_web(accion: str = "listar", url: str = "", indice: int = 0) -> str:
    """
    Administra las pestañas del navegador Microsoft Edge:
    - 'listar': Muestra las pestañas abiertas con sus títulos y URLs.
    - 'nueva': Abre una nueva pestaña (opcionalmente navega a 'url').
    - 'cerrar': Cierra la pestaña activa o la del índice especificado.
    - 'cambiar': Trae al frente la pestaña indicada por el número de 'indice'.

    Args:
        accion: 'listar', 'nueva', 'cerrar', 'cambiar'.
        url: Dirección web para abrir si accion='nueva' (opcional).
        indice: Índice numérico de la pestaña para 'cambiar' o 'cerrar' (0, 1, 2...).
    """
    res = _hacer_peticion_puente("/api/manos_ojos/web/pestanas", {"accion": accion, "url": url, "indice": indice})
    return json.dumps(res, ensure_ascii=False)


@tool
def tool_gestionar_ventanas_pc(accion: str = "maximizar", titulo_o_proceso: str = "") -> str:
    """
    Controla las ventanas del sistema Windows (los 3 botones de control y cambio de apps):
    - 'maximizar': Maximiza la ventana a pantalla completa.
    - 'minimizar': Minimiza la ventana a la barra de tareas.
    - 'restaurar': Restaura la ventana a su tamaño original.
    - 'cerrar': Cierra la ventana indicada.
    - 'enfocar': Trae la ventana al frente de la pantalla.
    - 'listar': Ver todas las ventanas visibles con sus títulos.

    Args:
        accion: 'maximizar', 'minimizar', 'restaurar', 'cerrar', 'enfocar', 'listar'.
        titulo_o_proceso: Nombre o parte del título de la ventana (ej: 'YouTube', 'Edge', 'Visual Studio', 'Notepad', 'Discord').
    """
    res = _hacer_peticion_puente("/api/manos_ojos/pc/ventanas", {"accion": accion, "titulo_o_proceso": titulo_o_proceso})
    return json.dumps(res, ensure_ascii=False)


HERRAMIENTAS_MANOS_Y_OJOS = [
    tool_navegar_web,
    tool_controlar_media_web,
    tool_gestionar_pestanas_web,
    tool_rellenar_formulario_web,
    tool_hacer_clic_web,
    tool_extraer_informacion_web,
    tool_capturar_pantalla_web,
    tool_cerrar_navegador_web,
    tool_gestionar_ventanas_pc,
    tool_capturar_pantalla_pc,
    tool_analizar_pantalla_pc,
    tool_hacer_clic_pc,
    tool_escribir_teclado_pc,
    tool_presionar_teclas_pc,
    tool_abrir_aplicacion_pc
]
