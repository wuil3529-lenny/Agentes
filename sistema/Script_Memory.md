# Documentación Técnica: `memory.py`

**Ubicación del Script:** `Agente_Orquestador/memory.py`  
**Rol del Módulo:** Motor de Memoria Compartida, Canales de Comunicación y Persistencia  
**Subsistema:** Memoria y Almacenamiento Central  

---

## 1. Propósito General

`memory.py` gestiona los mecanismos de persistencia compartida y comunicación que permiten la interoperabilidad entre el Agente Orquestador, los subagentes y el usuario. Coordina el flujo de información a través de tres pilares arquitectónicos claramente diferenciados:
1. **Pilar Canal (JSON):** Comunicación y recepción de órdenes del usuario y coordinación libre.
2. **Pilar Bitácora (Markdown):** Tablero central de tareas (*Blackboard*) para asignación, seguimiento y transición de tickets.
3. **Pilar Cerebro (Bóveda Markdown + RAG):** Registro inmutable de conocimiento a largo plazo para misiones culminadas con éxito.

---

## 2. Arquitectura de los Tres Pilares

### 2.1. Pilar Canal: Mensajería y Compresión Rodante
- **Publicación y Lectura de Mensajes:** Funciones `publicar_mensaje` y `leer_mensajes` que gestionan el archivo `canal_usuario.json`. Permite el marcado de mensajes leídos mediante arreglos de confirmación (`leido_por`).
- **Compresión Rodante del Contexto de Usuario (`construir_contexto_canal_usuario`):**
  - Aplica un presupuesto controlado de tokens (~3,500 tokens / 14,000 caracteres) para el historial que se inyecta al orquestador.
  - Divide la conversación en dos segmentos:
    - *Mensajes Recientes:* Conservados de manera textual íntegra palabra por palabra.
    - *Mensajes Antiguos:* Comprimidos automáticamente en un resumen ejecutivo cronológico que preserva únicamente las órdenes del usuario y los resultados finales de las misiones.

### 2.2. Pilar Bitácora: Tablero de Tareas (*Blackboard*)
- **Creación de Tickets (`crear_ticket_bitacora`):** Genera bloques estructurados con identificadores únicos (`TKT-[UUID]`), marcando timestamp, tarea, responsable y estado inicial `PENDIENTE`.
- **Actualización de Tickets (`actualizar_ticket_bitacora`):** Modifica el estado de un ticket existente (`EN_PROGRESO`, `PENDIENTE_REVISION`, `CERRADO`) sin destruir el contexto ni las notas previas de ejecución.
- **Historial de Auditoría:** Mantiene la trazabilidad de intentos, diagnósticos y evidencias físicas requeridas por el auditor del sistema.

### 2.3. Pilar Cerebro: Memoria de Largo Plazo
- **Registro de Soluciones Exitosas (`guardar_cerebro`):**
  - Solo se invoca cuando una misión ha alcanzado el estado `CERRADO`.
  - Genera un archivo Markdown dedicado dentro del directorio `memoria/` con el Recibo Ejecutivo de Misión.
  - El recibo estructura: agentes involucrados, herramientas utilizadas, ruta de evidencia física validada y decisiones clave adoptadas.
  - Agrega la entrada correspondiente al índice central `Cerebro.md`.

---

## 3. Cargador Central de Perfiles (`cargar_perfil_agente`)

El script centraliza la lectura de identidades de los agentes:
- **Prioridad Canónica:** Comprueba prioritariamente la existencia de `agente.md` en los directorios `_agents` o `.agents` de cada agente.
- **Formato Estructurado:** Retorna un diccionario con el nombre canónico y la presentación completa del agente lista para ser utilizada como system prompt.
- **Fallback Retrocompatible:** En caso de no existir `agente.md`, inspecciona archivos `*_perfil.json` para garantizar estabilidad operativa durante fases de migración.

---

## 4. Funciones Auxiliares de Consulta

- `leer_nodo_obsidian(ruta_relativa)`: Lee archivos Markdown de la memoria compartida o protocolos, asegurando la extensión `.md`.
- `leer_turno()`: Provee la estructura básica de control de turno orientada a orquestación on-demand.
- `limpiar_canal_mensajes()`: Utilidad de mantenimiento para depurar mensajes antiguos ya procesados.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
