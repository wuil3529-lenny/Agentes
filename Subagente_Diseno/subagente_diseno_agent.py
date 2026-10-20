"""
subagente_diseno_agent.py — Subagente de Diseño, Directora Creativa y Prototipado UI/UX
========================================================================================
Entidad canónica de la tripulación/flota para la conceptualización visual, prototipado
de interfaces interactivas (Live Previews en HTML/Tailwind), dirección de arte,
generación multimedia con IA (Ideogram, DALL-E 3, Pollinations), diapositivas Marp,
edición de vídeo programático y estrategias digitales de redes sociales.

Identidad Canónica: Subagente_Diseno
Identidad Conversacional / Alias: Nami
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

# Ubicaciones oficiales de trabajo
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"
INFORMES_PATH = _SUBAGENTE_PATH / "informes"
INFORMES_PATH.mkdir(parents=True, exist_ok=True)
ARCHIVOS_TEMPORALES_PATH.mkdir(parents=True, exist_ok=True)

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
    def guardar_cerebro(*args, **kwargs): return ""
try:
    from bucle_autocorreccion import interceptar_tool_call
except Exception:
    try:
        from Agente_Orquestador.bucle_autocorreccion import interceptar_tool_call
    except Exception:
        interceptar_tool_call = None

# ─── Carga Modular de las 12 Habilidades y sus Prompts Especializados ──────────
HERRAMIENTAS_DISENO = [
    registrar_bitacora,
    guardar_cerebro,
    publicar_mensaje,
    leer_mensajes,
    leer_nodo_obsidian
]

# 1. Base del Sistema y Shell Seguro
from Subagente_Diseno.skills.base.skill_base import (
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando,
    obtener_prompt_base
)
HERRAMIENTAS_DISENO.extend([crear_archivo, leer_archivo, listar_directorio, ejecutar_comando])

# 2. IA Creativa Multimedia
from Subagente_Diseno.skills.ia_creativa.skill_ia_creativa import (
    generar_multimedia_ia,
    auditar_calidad_imagen,
    consultar_catalogo_prompts,
    consultar_catalogo_estilos,
    consultar_catalogo_sujetos,
    consultar_brand_book,
    obtener_prompt_ia_creativa
)
HERRAMIENTAS_DISENO.extend([
    generar_multimedia_ia,
    auditar_calidad_imagen,
    consultar_catalogo_prompts,
    consultar_catalogo_estilos,
    consultar_catalogo_sujetos,
    consultar_brand_book
])


# 3. Imágenes Locales y Feeds
from Subagente_Diseno.skills.imagenes_locales.skill_imagenes_locales import (
    maquetar_carrusel_instagram,
    maquetar_carrusel_completo,
    superponer_branding_producto,
    obtener_prompt_imagenes_locales
)
HERRAMIENTAS_DISENO.extend([
    maquetar_carrusel_instagram,
    maquetar_carrusel_completo,
    superponer_branding_producto
])

# 4. Vídeo Cinemático e Imagen en Movimiento (Higgsfield I2V)
from Subagente_Diseno.skills.video.skill_video import (
    generar_video_ia,
    estructurar_prompt_movimiento_video,
    obtener_prompt_video
)
HERRAMIENTAS_DISENO.extend([generar_video_ia, estructurar_prompt_movimiento_video])

# 4.1 Edición Dinámica de Vídeo y Motion Graphics
from Subagente_Diseno.skills.edicion_video.skill_edicion_video import (
    superponer_motion_overlay,
    insertar_broll,
    generar_subtitulos_dinamicos,
    generar_lower_third_callout,
    ensamblar_edicion_video_completa,
    obtener_prompt_edicion_video
)
HERRAMIENTAS_DISENO.extend([
    superponer_motion_overlay,
    insertar_broll,
    generar_subtitulos_dinamicos,
    generar_lower_third_callout,
    ensamblar_edicion_video_completa
])

# 4.2 Descarga Universal de Multimedia y Redes Sociales (yt-dlp)
from Subagente_Diseno.skills.descargar_multimedia.skill_descargar_multimedia import (
    descargar_video_redes,
    extraer_audio_redes,
    inspeccionar_info_multimedia,
    obtener_prompt_descargar_multimedia
)
HERRAMIENTAS_DISENO.extend([
    descargar_video_redes,
    extraer_audio_redes,
    inspeccionar_info_multimedia
])

# 5. Presentaciones Ejecutivas Marp
from Subagente_Diseno.skills.presentaciones.skill_presentaciones import (
    generar_presentacion_marp,
    obtener_prompt_presentaciones
)
HERRAMIENTAS_DISENO.append(generar_presentacion_marp)

# 6. Búsqueda Web de Referencias
from Subagente_Diseno.skills.buscar_internet.skill_buscar_internet import (
    buscar_referencias_diseno,
    obtener_prompt_buscar_internet
)
HERRAMIENTAS_DISENO.append(buscar_referencias_diseno)

# 7. Sentry y Resiliencia ante Errores
from Subagente_Diseno.skills.sentry.skill_sentry import (
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
    obtener_prompt_sentry
)
HERRAMIENTAS_DISENO.extend([
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico
])

# 8. Limpieza y Sanitización de Workspace
from Subagente_Diseno.skills.limpiar_workspace.skill_limpiar_workspace import (
    tool_limpiar_workspace_diseno,
    tool_limpiar_workspace,
    obtener_prompt_limpiar_workspace
)
HERRAMIENTAS_DISENO.extend([tool_limpiar_workspace_diseno, tool_limpiar_workspace])

# 11. Soporte en Pizarra [HS-08]
from Subagente_Diseno.skills.solicitar_soporte_pizarra.skill_solicitar_soporte_pizarra import (
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra,
    obtener_prompt_solicitar_soporte_pizarra
)
HERRAMIENTAS_DISENO.extend([tool_solicitar_ayuda_pizarra, tool_consultar_estado_ticket_pizarra])

# 12. Auto-Aprendizaje Continuo [HS-07]
from Subagente_Diseno.skills.auto_aprendizaje.skill_auto_aprendizaje import (
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    obtener_prompt_auto_aprendizaje
)
HERRAMIENTAS_DISENO.extend([tool_consultar_playbook_memoria, tool_registrar_playbook_memoria])

# 13. Manos y Ojos (Navegación Web con Playwright y Control de PC con PyAutoGUI + Visión IA)
from Subagente_Diseno.skills.manos_y_ojos import (
    HERRAMIENTAS_MANOS_Y_OJOS,
    obtener_prompt_manos_y_ojos
)
HERRAMIENTAS_DISENO.extend(HERRAMIENTAS_MANOS_Y_OJOS)

NOMBRE_AGENTE = "Subagente_Diseno"
NOMBRE_AGENTE_ALIAS = "Nami"

# ═══════════════════════════════════════════════════════════════════════════════
# MAPA DE INYECCIÓN NIVEL 2: Herramienta -> (Nombre_Skill, Prompt_Getter)
# ═══════════════════════════════════════════════════════════════════════════════
MAPA_HERRAMIENTA_PROMPTS = {
    # 1. Base
    "crear_archivo": ("Operaciones Base de Archivos", obtener_prompt_base),
    "leer_archivo": ("Operaciones Base de Archivos", obtener_prompt_base),
    "listar_directorio": ("Operaciones Base de Archivos", obtener_prompt_base),
    "ejecutar_comando": ("Operaciones Base de Archivos", obtener_prompt_base),
    # 2. IA Creativa
    "generar_multimedia_ia": ("Generación Multimedia e IA Creativa", obtener_prompt_ia_creativa),
    "auditar_calidad_imagen": ("Generación Multimedia e IA Creativa", obtener_prompt_ia_creativa),
    "consultar_catalogo_prompts": ("Generación Multimedia e IA Creativa", obtener_prompt_ia_creativa),
    "consultar_catalogo_estilos": ("Generación Multimedia e IA Creativa", obtener_prompt_ia_creativa),
    "consultar_catalogo_sujetos": ("Generación Multimedia e IA Creativa", obtener_prompt_ia_creativa),
    "consultar_brand_book": ("Generación Multimedia e IA Creativa", obtener_prompt_ia_creativa),
    # 3. Imágenes Locales
    "maquetar_carrusel_instagram": ("Maquetación Local de Imágenes y Feeds", obtener_prompt_imagenes_locales),
    "maquetar_carrusel_completo": ("Maquetación Local de Imágenes y Feeds", obtener_prompt_imagenes_locales),
    "superponer_branding_producto": ("Maquetación Local de Imágenes y Feeds", obtener_prompt_imagenes_locales),
    # 4. Video (I2V)
    "generar_video_ia": ("Dirección y Generación de Vídeo con IA (I2V)", obtener_prompt_video),
    "estructurar_prompt_movimiento_video": ("Dirección y Generación de Vídeo con IA (I2V)", obtener_prompt_video),
    # 4.1 Edición Dinámica de Vídeo y Motion Graphics
    "superponer_motion_overlay": ("Edición Dinámica de Vídeo y Motion Graphics", obtener_prompt_edicion_video),
    "insertar_broll": ("Edición Dinámica de Vídeo y Motion Graphics", obtener_prompt_edicion_video),
    "generar_subtitulos_dinamicos": ("Edición Dinámica de Vídeo y Motion Graphics", obtener_prompt_edicion_video),
    "generar_lower_third_callout": ("Edición Dinámica de Vídeo y Motion Graphics", obtener_prompt_edicion_video),
    "ensamblar_edicion_video_completa": ("Edición Dinámica de Vídeo y Motion Graphics", obtener_prompt_edicion_video),
    # 4.2 Descarga Universal de Multimedia y Redes Sociales
    "descargar_video_redes": ("Descarga Universal de Multimedia y Redes Sociales", obtener_prompt_descargar_multimedia),
    "extraer_audio_redes": ("Descarga Universal de Multimedia y Redes Sociales", obtener_prompt_descargar_multimedia),
    "inspeccionar_info_multimedia": ("Descarga Universal de Multimedia y Redes Sociales", obtener_prompt_descargar_multimedia),
    # 5. Presentaciones
    "generar_presentacion_marp": ("Presentaciones Ejecutivas Marp", obtener_prompt_presentaciones),
    # 6. Buscar Internet
    "buscar_referencias_diseno": ("Búsqueda Web y Referencias de Diseño", obtener_prompt_buscar_internet),
    "tool_buscar_internet_diseno": ("Búsqueda Web y Referencias de Diseño", obtener_prompt_buscar_internet),
    "tool_buscar_internet_nami": ("Búsqueda Web y Referencias de Diseño", obtener_prompt_buscar_internet),
    # 7. Sentry
    "tool_consultar_sentry_errores": ("Diagnóstico Sentry y Resiliencia", obtener_prompt_sentry),
    "tool_registrar_solucion_error": ("Diagnóstico Sentry y Resiliencia", obtener_prompt_sentry),
    "tool_reportar_fallo_critico": ("Diagnóstico Sentry y Resiliencia", obtener_prompt_sentry),
    # 8. Limpieza Workspace
    "tool_limpiar_workspace_diseno": ("Higiene de Workspace", obtener_prompt_limpiar_workspace),
    "tool_limpiar_habitacion_nami": ("Higiene de Workspace", obtener_prompt_limpiar_workspace),
    "tool_limpiar_workspace": ("Higiene de Workspace", obtener_prompt_limpiar_workspace),
    # 9. Soporte Pizarra
    "tool_solicitar_ayuda_pizarra": ("Solicitud de Soporte en Pizarra", obtener_prompt_solicitar_soporte_pizarra),
    "tool_consultar_estado_ticket_pizarra": ("Solicitud de Soporte en Pizarra", obtener_prompt_solicitar_soporte_pizarra),
    # 10. Auto-Aprendizaje
    "tool_consultar_playbook_memoria": ("Auto-Aprendizaje Continuo", obtener_prompt_auto_aprendizaje),
    "tool_registrar_playbook_memoria": ("Auto-Aprendizaje Continuo", obtener_prompt_auto_aprendizaje),
    # 11. Manos y Ojos
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
_DEFAULT_PROV = os.getenv("PROVIDER_SUBAGENTE_DISENO") or os.getenv("PROVIDER_NAMI") or os.getenv("DEFAULT_PROVIDER", "deepseek").lower()
_LLM_API_KEY = os.getenv(f"{_DEFAULT_PROV.upper()}_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
_LLM_BASE_URL = "https://api.deepseek.com" if _DEFAULT_PROV == "deepseek" else None
_LLM_MODEL = os.getenv(f"MODEL_SUBAGENTE_DISENO") or os.getenv(f"MODEL_NAMI") or ("deepseek-chat" if _DEFAULT_PROV == "deepseek" else "gpt-4o")
_LLM_TEMPERATURE = float(os.getenv("TEMP_SUBAGENTE_DISENO", "0.2"))
_LLM_MAX_TOKENS = int(os.getenv("MAX_TOKENS_SUBAGENTE_DISENO", "4096"))


def _crear_client() -> OpenAI:
    """Instancia el cliente LLM."""
    api_key = _LLM_API_KEY
    base_url = _LLM_BASE_URL
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = None
    return OpenAI(api_key=api_key, base_url=base_url)


def cargar_prompt_diseno() -> str:
    """Carga el System Prompt SSOT canónico desde _agents/agente.md."""
    archivo_perfil = _SUBAGENTE_PATH / "_agents" / "agente.md"
    if archivo_perfil.exists():
        return archivo_perfil.read_text(encoding="utf-8", errors="replace")

    perfil = cargar_perfil_agente(NOMBRE_AGENTE) or cargar_perfil_agente(NOMBRE_AGENTE_ALIAS)
    if perfil and "presentacion" in perfil:
        return perfil["presentacion"]

    return f"Eres {NOMBRE_AGENTE} (alias {NOMBRE_AGENTE_ALIAS}), Directora Creativa y Diseñadora UI/UX."


def detectar_prompts_habilidad(texto_tarea: str) -> List[str]:
    """
    Inyección Nivel 1: Detecta intenciones y requerimientos en la tarea asignada
    e inyecta preventivamente el System Prompt de la habilidad correspondiente.
    """
    t = texto_tarea.lower()
    inyectados = []

    # IA Creativa / Multimedia / Imágenes / Brand Book
    if any(k in t for k in ["imagen", "foto", "fotografía", "higgsfield", "dall-e", "ideogram", "pollinations", "multimedia", "ilustración", "banner", "publicidad", "packshot", "diseño visual", "ia creativa", "brand book", "brand_book", "identidad de marca", "manual de marca"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de IA Creativa.")
            inyectados.append(obtener_prompt_ia_creativa())
        except Exception:
            pass

    # Feeds / Carruseles Instagram
    if any(k in t for k in ["carrusel", "feed", "instagram", "overlay"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Imágenes Locales.")
            inyectados.append(obtener_prompt_imagenes_locales())
        except Exception:
            pass

    # Video I2V con IA
    if any(k in t for k in ["video", "vídeo", "reel", "tiktok", "short", "higgsfield", "kling", "i2v", "image-to-video", "imagen en movimiento"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Vídeo I2V.")
            inyectados.append(obtener_prompt_video())
        except Exception:
            pass

    # Edición Dinámica de Vídeo / Motion Graphics / B-Roll / Captions
    if any(k in t for k in ["b-roll", "broll", "overlay", "caption", "subtítulo", "subtitulo", "hormozi", "lower third", "tercero inferior", "callout", "motion graphic", "sticker animado", "postproducción", "edición de video"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Edición Dinámica de Vídeo.")
            inyectados.append(obtener_prompt_edicion_video())
        except Exception:
            pass

    # Descarga Universal de Multimedia y Redes Sociales (yt-dlp)
    if any(k in t for k in ["descargar", "descarga", "bajar video", "bajar audio", "extraer audio", "descargame", "descárgame", "url de instagram", "url de tiktok", "url de youtube", "link de video", "link de instagram", "link de tiktok"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Descarga Multimedia.")
            inyectados.append(obtener_prompt_descargar_multimedia())
        except Exception:
            pass

    # Presentaciones Marp
    if any(k in t for k in ["presentacion", "presentación", "marp", "pitch", "slide", "diapositiva"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Presentaciones Marp.")
            inyectados.append(obtener_prompt_presentaciones())
        except Exception:
            pass

    # Búsqueda Web / Referencias
    if any(k in t for k in ["buscar", "investigar", "referencia", "benchmark", "tendencia visual"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Búsqueda Web.")
            inyectados.append(obtener_prompt_buscar_internet())
        except Exception:
            pass

    # Sentry / Excepciones
    if any(k in t for k in ["sentry", "error", "fallo", "excepción", "remedio"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Sentry.")
            inyectados.append(obtener_prompt_sentry())
        except Exception:
            pass

    # Limpiar Workspace / Habitación
    if any(k in t for k in ["limpiar", "limpieza", "purgar", "habitacion", "habitación"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Limpieza Workspace.")
            inyectados.append(obtener_prompt_limpiar_workspace())
        except Exception:
            pass

    # Soporte Pizarra / Pausa Operativa
    if any(k in t for k in ["ayuda", "bloqueo", "soporte", "auxilio", "pausa operativa"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Soporte Pizarra.")
            inyectados.append(obtener_prompt_solicitar_soporte_pizarra())
        except Exception:
            pass

    # Auto-Aprendizaje / Playbooks
    if any(k in t for k in ["playbook", "blueprint", "memoria procedural", "auto-aprendizaje", "autoaprendizaje", "one-shot"]):
        try:
            print(f"[{NOMBRE_AGENTE}] 💉 Inyección preventiva: System Prompt de Auto-Aprendizaje.")
            inyectados.append(obtener_prompt_auto_aprendizaje())
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
    """Construye el System Prompt combinando el SSOT canónico y las directivas de Nivel 1."""
    prompt_base = cargar_prompt_diseno()
    if instruccion:
        prompts_especificos = detectar_prompts_habilidad(instruccion)
        if prompts_especificos:
            prompt_base += "\n\n" + "\n\n".join(prompts_especificos)
    return prompt_base


def _ejecutar_herramienta(nombre_tool: str, args_tool: dict) -> str:
    """Localiza y ejecuta la herramienta adecuada."""
    for herramienta in HERRAMIENTAS_DISENO:
        nombre = getattr(herramienta, 'name', None) or getattr(herramienta, '__name__', None)
        if nombre == nombre_tool:
            try:
                if hasattr(herramienta, 'invoke'):
                    resultado = herramienta.invoke(args_tool)
                else:
                    resultado = herramienta(**args_tool)
                return str(resultado)
            except Exception as e:
                return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "error", "mensaje": f"Herramienta '{nombre_tool}' no encontrada."}, ensure_ascii=False)


def _herramientas_schema() -> list:
    """Genera el schema para function calling de OpenAI."""
    schemas = []
    for h in HERRAMIENTAS_DISENO:
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
    Ejecuta herramientas e inyecta dinámicamente las directivas de Nivel 2.
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
    Ejecuta un ciclo completo de razonamiento y diseño para el Subagente de Diseño.
    Aplica el Escudo JSON con validación Zero-Trust de evidencia física en informes/.
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
            return json.dumps({"status": "error", "mensaje": f"Error llamando al LLM: {str(e)}"}, ensure_ascii=False)

        if hasattr(response, "usage") and response.usage:
            try:
                from costos_tracker import registrar_consumo_tokens
                in_t = getattr(response.usage, "prompt_tokens", 0) or 0
                out_t = getattr(response.usage, "completion_tokens", 0) or 0
                registrar_consumo_tokens("subagente_diseno", in_t, out_t, _LLM_MODEL)
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
                            "Este campo DEBE contener la ruta física al prototipo HTML o asset generado en informes/. "
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
                "{\"ticket_actualizado\": \"<markdown>\", \"evidencia_hallazgo\": \"<ruta_al_archivo_en_informes>\"}."
            )})
            continue

        # Envoltura de seguridad si se agotan las rondas
        entregables = sorted(INFORMES_PATH.glob("*.*"), reverse=True)
        ruta_evidencia = str(entregables[0]) if entregables else "/app/Subagente_Diseno/informes/index.html"
        return json.dumps({
            "ticket_actualizado": respuesta,
            "evidencia_hallazgo": ruta_evidencia
        }, ensure_ascii=False)

    return json.dumps({
        "ticket_actualizado": "Límite de rondas alcanzado en Subagente_Diseno.",
        "evidencia_hallazgo": "Límite de rondas alcanzado."
    }, ensure_ascii=False)


def funcion_nodo_subagente_diseno(estado: dict) -> dict:
    """Función de nodo para LangGraph en el flujo del Subagente de Diseño."""
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
    print(f"[{NOMBRE_AGENTE}] Activada. Procesando diseño...")

    respuesta_final = ejecutar_ciclo(instruccion)
    print(f'=== SUBAGENTE_DISENO RESPONSE ===\n{respuesta_final}\n====================================')

    return {"messages": [AIMessage(content=respuesta_final, name=NOMBRE_AGENTE)]}


# Exportar alias de compatibilidad canónica
funcion_nodo_nami = funcion_nodo_subagente_diseno


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Diseña un dashboard interactivo moderno para telemetría de agentes."
    print(ejecutar_ciclo(entrada))
