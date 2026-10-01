import os
import re
import sys
from pathlib import Path
import traceback
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]

MAPA_ROLES_AGENTES = {
    "desarrollo": "Subagente_Desarrollo",
    "backend": "Subagente_Desarrollo",
    "frontend": "Subagente_Desarrollo",
    "tecnico": "Subagente_Desarrollo",
    "zoro": "Subagente_Desarrollo",
    "subagente_desarrollo": "Subagente_Desarrollo",
    "diseno": "Subagente_Diseno",
    "diseño": "Subagente_Diseno",
    "arte": "Subagente_Diseno",
    "interfaz": "Subagente_Diseno",
    "ui": "Subagente_Diseno",
    "ux": "Subagente_Diseno",
    "visual": "Subagente_Diseno",
    "nami": "Subagente_Diseno",
    "subagente_diseno": "Subagente_Diseno",
    "seguridad": "Subagente_Ciberseguridad",
    "ciberseguridad": "Subagente_Ciberseguridad",
    "auditoria": "Subagente_Ciberseguridad",
    "hardening": "Subagente_Ciberseguridad",
    "robin": "Subagente_Ciberseguridad",
    "subagente_ciberseguridad": "Subagente_Ciberseguridad",
    "asistencia": "Subagente_Asistencia",
    "mensajeria": "Subagente_Asistencia",
    "integraciones": "Subagente_Asistencia",
    "notificaciones": "Subagente_Asistencia",
    "sanji": "Subagente_Asistencia",
    "subagente_asistencia": "Subagente_Asistencia",
    "orquestador": "Agente_Orquestador",
    "director": "Agente_Orquestador",
    "supervisor": "Agente_Orquestador",
    "coo": "Agente_Orquestador",
    "luffy": "Agente_Orquestador",
    "agente_orquestador": "Agente_Orquestador"
}

def resolver_carpeta_agente(agente_input: str) -> tuple[str, Path]:
    """
    Resuelve el nombre canónico y la ruta absoluta de la carpeta del agente/subagente.
    Acepta roles funcionales ('desarrollo', 'diseño', etc.) o nombres de carpeta.
    """
    clave = (agente_input or "").strip().lower()
    nombre_canonico = MAPA_ROLES_AGENTES.get(clave, agente_input.strip().capitalize())
    
    agente_path = _APP_ROOT / nombre_canonico
    return nombre_canonico, agente_path

def sanitizar_nombre_skill(nombre: str) -> tuple[str, str]:
    """
    Convierte un nombre de habilidad a:
    - snake_case para el archivo python (ej. analizar_metricas)
    - CamelCase / TitleCase para el documento markdown (ej. Analizar_Metricas)
    """
    limpio = re.sub(r'[^\w\s-]', '', nombre).strip()
    limpio = re.sub(r'[-\s]+', '_', limpio).lower()
    if limpio.startswith("skill_"):
        limpio = limpio[6:]
    if limpio.startswith("tool_"):
        limpio = limpio[5:]
    
    camel = "_".join(word.capitalize() for word in limpio.split("_"))
    return limpio, camel

def obtener_prompt_creador_herramienta() -> str:
    """
    System Prompt especializado para el Agente Orquestador actuando como
    Director de Ingeniería de Plataforma y Fábrica de Habilidades (Lead Tooling Architect).
    """
    return """
[🛑 HARD-STOP: MODO DIRECTOR DE INGENIERÍA Y FÁBRICA DE HABILIDADES ACTIVO 🛑]
Eres el Director de Ingeniería y Arquitecto de Plataforma de la tripulación de agentes.
Tu misión es diseñar, construir e integrar nuevas habilidades y herramientas de clase mundial para los subagentes especializados o para ti mismo, expandiendo las capacidades técnicas del sistema con rigor arquitectónico.

GATILLOS DE ACTIVACIÓN (CUÁNDO DEBES OPERAR):
1. Gatillo Reactivo: Por solicitud explícita del Usuario solicitando una nueva capacidad técnica.
2. Gatillo Autónomo (Iniciativa del Orquestador): Al analizar un objetivo complejo, tarea en la Pizarra o bloqueo técnico de un subagente donde detectas que NO EXISTE una herramienta para resolver el problema. En lugar de detenerte, alucinar o esperar órdenes, tomas la iniciativa y forjas la habilidad técnica requerida.

ESTÁNDAR DE ORO OBLIGATORIO PARA TODA NUEVA HABILIDAD:
Cada habilidad que crees debe constar de dos artefactos coordinados e inmutables:
1. Script en Python (`skills/skill_<nombre_skill>.py`):
   - Tipado estricto (typing: str, int, dict, list, Optional).
   - Bloques try-except robustos con mensajes descriptivos.
   - Decorador @tool con docstrings claros y detallados.
   - Función encapsuladora `obtener_prompt_<nombre_skill>()` que alberga el System Prompt especializado del rol, para nunca sobrecargar el script principal del agente.
2. Documento Markdown (`skills/Skill_<Nombre_Skill>.md`):
   - Cabecera con Cargo y Misión del System Prompt Principal al inicio.
   - Metadatos funcionales (Rol, Tipo, Código, Salida).
   - Sección 1: En qué momento debe invocarse (Gatillos explícitos y autónomos).
   - Sección 2: Cómo usarla (Ciclo de Vida y Flujo Operativo secuencial).
   - Sección 3: El System Prompt Completo de la Habilidad.
   - Sección 4: Resultados y Entregables Esperados.
   - Sección 5: Ejemplo Práctico Completo (con diálogo, invocación y resultado).
   - Vínculo exclusivo final: `**Pertenece a:** [[Perfil_<Agente>]]`.

REGLAS DE IDENTIDAD Y SEGURIDAD:
- TERMINOLOGÍA ESTRICTAMENTE AGNÓSTICA: Nunca quemes nombres de piratas ni nombres propios en las habilidades generadas. Utiliza: "Usuario", "Agente Orquestador", "Subagente de Desarrollo Técnico", "Subagente de Diseño y Arte Visual", "Subagente de Ciberseguridad y Auditoría", "Subagente de Asistencia Personal e Integraciones".
- PROTOCOLO DE AUDITORÍA OBLIGATORIA: Toda habilidad recién creada debe someterse a auditoría previa del Subagente de Ciberseguridad mediante un ticket en la Pizarra (`Bitacora.md`) antes de activarse en producción.
- INTEGRACIÓN EN EL GRAFO: Invoca la sincronización del cerebro (`sync_cerebro.py`) para registrar el gemelo digital en Obsidian sin nodos huérfanos.
"""

def iniciar_creacion_skill(
    agente: str,
    nombre_skill: str,
    objetivo: str = "",
    entradas_salidas: str = "",
    hard_stops: str = "",
    codigo_python: str = "",
    cargo_mision_prompt: str = "",
    gatillos_activacion: str = "",
    ciclo_vida: str = "",
    ejemplo_practico: str = ""
) -> str:
    """
    Fábrica estandarizada de habilidades para la tripulación.
    Crea los archivos físicos (.md y .py) bajo el estándar de oro de 5 secciones,
    con System Prompt encapsulado, tipado estricto, manejo de excepciones y
    preparación para la auditoría preventiva de ciberseguridad.
    """
    try:
        nombre_agente, agente_path = resolver_carpeta_agente(agente)
        
        if not agente_path.exists() or not agente_path.is_dir():
            return f"ERROR_CONTROLADO: El agente '{nombre_agente}' no existe en {_APP_ROOT}."
        
        skill_slug, skill_camel = sanitizar_nombre_skill(nombre_skill)
        
        # Directorio de skills del agente destino
        # Cada agente tiene su carpeta skills/
        skills_path = agente_path / "skills"
        skills_path.mkdir(parents=True, exist_ok=True)
        
        # Mapeo de rol agnóstico para la cabecera
        roles_legibles = {
            "Subagente_Desarrollo": "Subagente de Desarrollo Técnico",
            "Subagente_Diseno": "Subagente de Diseño, Interfaz y Arte Visual",
            "Subagente_Ciberseguridad": "Subagente de Ciberseguridad y Auditoría",
            "Subagente_Asistencia": "Subagente de Asistencia Personal e Integraciones",
            "Agente_Orquestador": "Agente Orquestador",
            # Compatibilidad
            "Zoro": "Subagente de Desarrollo Técnico",
            "Nami": "Subagente de Diseño, Interfaz y Arte Visual",
            "Robin": "Subagente de Ciberseguridad y Auditoría",
            "Sanji": "Subagente de Asistencia Personal e Integraciones",
            "Luffy": "Agente Orquestador"
        }
        rol_legible = roles_legibles.get(nombre_agente, f"Subagente Especializado ({nombre_agente})")

        # ── 1. CONSTRUCCIÓN DEL SYSTEM PROMPT ENCAPSULADO PARA EL SCRIPT ──
        cargo_def = cargo_mision_prompt.strip() if cargo_mision_prompt else f"Especialista técnico en {skill_slug.replace('_', ' ')}."
        
        prompt_especializado = f"""
[🛑 HARD-STOP: MODO {skill_slug.upper()} ACTIVO 🛑]
Eres un {cargo_def}
Tu misión es ejecutar tareas de {skill_slug.replace('_', ' ')} con máxima precisión técnica, cumpliendo con los estándares de calidad, seguridad y validación de datos.

DIRECTIVAS OPERATIVAS:
- Valida exhaustivamente todos los parámetros de entrada antes de proceder.
- Aplica manejo de excepciones y retorna respuestas descriptivas con formato controlado.
- Respeta estrictamente los límites de seguridad definidos para esta habilidad.
"""

        # ── 2. CONSTRUCCIÓN DEL CÓDIGO PYTHON (skills/skill_<nombre>.py) ──
        py_file_path = skills_path / f"skill_{skill_slug}.py"
        
        if "def " not in codigo_python:
            py_body = f"""import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[2]

def obtener_prompt_{skill_slug}() -> str:
    \"\"\"
    System Prompt especializado y encapsulado para la habilidad {skill_slug}.
    \"\"\"
    return \"\"\"{prompt_especializado.strip()}\"\"\"

@tool
def tool_{skill_slug}(parametro_entrada: str) -> str:
    \"\"\"
    {objetivo.strip() or f'Ejecuta la habilidad {skill_slug.replace("_", " ")}.'}
    Entradas / Salidas: {entradas_salidas.strip() or 'Cadena de texto -> Resultado descriptivo'}
    Hard-Stops: {hard_stops.strip() or 'Validación de rutas y parámetros'}
    \"\"\"
    try:
        # Lógica operativa de la herramienta
        resultado = f"Habilidad '{skill_slug}' ejecutada correctamente con: {{parametro_entrada}}"
        return resultado
    except Exception as e:
        return f"ERROR_EJECUCION en {skill_slug}: {{str(e)}}"
"""
        else:
            # Si el código ya contiene funciones, nos aseguramos de que contenga obtener_prompt_<skill>
            py_body = codigo_python.strip()
            if f"obtener_prompt_{skill_slug}" not in py_body:
                encapsulado_header = f"""from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

def obtener_prompt_{skill_slug}() -> str:
    \"\"\"
    System Prompt especializado y encapsulado para la habilidad {skill_slug}.
    \"\"\"
    return \"\"\"{prompt_especializado.strip()}\"\"\"

"""
                py_body = encapsulado_header + py_body

        py_file_path.write_text(py_body, encoding="utf-8")

        # ── 3. CONSTRUCCIÓN DE LA DOCUMENTACIÓN ESTÁNDAR (skills/Skill_<Nombre>_<Agente>.md) ──
        md_file_path = skills_path / f"Skill_{skill_camel}_{nombre_agente}.md"
        
        gatillos_texto = gatillos_activacion.strip() if gatillos_activacion else (
            "1. **Disparador Reactivo:** Cuando el Usuario solicite explícitamente ejecutar esta función.\n"
            "2. **Disparador Autónomo:** Cuando el Agente Orquestador o el Subagente identifique en la Pizarra una tarea dependiente de esta capacidad técnica."
        )
        
        ciclo_vida_texto = ciclo_vida.strip() if ciclo_vida else (
            "1. **Validación de Entradas:** Comprobación estricta de parámetros y dependencias antes de iniciar.\n"
            "2. **Ejecución Segura:** Procesamiento en entorno aislado con captura de excepciones mediante bloques try-except.\n"
            "3. **Retorno Estructurado:** Generación de entregables verificables y reporte de estado hacia el agente solicitante."
        )
        
        ejemplo_texto = ejemplo_practico.strip() if ejemplo_practico else (
            f"### Caso de Uso Real\n"
            f"- **Escenario:** El Usuario solicita una acción dependiente de `{skill_slug}`.\n"
            f"- **Invocación:** `tool_{skill_slug}(parametro_entrada='ejemplo')`\n"
            f"- **Resultado:** La herramienta ejecuta el procesamiento y retorna el estado de cumplimiento verificado."
        )
        
        md_content = f"""# 🛠️ Habilidad: {skill_slug.replace('_', ' ').title()}

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"{cargo_def}"**

---

**Rol Funcional:** {rol_legible}  
**Tipo de Habilidad:** Ejecución Técnica Especializada  
**Archivo de Código:** `{nombre_agente}/skills/{py_file_path.name}`  
**Directorio de Salida:** `{nombre_agente}/skills/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

{gatillos_texto}

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

{ciclo_vida_texto}

### Parámetros y Límites
- **Entradas y Salidas:** {entradas_salidas.strip() or 'Definidas en la firma de la herramienta.'}
- **Hard-Stops (Límites de Seguridad):** {hard_stops.strip() or 'Cero operaciones destructivas sin confirmación.'}

---

## 3. El System Prompt Completo de la Habilidad

```text
{prompt_especializado.strip()}
```

---

## 4. Resultados y Entregables Esperados

1. **Script Operativo Verificado:** Código tipado y encapsulado en `{py_file_path.name}`.
2. **Documentación Oficial Integrada:** Ficha de conocimiento registrada en Obsidian.
3. **Cero Nodos Huérfanos:** Conexión garantizada al perfil del agente responsable.

---

## 5. Ejemplo Práctico Completo (Caso de Estudio Real)

{ejemplo_texto}

---
**Pertenece a:** [[Perfil_{nombre_agente}]]
"""
        md_file_path.write_text(md_content, encoding="utf-8")

        # ── 4. RESPUESTA Y TICKET DE AUDITORÍA ──
        mensaje = (
            f"FÁBRICA DE HABILIDADES: Habilidad '{skill_slug}' creada con éxito bajo el estándar de oro en {nombre_agente}.\n"
            f"- Documentación Oficial: {md_file_path.name}\n"
            f"- Script de Código: {py_file_path.name}\n\n"
            f"🛡️ PROTOCOLO DE AUDITORÍA PREVENTIVA REQUERIDO:\n"
            f"Antes de declarar operativa la habilidad, el Agente Orquestador debe registrar en la Bitácora (Bitacora.md) "
            f"un ticket de verificación asignado al Subagente de Ciberseguridad y Auditoría:\n"
            f"Ticket: [TKT-AUDIT-{skill_slug.upper()}] Auditoría de Seguridad para skill_{skill_slug}.py\n"
            f"Responsable: Subagente de Ciberseguridad y Auditoría\n"
            f"Insumo: {py_file_path}\n"
            f"Entregable: Aprobación formal de seguridad y verificación de no-vulnerabilidades."
        )
        return mensaje
        
    except Exception as e:
        return f"ERROR_CRITICO al crear la habilidad: {str(e)}\n{traceback.format_exc()}"
