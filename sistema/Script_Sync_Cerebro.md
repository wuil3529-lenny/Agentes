# Documentación Técnica: `sync_cerebro.py`

**Ubicación del Script:** `Agente_Orquestador/sync_cerebro.py`  
**Rol del Módulo:** Sincronizador del Grafo de Conocimiento en Obsidian y Base Vectorial RAG  
**Subsistema:** Gestión del Conocimiento e Integración Semántica  

---

## 1. Propósito General

`sync_cerebro.py` es el motor de sincronización y coherencia documental del ecosistema. Su responsabilidad es recorrer la estructura de archivos del proyecto, extraer las identidades, reglas y habilidades de cada agente y construir de forma orgánica el grafo de conocimiento en Obsidian mediante enlaces bidireccionales (`[[...]]`).

Simultáneamente, si la bandera de RAG está activa, el script vectoriza el contenido de estos documentos e indexa sus fragmentos en ChromaDB para permitir recuperación semántica y consultas contextuales de alta precisión.

---

## 2. Mecanismos y Flujo de Sincronización

### 2.1. Interconexión de la Trinidad Central
El script asegura que los tres nodos fundamentales del sistema mantengan hiperenlaces cruzados permanentes:
- `Bitacora.md` (Pizarra de tareas a corto plazo)
- `Cerebro.md` (Registro histórico a largo plazo)
- `protocolo/Reglas de la Tripulacion.md` (Directivas y protocolos globales)

Cualquier agente que consulte uno de estos nodos dispone de navegación directa hacia los otros dos pilares.

### 2.2. Generación Orgánica de Nodos de Perfil (`Perfil_[Agente].md`)
Para cada uno de los agentes del sistema (`Agente_Orquestador`, `Subagente_Desarrollo`, `Subagente_Diseno`, `Subagente_Ciberseguridad`, `Subagente_Asistencia`):
1. **Extracción de Identidad:** Inspecciona prioritariamente el archivo unificado `agente.md` o el nodo existente `Perfil_[Agente].md` para extraer la presentación ejecutiva del rol.
2. **Descubrimiento de Habilidades:** Escanea recursivamente el directorio de skills del agente localizando tanto scripts ejecutables (`skill_*.py`) como sus especificaciones Markdown (`Skill_*.md`), así como extensiones de sistema.
3. **Mapeo de Conexiones:** Ensambla un bloque de enlaces al pie del perfil que conecta al agente directamente con los 3 pilares centrales y con todas las habilidades que conforman su inventario operativo.
4. **Sobreescritura Segura:** Actualiza el archivo de perfil preservando la estructura limpia y evitando duplicación de secciones.

### 2.3. Barrido de Archivos Huérfanos y Conexión Exclusiva
Para evitar nodos desconectados en la visualización del grafo de Obsidian:
- La función `sanear_enlace_exclusivo` recorre los directorios de trabajo de cada agente (`memoria/`, `proyectos/`, `informes/`, `reportes/`, `documentos_asistencia/`, etc.).
- Limpia metadatos residuales o conexiones rotas.
- Inyecta al final de cada archivo una única directiva canónica:
  ```markdown
  ---

  ```
- Garantiza una topología visual clara donde cada documento converge jerárquicamente hacia su nodo responsable.

### 2.4. Integración con Memoria Vectorial (ChromaDB / RAG)
Cuando la variable de entorno `ENABLE_RAG_SYNC` está habilitada:
- Obtiene la colección activa de ChromaDB mediante el módulo de memoria vectorial.
- Prepara documentos estructurados asignando identificadores normalizados (ej. `SKILL-[AGENTE]-[NOMBRE]`, `PROTOCOLO-REGLAS`, `PROTOCOLO-ORQUESTADOR`).
- Ejecuta una operación de actualización masiva atómica (`upsert`), sincronizando los contenidos textuales y sus metadatos asociados para consultas de similitud semántica.

---

## 3. Ejecución y Salidas

El script puede ejecutarse de manera autónoma desde la terminal:
```bash
python Agente_Orquestador/sync_cerebro.py
```
- **Salida:** Registros informativos en consola confirmando la creación de nodos de perfil, saneamiento de enlaces y el número de documentos indexados en el motor RAG.
- **Retorno:** Código de salida `0` al culminar exitosamente sin excepciones.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
