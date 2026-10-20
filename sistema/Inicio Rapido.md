# Inicio Rápido (Antigravity 2.0)

Guía rápida para la puesta en marcha, operación diaria y adición de nuevo conocimiento en el ecosistema de la tripulación de agentes autónomos.

---

## 1. Levantamiento del Sistema

El ecosistema opera mediante servicios en segundo plano (*daemons*) y agentes efímeros bajo demanda:

### Opción A: Modo Escucha Central (Daemon de Pizarra)
Para iniciar la vigilancia activa de tickets en la Bitácora y mensajes de usuario:
```bash
# Iniciar listener para el Agente Orquestador
python Agente_Orquestador/base_listener.py --agente Agente_Orquestador
```

### Opción B: Ejecución de un Ticket Específico (Spawn Efímero)
Para ejecutar directamente un ticket puntual sin mantener el listener activo:
```bash
python Agente_Orquestador/base_listener.py --agente Subagente_Desarrollo --ticket TKT-DEV-20261009001
```

### Opción C: Ejecución Directa por CLI
Cada agente cuenta con su script de ejecución interactiva o por argumento:
```bash
python Subagente_Desarrollo/Perfil_Subagente_Desarrollo.py "Crea un scaffold web en proyectos/landing_page"
```

---

## 2. Sincronización Automática del Cerebro (`sync_cerebro.py`)

Al inicializarse el entorno o de forma manual tras cambios estructurales importantes, se ejecuta `sync_cerebro.py`:
```bash
python Agente_Orquestador/sync_cerebro.py
```
- **Grafo de Obsidian:** Genera o actualiza los nodos de habilidades (`Skill_*.md`), enlaza la documentación técnica y conecta cada archivo con su nodo agente responsable.
- **Memoria Vectorial RAG:** Si `ENABLE_RAG_SYNC=1`, sincroniza los documentos en ChromaDB para permitir a los agentes consultar *Playbooks* procedurales previos.
- **Higiene Preventiva:** Purga carpetas obsoletas o temporales para mantener la integridad del sistema.

---

## 3. Flujo de Trabajo Operativo en la Pizarra (`Bitacora.md`)

1. **Creación:** El usuario o el `Agente_Orquestador` añade un ticket estructurado en `Bitacora.md` con estado `PENDIENTE`.
2. **Detección:** `base_listener.py` detecta la asignación y levanta un subproceso efímero para el agente especialista correspondiente.
3. **Ejecución Protegida:** El subagente ejecuta sus herramientas a través del interceptor de `bucle_autocorreccion.py` y `qa_gherkin.py`.
4. **Entrega y Auditoría Zero-Trust:** El subagente deposita su entregable físico en su carpeta oficial (`proyectos/`, `informes/`, etc.) y emite el Escudo JSON. El Orquestador audita la existencia y validez del archivo en disco antes de marcar el ticket como `CERRADO`.

---

## 4. Cómo Añadir Nuevo Conocimiento Manual

Para dotar a cualquier agente de nuevo contexto, guías técnicas o documentación de librerías:
1. Crea un archivo Markdown (`.md`) con el contenido técnico (ejemplo: `guia_fastapi.md`).
2. Guárdalo dentro del directorio del agente al que le competa (ejemplo: `Subagente_Desarrollo/guia_fastapi.md`).
3. Ejecuta `sync_cerebro.py` (o espera al siguiente ciclo).
4. El script enlazará automáticamente el nodo al perfil del agente en el grafo de Obsidian y lo indexará en la memoria semántica para su consulta en tareas futuras.

---
**Conexiones:** [[sistema]]
