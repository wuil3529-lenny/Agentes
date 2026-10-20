# Protocolo para Crear e Integrar Nuevas Skills y Herramientas

Este documento establece el estándar técnico y arquitectónico obligatorio (**Estándar de Oro**) para crear, modularizar e integrar nuevas habilidades (*skills*) y herramientas (*tools*) dentro del ecosistema de la tripulación de agentes autónomos.

---

## 1. Principio Fundamental: Las 5 Reglas de Oro Arquitectónicas

Toda nueva habilidad que se incorpore a cualquier agente debe satisfacer estrictamente las 5 Reglas de Oro:

1. **Modularización Pura y Aislamiento:**
   - La habilidad debe residir en su propio paquete independiente bajo `<Agente>/skills/<nombre_skill>/`.
   - Debe contener al menos tres artefactos: `__init__.py`, `skill_<nombre_skill>.py` y su espejo cognitivo Markdown `Skill_<Nombre_Skill>_<Agente>.md`.
   - Cero dependencias cruzadas entre herramientas; las fallas en un módulo no deben comprometer a otros.

2. **Decorador Canónico `@tool` con Tipado Fuerte:**
   - Toda función ejecutable expuesta al LLM debe emplear el decorador `@tool` de LangChain (`langchain_core.tools`).
   - Todos los argumentos deben estar estrictamente tipados (`str`, `int`, `dict`, `list`, `bool`) con valores por defecto seguros.
   - El docstring debe documentar detalladamente el propósito, parámetros y formato de retorno JSON.

3. **Documentación Espejo de 5 Secciones (El Prompt Modular):**
   - El archivo Markdown de la habilidad (`Skill_<Nombre_Skill>_<Agente>.md`) es la Fuente Única de Verdad de su comportamiento cognitivo.
   - Debe implementar obligatoriamente las 5 secciones estándar:
     - **Cabecera:** System Prompt Principal con Cargo Profesional y Misión.
     - **Metadatos Técnicos:** Rol funcional, tipo de habilidad, script Python y directorio de salida.
     - **Sección 1 (Gatillos de Activación):** Cuándo invocarla reactivamente (orden explícita) o autónomamente.
     - **Sección 2 (Ciclo de Vida y Flujo Operativo):** Fases de ejecución y diagrama Mermaid.
     - **Sección 3 (System Prompt Completo):** Directivas operativas íntegras.
     - **Sección 4 (Entregables y Evidencias):** Artefactos físicos esperados en disco y criterios de aceptación.
     - **Sección 5 (Ejemplo Práctico Few-Shot):** Caso de estudio con entrada, tool call y salida física comprobable.

4. **Inyección Dinámica de Prompts en Dos Niveles:**
   - **Nivel 1 (Pre-ejecución):** Detección preventiva de intención en `detectar_prompts_habilidad()` para cargar únicamente las directivas necesarias antes de invocar al LLM.
   - **Nivel 2 (Inter-rondas en Vivo):** Mapeo en `MAPA_HERRAMIENTA_PROMPTS` para inyectar en caliente las directivas de la skill en el `ToolMessage` tras su invocación.

5. **Intercepción Universal, Anti-Bucle y QA Gherkin:**
   - Toda llamada a herramienta pasa obligatoriamente por `interceptar_tool_call` de `bucle_autocorreccion.py`.
   - Si la herramienta se invoca repetidamente con argumentos idénticos tras haber obtenido datos, el sistema la congela automáticamente (Pilar 3 Anti-Bucle).
   - Su resultado es validado en Capa 1 (red/infraestructura) y Capa 2 (contenido analizable) mediante `qa_gherkin.py`.

---

## 2. Estructura de Directorios de una Skill Canónica

```
<Agente>/skills/<nombre_skill>/
├── __init__.py                                 # Exporta la función obtener_prompt_<skill>() y las tools
├── skill_<nombre_skill>.py                     # Lógica ejecutable en Python decorada con @tool
└── Skill_<Nombre_Skill>_<Agente>.md           # Espejo cognitivo con las 5 secciones estándar
```

---

## 3. Plantilla de Código Python (`skill_<nombre_skill>.py`)

```python
"""
skill_<nombre_skill>.py — [Descripción breve de la habilidad]
"""
import os
import json
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[2]
_SKILL_DIR = Path(__file__).resolve().parent

def obtener_prompt_<nombre_skill>() -> str:
    """Extrae el System Prompt desde el archivo Markdown espejo."""
    md_path = _SKILL_DIR / "Skill_<Nombre_Skill>_<Agente>.md"
    if md_path.exists():
        try:
            return md_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return "Directivas operativas de la habilidad <nombre_skill>."

@tool
def tool_<nombre_accion>(parametro_1: str, parametro_2: int = 10) -> str:
    """
    Descripción clara y detallada de lo que hace la herramienta para el LLM.

    Args:
        parametro_1: Propósito del primer argumento.
        parametro_2: Propósito del segundo argumento con valor por defecto.
    """
    try:
        # 1. Validación de entradas
        if not parametro_1:
            return json.dumps({"status": "error", "mensaje": "parametro_1 no puede estar vacío."}, ensure_ascii=False)

        # 2. Lógica operativa determinista
        resultado_datos = {"items": [parametro_1], "total": parametro_2}

        # 3. Retorno JSON parseable y sustancial
        return json.dumps({
            "status": "success",
            "datos": resultado_datos,
            "mensaje": "Operación completada con éxito."
        }, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"status": "error", "mensaje": f"Excepción en ejecución: {str(exc)}"}, ensure_ascii=False)
```

---

## 4. Registro y Sincronización Automática

Una vez creado el paquete de la habilidad:
1. **Importar y Registrar en el Agente:** Añadir la herramienta al arreglo `herramientas_disponibles` del agente (`<agente>_agent.py`) y registrarla en el diccionario de mapeo `MAPA_HERRAMIENTA_PROMPTS`.
2. **Sincronización Orgánica:** Ejecutar `python Agente_Orquestador/sync_cerebro.py`.
   - El sincronizador detectará automáticamente la nueva skill.
   - Enlazará la documentación Markdown en el grafo de Obsidian.
   - Si `ENABLE_RAG_SYNC=1`, indexará sus especificaciones en ChromaDB para permitir su consulta semántica.

---
**Conexiones:** [[sistema]]
