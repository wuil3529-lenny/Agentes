import os
import json
import re
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]
CONTEXTO_DIR = _APP_ROOT / "contexto"
ORQUESTADOR_DIR = _APP_ROOT / "Agente_Orquestador"
LUFFY_DIR = ORQUESTADOR_DIR  # Alias de compatibilidad
ESTADO_ENTREVISTA = ORQUESTADOR_DIR / "estado_entrevista.json"

def asegurar_directorios():
    CONTEXTO_DIR.mkdir(exist_ok=True, parents=True)

def sanitizar_nombre_proyecto(nombre: str) -> str:
    if not nombre or not nombre.strip():
        return datetime.now().strftime("%Y%m%d%H%M%S")
    # Limpiar caracteres especiales y normalizar a slug limpio
    limpio = re.sub(r'[^\w\s-]', '', nombre).strip()
    limpio = re.sub(r'[-\s]+', '-', limpio)
    return limpio.title().replace(' ', '')[:40]

def obtener_prompt_estrategico_entrevista(estado_file: Path = None) -> str:
    """
    Genera el System Prompt de CEO y Director Técnico (CTO) encapsulado
    exclusivamente dentro de la habilidad de Entrevistador.
    """
    if estado_file is None:
        estado_file = ESTADO_ENTREVISTA

    contenido_ctx = "Aún no se ha inicializado el documento del proyecto. Tu primera acción debe ser invocar tool_gestionar_entrevista con accion='iniciar' bautizando el proyecto con un nombre descriptivo."
    ya_iniciada = False
    nombre_proyecto_actual = "Nuevo Proyecto"

    try:
        if estado_file.exists():
            estado_data = json.loads(estado_file.read_text(encoding="utf-8"))
            ctx_path = Path(estado_data.get("ctx_path", ""))
            if ctx_path.exists():
                contenido_ctx = ctx_path.read_text(encoding="utf-8")
                ya_iniciada = True
                nombre_proyecto_actual = estado_data.get("proyecto", ctx_path.stem.replace("CTX-", ""))
    except Exception as e:
        print(f"[Skill Entrevistador] Error leyendo estado: {e}")

    regla_accion = (
        f"- LA ENTREVISTA YA ESTÁ INICIADA para el proyecto '{nombre_proyecto_actual}'. TIENES ESTRICTAMENTE PROHIBIDO usar accion='iniciar'. USA ÚNICAMENTE accion='actualizar' para incorporar los nuevos acuerdos y detalles a este mismo archivo.\n"
        if ya_iniciada else
        "- DEBES INICIAR LA ENTREVISTA AHORA MISMO invocando `tool_gestionar_entrevista` con accion='iniciar' y pasando un `nombre_proyecto` representativo de la idea del Usuario.\n"
    )

    prompt = f"""

[🛑 HARD-STOP: MODO ENTREVISTADOR ESTRATÉGICO (CEO & CTO) ACTIVO 🛑]
Eres un CEO y Director Estratégico de Producto (CTO). Actuarás de forma estratégica para planificar la idea del usuario, aportar ideas, resolver preguntas, dar varias posibilidades hasta formar una idea principal estructurada y completa, y nutrir la idea de contexto.

Tu misión NO es cuestionar como un robot, sino asociarte con el Usuario para madurar, blindar y enriquecer su idea hasta convertirla en una especificación técnica de clase mundial.

TIENES ESTRICTAMENTE PROHIBIDO CREAR TICKETS EN LA PIZARRA, DELEGAR O GENERAR ARCHIVOS DE CÓDIGO ANTES DE TIEMPO.

DOCUMENTO DE CONTEXTO VIVO ACTUAL DEL PROYECTO:
==================================================
{contenido_ctx}
==================================================

DIRECTIVAS DE OPERACIÓN DEL ESTRATEGA (CEO & CTO):
{regla_accion}
1. UN SOLO ARCHIVO VIVO:
   - Todo lo que se discuta vive y crece en este único documento de contexto.
   - NUNCA crees archivos paralelos ni escribas en la Pizarra.
   - En CADA TURNO, antes de responderle al usuario, invoca OBLIGATORIAMENTE `tool_gestionar_entrevista` con accion='actualizar', pasando en 'contenido' una síntesis estructurada de lo decidido, opciones evaluadas y especificaciones acordadas.
   - No hay límite de rondas ni de tamaño: mientras más rico y detallado sea el contexto, mejor será la ejecución final.

2. COMPORTAMIENTO CONVERSACIONAL Y CONSULTIVO:
   - Si el Usuario te hace preguntas técnicas o te pide opinión, responde con autoridad técnica, criterio de negocio y fundamentos sólidos.
   - Analiza siempre varios caminos posibles y ofrécele opciones claras (por ejemplo: "Opción A: ... con ventajas X", "Opción B: ... con ventajas Y") para que el Usuario elija la mejor dirección.
   - Plantea preguntas lógicas y relevantes acordes a la naturaleza del proyecto:
     * Si es Diseño o Imágenes: estilo visual, motor (ej. Flux, DALL-E), proporciones, subagente de diseño y arte, entregables.
     * Si es Software o Web: arquitectura, stack (Python, FastAPI, React/Tailwind), dependencias, rol del subagente de desarrollo y subagente de UI.
     * Si es Automatización: disparadores, webhooks, credenciales en .env, flujos n8n y monitoreo.
     * Si es Seguridad: secretos, permisos, vectores de ataque que auditará el subagente de ciberseguridad.

3. PROCESO HACIA EL MODO PLAN:
   - Continúa el diálogo estratégico de forma fluida mientras el Usuario siga refinando o agregando ideas.
   - Cuando el Usuario manifieste satisfacción con la idea (o cuando indique que está listo para avanzar), realiza un breve resumen de cierre, invoca `tool_gestionar_entrevista` con accion='cerrar', y avísale que el documento de contexto está consolidado y listo para pasar al Modo Plan.

RESPONDE DE FORMA NATURAL, ESTRATÉGICA Y HUMANA EN EL CHAT.
"""
    return prompt

@tool
def tool_gestionar_entrevista(accion: str, contenido: str = "", nombre_proyecto: str = "", dimensiones_faltantes: str = "", **kwargs) -> str:
    """
    Herramienta oficial para gestionar el Modo Entrevistador Estratégico (CEO & CTO).
    Acciones permitidas:
    - 'iniciar': Bautiza el proyecto y crea su documento único de contexto (CTX-[Nombre].md) en contexto/.
    - 'actualizar': Enriquece el documento acumulativo del proyecto con los acuerdos, opciones y detalles técnicos del turno.
    - 'cerrar': Finaliza la fase de descubrimiento, marca el documento como consolidado y prepara el terreno para el Modo Plan.
    - 'abortar': Cancela la sesión activa y elimina el candado de entrevista.
    """
    asegurar_directorios()
    
    try:
        if accion == "iniciar":
            if ESTADO_ENTREVISTA.exists():
                return "Error: Ya hay una entrevista en curso para un proyecto. Usa accion='actualizar' para enriquecer el documento actual o accion='cerrar' si ya concluyó."
            
            slug = sanitizar_nombre_proyecto(nombre_proyecto)
            ctx_path = CONTEXTO_DIR / f"CTX-{slug}.md"
            
            # Si ya existía un archivo con ese nombre, no pisarlo ciegamente, adjuntar timestamp corto
            if ctx_path.exists():
                slug = f"{slug}-{datetime.now().strftime('%H%M%S')}"
                ctx_path = CONTEXTO_DIR / f"CTX-{slug}.md"

            plantilla = f"""# CTX: {slug.replace('-', ' ')}

**Proyecto:** {slug.replace('-', ' ')}  
**Fecha de Inicio:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Estratega / Lead:** Agente Orquestador (Modo Entrevista - CEO & CTO)  
**Estado:** En Descubrimiento Estratégico  

---

## 1. Visión General y Propósito del Proyecto
{contenido.strip() if contenido else "Definición inicial en proceso de refinamiento estratégico."}

## 2. Caminos Evaluados, Opciones y Decisiones Clave
Registro de alternativas analizadas, trade-offs y elecciones del Usuario.

## 3. Requerimientos Técnicos y de Negocio
Especificaciones técnicas, dependencias, estándares de calidad y restricciones.

## 4. Participación y Roles de la Tripulación
- **Agente Orquestador:** Supervisión general, orquestación y control de calidad.
- **Subagente de Desarrollo:** Implementación técnica, código, APIs y testing.
- **Subagente de Diseño y Arte:** UI/UX, estilos visuales, arte conceptual y maquetación.
- **Subagente de Ciberseguridad:** Auditoría de vulnerabilidades, control de accesos y secretos.
- **Subagente de Asistencia e Integraciones:** Notificaciones, documentación y servicios conectados.

## 5. Entregables Concretos y Criterios de Éxito
Definición de qué resultado exacto considerará el Usuario como misión cumplida.

## 6. Historial de Diálogo y Refinamiento Continuo
Registro acumulativo de las rondas de intercambio estratégico.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
"""
            ctx_path.write_text(plantilla, encoding="utf-8")
            
            estado = {
                "activa": True,
                "proyecto": slug.replace('-', ' '),
                "ctx_path": str(ctx_path),
                "rondas_entrevista": 0,
                "fecha_inicio": datetime.now().isoformat()
            }
            ESTADO_ENTREVISTA.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
            
            return f"Descubrimiento iniciado exitosamente. Documento único creado en {ctx_path.name}. Modo Estratega (CEO & CTO) activo."
            
        elif accion == "actualizar":
            if not ESTADO_ENTREVISTA.exists():
                return "Error: No hay una sesión de entrevista activa. Invoca accion='iniciar' primero."
            
            estado = json.loads(ESTADO_ENTREVISTA.read_text(encoding="utf-8"))
            ctx_path = Path(estado.get("ctx_path", ""))
            
            if not ctx_path.exists():
                return f"Error: El archivo de contexto '{ctx_path.name}' no fue encontrado en disco."
                
            estado["rondas_entrevista"] = estado.get("rondas_entrevista", 0) + 1
            ESTADO_ENTREVISTA.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")

            texto_actual = ctx_path.read_text(encoding="utf-8")
            
            # Incorporar la nueva actualización al historial acumulativo
            bloque_nuevo = (
                f"\n\n### Ronda de Descubrimiento #{estado['rondas_entrevista']} — {datetime.now().strftime('%H:%M:%S')}\n"
                f"{contenido.strip()}\n"
            )
            
            # Si el archivo tiene la marca de pertenencia al final, insertar antes de ella
            marca = "\n---\n**Pertenece a:** [[Perfil_Agente_Orquestador]]"
            marca_legada = "\n---\n**Pertenece a:** [[Perfil_Luffy]]"
            if marca in texto_actual:
                partes = texto_actual.split(marca)
                texto_actual = partes[0] + bloque_nuevo + marca + "\n"
            elif marca_legada in texto_actual:
                partes = texto_actual.split(marca_legada)
                texto_actual = partes[0] + bloque_nuevo + marca + "\n"
            else:
                texto_actual += bloque_nuevo

            ctx_path.write_text(texto_actual, encoding="utf-8")

            return f"Contexto enriquecido exitosamente en {ctx_path.name} (Ronda #{estado['rondas_entrevista']}). Continúa dialogando con el Usuario o cierra la entrevista si ya está satisfecho."
            
        elif accion == "cerrar":
            if not ESTADO_ENTREVISTA.exists():
                return "Error: No hay ninguna entrevista activa para cerrar."
            
            estado = json.loads(ESTADO_ENTREVISTA.read_text(encoding="utf-8"))
            ctx_path = Path(estado.get("ctx_path", ""))
            
            if ctx_path.exists():
                texto_actual = ctx_path.read_text(encoding="utf-8")
                texto_actual = texto_actual.replace("**Estado:** En Descubrimiento Estratégico", "**Estado:** [CONSOLIDADO] Listo para Modo Plan")
                ctx_path.write_text(texto_actual, encoding="utf-8")
            
            ESTADO_ENTREVISTA.unlink(missing_ok=True)
            return f"Entrevista cerrada exitosamente. Documento maestro consolidado en {ctx_path.name}. La idea cuenta con contexto suficiente para proceder al Modo Plan."
            
        elif accion == "abortar":
            if ESTADO_ENTREVISTA.exists():
                ESTADO_ENTREVISTA.unlink(missing_ok=True)
            return "Sesión de entrevista cancelada. El candado fue liberado y se restauró el modo habitual."
            
        else:
            return f"Acción '{accion}' no reconocida. Usa 'iniciar', 'actualizar', 'cerrar' o 'abortar'."
            
    except Exception as e:
        return f"Error ejecutando gestión de entrevista: {e}"
