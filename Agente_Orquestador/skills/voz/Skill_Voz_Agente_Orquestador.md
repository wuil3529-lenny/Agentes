# Skill: Sistema de Voz Bidireccional, Cornetas y Notas de Voz (Agente Orquestador)

## 1. Propósito y Objetivo Operativo
Dotar al `Agente_Orquestador` de un sistema de voz integral que opera en tres modalidades complementarias:
1. **Comunicación en Vivo por Consola (Micrófono + Cornetas de la PC):** Captura la voz del usuario desde el micrófono de la computadora con corte automático por silencio (VAD), la transcribe a texto en español y reproduce la respuesta del `Agente_Orquestador` directamente por las cornetas (altavoces) de la computadora.
2. **Notas de Voz en la Consola:** Permite al usuario grabar y enviar notas de voz desde la interfaz de consola y recibir respuestas del `Agente_Orquestador` con reproductor de audio integrado (`audio_url`).
3. **Notas de Voz en Telegram Bidireccionales:** Recibe y transcribe automáticamente cualquier nota de voz (`voice`/`audio`) que el usuario envíe al bot de Telegram, y permite al `Agente_Orquestador` enviar notas de voz nativas (`sendVoice` en formato `.ogg` Opus / `.mp3`) de vuelta a Telegram.

## 2. Entradas y Salidas (Esquema de Herramientas)
- **`tool_enviar_nota_voz(mensaje_a_hablar, destino, reproducir_en_cornetas)`**
  - **Entradas:** Texto a sintetizar, `destino` (`'telegram'`, `'consola'`, `'ambos'`) y booleano `reproducir_en_cornetas`.
  - **Salida:** JSON con la URL del archivo de audio generado (`/static/notas_voz/...`) y confirmación de entrega en Telegram/Consola.
- **`tool_hablar_por_cornetas(mensaje)`**
  - **Entradas:** Texto que el `Agente_Orquestador` pronunciará por los altavoces físicos de la computadora.
  - **Salida:** JSON confirmando la reproducción por las cornetas de la PC.
- **`tool_escuchar_microfono(duracion_max_segundos)`**
  - **Entradas:** Duración máxima de escucha en segundos.
  - **Salida:** JSON con el texto transcrito desde el micrófono de la PC y la ruta del archivo `.wav` grabado.

## 3. Hard-Stops y Reglas de Calidad
1. **Limpieza Fonética Automática:** Antes de sintetizar voz, se filtran bloques de código, rutas largas y símbolos Markdown para que la locución sea natural y clara.
2. **Triple Fallback de Síntesis (TTS):** Utiliza `edge-tts` (voz neural `es-MX-JorgeNeural`) como motor principal, con conmutación automática a `gTTS` y a `pyttsx3` (SAPI5 local de Windows) si no hay conexión.
3. **Control de Concurrencia en Altavoces:** Uso de candado de hilo (`_SPEAKER_LOCK`) para evitar que dos locuciones suenen solapadas en las cornetas de la PC.

---
**Conexiones:** [[Perfil_Agente_Orquestador]]
