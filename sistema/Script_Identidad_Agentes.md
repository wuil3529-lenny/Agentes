# Documentación Técnica: `identidad_agentes.py`

**Ubicación del Script:** `Agente_Orquestador/identidad_agentes.py`  
**Rol del Módulo:** Cargador Dinámico de Identidades, Enrutador de Responsables y Sincronizador de SSOT  
**Subsistema:** Gestión de Identidad y Enrutamiento Multi-Agente  

---

## 1. Propósito General

`identidad_agentes.py` implementa la arquitectura de **Identidad Desacoplada** en la tripulación de agentes. Su función es leer en tiempo real los archivos de definición Markdown (`_agents/agente.md` o `.agents/agente.md`) de cada agente para extraer y resolver dinámicamente:
1. **Identidad Canónica del Sistema:** El nombre técnico invariable utilizado para el enrutamiento de procesos (`Agente_Orquestador`, `Subagente_Desarrollo`, `Subagente_Diseno`, `Subagente_Ciberseguridad`, `Subagente_Asistencia`).
2. **Identidad Asignada por el Usuario:** El nombre o alias conversacional personalizado configurado por el usuario (ej. *Luffy*, *Zoro*, *Nami*, *Robin*, *Sanji*, o cualquier nombre arbitrario).
3. **Rol y Título Profesional:** Descripción del cargo extraída directamente de la cabecera del documento.
4. **Aliases Dinámicos:** Mapeo de sinónimos para interpretación flexible de destinatarios en la Pizarra (`Bitacora.md`) y la consola web.

---

## 2. Mapa Base de Slots de la Tripulación

El módulo mantiene una definición estructurada de los 5 slots base del sistema:

| Slot | Carpeta Canónica | Identidad Canónica | Nombre por Defecto | Rol por Defecto |
| :--- | :--- | :--- | :--- | :--- |
| `luffy` | `Agente_Orquestador` | `Agente_Orquestador` | Luffy | Director de Operaciones y Supervisor Supremo |
| `zoro` | `Subagente_Desarrollo` | `Subagente_Desarrollo` | Zoro | Ingeniero de Software Full-Stack y Orquestación |
| `nami` | `Subagente_Diseno` | `Subagente_Diseno` | Nami | Directora Creativa, Navegante de Interfaces y Estratega Visual |
| `robin` | `Subagente_Ciberseguridad` | `Subagente_Ciberseguridad` | Robin | Oficial de Seguridad Defensiva y Auditoría |
| `sanji` | `Subagente_Asistencia` | `Subagente_Asistencia` | Sanji | Gestor Ejecutivo y Automatización de Workspace |

---

## 3. Funciones Clave y Flujo Operativo

### 3.1. `obtener_identidades_agentes(directorio_raiz=None)`
- Inspecciona la estructura de carpetas de la flota.
- Para cada slot, localiza el archivo SSOT (`_agents/agente.md` o `.agents/agente.md`).
- Extrae mediante expresiones regulares:
  - `**Identidad Canónica del Sistema:**`
  - `**Identidad Asignada por el Usuario:**`
  - Título/Rol en la cabecera Markdown (`# Rol — Cargo`).
- Ensambla una lista dinámica de aliases combinando la identidad canónica, el nombre asignado, sus partes individuales y los sinónimos base.
- Retorna un diccionario indexado por slot con los metadatos completos de cada agente.

### 3.2. `mapear_responsable_a_canonico(texto_responsable, identidades=None)`
Resuelve de forma robusta e insensible a mayúsculas/acentos el destinatario de un ticket o mensaje:
1. Comprobación exacta por nombre asignado o canónico.
2. Búsqueda por límites de palabra (`\b<alias>\b`) en el catálogo dinámico de aliases.
3. Fallback determinista seguro hacia `Subagente_Desarrollo` si no hay coincidencias.

### 3.3. `obtener_nombre_display(identificador, identidades=None)`
Convierte cualquier identificador canónico o clave de slot en el nombre visible asignado por el usuario para su presentación limpia en interfaces gráficas, logs o mensajes de Telegram.

### 3.4. `actualizar_nombre_asignado_en_md(slot_o_canonico, nuevo_nombre, directorio_raiz=None)`
Permite modificar programáticamente el nombre de un agente actualizando de forma atómica su archivo `_agents/agente.md`, garantizando persistencia inmediata sin requerir reinicios ni migraciones de base de datos.

### 3.5. `normalizar_texto(texto)`
Elimina marcas diacríticas, tildes y normaliza a minúsculas mediante Unicode NFD para garantizar comparaciones de texto fiables entre distintas fuentes de entrada.

---

## 4. Beneficios Arquitectónicos

- **Cero Acoplamiento:** Los scripts de herramientas y pipelines nunca asumen un nombre humano hardcodeado; siempre operan sobre las identidades canónicas.
- **Personalización Total:** El usuario puede cambiar los nombres de la flota a su conveniencia simplemente modificando `_agents/agente.md` o desde la consola web.
- **Tolerancia a Variaciones:** La Pizarra acepta tickets dirigidos tanto a nombres canónicos (`Subagente_Desarrollo`), alias populares (*Zoro*, *dev*, *programador*) o nombres asignados por el usuario.

---
**Conexiones:** [[sistema]]
