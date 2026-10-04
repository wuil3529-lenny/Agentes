# Documentación Técnica: `agente_orquestador_agent.py`

**Ubicación del Script:** `Agente_Orquestador/agente_orquestador_agent.py`  
**Rol del Módulo:** Script Principal de Ejecución y Orquestación Cognitiva  
**Subsistema:** Agente Orquestador  

---

## 1. Propósito General

`agente_orquestador_agent.py` constituye el punto de entrada ejecutable del Agente Orquestador. Su función principal es inicializar el modelo de lenguaje de acuerdo con las variables de entorno, cargar la identidad base del agente, vincular el conjunto de herramientas estratégicas autorizadas y gestionar el ciclo de invocación conversacional y operativa.

El script implementa una arquitectura modular que previene la sobrecarga de contexto mediante la inyección bajo demanda de directivas especializadas en cada etapa del razonamiento.

---

## 2. Componentes y Arquitectura Interna

### 2.1. Carga de Identidad Base y Configuración
El script prescinde de prompts cableados en código. Al inicializarse:
- Localiza y carga el archivo canónico `_agents/agente.md` (o su homólogo `.agents/agente.md`).
- Extrae la directiva maestra de comportamiento, paradas duras (*hard-stops*), topología del sistema y pautas de relación con el usuario.

### 2.2. Factoría del Modelo de Lenguaje (`crear_llm`)
Configura la instancia de inferencia mediante LangChain (`ChatOpenAI`):
- **Soporte Multi-Proveedor:** Lee las credenciales y modelos configurados en el archivo `.env` para proveedores como OpenAI, DeepSeek, NVIDIA NIM u Ollama local.
- **Rastreo Financiero Automático:** Vincula en el parámetro `callbacks` la clase `TokenTrackerCallbackHandler`, asegurando que cada inferencia registre sus tokens de entrada y salida en el subsistema de costos.
- **Parámetros de Inferencia:** Configura valores de temperatura y límites de tokens adecuados para razonamiento estratégico y toma de decisiones deterministas.

### 2.3. Mecanismo de Inyección de Prompts Bajo Demanda
Para evitar la saturación del contexto con directivas masivas, el script implementa funciones de extracción dinámica que recuperan los system prompts especializados únicamente cuando el orquestador entra en un modo específico:
- **Modo Entrevista:** Inyecta las pautas conductuales para formular preguntas aclaratorias cuando un objetivo de usuario es ambiguo o incompleto.
- **Modo Planificación:** Inyecta las directivas para formular planes de implementación estructurados con estimación de recursos y división de fases.
- **Modo Refinamiento:** Provee los criterios de viabilidad técnica y análisis de riesgos para validar requerimientos.
- **Modo Supervisión y Control de Calidad:** Aplica las reglas de verificación de entregables, cumplimiento de formatos y aprobación de misiones.
- **Modo Sentry / Observabilidad:** Inyecta pautas para la inspección y diagnóstico de trazas de error reportadas por los subagentes.
- **Modo Auto-Aprendizaje y Playbooks:** Inyecta directivas del Paso 0 (consulta obligatoria de antecedentes para ejecución One-Shot) y Paso Final (registro procedural de playbooks pioneros).

### 2.4. Caja de Herramientas Canónicas
El script expone y vincula al LLM las herramientas operativas de su dominio:
- **Investigación Web:** Búsqueda en internet para documentar tecnologías, arquitecturas y librerías durante la fase de análisis.
- **Inspección de Workspace:** Comandos para listar directorios, inspeccionar archivos del proyecto y localizar patrones de código (`grep`).
- **Gestión de Memoria y Pizarra:** Creación de tickets en la Bitácora, registro de conocimiento consolidado en el Cerebro y comunicación por canales internos.
- **Notificaciones Externas:** Envío de mensajes ejecutivos hacia la interfaz de usuario y Telegram.
- **Auto-Aprendizaje y Playbooks:** Consulta (`tool_consultar_playbook_memoria`) y registro (`tool_registrar_playbook_memoria`) de recetas procedurales en `memoria/` y ChromaDB.

---

## 3. Modos de Ejecución

1. **Modo Directo / CLI:** Permite ejecutar consultas interactivas o tareas de prueba en consola mediante la bandera `--prompt` o un bucle de diálogo continuo.
2. **Modo Función de Nodo (`funcion_nodo_agente_orquestador`):** Función exportada para su integración en grafos de orquestación (LangGraph) o para ser invocada por el daemon de escucha ante la presencia de un ticket asignado.

---

## 4. Entradas y Salidas

- **Entradas:** Mensajes del usuario (canal directo o Telegram), estado de la Bitácora central, historial conversacional comprimido y parámetros del ticket en procesamiento.
- **Salidas:** Ejecución de herramientas locales, formulación de planes de implementación, tickets de delegación estructurados en la Bitácora o respuestas directas al usuario.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
