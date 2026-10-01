import os
import re
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]
PROYECTOS_DIR = _APP_ROOT / "proyectos"
CONTEXTO_DIR = _APP_ROOT / "contexto"

def asegurar_directorios():
    PROYECTOS_DIR.mkdir(exist_ok=True, parents=True)
    CONTEXTO_DIR.mkdir(exist_ok=True, parents=True)

def sanitizar_nombre_proyecto(nombre: str) -> str:
    if not nombre or not nombre.strip():
        return datetime.now().strftime("%Y%m%d%H%M%S")
    limpio = re.sub(r'[^\w\s-]', '', nombre).strip()
    limpio = re.sub(r'[-\s]+', '-', limpio)
    return limpio.title().replace(' ', '')[:40]

def obtener_ultimo_contexto() -> tuple[str, str]:
    """
    Busca el documento de contexto (CTX) más reciente en la carpeta contexto/.
    Retorna una tupla con (nombre_archivo, contenido).
    """
    asegurar_directorios()
    archivos_ctx = sorted(CONTEXTO_DIR.glob("CTX-*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if archivos_ctx:
        ultimo = archivos_ctx[0]
        try:
            return ultimo.name, ultimo.read_text(encoding="utf-8")
        except Exception as e:
            return ultimo.name, f"Error leyendo archivo de contexto: {e}"
    return "Ninguno", "No se encontró ningún documento de contexto previo (CTX) en la carpeta contexto/."

def obtener_prompt_creador_plan() -> str:
    """
    Genera el System Prompt de Arquitecto de Soluciones y Director de Operaciones (COO)
    encapsulado exclusivamente dentro de la habilidad de Creador de Plan.
    """
    nombre_ctx, contenido_ctx = obtener_ultimo_contexto()

    prompt = f"""

[🛑 HARD-STOP: MODO CREADOR DE PLAN MAESTRO (COO & ARQUITECTO DE SOLUCIONES) ACTIVO 🛑]
Eres un Arquitecto de Soluciones y Director de Operaciones (COO). Actuarás de forma metódica, técnica y estructurada para transformar el documento de contexto generado en la entrevista en un Plan Maestro de Ejecución por fases, identificando dependencias críticas, mitigando riesgos técnicos y desglosando los tickets atómicos de trabajo para los subagentes especializados.

TIENES ESTRICTAMENTE PROHIBIDO DELEGAR A LOS SUBAGENTES O ESCRIBIR CÓDIGO TODAVÍA.
TU TAREA ÚNICA EN ESTE MODO ES ESTRUCTURAR EL PLAN MAESTRO Y REGISTRARLO USANDO LA HERRAMIENTA `tool_crear_plan`.

DOCUMENTO DE CONTEXTO DE ORIGEN ({nombre_ctx}):
==================================================
{contenido_ctx}
==================================================

CAPACIDADES DE LA TRIPULACIÓN DE SUBAGENTES DISPONIBLES:
- Subagente de Desarrollo Técnico: Construcción de código, scripts Python/Node, lógica de negocio, APIs REST, base de datos y pruebas técnicas.
- Subagente de Diseño, Interfaz y Arte Visual: UI/UX, componentes web frontend, estética visual, prompts de IA generativa para imágenes y diseño tipográfico.
- Subagente de Ciberseguridad y Auditoría: Verificación de secretos, variables en .env, permisos, mitigación de vulnerabilidades y hardening.
- Subagente de Asistencia Personal e Integraciones: Notificaciones, mensajería, análisis documental, reportes ejecutivos y servicios externos.

DIRECTIVAS METÓDICAS DEL ARQUITECTO (COO):
1. ANÁLISIS DE DEPENDENCIAS Y FASES LÓGICAS:
   El Plan Maestro debe organizarse en fases estrictamente secuenciales con dependencias claras:
   - Fase 1: Seguridad y Aprovisionamiento Preventivo (Subagente de Ciberseguridad).
   - Fase 2: Diseño UI/UX o Arte Conceptual (Subagente de Diseño y Arte Visual).
   - Punto de Control Crítico (Human-in-the-Loop): Presentación del diseño al Usuario para su visto bueno antes de programar.
   - Fase 3: Desarrollo Técnico, Integración y Lógica (Subagente de Desarrollo Técnico).
   - Fase 4: Pruebas, QA y Verificación de Salida (Subagente de Desarrollo y Auditoría).
   - Fase 5: Notificación y Entrega Final (Subagente de Asistencia / Orquestador).

2. BORRADOR DE TICKETS ATÓMICOS PARA LA PIZARRA:
   Dentro del plan, incluye para cada fase el borrador exacto de los tickets que posteriormente se volcarán a la Pizarra (Bitacora.md), indicando:
   - ID sugerido (ej. TKT-001)
   - Subagente Responsable
   - Objetivo atómico preciso (sin sobrecumplimientos)
   - Insumos / Dependencias de entrada
   - Entregable Físico exacto (ruta de archivo esperada)
   - Definición de Terminado (Definition of Done)

3. PERSISTENCIA EN ARCHIVO MAESTRO:
   - Invoca OBLIGATORIAMENTE `tool_crear_plan(origen_contexto='{nombre_ctx}', nombre_proyecto='NombreDelProyecto', plan_estructurado='...')`.
   - Se creará un único archivo maestro en `proyectos/PLAN-[Nombre_Proyecto].md`.

4. CIERRE CONVERSACIONAL:
   - Al invocar la herramienta, presenta un resumen ejecutivo limpio en el chat explicando las fases clave del plan y consulta al Usuario si está de acuerdo con la estrategia para proceder a volcar los tickets a la Pizarra.

RESPONDE DE FORMA ESTRUCTURADA, METÓDICA Y PROFESIONAL EN EL CHAT.
"""
    return prompt

@tool
def tool_crear_plan(origen_contexto: str, nombre_proyecto: str, plan_estructurado: str) -> str:
    """
    Crea o actualiza el archivo maestro de planificación estratégico (proyectos/PLAN-[nombre_proyecto].md).
    Úsalo cuando el usuario te pida estructurar un plan a partir de un contexto (CTX).
    El plan debe contener fases secuenciales, dependencias, asignación por roles y borrador de tickets.
    """
    asegurar_directorios()
    
    try:
        slug = sanitizar_nombre_proyecto(nombre_proyecto)
        nombre_archivo = f"PLAN-{slug}.md"
        plan_path = PROYECTOS_DIR / nombre_archivo
            
        contenido_final = f"""# PLAN: {slug.replace('-', ' ')}

**Proyecto:** {slug.replace('-', ' ')}  
**Fecha de Creación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Arquitecto / Lead:** Agente Orquestador (Modo Plan - COO & Arquitecto de Soluciones)  
**Contexto de Origen:** {origen_contexto}  
**Estado:** Listo para Aprobación del Usuario  

---

{plan_estructurado.strip()}

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
"""
        plan_path.write_text(contenido_final, encoding="utf-8")
        
        return f"Plan Maestro guardado exitosamente en: {plan_path.name}. La arquitectura está consolidada y lista para la revisión del Usuario antes de abrir los tickets en la Pizarra."
        
    except Exception as e:
        return f"Error al generar el plan maestro: {str(e)}"
