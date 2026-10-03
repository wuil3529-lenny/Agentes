# Documentación Técnica: `nim_client.py`

**Ubicación del Script:** `Agente_Orquestador/nim_client.py`  
**Rol del Módulo:** Cliente de Inferencia Resiliente con Reintentos y Conmutación por Fallo (*Fallback*)  
**Subsistema:** Motor de Conectividad con Modelos de Lenguaje  

---

## 1. Propósito General

`nim_client.py` proporciona una capa de abstracción para la ejecución de inferencias hacia la API de NVIDIA NIM (o endpoints compatibles con la API de OpenAI, tales como DeepSeek). Su objetivo es garantizar la resiliencia en las llamadas a los modelos de lenguaje, implementando reintentos exponenciales automáticos y conmutación transparente a un modelo de respaldo cuando el modelo principal no responde o experimenta fallos de servicio.

El módulo integra de manera nativa la notificación de consumo de tokens hacia el subsistema de rastreo financiero.

---

## 2. Componentes y Flujo Operativo (`call_nim_with_fallback`)

La función central del módulo recibe las credenciales, el modelo principal (`model_1`), el modelo alternativo (`model_2`), el prompt del usuario, el system prompt opcional y el identificador del agente que realiza la consulta:

```python
call_nim_with_fallback(api_key, model_1, model_2, prompt, system_prompt="", agente="agente_orquestador")
```

### 2.1. Selección Dinámica de Endpoint Base
El cliente analiza el identificador del modelo solicitado:
- Si el nombre del modelo contiene la cadena `"deepseek"`, enruta la solicitud hacia `https://api.deepseek.com/v1`.
- Para otros modelos soportados, utiliza la pasarela de inferencia acelerada `https://integrate.api.nvidia.com/v1`.

### 2.2. Política de Reintentos Exponenciales (Modelo 1)
- Ejecuta hasta **3 intentos consecutivos** sobre el modelo principal.
- Si una llamada genera una excepción de red, timeout (configurado en 30 segundos) o error de API, el cliente calcula una espera exponencial ($2^{\text{intento}}$ segundos) antes de reintentar.
- Si la llamada es exitosa, procesa la respuesta y finaliza el flujo sin recurrir al modelo de respaldo.

### 2.3. Conmutación por Fallo (*Fallback Logic* - Modelo 2)
- Si los 3 intentos con el modelo principal se agotan sin éxito, el cliente emite una alerta en los registros del sistema e inicia de forma inmediata la solicitud sobre el modelo secundario (`model_2`).
- Esta conmutación asegura que procesos de misión crítica no queden interrumpidos por incidencias puntuales de infraestructura del proveedor primario.

### 2.4. Telemetría y Contabilidad de Tokens
Tanto en la ejecución del modelo principal como en la del modelo de respaldo:
- El cliente inspecciona la propiedad `response.usage` de la respuesta devuelta por el servidor.
- Extrae con precisión los `prompt_tokens` y `completion_tokens`.
- Invoca la función `registrar_consumo_tokens` del módulo `costos_tracker`, atribuyendo el gasto directamente al agente invocador correspondiente.

---

## 3. Entradas, Salidas y Manejo de Errores

- **Entradas:** Clave de API válida, identificadores de modelos primario y secundario, mensajes estructurados de sistema y usuario, y nombre del agente.
- **Salidas:** Cadena de texto con el contenido generado por el modelo de lenguaje (`response.choices[0].message.content`).
- **Manejo de Errores:** En caso de falla catastrófica de ambos modelos o credenciales no configuradas, emite advertencias detalladas en consola y retorna de manera segura `None`, permitiendo que las capas superiores gestionen la contingencia sin interrupción abrupta del proceso.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
