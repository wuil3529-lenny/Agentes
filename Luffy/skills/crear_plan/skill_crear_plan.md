---
name: tool_crear_plan
description: Permite a Luffy estructurar un plan estratégico y desglosar tareas (tickets) basándose en el contexto recabado.
---

# Habilidad: Crear Plan Estratégico (tool_crear_plan)

## Objetivo
Analizar un documento de contexto (`CTX-[ID].md`) o las instrucciones directas del usuario para desglosar un proyecto en fases lógicas y generar un archivo maestro de planificación (`PLAN-[ID].md`) dentro de la carpeta `Agentes/proyectos/`.

## Entradas
- **origen_contexto** (str): Nombre o ruta del archivo de contexto (ej. `CTX-20231010.md`), o una cadena con la idea principal si no hay archivo.
- **nombre_proyecto** (str): Nombre corto y descriptivo del proyecto, usado para nombrar el archivo (ej. `app_finanzas`).
- **plan_estructurado** (str): El contenido detallado del plan, incluyendo fases, dependencias, y asignación de responsables (Zoro, Sanji, Nami, Robin, Luffy).

## Salidas
- Retorna la ruta absoluta del archivo `PLAN-[ID].md` creado.
- Si falla, retorna el error específico para que Luffy pueda corregirlo.

## Hard-Stops (Límites de Seguridad)
1. **Validación de Directorio:** El archivo solo puede ser creado dentro del directorio oficial `Agentes/proyectos/` (o su equivalente autorizado).
2. **Inmutabilidad:** Si el archivo de plan ya existe, la herramienta debe negarse a sobrescribirlo por completo, sugiriendo en su lugar la actualización manual de la Pizarra o la creación de un nuevo plan versionado (ej. `PLAN-[ID]-v2.md`).


---
**Pertenece a:** [[Perfil_Luffy]]
