# Documentación Técnica: `sync_cerebro.py`

**Ubicación del Script:** `Agente_Orquestador/sync_cerebro.py`  
**Rol del Módulo:** Sincronizador del Grafo de Conocimiento en Obsidian y Base Vectorial RAG  
**Subsistema:** Gestión del Conocimiento e Integración Semántica  

---

## 1. Propósito General

`sync_cerebro.py` es el motor de sincronización y coherencia documental del ecosistema. Su responsabilidad es recorrer la estructura de archivos del proyecto, extraer las identidades, reglas y habilidades de cada agente y construir de forma orgánica el grafo de conocimiento en Obsidian mediante enlaces bidireccionales (`...`).

Simultáneamente, si la bandera de RAG está activa, el script vectoriza el contenido de estos documentos e indexa sus fragmentos en ChromaDB para permitir recuperación semántica y consultas contextuales de alta precisión.

---

## 2. Mecanismos y Flujo de Sincronización (Arquitectura de 3 Niveles)

### 2.1. Nivel 1: Nodos Principales (Núcleo Central)
El triángulo central del sistema está compuesto por los 3 pilares maestros interconectados recíprocamente:
- `Bitacora.md` -> Conecta a `Cerebro Reglas de la Tripulacion`
- `Cerebro.md` -> Conecta a `Bitacora Reglas de la Tripulacion`
- `protocolo/Reglas de la Tripulacion.md` -> Conecta a `Bitacora Cerebro`

### 2.2. Nivel 2: Nodos Secundarios (Agentes y Memoria.md)
Los nodos secundarios representan a los 5 agentes y el archivo maestro de memoria:
- `Perfil_Agente_Orquestador.md`
- `Perfil_Subagente_Desarrollo.md`
- `Perfil_Subagente_Diseno.md`
- `Perfil_Subagente_Ciberseguridad.md`
- `Perfil_Subagente_Asistencia.md`
- `memoria/memoria.md`

> [!IMPORTANT]
> **Regla de Aislamiento Secundario:** Los nodos secundarios se conectan a los tres nodos principales (`Bitacora Cerebro Reglas de la Tripulacion`), pero **NO se conectan entre ellos**, evitando líneas cruzadas o enredos en el grafo.

### 2.3. Nivel 3: Nodos de Salida de los Agentes (Carpetas de Entregables)
Representan las carpetas donde cada agente escribe y deposita su trabajo:
- `Subagente_Desarrollo/proyectos/proyectos.md` -> Conecta ÚNICAMENTE a `Perfil_Subagente_Desarrollo`
- `Subagente_Diseno/informes/informes.md` -> Conecta ÚNICAMENTE a `Perfil_Subagente_Diseno`
- `Subagente_Ciberseguridad/reportes/reportes.md` -> Conecta ÚNICAMENTE a `Perfil_Subagente_Ciberseguridad`
- `Subagente_Asistencia/documentos_asistencia/documentos_asistencia.md` -> Conecta ÚNICAMENTE a `Perfil_Subagente_Asistencia`

> [!IMPORTANT]
> **Regla de Aislamiento de Salida:** Los nodos de salida SOLO se conectan con su respectivo nodo secundario.

### 2.4. Saneamiento Total Anti-Nudo
Para garantizar un grafo limpio, espacioso y estético en Obsidian:
- El script recorre todo el repositorio y purga cualquier enlace residual (`**Pertenece a:**`, `**Conexiones:**`, `Nexo`) de archivos ajenos a estos 13 nodos oficiales (skills, notas de soporte de sistema, archivos temporales, contexto, entregables individuales y notas de memoria).
- De esta forma, el grafo de Obsidian muestra exactamente **13 nodos** organizados en perfecta simetría radial.

### 2.5. Integración con Memoria Vectorial (ChromaDB / RAG)
Cuando la variable de entorno `ENABLE_RAG_SYNC` está habilitada:
- Obtiene la colección activa de ChromaDB mediante el módulo de memoria vectorial.
- Prepara documentos estructurados asignando identificadores normalizados (`SKILL-[NOMBRE]`, `AGENTE-[NOMBRE]`, `PROTOCOLO-REGLAS`).
- Ejecuta una operación atómica de `upsert` para permitir la recuperación semántica por los agentes.

---

## 3. Ejecución y Salidas

El script puede ejecutarse de manera autónoma desde la terminal:
```bash
python Agente_Orquestador/sync_cerebro.py
```
- **Salida:** Registros en consola confirmando la actualización de los 3 niveles del grafo y el saneamiento de archivos externos.
- **Retorno:** Código de salida `0` al culminar exitosamente sin excepciones.

---
**Conexiones:** [[sistema]]
