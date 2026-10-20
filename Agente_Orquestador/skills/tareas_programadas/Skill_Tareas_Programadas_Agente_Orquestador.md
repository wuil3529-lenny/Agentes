# Skill: Gatillos Zero-Token, Sensores Python y Tareas Repetitivas (Agente Orquestador)

## 1. Propósito y Objetivo Operativo
Dotar al `Agente_Orquestador` y a toda la flota de una arquitectura de **Gatillos Reactivos de Cero Consumo de Tokens (`Zero-Token Idle`)**, **Sensores en Código Python Puro** y un **Motor de Tareas Semanales de Alta Precisión**, capaz de coordinar tareas periódicas y reactivas sin desperdiciar llamadas al LLM:
- **Regla de Oro de Eficiencia de Tokens:** Jamás se despierta a un subagente LLM periódicamente para "ir a mirar" si entró un correo nuevo, si cambió una fila en una base de datos, si llegó un webhook o si llegó la hora de una tarea programada.
- **Vigía en Python Puro (0 Tokens):** El demonio `base_listener.py` ejecuta sensores ligeros en Python puro (`gatillo_correo`, `gatillo_sql`, `gatillo_archivo`, o cualquier sensor a medida creado con `tool_crear_gatillo_sensor_python`). Mientras no ocurra el evento o no llegue el día y hora exactos, **el gasto de tokens es exactamente 0**.
- **Activación solo ante Evento o Horario Cumplido:** Únicamente cuando el gatillo detecta el evento real (ej. correo no leído, stock crítico SQL) o cuando el reloj semanal alcanza el día y hora programados sin haberse ejecutado en la sesión de hoy, se inyecta el ticket `TKT-REC-...` en `Bitacora.md` para despertar una sola vez al agente responsable con el contexto y playbook adjuntos.
- **Reloj Semanal Inteligente con Detección de Días y Cuenta Regresiva:** Administra rutinas semanales complejas (como `REC-SCOUT-001` en Computrabajo), identificando los días programados (ej. Lunes y Jueves a las 09:00), reconociendo qué día ya se ejecutó y qué día no, calculando el tiempo exacto restante en días y horas, y garantizando reposo absoluto Zero-Token tras reinicios del sistema en días no programados.

## 2. Entradas y Salidas (Esquema de Herramientas)
- **`tool_crear_gatillo_sensor_python(nombre_sensor, codigo_python_sensor, descripcion)`**
  - **Propósito:** Permite a la flota construir al vuelo un sensor `.py` de 0 tokens en `Agente_Orquestador/data/sensores/` para cualquier requerimiento nuevo o particular del usuario (APIs de terceros, bases de datos PostgreSQL/MySQL, tiendas online, webhooks, etc.).
- **`tool_programar_tarea_repetitiva(...)`**
  - **Entradas:** `nombre_tarea`, `responsable_principal`, `instrucciones_detalladas`, `tipo_activacion` (`gatillo_correo`, `gatillo_sql`, `gatillo_archivo`, `gatillo_script_python`, `reloj_programado`), `intervalo_segundos_sensor`, `hora_ejecucion`, `frecuencia_reloj` (`diaria` o `semanal`), `ruta_script_sensor`, `ruta_bd`, `consulta_sql`, `ruta_vigilada`, `condicion_notificacion`, `pipeline_secundario`, `disparar_inmediatamente`.
  - **Salida:** JSON confirmando el registro en `Agente_Orquestador/data/tareas_programadas.json`.
- **`tool_listar_tareas_repetitivas()`**
  - **Propósito:** Inspección en vivo del estado de todos los gatillos y rutinas activas o pausadas.
  - **Salida:** Lista enriquecida dinámicamente con `proxima_ejecucion`, `tiempo_restante` (en días y horas), `nombre_proximo_dia`, `dias_programados` y diagnóstico `estado_hoy` (ej. "Ya ejecutada hoy lunes. Próxima ejecución: jueves a las 09:00 (faltan 2 días y 15 horas). Modo Zero-Token Idle.").
- **`tool_modificar_estado_tarea_repetitiva(id_tarea, accion)`**
  - **Entradas:** `id_tarea` y `accion` (`pausar`, `reanudar`, `eliminar`, `disparar_ahora`).
  - **Salida:** Confirmación de actualización de estado y sincronización inmediata con la Pizarra.

## 3. Hard-Stops y Reglas de Seguridad (Zero-Trust & Zero-Token)
1. **HS-SCHED-01 (Prohibición Absoluta de Polling LLM):** Ningún subagente o modelo de lenguaje puede mantenerse en bucles de espera pasiva consumiendo tokens. Las esperas y evaluaciones periódicas deben residir exclusivamente en código Python puro dentro de `base_listener.py`.
2. **HS-SCHED-02 (Anti-Duplicado de Sesión y Reinicios):** Si una tarea semanal ya se ejecutó en la fecha actual (`hoy_ejecutado == True`), cualquier reinicio del host o contenedor en ese mismo día (o en días intermedios no programados) debe mantener el estado inerte de reposo sin generar re-disparos accidentales.
3. **HS-SCHED-03 (Anti-Solapamiento de Tickets Activos):** El despachador no puede inyectar un nuevo ticket para una tarea si ya existe un ticket previo en estado `PENDIENTE`, `EN_PROGRESO` o `PENDIENTE_REVISION` en `Bitacora.md`.
4. **HS-SCHED-04 (Sincronización Bidireccional SSOT):** `Bitacora.md` es la Fuente Única de la Verdad visual. Las modificaciones en la tabla Markdown se sincronizan de forma atómica con `tareas_programadas.json` y `dashboard/tareas_programadas.json`.

## 4. Procedimiento Operativo Paso a Paso

### 4.1. Algoritmo del Motor Semanal y Cálculo de Próxima Ejecución
1. **Extracción de Parámetros:** `_parsear_dias_semana(frecuencia)` extrae la lista numérica de días programados (0=Lunes, 3=Jueves).
2. **Verificación de Sesión Actual:** Se compara la fecha de `ultima_ejecucion` con `datetime.now().date()`.
3. **Exploración de Candidatos Futuros:** Se evalúa una ventana de 14 días:
   - Si el día coincide con hoy pero ya se ejecutó o la hora ya pasó, se descarta hoy y se avanza al siguiente día programado.
   - Se selecciona el candidato más próximo en el tiempo (`prox_dt`).
4. **Cálculo de Cuenta Regresiva:** Se calcula `(prox_dt - ahora).total_seconds()` y se convierte a formato legible (`_formatear_tiempo_restante` -> ej. "2 días y 15 horas").
5. **Comportamiento ante Reinicio de PC (Martes / Días Intermedios):**
   - Al encender la PC en un día no programado (ej. Martes `weekday=1`), el motor comprueba `dia_actual not in dias_programados`.
   - Dictamen instantáneo: `(False, "Hoy no corresponde ejecución. Próximo día: Jueves a las 09:00.")`. Consumo: **0 tokens**.

### 4.2. Playbook Operativo de Exploración y Postulación (`REC-SCOUT-001`)
Cuando el gatillo semanal se activa (Jueves a las 09:00 AM) o por comando manual del Capitán, se despacha el ticket con las 7 fases operativas:
1. **Conexión CDP / Web Browser:** Conectar a la sesión autenticada en Chrome (`http://localhost:9222`) verificando persistencia de cookies en Computrabajo.
2. **Exploración de Vacantes:** Navegar al feed reciente de ofertas en áreas objetivo (Gerencia TI, Project Management PMP, Arquitectura de Software, Cloud/DevOps).
3. **Matching Zero-Noise:** Contrastar los requisitos y tecnologías contra `memoria/Perfil_Laboral_Wuil.md`. Filtrar únicamente vacantes con afinidad $\ge 75\%$.
4. **Resolución de Killer Questions:** Completar preguntas filtro con veracidad técnica y coherencia curricular estricta.
5. **Ejecución de Postulación:** Confirmar envío del CV y validar visualmente el mensaje de confirmación de postulación en pantalla.
6. **Evidencia Física Zero-Trust:** Capturar pantalla de confirmación, emitir reporte en `Agente_Orquestador/informes/` y persistir estado en `dashboard/canal_usuario.json`.
7. **Cierre y Notificación Neural:** Actualizar `Bitacora.md` con timestamp de cierre y notificar al Capitán vía Telegram y nota de voz.

## 5. Manejo de Errores, Idempotencia y Trazabilidad
- **Persistencia de Trazabilidad:** Cada ejecución exitosa actualiza `ultima_ejecucion`, `ultimo_dia_ejecutado` y `ciclos_completados` en `tareas_programadas.json`.
- **Tolerancia a Formatos de Pizarra:** La función `sincronizar_tareas_desde_bitacora()` detecta dinámicamente si la tabla posee 7 u 8 columnas (con `Próxima Ejecución`), mapeando cabeceras de forma resiliente sin romper índices.
- **Sincronización SOC en Tiempo Real:** El archivo `dashboard/tareas_programadas.json` clasifica automáticamente las tareas en `diarias`, `semanales` y `mensuales` con campos directos para alimentar el frontend del dashboard sin conversiones complejas.

---
**Conexiones:** [[Perfil_Agente_Orquestador]]
