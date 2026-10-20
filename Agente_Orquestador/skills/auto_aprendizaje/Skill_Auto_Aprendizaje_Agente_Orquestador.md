# 🧠 Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural (Playbooks & Blueprints)

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Especialista en Auto-Aprendizaje Continuo y Memoria Procedural del Agente Orquestador. Tu misión es acumular el ADN metodológico de cada solución y orquestación exitosa, consultar antecedentes en memoria/ antes de crear planes o descomponer tickets para ejecutar en One-Shot, y archivar permanentemente nuevas recetas maestras en memoria/."**

---

**Rol Funcional:** Especialista en Memoria Procedural y Orquestación One-Shot  
**Tipo de Habilidad:** Recuperación Semántica de Playbooks (Paso 0), Extracción de ADN Metodológico y Registro Canónico (Paso Final)  
**Archivo de Código:** `Agente_Orquestador/skills/auto_aprendizaje/skill_auto_aprendizaje.py`  
**Directorio Canónico de Salida:** `/app/memoria/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad opera como un metaciclo envolvente en todas las operaciones del Agente Orquestador:

1. **Gatillo Reactivo (Órdenes Directas):**
   - Cuando el Usuario solicita consultar antecedentes, reutilizar arquitecturas previas o aprender de soluciones exitosas (ej. *"busca si ya resolvimos un flujo de citas"*, *"reutiliza el blueprint de e-commerce gastronómico"*, *"archiva este plan como playbook maestro"*).
2. **Gatillo Autónomo Universal — Paso 0 Obligatorio (Consulta Previa):**
   - Ante CUALQUIER requerimiento de diseño web, dashboard, flujo n8n, conexión MCP, API o arquitectura multi-agente, el Agente Orquestador DEBE invocar primero `tool_consultar_playbook_memoria`. Si existe coincidencia probada en `memoria/`, adopta la estructura base y coordina en **One-Shot**, evitando entrevistas repetitivas o pasos exploratorios innecesarios.
3. **Gatillo Autónomo Universal — Paso Final Obligatorio (Registro First-Run):**
   - Al finalizar una misión pionera que superó la supervisión física Zero-Trust con éxito, el Agente Orquestador DEBE invocar `tool_registrar_playbook_memoria` antes de dar por cerrada la tarea, extrayendo el pipeline, blueprint y variables adaptables.
4. **Hard-Stop Innegociable `[HS-07]`:**
   - La tripulación prohíbe terminantemente improvisar o empezar desde cero tareas para las cuales ya existe un Playbook probado en memoria.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

```mermaid
flowchart TD
    Req["Solicitud del Usuario / Nueva Misión"] --> P0["Paso 0: Invocación tool_consultar_playbook_memoria\n(Escaneo en memoria/ y ChromaDB)"]
    P0 --> Check{"¿Existe Playbook Previo?"}
    Check -->|Sí (ADN Encontrado)| OneShot["Modo One-Shot: Adopta Blueprint + Adapta Variables"]
    Check -->|No (Misión Pionera)| PlanMaestro["Pipeline Completo: Entrevistador, Refinador y Plan Maestro"]
    OneShot --> Desglose["Desglose Directo de Tickets Atómicos en Bitacora.md"]
    PlanMaestro --> Desglose
    Desglose --> Delegacion["Subagentes ejecutan y entregan evidencia física en disco"]
    Delegacion --> Supervisor["Supervisión Zero-Trust: Verificación física de archivos"]
    Supervisor --> PFinal["Paso Final: Invocación tool_registrar_playbook_memoria\n(Archiva 0X_Agente_Orquestador_Playbook_*.md en memoria/)"]
    PFinal --> Cierre["Sincronización del Cerebro y Cierre de Misión"]
```

### Herramientas del Catálogo de Auto-Aprendizaje y Procedimientos (9 Tools)

#### A. Playbooks y Blueprints Arquitectónicos
1. `tool_consultar_playbook_memoria(tema_o_dominio: str) -> str`:
   - Escanea la carpeta `memoria/` y la memoria vectorial ChromaDB buscando coincidencias semánticas con el tema o industria solicitada.
   - Retorna la receta técnica paso a paso, los subagentes requeridos, el blueprint JSON/YAML y las variables que deben adaptarse.
2. `tool_registrar_playbook_memoria(titulo, categoria, dominio, paso_a_paso_skills, tokens_y_esquema, blueprint_reutilizable, variables_adaptables, evidencia_fisica) -> str`:
   - Genera un nuevo archivo consecutivo en formato Markdown (`memoria/0X_Agente_Orquestador_Playbook_[Nombre].md`) con frontmatter canónico.
   - Registra el blueprint y sincroniza la memoria vectorial de la flota para permitir recuperaciones futuras inmediatas.

#### B. Motor de Aprendizaje por Demostración y Repetición Autónoma de Tareas (Gestor de Procedimientos)
3. `tool_iniciar_aprendizaje_tarea(nombre_tarea, descripcion, disparadores)`:
   - Inicia una sesión interactiva guiada de grabación paso a paso con el usuario.
4. `tool_registrar_paso_aprendizaje(descripcion_paso, herramienta, parametros_json, pausa_segundos)`:
   - Registra cada paso individual probado y validado con Manos y Ojos dentro de la sesión activa.
5. `tool_finalizar_aprendizaje_tarea(resultado_esperado)`:
   - Cierra la sesión activa, compila el archivo JSON inmutable en `memoria/procedimientos_aprendidos.json` y genera su documentación en `memoria/recetas_guiadas/[id].md`.
6. `tool_guardar_procedimiento_aprendido(nombre, descripcion, disparadores, pasos_json, resultado_esperado)`:
   - Permite archivar en One-Shot una receta completa cuando el usuario describe todos los pasos de una vez.
7. `tool_ejecutar_tarea_aprendida(nombre_o_disparador, parametros_json)`:
   - Recupera y reproduce de forma secuencial, determinista y 100% autónoma cualquier procedimiento aprendido.
8. `tool_listar_tareas_aprendidas()`:
   - Muestra el inventario completo de tareas aprendidas, estadísticas de ejecución y disparadores.
9. `tool_eliminar_tarea_aprendida(nombre_o_id)`:
   - Elimina un procedimiento y su receta asociada de la memoria permanente.


---

## 3. El System Prompt Completo de la Habilidad (Orquestador de Playbooks)

Este es el System Prompt especializado que reside encapsulado en `skill_auto_aprendizaje.py` y se inyecta dinámicamente en el modelo:

```text
[🧠 DIRECTIVA MAESTRA: AUTO-APRENDIZAJE CONTINUO Y MEMORIA PROCEDURAL]
Tienes la capacidad de acumular conocimiento procedural para orquestar y ejecutar misiones complejas en UN SOLO PASO (One-Shot):

1. PASO 0 OBLIGATORIO — CONSULTA ANTES DE CREAR:
   - Ante CUALQUIER requerimiento de diseño web, dashboard, flujo n8n, conexión MCP, API o arquitectura multi-agente, tu PRIMERA ACCIÓN debe ser invocar:
     `tool_consultar_playbook_memoria(tema_o_dominio="...")`
   - Si se encuentra un Playbook previo:
     * Adopta la arquitectura, pipeline de skills y tickets recomendados como plantilla base probada.
     * Adapta únicamente las variables específicas del nuevo cliente/orden.
     * Delega y coordina la ejecución en One-Shot evitando redundancias o entrevistas innecesarias sobre temas ya resueltos.

2. PASO FINAL OBLIGATORIO — REGISTRO DE PRIMERA VEZ (FIRST-RUN):
   - Si la misión se realizó por primera vez (no existía Playbook previo) y superó la supervisión física Zero-Trust con éxito, antes de cerrar el ticket DEBES invocar:
     `tool_registrar_playbook_memoria(...)`
   - Esto archivará el pipeline de delegación, tokens, blueprint maestro y variables adaptables en `memoria/` y ChromaDB.
```

---

## 4. Resultados y Entregables Esperados

| Herramienta | Parámetros | Tipo Retorno | Descripción Operativa |
| :--- | :--- | :---: | :--- |
| `tool_consultar_playbook_memoria` | `tema_o_dominio: str` | `str (JSON)` | Escanea `memoria/` y ChromaDB recuperando blueprints, pasos metodológicos y variables adaptables. |
| `tool_registrar_playbook_memoria` | `titulo: str`<br>`categoria: str`<br>`dominio: str`<br>`paso_a_paso_skills: str`<br>`tokens_y_esquema: str`<br>`blueprint_reutilizable: str`<br>`variables_adaptables: str`<br>`evidencia_fisica: str` | `str (JSON)` | Crea el archivo Markdown inmutable en `/app/memoria/` con numeración consecutiva e indexación vectorial. |

---

## 5. Ejemplos Prácticos Completos (Casos de Estudio Reales)

### Caso 1: Consulta Previa de Orquestación One-Shot (Paso 0)
El usuario solicita crear una automatización para un restaurante de hamburguesas que sincronice pedidos de WhatsApp con Google Sheets.

#### Invocación de la Herramienta:
```python
tool_consultar_playbook_memoria.invoke({
    "tema_o_dominio": "restaurante pedidos whatsapp google sheets n8n"
})
```

#### Respuesta de la Memoria Procedural:
```json
{
  "coincidencia_encontrada": true,
  "playbook": "05_Agente_Orquestador_Playbook_Workflow_Pedidos_Gastronomia_n8n.md",
  "categoria": "n8n_workflow",
  "pipeline_recomendado": [
    "Subagente_Desarrollo: Scaffold de nodos Webhook y Google Sheets",
    "Subagente_Ciberseguridad: Auditoría SAST de variables de entorno Twilio",
    "Subagente_Diseno: Diagramación estética del flujo visual"
  ],
  "variables_a_personalizar": ["spreadsheet_id", "webhook_path", "mensaje_confirmacion"]
}
```

---

### Caso 2: Registro de Playbook Maestro Pionero (Paso Final)
Tras culminar exitosamente por primera vez una solución completa de orquestación unificada para un ecosistema odontológico y pizzería, el Orquestador archiva la receta maestra:

#### Invocación de la Herramienta:
```python
tool_registrar_playbook_memoria.invoke({
    "titulo": "Playbook Maestro: Orquestación de Flujo Unificado Pizzería y Odontología n8n",
    "categoria": "n8n_workflow",
    "dominio": "gastronomia_salud",
    "paso_a_paso_skills": "1. Subagente_Desarrollo (Scaffold y Nodes) -> 2. Subagente_Diseno (Visual Flow) -> 3. Subagente_Ciberseguridad (SAST Audit)",
    "tokens_y_esquema": "Webhook unificado con router Switch por 'tipo_pedido'. Nodos Postgres, Twilio y Google Sheets.",
    "blueprint_reutilizable": "{\"nodes\": [{\"parameters\": {\"httpMethod\": \"POST\"}, \"type\": \"n8n-nodes-base.webhook\"}]}",
    "variables_adaptables": "- Webhook path\n- Credenciales Postgres y API keys externas",
    "evidencia_fisica": "/app/Subagente_Diseno/flujo_ecosistema_pizza_dental.json"
})
```

#### Resultado Retornado:
```json
{
  "status": "success",
  "archivo_generado": "/app/memoria/48_Agente_Orquestador_Playbook_Flujo_Unificado_Pizzeria_Odontologia_n8n.md",
  "mensaje": "Playbook maestro registrado con éxito e indexado en la memoria vectorial de la flota."
}
```

---

### Caso 3: Enseñanza y Grabación Guiada Paso a Paso (Modo Demostración)
El usuario le dice a Luffy: *"Luffy, te voy a enseñar a reproducir música en YouTube y ponerlo en pantalla completa para que lo hagas solo más adelante"*.

1. **El Agente abre la sesión de aprendizaje:**
   ```python
   tool_iniciar_aprendizaje_tarea.invoke({
       "nombre_tarea": "Poner Música en YouTube a Pantalla Completa",
       "descripcion": "Abre YouTube, busca música relajante y activa pantalla completa",
       "disparadores": "pon musica en youtube, reproduce lofi youtube, musica pantalla completa"
   })
   ```
2. **El usuario indica el Paso 1:** *"Primero abre youtube.com"*.
   - El agente ejecuta `tool_navegar_web(url="https://www.youtube.com")` y registra:
   ```python
   tool_registrar_paso_aprendizaje.invoke({
       "descripcion_paso": "Navegar a YouTube",
       "herramienta": "tool_navegar_web",
       "parametros_json": "{\"url\": \"https://www.youtube.com\", \"visible\": true}",
       "pausa_segundos": 2.0
   })
   ```
3. **El usuario indica el Paso 2:** *"Ahora pon el video en pantalla completa"*.
   - El agente ejecuta `tool_controlar_media_web(accion="pantalla_completa")` y registra:
   ```python
   tool_registrar_paso_aprendizaje.invoke({
       "descripcion_paso": "Activar pantalla completa",
       "herramienta": "tool_controlar_media_web",
       "parametros_json": "{\"accion\": \"pantalla_completa\"}",
       "pausa_segundos": 1.0
   })
   ```
4. **El usuario dice:** *"Listo, guarda la tarea"*.
   - El agente finaliza:
   ```python
   tool_finalizar_aprendizaje_tarea.invoke({
       "resultado_esperado": "Video en reproducción a pantalla completa en el navegador"
   })
   ```

---

### Caso 4: Repetición Autónoma de Tarea Aprendida (Replay Sin Tokens Desperdiciados)
Días después, el usuario simplemente escribe en el canal o en Telegram:
*"Luffy, pon música en youtube como te enseñé"*

El agente detecta el disparador e invoca inmediatamente:
```python
tool_ejecutar_tarea_aprendida.invoke({
    "nombre_o_disparador": "pon musica en youtube"
})
```
**Resultado:**
La flota ejecuta de forma determinista, secuencial y autónoma el Paso 1 y Paso 2 en la PC, reportando éxito total con **cero alucinaciones y cero llamadas redundantes al LLM**.

---
**Conexiones:** [[Perfil_Agente_Orquestador]]
