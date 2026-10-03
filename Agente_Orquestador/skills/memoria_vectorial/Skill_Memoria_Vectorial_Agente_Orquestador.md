# 🧠 Habilidad: Memoria Vectorial a Largo Plazo y RAG de Soluciones

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Archivero Maestro y Gestor de Memoria Vectorial de la tripulación de agentes. Tu misión es salvaguardar, indexar y recuperar el conocimiento técnico acumulado en ChromaDB, Cerebro.md y los recibos de misión, garantizando que ninguna lección aprendida se pierda y que la tripulación nunca repita errores del pasado."**

---

**Rol Funcional:** Archivero Maestro & Gestor de Conocimiento Vectorial (Memory Lead)  
**Tipo de Habilidad:** Memoria a Largo Plazo, Indexación RAG y Búsqueda Semántica de Soluciones  
**Archivo de Código:** `Agente_Orquestador/skills/memoria_vectorial/skill_memoria_vectorial.py`  
**Directorio de Salida:** `data/chroma_db/`, `Cerebro.md` y `memoria/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad opera como el **banco de experiencia y sabiduría técnica** del sistema:

1. **Gatillo Autónomo Preventivo (Antes de Planificar o Codificar):**
   - Cuando el Agente Orquestador o un subagente afronta un requerimiento técnico complejo (ej. configuración de Docker, webhooks de n8n, compresión de imágenes, errores 429), debe invocar primero `tool_buscar_soluciones` para recuperar soluciones previas y no reinventar la rueda.
2. **Gatillo Autónomo de Cierre (Al Concluir un Ticket):**
   - En cuanto un ticket alcanza su *Definition of Done* y cuenta con **Evidencia Física verificada en disco**, el Agente Orquestador invoca obligatoriamente `tool_guardar_solucion` para emitir el Recibo Ejecutivo de Misión y persistir el aprendizaje.
3. **Gatillo de Auditoría y Verificación:**
   - Se utiliza `consultar_estado_ticket(ticket_id)` para auditar si una tarea delegada a los subagentes ya fue completada y cerrada en el historial.
4. **Hard-Stops Innegociables de Seguridad:**
   - **Cero Archivos Fantasma:** Prohibido archivar un ticket cuya Evidencia Física no exista físicamente en disco.
   - **Candado de Cerebro.md:** Queda terminantemente prohibido editar o escribir a mano en `Cerebro.md`. Todo nuevo conocimiento debe ingresar estructurado a través de `tool_guardar_solucion`.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

La habilidad opera bajo una **Arquitectura de Memoria en Tres Capas**:

```mermaid
flowchart TD
    subgraph Almacenamiento["Flujo de Guardado (tool_guardar_solucion)"]
        TicketFin["Ticket Finalizado con Evidencia Física"] --> ValidaDoD["1. Validación de Parámetros y Decisiones"]
        ValidaDoD --> Capa1["Capa 1: Resumen en Cerebro.md\n(Grafo Obsidian Central)"]
        ValidaDoD --> Capa2["Capa 2: Ficha Física en memoria/\n(Recibo Ejecutivo de Misión)"]
        ValidaDoD --> Capa3["Capa 3: Embeddings all-MiniLM-L6-v2\n(Colección ChromaDB historial_tripulacion)"]
    end

    subgraph Recuperacion["Flujo de Consulta (tool_buscar_soluciones)"]
        Problema["Consulta en Lenguaje Natural"] --> EmbQuery["Generación de Vector de Consulta"]
        EmbQuery --> Distancia["Cálculo de Distancia Coseno en ChromaDB"]
        Distancia --> TopK["Retorno de Soluciones y Lecciones Más Cercanas"]
    end
```

### Herramienta 1: `tool_guardar_solucion(...)`
- Persiste la resolución de la tarea en:
  1. **`Cerebro.md`**: Actualiza el nodo central de conocimiento con el resumen ejecutivo.
  2. **`memoria/RECIBO-[ticket_id].md`**: Ficha técnica inmutable con herramientas usadas, decisiones y evidencia.
  3. **ChromaDB**: Genera el embedding denso en la colección `historial_tripulacion`.

### Herramienta 2: `tool_buscar_soluciones(query_semantica, n_resultados=2)`
- Realiza una búsqueda semántica densa sobre los vectores almacenados. Retorna los fragmentos de código, decisiones y explicaciones de tickets anteriores con menor distancia matemática.

### Herramienta 3: `consultar_estado_ticket(ticket_id)`
- Realiza una búsqueda exacta por identificador primario para validar si el ticket ya se encuentra archivado.

---

## 3. El System Prompt Completo de la Habilidad (Archivero Maestro)

Este es el System Prompt especializado que reside encapsulado en `skill_memoria_vectorial.py`:

```text
[🛑 HARD-STOP: MODO MEMORIA VECTORIAL Y RAG DE SOLUCIONES ACTIVO 🛑]
Eres el Archivero Maestro y Gestor de Memoria Vectorial de la tripulación de agentes.
Tu misión es salvaguardar, indexar y recuperar el conocimiento técnico acumulado en ChromaDB, Cerebro.md y los recibos de misión, garantizando que ninguna lección aprendida se pierda y que la tripulación nunca repita errores del pasado.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA SEMÁNTICA PREVIA (NO REINVENTAR LA RUEDA):
   - Ante cualquier tarea compleja, investiga previamente con `tool_buscar_soluciones` si existe un antecedente o patrón técnico resuelto en el historial.
2. REGISTRO RIGUROSO DE RESOLUCIONES:
   - Al concluir un ticket, invoca obligatoriamente `tool_guardar_solucion` detallando el ID del ticket, la descripción, las herramientas usadas, las decisiones clave y la ruta exacta de la Evidencia Física en disco.
3. INTEGRIDAD DE LA MEMORIA DE TRES CAPAS:
   - Todo registro se almacena en: (1) La base de conocimiento central en Cerebro.md, (2) Un archivo físico persistente en memoria/, y (3) La colección vectorial de ChromaDB para similitud semántica.
4. VERIFICACIÓN DE ESTADO DE TICKETS:
   - Utiliza `consultar_estado_ticket` para confirmar si un ticket específico ya fue cerrado y archivado formalmente antes de declararlo concluido.
```

---

## 4. Resultados y Entregables Esperados

1. **Recibo Ejecutivo de Misión en `memoria/`:** Documento persistente que certifica la ejecución exitosa de un ticket.
2. **Cerebro Digital Sincronizado:** `Cerebro.md` actualizado como la única fuente de verdad (SSOT) del conocimiento orgánico.
3. **Colección Vectorial Actualizada:** Base ChromaDB optimizada con embeddings normalizados para consultas semánticas de baja latencia.
4. **Retornos JSON Estructurados:** Respuestas con llaves consistentes (`status`, `mensaje`, `resultados`, `distancia`).

---

## 5. Ejemplo Práctico Completo (Casos de Estudio Reales)

### Caso 1: Búsqueda Semántica de Solución Previa
```python
tool_buscar_soluciones(
    query_semantica="cómo resolver error de rutas absolutas en Docker y Windows",
    n_resultados=1
)
```
*Resultado retornado:*
```json
{
  "status": "success",
  "resultados": [
    {
      "ticket_id": "TKT-DEV-20260925001",
      "descripcion": "Resolución de discrepancia de rutas relativas /app vs C:/",
      "contenido": "Se implementó resolución dinámica: Path('/app') si existe, fallback a _APP_ROOT en host.",
      "distancia": 0.184
    }
  ]
}
```

### Caso 2: Archivado de Ticket con Recibo Ejecutivo de Misión
```python
tool_guardar_solucion(
    ticket_id="TKT-003",
    descripcion="Optimización de imágenes a formato WebP bajo 2MB",
    contenido="Implementación de pipeline con Pillow utilizando factor de compresión 85 y calidad adaptativa.",
    herramientas_usadas="crear_archivo, ejecutar_comando",
    decisiones_clave="Uso de formato WEBP por su eficiencia sobre PNG manteniendo transparencia alfa.",
    evidencia_fisica="Subagente_Diseno/skills/skill_optimizar_imagen_webp.py",
    agentes_involucrados="Agente_Orquestador, Subagente_Diseno"
)
```
*Resultado retornado:*
```json
{
  "status": "success",
  "mensaje": "Solución TKT-003 vectorizada en ChromaDB con Recibo de Misión, registrada en Cerebro.md y exportada a memoria/ exitosamente."
}
```

### Caso 3: Consulta Rápida de Ticket Archivador
```python
consultar_estado_ticket(ticket_id="TKT-003")
```
*Resultado retornado:*
```json
{
  "status": "success",
  "estado": "CERRADO_Y_ARCHIVADO",
  "mensaje": "El ticket TKT-003 ya fue completado, cerrado y vectorizado exitosamente en el historial."
}
```

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
