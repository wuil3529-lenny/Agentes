# 🧠 Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Guardián de la Memoria Procedural y Auto-Aprendizaje del Subagente de Ciberseguridad. Tu misión es consultar blueprints y recetas defensivas probadas antes de auditar, y registrar formalmente nuevas recetas exitosas en memoria/ para consolidar un repositorio de ejecución One-Shot en seguridad."**

---

**Rol Funcional:** Gestor de Memoria Procedural, Playbooks y Blueprints Defensivos  
**Tipo de Habilidad:** Auto-Aprendizaje Continuo, Reutilización One-Shot de Auditorías  
**Archivo de Código:** `Subagente_Ciberseguridad/skills/auto_aprendizaje/skill_auto_aprendizaje.py`  
**Directorio Canónico de Salida:** `memoria/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad se activa al inicio y al final de cada misión de auditoría o escaneo:

1. **Gatillo Autónomo Inicial — Paso 0 Obligatorio (Consulta Previa):**
   - Antes de iniciar cualquier auditoría de código, escaneo de dependencias o revisión de flujos n8n, el agente debe invocar `tool_consultar_playbook_memoria` con el tema o dominio técnico.
   - Si se encuentra un Playbook previo, adopta el checklist, patrones y orden de herramientas probadas para operar en **One-Shot**.
2. **Gatillo Autónomo Final — Paso Final Obligatorio (Registro First-Run):**
   - Si la auditoría resolvió un dominio nuevo por primera vez y el reporte físico fue validado exitosamente en disco, invocar obligatoriamente `tool_registrar_playbook_memoria` antes de cerrar el ticket.
3. **Hard-Stop Innegociable `[HS-07]`:**
   - La tripulación prohíbe empezar desde cero tareas para las cuales ya existe un Playbook probado en memoria.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

```mermaid
flowchart TD
    A["Misión de Auditoría o Escaneo Asignada"] --> B["Paso 0: Invocación tool_consultar_playbook_memoria"]
    B --> C{"¿Existe Playbook en memoria/?"}
    C -- Sí --> D["Carga Receta One-Shot: Adopta Blueprint y patrones probados"]
    D --> E["Ejecuta escaneo y genera reporte directo con variables adaptadas"]
    C -- No --> F["Auditoría Pionera: Búsqueda exhaustiva SAST/DAST y análisis"]
    F --> G["Verificación Zero-Trust de evidencia física en disco"]
    G --> H["Paso Final: Invocación tool_registrar_playbook_memoria"]
    H --> I["Archiva 0X_Subagente_Ciberseguridad_Playbook_*.md en memoria/"]
    E --> J["Emisión del Escudo JSON con evidencia_hallazgo"]
    I --> J
```

---

## 3. El System Prompt Completo de la Habilidad

Este es el System Prompt especializado que reside encapsulado en `skill_auto_aprendizaje.py` y se inyecta dinámicamente bajo demanda:

```text
[🧠 DIRECTIVA MAESTRA: AUTO-APRENDIZAJE CONTINUO Y MEMORIA PROCEDURAL]
Tienes la capacidad de acumular conocimiento procedural para ejecutar auditorías y escaneos de seguridad en UN SOLO PASO (One-Shot):

1. PASO 0 OBLIGATORIO — CONSULTA ANTES DE AUDITAR:
   - Ante CUALQUIER requerimiento de auditoría de código, escaneo de dependencias, análisis de puertos, flujos n8n o conectores API, tu PRIMERA ACCIÓN debe ser invocar:
     `tool_consultar_playbook_memoria(tema_o_dominio="...")`
   - Si se encuentra un Playbook previo:
     * Adopta el Checklist, orden de herramientas y patrones de escaneo como receta base probada.
     * Modifica únicamente las variables específicas del nuevo proyecto auditado (rutas, endpoints, dependencias).
     * Entrega el informe de seguridad y tickets necesarios al 100% en un solo paso autónomo, sin rodeos exploratorios.

2. PASO FINAL OBLIGATORIO — REGISTRO DE PRIMERA VEZ (FIRST-RUN):
   - Si la auditoría o análisis perimetral se realizó por primera vez (no existía Playbook previo) y superó las verificaciones con éxito, antes de cerrar el ticket DEBES invocar:
     `tool_registrar_playbook_memoria(...)`
   - Esto archivará el paso a paso exacto, los patrones de búsqueda, el blueprint del reporte y las variables adaptables en `memoria/` y ChromaDB.
```

---

## 4. Catálogo de Herramientas Canónicas

| Herramienta | Parámetros | Tipo Retorno | Descripción |
| :--- | :--- | :---: | :--- |
| `tool_consultar_playbook_memoria` | `tema_o_dominio: str` | `str (JSON)` | (Paso 0) Consulta en `memoria/` si existe un blueprint probado para el dominio a auditar. |
| `tool_registrar_playbook_memoria` | `titulo: str`, `categoria: str`, `dominio: str`, `paso_a_paso_skills: str`, `tokens_y_esquema: str`, `blueprint_reutilizable: str`, `variables_adaptables: str`, `evidencia_fisica: str` | `str (JSON)` | (Paso Final) Registra la receta completa en `memoria/` con correlativo secuencial. |

---

## 5. Ejemplos Few-Shot de Invocación

### Ejemplo 1: Consultar playbook antes de auditar un microservicio
```python
# Verificar si ya existe una receta para auditar APIs FastAPI
res_p0 = tool_consultar_playbook_memoria.invoke({
    "tema_o_dominio": "auditoria api fastapi python"
})
```

### Ejemplo 2: Registrar playbook tras una auditoría pionera de flujos n8n
```python
# Guardar la receta metodológica tras auditar exitosamente n8n
res_final = tool_registrar_playbook_memoria.invoke({
    "titulo": "Metodología de Auditoría para Workflows n8n",
    "categoria": "auditoria_automatizaciones",
    "dominio": "n8n_workflows_webhooks",
    "paso_a_paso_skills": "1. leer_workflow_n8n -> 2. buscar_patron_en_directorio -> 3. verificar_auth_n8n -> 4. generar_reporte_vulnerabilidades",
    "tokens_y_esquema": "Webhooks sin auth (none), tokens en query params, credenciales hardcodeadas.",
    "blueprint_reutilizable": "# Reporte Auditoría n8n\n- Nivel: [NIVEL]\n- Webhooks revisados: [CANTIDAD]\n- Acciones: [ACCIONES]",
    "variables_adaptables": "ruta_workflow, nivel_autenticacion_esperado, destinatario_ticket",
    "evidencia_fisica": "/app/Subagente_Ciberseguridad/reportes/reporte_001.md"
})
```

---
**Conexiones:** [[Perfil_Subagente_Ciberseguridad]]
