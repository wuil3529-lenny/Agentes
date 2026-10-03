# Documentación Técnica: `costos_tracker.py`

**Ubicación del Script:** `Agente_Orquestador/costos_tracker.py`  
**Rol del Módulo:** Rastreador de Consumo de Tokens y Control Presupuestario en Tiempo Real  
**Subsistema:** Finanzas y Gobernanza Operativa  

---

## 1. Propósito General

`costos_tracker.py` proporciona la infraestructura de telemetría financiera del sistema. Intercepta, contabiliza y persiste en tiempo real el consumo de tokens (de entrada y salida) generado por las consultas de los agentes hacia los modelos de lenguaje, traduciendo ese consumo a un gasto monetario acumulado en dólares estadounidenses (USD) que se almacena en `dashboard/costos.json`.

El script actúa como un guardián financiero capaz de bloquear preventivamente nuevas ejecuciones si se supera el presupuesto mensual establecido por el usuario.

---

## 2. Componentes y Funcionalidades Principales

### 2.1. Tabla Maestra de Tarifas (`TARIFAS_POR_1K`)
Define los costos por cada 1,000 tokens tanto para el prompt de entrada (*input*) como para la respuesta generada (*completion*):
- **DeepSeek:** Tarifas de alta eficiencia.
- **OpenAI (GPT-4o y GPT-4o-mini):** Tarifas diferenciadas por capacidad de razonamiento.
- **Google Gemini:** Tarifas de entrada/salida optimizadas.
- **NVIDIA NIM:** Tarifas estándar de inferencia acelerada.
- **Ollama / Modelos Locales:** Tarifa fija de $0.00 (sin costo financiero directo).
- **Tarifa por Defecto (*default*):** Aplica para modelos no explícitamente indexados.

### 2.2. Cálculo de Costos (`calcular_costo_llamada`)
Función matemática determinista que recibe el conteo de tokens de entrada, tokens de salida y el identificador del modelo, aplicando la fórmula:
$$\text{Costo Total} = \left(\frac{\text{Tokens Prompt}}{1000} \times \text{Tarifa In}\right) + \left(\frac{\text{Tokens Completion}}{1000} \times \text{Tarifa Out}\right)$$
El resultado se redondea a 6 cifras decimales para garantizar precisión contable.

### 2.3. Registro Concurrente y Atómico (`registrar_consumo_tokens`)
Gestiona la persistencia segura hacia el archivo `costos.json`:
- **Bloqueo por Hilo (`threading.Lock`):** Garantiza que múltiples llamadas concurrentes de distintos agentes o subprocesos no corrompan los datos.
- **Rotación Mensual Automática:** Identifica el mes calendario en curso (`YYYY-MM`). Si detecta un cambio de mes, archiva el balance previo en la sección `historial_meses` e inicializa el nuevo ciclo en ceros.
- **Escritura Atómica en Disco:** Genera un archivo temporal único con el PID del proceso y la marca de tiempo (`costos_tmp_...json`) y lo reemplaza atómicamente sobre `costos.json` para evitar escrituras a medio completar ante caídas imprevistas.
- **Normalización Canónica de Agentes:** Emplea un diccionario de normalización que agrupa el consumo bajo los cinco agentes canónicos del sistema (`agente_orquestador`, `subagente_desarrollo`, `subagente_diseno`, `subagente_ciberseguridad`, `subagente_asistencia`), admitiendo alias con total retrocompatibilidad.

### 2.4. Salvaguarda de Presupuesto (*Budget Guard*)
Evalúa constantemente el costo mensual acumulado frente a la clave `presupuesto_maximo`:
- Si el costo alcanza o supera el límite, activa la bandera `bloqueado_por_presupuesto = true`.
- Esta bandera es leída por la API del dashboard y los agentes para suspender tareas no críticas e informar al usuario inmediatamente.

### 2.5. Callback Handler para LangChain (`TokenTrackerCallbackHandler`)
Implementa un observador nativo derivado de `BaseCallbackHandler`:
- Se adjunta al objeto LLM durante su instanciación.
- En el evento `on_llm_end`, extrae automáticamente el `token_usage` (o `response_metadata`) de la respuesta del modelo y llama a `registrar_consumo_tokens` sin necesidad de instrumentar manualmente cada invocación.

---

## 3. Estructura de Datos de Persistencia (`costos.json`)

```json
{
  "mes_activo": "2026-10",
  "tokens": 427155,
  "costo": 0.060571,
  "bloqueado_por_presupuesto": false,
  "presupuesto_maximo": 100.0,
  "agentes": {
    "agente_orquestador": { "tokens": 427155, "costo": 0.060571 },
    "subagente_desarrollo": { "tokens": 0, "costo": 0.0 },
    "subagente_diseno": { "tokens": 0, "costo": 0.0 },
    "subagente_ciberseguridad": { "tokens": 0, "costo": 0.0 },
    "subagente_asistencia": { "tokens": 0, "costo": 0.0 }
  },
  "historial_meses": {
    "2026-09": { "costo": 0.321716, "tokens": 2219241 }
  }
}
```

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
