---
name: crear-herramienta-tripulacion
description: >-
  Usa esta habilidad de Antigravity obligatoriamente cada vez que el Capitán (Wuilfredo) te pida crear una nueva herramienta, skill o capacidad técnica para cualquier agente de la tripulación (Zoro, Nami, Robin, Sanji, o para ti mismo). Esta habilidad dicta el protocolo estricto de 5 pasos para diseñar, programar, auditar mediante Robin y registrar herramientas en el Cerebro.
---

# Protocolo de Creación de Herramientas de Tripulación

Sigue estrictamente estos 5 pasos cada vez que debas dotar a un agente de una nueva habilidad. Nunca te saltes un paso ni asumas capacidades sin generar el código.

## Paso 1: Diseño de la Habilidad (Drafting)

Crea un archivo Markdown que documente la nueva habilidad.
**Ruta de destino:** `C:\Users\admin\Documents\Agentes\<NombreAgente>\skills\<nombre_habilidad>.md`.
**Formato obligatorio:** Usa la estructura de la [Plantilla de Skill](./resources/plantilla_skill.md) como base. Debe contener las secciones: Objetivo, Entradas/Salidas esperadas y Límites de Seguridad (Hard-Stops).

## Paso 2: Generación del Wrapper/Script (Código en Python)

Escribe el código Python de la herramienta que le dará vida a la habilidad.
**Ruta de destino:** `C:\Users\admin\Documents\Agentes\<NombreAgente>\skills\<nombre_habilidad>.py`.
**Formato obligatorio:** Usa la Plantilla de Script(./resources/template_herramienta.py) como base. El código debe estar fuertemente tipado y contener bloques `try-except` para evitar excepciones no controladas. 
**Aislamiento:** Si requieres instalar nuevas librerías, asegúrate de documentarlo para el entorno del contenedor del agente, nunca a nivel global del servidor.

## Paso 3: Petición de Verificación a Robin (Dry-Run)

Antes de dar la herramienta por terminada, debes auditarla.
Ve a la Pizarra Central (`C:\Users\admin\Documents\Agentes\Bitacora.md`) y crea un ticket asignado a **Robin** pidiéndole que verifique el código generado. Robin auditará la seguridad y verificará que no haya bucles infinitos.
**Derecho a Vetar (Hard-Stop):** Si Robin rechaza el código 2 veces seguidas debido a fallos o vulnerabilidades, DEBES abortar el proceso inmediatamente. Registra el intento fallido en `C:\Users\admin\Documents\Agentes\memoria\Memoria_Viva_Errores.md` explicando que la habilidad falló la auditoría repetidamente, y notifica a Wuilfredo.

## Paso 4: Actualización de Perfil JSON (Catálogo Few-Shot)

Una vez que Robin haya dado su aprobación explícita en la Pizarra, debes modificar el perfil interno del agente destino (por ejemplo, `nami_perfil.json`) para enseñarle a usar la herramienta.
Documenta allí bajo qué circunstancias exactas debe usarla (el "gatillo") para evitar alucinaciones.

## Paso 5: Registro en el Cerebro

Finalmente, actualiza `C:\Users\admin\Documents\Agentes\Cerebro.md` informando que el agente ahora posee esta nueva capacidad.
**REGLA TÉCNICA DE ORO (Gemelo Digital):** Tienes estrictamente **PROHIBIDO** crear manualmente nodos Markdown de Obsidian para representar el archivo Python de la herramienta. Tu responsabilidad de creación termina al colocar el archivo en la carpeta `skills`. El motor `sync_cerebro.py` se encargará automáticamente de generar el archivo espejo visual y enlazarlo al perfil del agente en el grafo en el siguiente reinicio.

---
**Conexiones:** [[Perfil_Luffy]]
