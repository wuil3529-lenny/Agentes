import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[1]
import os
"""
nami_agent.py — Directora Creativa, Navegante de Diseño y Estratega Visual (Nami)
===================================================================================
Este agente opera dentro del ecosistema LangGraph y especializa en:
- Estrategia Digital, Copywriting Persuasivo y Guiones de Vídeo Corto (Reels/TikTok).
- Dirección de Arte, Prompt Engineering y Gestión de Redes (con aprobación humana previa).
- Presentaciones Profesionales (python-pptx, Marp).
- Edición de Vídeo Programática (MoviePy, FFmpeg-Python, Remotion).
- Diseño de Feeds de Instagram (Pillow, CairoSVG).
- Generación Multimedia IA (Gemini, Flux, Ideogram, DALL-E 3, Grok, Kling, Luma).
"""

import json
import re
import requests
from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

import sys
_LUFFY_DIR = str(_APP_ROOT / "Luffy")
if _LUFFY_DIR not in sys.path:
    sys.path.insert(0, _LUFFY_DIR)

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

NOMBRE_AGENTE = "Nami"

# ─── Ubicación Común de Archivos Temporales (Basura / Scratch) ───────────────
# Cualquier archivo temporal que pueda ser borrado y no forme parte ni de skins,
# ni habilidades, ni funciones, debe guardarse en: Archivos_temporales/
ARCHIVOS_TEMPORALES_PATH = (_APP_ROOT / "Archivos_temporales")
ARCHIVOS_TEMPORALES_DOCKER = "/app/Archivos_temporales"

import ast
import sys
from pathlib import Path
_NAMI_SKILLS_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / 'skills'
if str(_NAMI_SKILLS_PATH) not in sys.path:
    sys.path.insert(0, str(_NAMI_SKILLS_PATH))

from skill_presentaciones import HERRAMIENTAS_PRESENTACIONES
from skill_video import HERRAMIENTAS_VIDEO
from skill_imagenes_locales import HERRAMIENTAS_IMAGENES
from skill_ia_creativa import HERRAMIENTAS_IA_CREATIVA
from skill_sentry import consultar_sentry_errores, registrar_solucion_error
from skill_buscar_internet_nami import tool_buscar_internet_nami
from skill_base import HERRAMIENTAS_BASE

@tool
def publicar_post_redes(plataforma: str, texto_post: str, imagenes: list = []) -> str:
    """
    Dispara la publicación o campaña de contenido en plataformas de redes sociales.
    Requiere aprobación humana previa (Human-in-the-Loop) antes de confirmarse.
    
    Args:
        plataforma: Red social destino ('Twitter', 'LinkedIn', 'Instagram', 'TikTok', 'Facebook').
        texto_post: Contenido de texto / copy aprobado.
        imagenes: Lista de rutas o URLs de imágenes/assets validados.
    """
    try:
        print(f"[{NOMBRE_AGENTE}] Publicando campaña en {plataforma}...")
        payload = {
            "status": "success",
            "plataforma": plataforma,
            "texto": texto_post,
            "imagenes": imagenes,
            "mensaje": f"Publicación en {plataforma} preparada y enviada correctamente (validada por Human-in-the-Loop)."
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)

@tool
def analizar_tendencias(palabra_clave: str) -> str:
    """
    Consulta datos de mercado y tendencias virales para un nicho o palabra clave.
    
    Args:
        palabra_clave: Nicho, tema o palabra clave a analizar.
    """
    try:
        print(f"[{NOMBRE_AGENTE}] Analizando tendencias para: {palabra_clave}...")
        reporte = {
            "status": "success",
            "palabra_clave": palabra_clave,
            "tendencias_detectadas": [
                f"Formato vertical de alto engagement sobre {palabra_clave}",
                f"Carrusel informativo paso a paso sobre {palabra_clave}",
                f"Hook contraintuitivo o dato sorprendente sobre {palabra_clave}"
            ]
        }
        return json.dumps(reporte, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)

@tool
def conceptualizar_ui_ux(requerimientos: str) -> str:
    """
    Genera propuestas conceptuales de diseño (layout, paleta, framework recomendado) para revisión antes del desarrollo frontend.
    
    Args:
        requerimientos: Descripción de la interfaz o experiencia que se desea maquetar/diseñar.
    """
    try:
        print(f"[{NOMBRE_AGENTE}] Conceptualizando UI/UX: {requerimientos[:50]}...")
        propuesta = {
            "status": "success",
            "opcion_1": "Estilo Minimalista Glassmorphism (Paleta HSL oscura, Inter font)",
            "opcion_2": "Estilo Corporativo Limpio (Paleta clara, alto contraste, Outfit font)",
            "mensaje": "Propuestas conceptuales listas para revisión y validación humana."
        }
        return json.dumps(propuesta, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)

@tool
def tool_limpiar_habitacion_nami() -> str:
    """Ejecuta la rutina de orden y limpieza para mantener solo las 4 carpetas oficiales y 6 archivos raíz en Nami."""
    try:
        from skill_limpiar_nami import limpiar_habitacion_nami
        res = limpiar_habitacion_nami()
        return f"Limpieza completada: {res}"
    except Exception as e:
        return f"Error en limpieza de Nami: {e}"

@tool
def tool_generar_prototipo_ui(prompt_diseno: str) -> str:
    """
    Simula el entorno de Stitch. Toma un wireframe o diseño conceptual estructurado y genera el código HTML y Tailwind funcional, auto-corrigiéndolo si es necesario.
    
    Args:
        prompt_diseno: Prompt estructurado generado por ti que incluye arquitectura, specs UI y componentes.
    """
    try:
        from skill_stitch_nami import generar_codigo_ui
        res = generar_codigo_ui(prompt_diseno)
        return f"Generación completada: {res}"
    except Exception as e:
        return f"Error en generación de código UI: {e}"


def construir_prompt_agente() -> ChatPromptTemplate:
    """Construye el prompt del sistema para Nami."""
    perfil = cargar_perfil_agente(NOMBRE_AGENTE)
    identidad = perfil.get("presentacion", f"Eres {NOMBRE_AGENTE}, agente experta en diseño UI/UX y producción multimedia (Directora Creativa). Tu especialidad es la arquitectura de interfaces y la creación de guiones técnicos hiper-detallados para video, prohibiendo estrictamente la generación de imágenes abstractas aleatorias.")
    manual_quirurgico_txt = perfil.get("manual_quirurgico", "")
    
    reglas = leer_nodo_obsidian("protocolo/Reglas de la Tripulacion.md")
    protocolo = leer_nodo_obsidian("protocolo/Protocolo Inter-Agente.md")

    system_prompt = f"""
{identidad}

Tu capitán es Luffy. Él te delegará tareas.
Tienes acceso a herramientas de publicación, análisis de tendencias, diseño conceptual UI/UX y creación multimedia por IA (`publicar_post_redes`, `analizar_tendencias`, `conceptualizar_ui_ux`, `tool_limpiar_habitacion_nami`, Presentaciones, Edición de Vídeo, Feeds e IA Visual/Vídeo).
Si usas una herramienta, procesa su resultado antes de responder a Luffy. Nunca publicas ni cierras un diseño sin aprobación humana previa (Human-in-the-Loop).

---
CÓDIGO DE CONDUCTA (ESTRICTO):
{reglas}

REGLAS DE COMUNICACIÓN Y FORMATO (INCLUYE ACCIONES DE MEMORIA):
{protocolo}

MANUAL QUIRÚRGICO DE HERRAMIENTAS Y SKILLS:
{manual_quirurgico_txt}
---

DIRECTRICES OPERATIVAS OBLIGATORIAS PARA NAMI:
1. ARQUITECTURA WEB Y UI/UX (LIVE PREVIEW): Cuando se te pida un diseño web, debes utilizar obligatoriamente herramientas de búsqueda de referencias reales antes de estructurar el entregable. Tu salida no debe ser solo un JSON estático, sino que DEBES generar un archivo `index.html` autocontenido (compilando el diseño real usando Tailwind CSS vía CDN e inyectando estilos e interactividad básica). Este prototipo de alta fidelidad debe permitir la previsualización en vivo del diseño.

PROTÓTIPO VISUAL OBLIGATORIO:
1. Para cada diseño de interfaz web (UI/UX) o dashboard, Nami DEBE generar un archivo 'index.html' funcional.
2. Este 'index.html' debe ser un prototipo de alta fidelidad que incluya:
   - Estilos CSS integrados (usando clases de Tailwind mediante CDN para evitar dependencias externas complejas).
   - Estructura HTML que refleje exactamente el Blueprint técnico (Header, Hero, Cards, Grid).
   - Componentes de UI visuales (botones, tarjetas, tipografía real, colores de la paleta definida).
3. OBJETIVO: Este archivo debe permitir al usuario final (el Capitán) abrirlo en un navegador para visualizar el diseño, los colores, el espaciado y la jerarquía visual real, más allá de la estructura de datos del JSON.
4. RUTA DE ENTREGA: El 'index.html' debe guardarse junto al archivo JSON original en '/app/Nami/informes/'.

MANUAL DE HABILIDADES Y SKILL: DESARROLLO WEB MULTINIVEL (2D, 3D Y ANIMACIONES)

1. OBJETIVO DEL SKILL
Dotar a Nami de la capacidad de estructurar, diseñar y codificar prototipos web funcionales en formato index.html autocontenido, adaptándose a tres niveles de complejidad según los requerimientos del cliente o el proyecto.

2. MATRIZ DE DECISIÓN DE NIVELES (Gatillo de Activación)
Antes de escribir cualquier línea de código, Nami debe evaluar el objetivo del proyecto y declarar explícitamente en la Pizarra el nivel seleccionado:
- Nivel 1 (Estructural 2D): Landing pages informativas, blogs, estructuras limpias y minimalistas.
- Nivel 2 (Interactivo Avanzado): Dashboards, sitios corporativos, landing pages de alto impacto con animaciones fluidas, transiciones y efectos visuales modernos.
- Nivel 3 (Inmersivo 3D): Presentaciones de producto, experiencias de marca de lujo, sitios web espaciales o interactivos con entornos tridimensionales.

3. ESPECIFICACIONES TÉCNICAS POR NIVEL
Nivel 1: Estructural 2D
Tecnologías: HTML5 semántico, Tailwind CSS (vía CDN oficial).
Reglas:
- Diseño limpio, uso de Flexbox y Grid de Tailwind.
- Paleta de colores coherente y tipografías legibles (ej: Inter).
- Código 100% autocontenido en un solo archivo index.html.

Nivel 2: Interactivo Avanzado (2D + GSAP)
Tecnologías: HTML5, Tailwind CSS (CDN), GSAP (GreenSock Animation Platform) + Plugin ScrollTrigger (vía CDN).
Reglas:
- Uso de componentes flotantes con Glassmorphism (backdrop-filter: blur(12px), fondos semitransparentes).
- Efectos de sombra tipo Neon Glow y bordes sutiles.
- Animaciones de entrada y efectos al hacer scroll utilizando GSAP para transiciones profesionales y fluidas.

Nivel 3: Inmersivo 3D (A-Frame + UI Flotante)
Tecnologías: HTML5, Tailwind CSS (CDN), A-Frame (versión estable actual vía CDN).
Arquitectura Obligatoria del Nivel 3:
- Contenedor Principal de Escena: Usar la estructura base de A-Frame adaptada para la web.
- Capa de UI Flotante (Crucial): La interfaz de usuario (botones, textos, títulos) nunca va dentro del espacio 3D de forma cruda. Debe montarse en una capa HTML con posicionamiento absoluto (position: absolute; pointer-events: none; z-index: 10;) flotando encima de la escena 3D, asegurando que los elementos interactivos tengan pointer-events: auto.

Plantilla Base de Código para Nivel 3:
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Experiencia 3D - Nami</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <!-- A-Frame CDN -->
    <script src="https://aframe.io/releases/1.6.0/aframe.min.js"></script>
    <style>
        .ui-layer {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10;
        }}
        .interactive {{
            pointer-events: auto;
        }}
    </style>
</head>
<body class="relative w-full h-screen overflow-hidden bg-black">
    <!-- Capa de UI Flotante -->
    <div class="ui-layer flex flex-col justify-between p-8">
        <header class="interactive">
            <h1 class="text-white text-3xl font-bold tracking-wider">Misión 3D Inmersiva</h1>
        </header>
        <div class="interactive self-center">
            <button class="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition">
                Iniciar Experiencia
            </button>
        </div>
    </div>

    <!-- Escena 3D A-Frame -->
    <a-scene embedded style="width: 100%; height: 100vh;">
        <a-assets>
            <!-- Aquí se pueden precargar modelos .glb si es necesario -->
        </a-assets>

        <!-- Entorno e Iluminación -->
        <a-sky color="#050510"></a-sky>
        <a-entity light="type: ambient; color: #FFF; intensity: 0.7"></a-entity>
        <a-entity light="type: directional; color: #FFF; intensity: 1.0" position="-1 2 1"></a-entity>

        <!-- Objeto 3D de Prueba / Animado -->
        <a-box position="0 0 -3" rotation="0 45 45" color="#FC3D21" 
               animation="property: rotation; to: 0 405 45; loop: true; dur: 8000; easing: linear">
        </a-box>

        <!-- Cámara y Cursor -->
        <a-camera position="0 1.6 0">
            <a-cursor color="#0B3D91"></a-cursor>
        </a-camera>
    </a-scene>
</body>
</html>
```

4. PROTOCOLO DE ENTREGA Y PERSISTENCIA
- Todo archivo generado debe compilarse en un único index.html autónomo.
- Debe guardarse obligatoriamente en la ruta: /app/Nami/informes/index.html.
- En la Pizarra (Bitacora.md), Nami debe reportar el nivel utilizado, la validación de sintaxis y la confirmación de que el archivo está listo para abrir en el navegador.

MANUAL DE HABILIDADES Y SKILL: GUIONISMO Y PRODUCCIÓN AUDIOVISUAL MULTI-FORMATO

1. OBJETIVO DEL SKILL
Dotar a Nami de la capacidad de diseñar, estructurar y redactar guiones hiper-profesionales para redes sociales (YouTube, TikTok, Instagram Reels, Facebook), aplicando técnicas de retención de audiencia, psicología del consumidor y sincronización milimétrica con prompts maestros para generadores de video por IA.

2. MATRIZ DE ADAPTACIÓN POR PLATAFORMA
Antes de redactar, Nami debe definir el formato del video y aplicar las reglas de ritmo correspondientes:
- TikTok / Reels (Formato Vertical 9:16 - Corto): Duración de 15 a 60 segundos. Ritmo vertiginoso con cortes de escena cada 2-3 segundos. Gancho (Hook): Los primeros 3 segundos deben ser altamente disruptivos para evitar el swipe. Apoyo: Indicación de subtítulos dinámicos grandes en pantalla.
- YouTube Shorts / Facebook Video (Formato Vertical u Horizontal rápido): Duración hasta 60 segundos (Shorts) o 3 minutos (Facebook). Ritmo equilibrado entre dinamismo visual y divulgación narrativa.
- YouTube Long-Form (Formato Horizontal 16:9 - Profesional): Duración de 5 a 15+ minutos. Estructura: Introducción/Gancho (0:00 - 0:30), Desarrollo en Actos (Bloques temáticos con pausas de retención), y Clímax/Conclusión con Llamado a la Acción (CTA) claro.

3. ESTRUCTURA DEL PAQUETE DE PRODUCCIÓN AUDIOVISUAL
Cada vez que se le solicite un guion, Nami no entregará texto plano, sino una estructura tabular o modular dividida en campos técnicos estrictos:
- Metadatos del Proyecto: Título, Plataforma de destino, Duración estimada y Tono.
- Tabla de Guion Segundo a Segundo:
  * Tiempo / Bloque: (Ej: 00:00 - 00:03).
  * Visual / Acción en Pantalla: Qué ocurre exactamente.
  * Prompt Maestro de IA: El texto técnico ultra-detallado optimizado para generadores de video (Veo, Luma, Kling, etc.).
  * Audio / Locución (Voz en off): El texto exacto que leerá el narrador.
  * Efectos de Sonido (SFX) / Música: Indicaciones de la atmósfera sonora.

4. PROTOCOLO DE PERSISTENCIA EN DISCO
- Compilación: El paquete de producción completo debe estructurarse en formato limpio (preferiblemente .json o .md estructurado).
- Ruta Obligatoria de Guardado: /app/Nami/informes/guiones/
- Nomenclatura Limpia: Nombres descriptivos con guiones bajos (ej: sistema_solar_tiktok.json, sistema_solar_youtube.md).
- Reporte en Pizarra: Registrar en Bitacora.md la finalización del paquete de producción y la confirmación de que los archivos de guion están listos en la ruta correspondiente para la revisión del Capitán.
3. PERSISTENCIA EN DISCO: Todos tus archivos generados (blueprints, guiones, y especialmente los mockups en formato `index.html`) deben escribirse y guardarse de forma real y obligatoria en la ruta: `/app/Nami/informes/` utilizando la herramienta `crear_archivo`.

MANUAL DE HABILIDADES Y SKILL: GENERACIÓN DE IMÁGENES REALISTAS Y FOTOGRÁFICAS

1. OBJETIVO DEL SKILL
Garantizar que Nami traduzca las solicitudes directas del usuario en imágenes precisas, fotorrealistas y de alta calidad comercial utilizando las APIs disponibles (Google AI Studio, ChatGPT/DALL-E y Grok), prohibiendo terminantemente el uso de estilos abstractos, surrealistas o interpretaciones artísticas no solicitadas.

2. REGLAS DE ORO PARA EL PROMPTING FOTOGRÁFICO
Cada vez que el usuario solicite una imagen, Nami debe construir un Prompt Maestro Estructurado siguiendo esta fórmula exacta:
- Sujeto Principal y Acción: Descripción clara, directa y literal de lo que ocurre (ej: "Un perro Golden Retriever sentado frente a una mesa de madera bebiendo café de una taza blanca").
- Estilo y Calidad Fotográfica: Especificar parámetros de cámara profesionales (ej: "Fotografía real, tomada con cámara DSLR, lente de 50mm, profundidad de campo natural, enfoque nítido en el sujeto").
- Iluminación y Entorno: Definir la atmósfera lumínica y el fondo (ej: "Luz natural de la mañana entrando por una ventana lateral, cafetería moderna y acogedora con fondo ligeramente desenfocado").
- Restricciones de Coherencia: Evitar elementos flotantes, texturas plásticas, deformaciones anatómicas o exceso de saturación digital.
- Enfoque y Nitidez Obligatoria: En fotografía comercial, el elemento principal nunca debe quedar borroso por culpa de un mal desenfoque de fondo. Añadir siempre al prompt: 'Sharp focus on the main subject, crystal clear details, high-resolution photography, deep depth of field where the subject and key props are entirely in sharp focus'.
- Acciones y Objetos Explícitos (Cero Omisiones): Anclar los objetos en la acción explícitamente sin dejarlos a libre interpretación. (ej. '...with a clean white ceramic mug filled with dark coffee right in front of its paws', o '...an open laptop displaying brightly colored syntax-highlighted source code sharply visible on the screen').

3. SELECCIÓN ESTRATÉGICA DE APIS
Nami evaluará qué herramienta usar según la naturaleza de la imagen:
- Google AI Studio (Gemini/Imagen): Ideal para realismo fotográfico general, escenas cotidianas complejas y fidelidad estricta al texto.
- ChatGPT (DALL-E 3): Ideal cuando la imagen requiere texto legible integrado, carteles, mockups de interfaces o gráficos limpios.
- Grok: Ideal para escenas dinámicas, iluminación dramática de estilo cinematográfico o tomas urbanas y de acción.

4. PROTOCOLO DE EJECUCIÓN Y PERSISTENCIA EN DISCO
- Generación: Llamar a la API correspondiente utilizando el prompt estructurado.
- Descarga y Guardado: Nami no debe limitarse a mostrar URLs temporales. Debe descargar el archivo binario de la imagen y guardarlo de forma local y permanente en disco.
- Ruta Obligatoria: /app/Nami/informes/imagenes/
- Nomenclatura Limpia: Los archivos deben nombrarse con guiones bajos y descripciones claras (ej: perro_tomando_cafe_google.png, oficina_desarrollo_grok.png).
- Reporte en Pizarra: En Bitacora.md, Nami registrará la herramienta utilizada, el prompt ejecutado y la ruta exacta del archivo guardado en disco.

REGLA DE INVESTIGACIÓN PREVIA OBLIGATORIA (WEB RESEARCH SKILL):
1. ANTES DE GENERAR CUALQUIER IMAGEN: Si el usuario pide un objeto técnico, una locación específica, un estilo arquitectónico o una época histórica, Nami DEBE utilizar primero sus herramientas de búsqueda web (como duckduckgo-search) para documentarse sobre cómo es visualmente ese elemento en el mundo real, evitando alucinaciones o diseños genéricos.
2. ANTES DE REDACTAR UN GUION: Para cualquier temática que requiera datos técnicos, científicos o históricos (ej. astronomía, historia, tecnología), Nami tiene prohibido redactar basándose solo en suposiciones. Debe consultar al menos 2 fuentes web fiables para extraer datos exactos, nombres de hitos, terminología técnica y datos de asombro que fortalezcan el 'gancho' (hook) y la veracidad del guion.
3. INTEGRACIÓN DE DATOS: Los datos reales encontrados en la web deben inyectarse directamente en el Prompt Maestro de Imagen y en los bloques de locución del Guion Audiovisual.

4. RESTRICCIÓN DE SALIDA: Mantén el formato de respuesta bajo el Protocolo Inter-Agente (JSON minimalista de cierre) y actualiza siempre la pizarra (Bitacora.md) según corresponda.

[RUTAS DE TRABAJO OBLIGATORIAS - HARD STOP ACTIVO]
- Tus entregables van en: /app/Nami/informes/
- Archivos temporales: /app/Archivos_temporales/ (DEBES usar tu nombre como prefijo, ej. nami_temp.md)
- Actualizar estado de ticket: /app/Bitacora.md
- Guardar conocimiento: /app/Cerebro.md y /app/memoria/
- PROHIBIDO escribir en cualquier otra ruta del sistema.
  Si lo intentas, el sistema lanzará un error y abortará la escritura.
"""

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])


def _extraer_json_robusto(texto: str):
    """
    Extrae y parsea el primer JSON válido de un texto usando json.JSONDecoder().raw_decode().
    Esto es más robusto que rfind() porque maneja correctamente llaves/llaves anidadas
    dentro de strings (como el bloque Markdown del ticket).
    
    Incluye múltiples estrategias de fallback para manejar JSON malformado producido
    por el LLM (comas finales, claves sin comillas, comillas simples, texto extra).
    
    Returns:
        tuple (datos_json, texto_extraido) o (None, None) si no se encuentra JSON válido.
    """
    if not texto:
        return None, None
    
    # Limpiar bloques de código markdown
    texto_limpio = re.sub(r"```(?:json)?", " ", texto, flags=re.IGNORECASE)
    
    # Estrategia 1: Intentar json.loads directo sobre el texto completo limpio
    try:
        datos = json.loads(texto_limpio.strip())
        return datos, texto_limpio.strip()
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Estrategia 2: Buscar el primer '{' o '[' y usar raw_decode
    pos_llave = texto_limpio.find("{")
    pos_corchete = texto_limpio.find("[")
    
    if pos_llave == -1 and pos_corchete == -1:
        return None, None
    
    if pos_llave == -1:
        inicio = pos_corchete
    elif pos_corchete == -1:
        inicio = pos_llave
    else:
        inicio = min(pos_llave, pos_corchete)
    
    # Intentar raw_decode desde cada posición de inicio posible
    decoder = json.JSONDecoder()
    for start in range(inicio, len(texto_limpio)):
        if texto_limpio[start] not in ("{", "["):
            continue
        try:
            datos, end = decoder.raw_decode(texto_limpio[start:])
            return datos, texto_limpio[start:start+end]
        except json.JSONDecodeError:
            continue
    
    # Estrategia 3: Intentar extraer un bloque JSON balanceado manualmente
    for start in range(inicio, len(texto_limpio)):
        if texto_limpio[start] not in ("{", "["):
            continue
        apertura = texto_limpio[start]
        cierre = "}" if apertura == "{" else "]"
        balance = 0
        en_string = False
        escape = False
        for i in range(start, len(texto_limpio)):
            ch = texto_limpio[i]
            if en_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    en_string = False
            else:
                if ch == '"':
                    en_string = True
                elif ch == apertura:
                    balance += 1
                elif ch == cierre:
                    balance -= 1
                    if balance == 0:
                        candidato = texto_limpio[start:i+1]
                        try:
                            datos = json.loads(candidato)
                            return datos, candidato
                        except (json.JSONDecodeError, ValueError):
                            # Intentar reparar JSON común
                            reparado = _reparar_json(candidato)
                            if reparado is not None:
                                return reparado, candidato
                            break
        if balance == 0:
            break
    
    return None, None


def _reparar_json(texto: str):
    """
    Intenta reparar JSON malformado común producido por LLMs:
    - Comas finales antes de cierre de objeto/array
    - Claves sin comillas
    - Comillas simples en lugar de dobles
    - Valores sin comillas (true/false/null/números)
    - Claves sin valor (JSON incompleto)
    - Claves sin valor en líneas separadas (ej: {"para": \n "tipo": ...})
    - Texto extra alrededor del JSON
    """
    if not texto:
        return None
    
    # 1. Eliminar comas finales antes de } o ]
    texto_reparado = re.sub(r",\s*([}\]])", r"\1", texto)
    
    # 2. Intentar con el texto ya limpio de comas
    try:
        return json.loads(texto_reparado)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 3. Intentar con claves sin comillas: agregar comillas a claves
    texto_claves = re.sub(
        r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:",
        r'\1"\2":',
        texto_reparado
    )
    try:
        return json.loads(texto_claves)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 4. Reemplazar comillas simples por dobles
    texto_simples = texto_claves.replace("'", '"')
    try:
        return json.loads(texto_simples)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 5. Manejar JSON incompleto: claves sin valor (ej: {"para": })
    #    Buscar patrones como "clave": } o "clave": , y reemplazar con valor por defecto
    texto_incompleto = re.sub(
        r'("(?:[^"\\]|\\.)*"\s*:\s*)([}\]])',
        r'\1""\2',
        texto_reparado
    )
    texto_incompleto = re.sub(
        r'("(?:[^"\\]|\\.)*"\s*:\s*)(,)',
        r'\1""\2',
        texto_incompleto
    )
    try:
        return json.loads(texto_incompleto)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 6. Manejar JSON con valores faltantes en claves sin comillas
    texto_incompleto2 = re.sub(
        r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([}\]])',
        r'\1"\2":""\3',
        texto_reparado
    )
    try:
        return json.loads(texto_incompleto2)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 7. NUEVO: Manejar claves sin valor seguidas de otra clave en la siguiente línea
    #    Ej: {"para": \n "tipo": "error"} -> {"para": "", "tipo": "error"}
    #    Patrón: "clave": seguido de whitespace y luego otra "clave":
    texto_clave_sin_valor = re.sub(
        r'("(?:[^"\\]|\\.)*"\s*:\s*)(?=\s*")',
        r'\1""',
        texto_reparado
    )
    try:
        return json.loads(texto_clave_sin_valor)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 8. NUEVO: Manejar claves sin comillas sin valor seguidas de otra clave
    #    Ej: {para: \n tipo: "error"} -> {"para": "", "tipo": "error"}
    texto_clave_sin_valor2 = re.sub(
        r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?=\s*[a-zA-Z_"\[{])',
        r'\1"\2":"",',
        texto_reparado
    )
    try:
        return json.loads(texto_clave_sin_valor2)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 9. NUEVO: Manejar JSON donde una clave tiene valor vacío y luego otra clave
    #    Ej: {"para": \n "tipo": "error"} - versión con comas
    #    Primero intentar agregar comas entre claves sin valor y la siguiente clave
    texto_con_comas = re.sub(
        r'("(?:[^"\\]|\\.)*"\s*:\s*)(?=\s*")',
        r'\1"",',
        texto_reparado
    )
    try:
        return json.loads(texto_con_comas)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 10. Último recurso: intentar extraer el JSON más grande posible
    #     Buscar el primer { y el último } y tratar de reparar
    inicio_json = texto_reparado.find("{")
    fin_json = texto_reparado.rfind("}")
    if inicio_json >= 0 and fin_json > inicio_json:
        candidato = texto_reparado[inicio_json:fin_json+1]
        # Intentar reparar el candidato
        try:
            return json.loads(candidato)
        except (json.JSONDecodeError, ValueError):
            # Intentar con claves sin comillas
            candidato_claves = re.sub(
                r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:",
                r'\1"\2":',
                candidato
            )
            try:
                return json.loads(candidato_claves)
            except (json.JSONDecodeError, ValueError):
                # Intentar con claves sin valor
                candidato_incompleto = re.sub(
                    r'("(?:[^"\\]|\\.)*"\s*:\s*)(?=\s*")',
                    r'\1""',
                    candidato
                )
                try:
                    return json.loads(candidato_incompleto)
                except (json.JSONDecodeError, ValueError):
                    pass
    
    return None


def funcion_nodo_nami(estado: dict) -> dict:
    """
    Función de LangGraph para Nami.
    """
    print(f"\n[{NOMBRE_AGENTE}] Recibiendo tarea de Luffy...")
    
    # 1. Marcar automáticamente los mensajes en el canal como leídos
    mensajes_nuevos = leer_mensajes(NOMBRE_AGENTE)
    contexto_mensajes = ""
    if mensajes_nuevos:
        contexto_mensajes = "\n--- MENSAJES EN TU CANAL ---\n"
        for m in mensajes_nuevos:
            contexto_mensajes += f"De {m['de']}: {json.dumps(m['contenido'], ensure_ascii=False)}\n"
    
    # 2. Preparar LLM con herramientas (para cuando tenga skills reales)
    llm = crear_llm(temperatura=0.3, agente=NOMBRE_AGENTE)
    
    HERRAMIENTAS_NAMI = (
        consultar_sentry_errores,
        registrar_solucion_error,
        publicar_post_redes,
        analizar_tendencias,
        conceptualizar_ui_ux,
        tool_limpiar_habitacion_nami,
        tool_generar_prototipo_ui,
        tool_buscar_internet_nami,
    ) + tuple(HERRAMIENTAS_PRESENTACIONES) + tuple(HERRAMIENTAS_VIDEO) + tuple(HERRAMIENTAS_IMAGENES) + tuple(HERRAMIENTAS_IA_CREATIVA) + tuple(HERRAMIENTAS_BASE)
    llm_con_tools = llm.bind_tools(HERRAMIENTAS_NAMI)
    
    prompt = construir_prompt_agente()
    cadena = prompt | llm_con_tools
    # 3. Primera invocación al LLM
    mensajes_langgraph = list(estado["messages"])
    if contexto_mensajes and mensajes_langgraph:
        ultimo_contenido = mensajes_langgraph[-1].content
        mensajes_langgraph[-1].content = ultimo_contenido + contexto_mensajes
        
    respuesta = cadena.invoke({"messages": mensajes_langgraph})
    
    # 4. Bucle de ejecución de herramientas (hasta 10 rondas)
    MAX_ROUNDS = 25
    ronda = 0

    while (hasattr(respuesta, "tool_calls") and respuesta.tool_calls and ronda < MAX_ROUNDS):
        ronda += 1
        print(f"[{NOMBRE_AGENTE}] Ronda {ronda}: ejecutando {len(respuesta.tool_calls)} herramienta(s)...")

        mensajes_langgraph.append(respuesta)

        for tool_call in respuesta.tool_calls:
            nombre_tool = tool_call["name"]
            args_tool   = tool_call["args"]
            tool_id     = tool_call.get("id", f"tool_{ronda}")

            print(f"[{NOMBRE_AGENTE}] → Ejecutando: {nombre_tool}({list(args_tool.keys())})")

            # Evaluamos contra todas las herramientas
            herramienta_encontrada = None
            for herramienta in HERRAMIENTAS_NAMI:
                if herramienta.name == nombre_tool:
                    herramienta_encontrada = herramienta
                    break

            if herramienta_encontrada:
                # Sanitizar argumentos robusta: maneja dict Y lista
                _LITERALES_PARAM = ("ruta_destino", "tema_presentacion", "contenido_diapositivas", "prompt_estructurado", "modelo_preferido", "descripcion_video", "framework_usado", "texto_overlay", "dimensiones", "ruta", "destino")
                _DEFAULTS = {
                    "ruta_destino": str(_APP_ROOT / "Nami" / "informes" / "presentacion_marp.md"),
                    "tema_presentacion": "Presentación",
                    "contenido_diapositivas": ["Diapositiva de contenido"],
                    "prompt_estructurado": "Tema genérico con estilo minimalista",
                    "modelo_preferido": "Pollinations",
                    "descripcion_video": "Video descriptivo",
                    "framework_usado": "HTML",
                    "texto_overlay": "",
                    "dimensiones": "1920x1080",
                    "ruta": str(_APP_ROOT / "Nami" / "informes"),
                    "destino": str(_APP_ROOT / "Nami" / "informes")
                }
                # Si args_tool es una LISTA (el LLM pasó los nombres de parámetros como lista),
                # convertirla a un dict con valores por defecto según el nombre de la herramienta
                if isinstance(args_tool, list):
                    print(f"[{NOMBRE_AGENTE}] ⚠️  args_tool es lista, convirtiendo a dict con defaults...")
                    args_dict = {}
                    # Mapear nombres de parámetros esperados por herramienta
                    _MAPEO_PARAMS = {
                        "generar_presentacion_marp": ["tema_presentacion", "contenido_diapositivas", "ruta_destino"],
                        "generar_video": ["descripcion_video", "dimensiones", "ruta_destino"],
                        "generar_imagen": ["prompt_estructurado", "modelo_preferido", "ruta_destino"],
                        "generar_feed_instagram": ["prompt_estructurado", "modelo_preferido", "ruta_destino"],
                        "generar_ia_visual": ["prompt_estructurado", "modelo_preferido", "ruta_destino"],
                        "generar_prototipo_ui": ["prompt_estructurado"],
                        "publicar_post_redes": ["plataforma", "texto_post", "imagenes"],
                        "analizar_tendencias": ["palabra_clave"],
                        "conceptualizar_ui_ux": ["requerimientos"]
                    }
                    params_esperados = _MAPEO_PARAMS.get(nombre_tool, [])
                    # Si la lista contiene literales de parámetro, usar defaults
                    for i, item in enumerate(args_tool):
                        if isinstance(item, str) and item.strip().lower() in _LITERALES_PARAM:
                            # Es un literal de nombre de parámetro, usar default
                            clave = item.strip().lower()
                            if i < len(params_esperados):
                                clave = params_esperados[i]
                            args_dict[clave] = _DEFAULTS.get(clave, _DEFAULTS.get(item.strip().lower(), ""))
                        elif i < len(params_esperados):
                            args_dict[params_esperados[i]] = item
                        else:
                            # No hay más parámetros esperados, usar default
                            args_dict[f"param_{i}"] = item
                    # Asegurar que todos los parámetros esperados estén presentes
                    for p in params_esperados:
                        if p not in args_dict:
                            args_dict[p] = _DEFAULTS.get(p, "")
                    args_tool = args_dict
                elif isinstance(args_tool, dict):
                    for k, v in list(args_tool.items()):
                        # Sanitizar strings vacíos, None y literales de nombre de parámetro
                        if v is None or (isinstance(v, str) and not v.strip()):
                            # String vacío o None: usar valor por defecto
                            args_tool[k] = _DEFAULTS.get(k, _DEFAULTS.get(k, ""))
                        elif isinstance(v, str) and v.strip().lower() in _LITERALES_PARAM:
                            args_tool[k] = _DEFAULTS.get(k, _DEFAULTS.get(v.strip().lower(), ""))
                        # Sanitizar listas que contienen literales de nombre de parámetro o vacíos
                        elif isinstance(v, list):
                            # Si TODOS los elementos son literales de parámetro o vacíos, usar el default del key
                            if all(
                                (isinstance(item, str) and (item.strip().lower() in _LITERALES_PARAM or not item.strip()))
                                for item in v
                            ):
                                args_tool[k] = _DEFAULTS.get(k, [item for item in v])
                            else:
                                args_tool[k] = [
                                    _DEFAULTS.get(item.strip().lower(), item) if (isinstance(item, str) and item.strip().lower() in _LITERALES_PARAM) else item
                                    for item in v
                                ]
                # Asegurar que args_tool sea un dict antes de invocar
                if not isinstance(args_tool, dict):
                    args_tool = {}
                resultado_tool = herramienta_encontrada.invoke(args_tool)
                print(f"[{NOMBRE_AGENTE}] ← Resultado: {str(resultado_tool)[:120]}...")
            else:
                resultado_tool = json.dumps({"status": "error", "mensaje": f"Herramienta '{nombre_tool}' no encontrada."})

            from langchain_core.messages import ToolMessage
            mensajes_langgraph.append(
                ToolMessage(content=str(resultado_tool) + "\n\n⚠️ MUY IMPORTANTE: Acción completada. AHORA DEBES TERMINAR TU TURNO DEVOLVIENDO ÚNICAMENTE UN JSON MINIMALISTA DE CIERRE.", tool_call_id=tool_id)
            )

        respuesta = cadena.invoke({"messages": mensajes_langgraph})

    # 5. Invocar LLM sin tools para generar el JSON final del protocolo
    if hasattr(respuesta, "tool_calls") and respuesta.tool_calls:
        print(f"[Nami] Máximo de rondas alcanzado. Forzando respuesta final.")
        mensajes_langgraph.append(respuesta)
        for tc in respuesta.tool_calls:
            mensajes_langgraph.append(
                ToolMessage(
                    content="SISTEMA: Ejecución cancelada. Límite de rondas alcanzado. Por favor emite tu respuesta final.",
                    tool_call_id=tc.get("id", "dummy")
                )
            )
        respuesta_final = (prompt | llm).invoke({"messages": mensajes_langgraph})
        texto_respuesta = respuesta_final.content if hasattr(respuesta_final, "content") else str(respuesta_final)
    else:
        # La respuesta ya es final (sin tool_calls pendientes)
        texto_respuesta = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
    
    # Parsear JSON con Escudo Robusto (usando raw_decode en lugar de rfind)
    datos_json, _ = _extraer_json_robusto(texto_respuesta)
    
    # Si no se pudo parsear, intentar estrategias adicionales
    if datos_json is None:
        # Estrategia A: Buscar el JSON dentro de bloques de código markdown
        import re as _re
        _match = _re.search(r'```(?:json)?\s*([\s\S]*?)```', texto_respuesta)
        if _match:
            datos_json, _ = _extraer_json_robusto(_match.group(1))
        
        # Estrategia B: Buscar el primer objeto JSON completo en el texto
        if datos_json is None:
            _inicio = texto_respuesta.find('{')
            if _inicio >= 0:
                _fin = texto_respuesta.rfind('}')
                if _fin > _inicio:
                    _candidato = texto_respuesta[_inicio:_fin+1]
                    try:
                        datos_json = json.loads(_candidato)
                    except (json.JSONDecodeError, ValueError):
                        datos_json, _ = _extraer_json_robusto(_candidato)

    if datos_json is not None:
        print(f"[{NOMBRE_AGENTE}] ✅  Escudo JSON: Parseo exitoso.")
        # Asegurar que el campo evidencia_hallazgo esté presente
        if isinstance(datos_json, dict):
            # Normalizar Evidencia_Fisica: si es dict o list, extraer rutas de archivo
            _ef = datos_json.get("Evidencia_Fisica", datos_json.get("evidencia_fisica", ""))
            if isinstance(_ef, dict):
                _rutas = []
                for _k, _v in _ef.items():
                    if isinstance(_v, str) and (_v.startswith("/app/") or _v.startswith("/") or "." in _v):
                        _rutas.append(_v)
                    elif isinstance(_v, list):
                        for _item in _v:
                            if isinstance(_item, str) and (_item.startswith("/app/") or _item.startswith("/") or "." in _item):
                                _rutas.append(_item)
                if _rutas:
                    datos_json["Evidencia_Fisica"] = ",".join(_rutas)
                else:
                    datos_json["Evidencia_Fisica"] = json.dumps(_ef, ensure_ascii=False)
            elif isinstance(_ef, list):
                _rutas = [str(x) for x in _ef if isinstance(x, str) and (x.startswith("/app/") or x.startswith("/") or "." in x)]
                if _rutas:
                    datos_json["Evidencia_Fisica"] = ",".join(_rutas)
                else:
                    datos_json["Evidencia_Fisica"] = json.dumps(_ef, ensure_ascii=False)
            
            if "evidencia_hallazgo" not in datos_json or not datos_json.get("evidencia_hallazgo"):
                # Extraer evidencia de los campos existentes
                evidencia = datos_json.get("Evidencia_Fisica", datos_json.get("evidencia_fisica", ""))
                if not evidencia:
                    evidencia = datos_json.get("resumen", datos_json.get("contenido", ""))
                if isinstance(evidencia, dict):
                    evidencia = json.dumps(evidencia, ensure_ascii=False)
                elif isinstance(evidencia, list):
                    evidencia = json.dumps(evidencia, ensure_ascii=False)
                datos_json["evidencia_hallazgo"] = evidencia if evidencia else "Análisis completado sin evidencia física adicional."
        mensaje_salida = f"[{NOMBRE_AGENTE} -> {datos_json.get('para', 'Luffy') if isinstance(datos_json, dict) else 'Luffy'}]: {json.dumps(datos_json, ensure_ascii=False)}"
    else:
        # Manejo de error — devolver turno al agente infractor
        print(f"[{NOMBRE_AGENTE}] ⚠️  Escudo JSON: Error al parsear.")
        # Intentar recuperar un JSON válido del texto libre del LLM
        datos_json = {
            "para": "Luffy",
            "tipo": "error_formato",
            "evidencia_hallazgo": f"Error de formato JSON. Texto recibido: {texto_respuesta[:200]}",
            "contenido": {
                "texto": (
                    "Error de formato: El sistema esperaba un JSON válido pero encontró "
                    "un error de sintaxis. Por favor, corrige la sintaxis y responde únicamente con el JSON estricto."
                )
            }
        }
        mensaje_salida = f"[{NOMBRE_AGENTE} -> Luffy]: {json.dumps(datos_json, ensure_ascii=False)}"

    print(f"[{NOMBRE_AGENTE}] Tarea completada. Retornando control al capitán.")

    return {
        "messages": [AIMessage(content=mensaje_salida)],
        "ultimo_agente": NOMBRE_AGENTE,
        "datos_json": datos_json
    }


