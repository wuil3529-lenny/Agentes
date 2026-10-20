# Documentación Técnica: `bucle_autocorreccion.py`

**Ubicación del Script:** `Agente_Orquestador/bucle_autocorreccion.py`  
**Rol del Módulo:** Interceptor Universal de Herramientas, Filtro Anti-Bucle y Grafo de Autocorrección Cognitiva  
**Subsistema:** Motor de Resiliencia y Ejecución de la Flota Multi-Agente  

---

## 1. Propósito General

`bucle_autocorreccion.py` es el motor central de resiliencia de la tripulación. Proporciona los mecanismos de blindaje necesarios para evitar bucles infinitos, corregir en caliente las ejecuciones fallidas de herramientas y garantizar que ningún agente quede atrapado en estados de parálisis o reintentos ciegos.

El módulo opera bajo dos modalidades complementarias:
1. **Interceptor Universal de Herramientas (`interceptar_tool_call`):** Funciona como middleware transparente para agentes con bucles conversacionales directos (OpenAI Function Calling).
2. **Grafo de Estado LangGraph (`crear_grafo_agente`):** Implementa el patrón de Reflexión/LATS mediante nodos especializados de ejecución (`Nodo_Ejecutor`) y diagnóstico (`Nodo_Reflexion`).

---

## 2. Componentes y Arquitectura Interna

### 2.1. Filtro Anti-Bucle (Pilar 3: Congelamiento por Redundancia)
Previene uno de los fallos más comunes en agentes autónomos: la repetición compulsiva de la misma herramienta con argumentos idénticos tras haber obtenido datos suficientes.
- **Firma Única de Invocación:** Genera un hash determinista a partir del nombre de la herramienta y sus argumentos serializados en JSON (`nombre_tool:{"arg1": ...}`).
- **Congelamiento Inmediato:** Si una firma idéntica ya fue ejecutada con éxito en el turno, la herramienta es **congelada** sin ejecutarse de nuevo.
- **Inyección Directiva:** Devuelve un mensaje de sistema ordenando al LLM analizar los datos existentes en su contexto y proceder al cierre o generación de entregable sin volver a consultar la herramienta.

### 2.2. Clasificador de Causa Raíz de Errores (`_clasificar_error`)
Analiza los mensajes de excepción, códigos de retorno y salidas de `stderr` para identificar la causa técnica precisa del fallo e inyectar instrucciones de remediación obligatorias:

| Categoría de Error | Patrón Detectado | Instrucción de Remediación Inyectada |
| :--- | :--- | :--- |
| **Módulo Faltante** | `ModuleNotFoundError`, `ImportError` | Instruye instalar el paquete con `python_pip_instalar` antes de reejecutar. |
| **Puerto Ocupado** | `Address already in use`, `EADDRINUSE` | Instruye verificar el proceso con `netstat` y reasignar el puerto. |
| **Error de Permisos** | `Permission denied`, `PermissionError` | Instruye verificar rutas autorizadas (`proyectos/`, `Archivos_temporales/`) y permisos ACL. |
| **Archivo No Encontrado** | `FileNotFoundError`, `No such file` | Exige listar el directorio con `listar_directorio` o crear el archivo previo con `crear_archivo`. |
| **Error de Sintaxis** | `SyntaxError`, `IndentationError` | Exige leer el traceback completo, identificar la línea exacta y reescribir con `crear_archivo`. |
| **Timeout de Ejecución** | `timed out`, `timeout` | Recomienda simplificar el comando, verificar red o ajustar umbrales. |
| **JSON Inválido** | `JSONDecodeError`, `invalid json` | Exige inspeccionar la sintaxis con `leer_archivo` y corregir delimitadores. |
| **Servicio No Disponible** | `Connection refused`, `ECONNREFUSED` | Recomienda verificar el servicio (ej. `n8n_iniciar()`) y esperar confirmación de healthcheck. |
| **Fallo Genérico (Exit Code != 0)** | Código de salida distinto de 0 | Protocolo de auto-diagnóstico en 4 pasos obligando a leer el traceback completo. |

### 2.3. Doble Validación QA Gherkin Integrada
El interceptor conecta directamente con [`Agente_Orquestador/qa_gherkin.py`](file:///c:/Users/admin/Documents/Agentes/Agente_Orquestador/qa_gherkin.py) para evaluar herramientas críticas (`crear_archivo`, `ejecutar_comando`, `python_ejecutar_script`, `git_commit`, etc.):
- **Capa 1 (Infraestructura):** Comprueba que no existan bloqueos de red, timeouts o códigos de retorno erróneos.
- **Capa 2 (Contenido):** Verifica que el resultado no sea un stub vacío o un payload insuficiente para los objetivos del ticket.

### 2.4. Control de Reintentos y Escalado Automático
- **Contador por Herramienta:** Mantiene un registro granular de reintentos fallidos (`conteo_fallos`).
- **Umbral de Escalado:** Si una herramienta falla de forma consecutiva tras 3 intentos (`max_reintentos = 3`), el interceptor emite una alerta crítica ordenando al agente escalar el ticket de inmediato al `Agente_Orquestador` junto con el historial de errores.

---

## 3. Integración en la Flota de Agentes

El interceptor se encuentra integrado de forma universal en los 5 agentes de la tripulación en su bucle de despacho de herramientas (`_procesar_tool_calls` o `ejecutar_ciclo`):
- `Agente_Orquestador/agente_orquestador_agent.py`
- `Subagente_Desarrollo/subagente_desarrollo_agent.py`
- `Subagente_Diseno/subagente_diseno_agent.py`
- `Subagente_Ciberseguridad/subagente_ciberseguridad_agent.py`
- `Subagente_Asistencia/subagente_asistencia_agent.py`

```python
# Patrón de invocación canónico
from bucle_autocorreccion import interceptar_tool_call

contenido_tool, es_exito, firma = interceptar_tool_call(
    nombre_tool=nombre_tool,
    args_tool=args_tool,
    func_ejecutar=ejecutar_tool_local,
    objetivo_ticket=ticket_info,
    nombre_agente="Subagente_Desarrollo",
    historial_firmas=historial_firmas,
    conteo_fallos=conteo_fallos,
    max_reintentos=3
)
```

---

## 4. Retorno y Salidas

La función `interceptar_tool_call` retorna una tupla estructurada:
- `contenido_salida (str)`: El resultado de la herramienta (si tuvo éxito) o la instrucción guiada de autocorrección (si falló o fue congelada).
- `es_exito (bool)`: `True` si pasó todas las validaciones; `False` si fue congelada por anti-bucle o reprobada por errores/QA Gherkin.
- `firma (str)`: Identificador canónico `nombre_tool:json_args` para alimentar el historial del turno.

---
**Conexiones:** [[sistema]]
