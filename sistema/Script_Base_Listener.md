# Documentación Técnica: `base_listener.py`

**Ubicación del Script:** `Agente_Orquestador/base_listener.py`  
**Rol del Módulo:** Daemon Central de Escucha, Arbitraje de Timeouts y Auditoría Zero-Trust  
**Subsistema:** Motor de Ejecución de la Flota Multi-Agente  

---

## 1. Propósito General

`base_listener.py` es la columna vertebral operativa del ecosistema multi-agente. Funciona como un servicio continuo en segundo plano (*daemon*) encargado de vigilar la Bitácora central (`Bitacora.md`) y los canales de mensajería, arbitrar el ciclo de vida de los agentes, invocar subagentes efímeros bajo demanda y validar de forma estricta e inviolable que cada tarea reportada como finalizada cuente con evidencia física verificable en el disco.

---

## 2. Mecanismos Clave y Arquitectura Interna

### 2.1. Bucle de Escucha Continua e Inspección de Pizarra
El listener ejecuta un bucle de escaneo a intervalos configurables:
- **Parseo de Tickets:** Analiza el contenido de `Bitacora.md` mediante expresiones regulares especializadas para extraer bloques estructurados con formato `## TKT-[AGENTE]-[TIMESTAMP]`.
- **Detección de Asignaciones:** Identifica tickets en estados accionables (`PENDIENTE`, `ESPERANDO_CORRECCION`, `NUEVO`) dirigidos al agente supervisado.
- **Detección de Mensajes de Usuario:** En el caso del Agente Orquestador, monitorea también el buzón de entrada del usuario (`canal_usuario.json`) para activar el modo de planificación ante nuevas solicitudes.

### 2.2. Auditoría Zero-Trust de Evidencia Física
Para evitar que un agente reporte falsamente la culminación de una tarea sin haber generado el entregable real, el script implementa la función `auditar_evidencia`:
1. **Comprobación de Existencia:** Verifica que las rutas declaradas en el campo `Evidencia_Fisica` existan físicamente en el sistema de archivos del host o dentro del contenedor Docker.
2. **Comprobación Temporal de Modificación:** Si el turno tiene una hora de inicio registrada, verifica que la marca de tiempo de modificación (`mtime`) del archivo sea posterior a la hora de asignación del ticket. Archivos preexistentes no modificados en el turno son rechazados.
3. **Requisito de Descripción Concreta:** Exige que el JSON de respuesta contenga el campo `evidencia_hallazgo` con una descripción no vacía de las acciones realizadas. Si la evidencia falla, el ticket se mantiene en `PENDIENTE` con un mensaje correctivo.

### 2.3. Árbitro de Timeout y Auto-Cura
Para neutralizar bloqueos, cuelgues o bucles infinitos en ejecuciones prolongadas:
- **Monitoreo de Tiempo Límite:** Registra la hora de inicio de procesamiento de cada ticket. Si el tiempo de ejecución supera el umbral máximo permitido (configurable por variable de entorno o por defecto), el árbitro interviene.
- **Liberación Forzada:** Cancela el proceso colgado, redacta una lección aprendida documentando el fallo en el historial del ticket y devuelve el control al orquestador o reasigna el ticket.

### 2.4. Sanitización y Transformación de Rutas (Docker `/app/`)
Dada la coexistencia de entornos de desarrollo en Windows y contenedores de ejecución en Linux/Docker:
- Implementa la función `transformar_rutas_windows`, la cual detecta rutas absolutas de Windows (ej. `C:\Users\admin\...`) y las traduce transparentemente a rutas absolutas del contenedor (`/app/...`).
- Garantiza que los agentes operen bajo un sistema de archivos estándar unificado sin importar el sistema operativo del host.

### 2.5. Parser Robusto de JSON en 4 Fases
Los modelos de lenguaje pueden generar ocasionalmente markdown decorativo o llaves desbalanceadas. El listener procesa las respuestas del LLM a través de un parser resiliente:
1. Intento de parseo directo con `json.loads`.
2. Extracción de bloques de código delimitados por triple tilde (` ```json ... ``` `).
3. Localización del primer carácter `{` y el último `}` para aislar el objeto JSON.
4. Algoritmo heurístico de balanceo automático de comillas y llaves de cierre para reparar respuestas truncadas.

### 2.6. Despacho y Ciclo de Vida de Subagentes On-Demand
Cuando un ticket requiere la intervención de un subagente especializado (Desarrollo, Diseño, Ciberseguridad o Asistencia):
- Despacha un subproceso (`subprocess.Popen`) ejecutando el script del agente respectivo con el ID de ticket efímero.
- Supervisa la salida en tiempo real, controla tiempos máximos de ejecución y asegura la terminación limpia de recursos al concluir la tarea.

---

## 3. Interfaces y Parámetros CLI

El script se invoca principalmente mediante la línea de comandos:
- `--agente`: Especifica el nombre canónico del agente que debe ejecutar el bucle de escucha (ej. `Agente_Orquestador`).
- `--ticket`: (Opcional) Especifica un ID de ticket único para procesamiento efímero inmediato, finalizando tras su resolución.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
