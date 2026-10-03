# Documentación Técnica: `telegram_bridge.py`

**Ubicación del Script:** `Agente_Orquestador/telegram_bridge.py`  
**Rol del Módulo:** Puente de Comunicación Bidireccional con la Plataforma Telegram  
**Subsistema:** Interfaz Externa y Canales de Comunicación Remota  

---

## 1. Propósito General

`telegram_bridge.py` establece una pasarela de comunicación externa entre el usuario remoto y el ecosistema de agentes mediante la API de bots de Telegram. Permite tanto el despacho de notificaciones y reportes ejecutivos hacia el chat del usuario, como la recepción continua de instrucciones, órdenes y consultas, inyectándolas de forma asíncrona en la memoria del sistema para su atención inmediata por el Agente Orquestador.

---

## 2. Componentes y Modos de Operación

### 2.1. Despacho Saliente de Mensajes (`enviar_mensaje_telegram`)
Permite a cualquier componente del sistema o herramienta enviar una notificación directa al usuario:
- **Lectura de Credenciales:** Obtiene el token del bot (`TELEGRAM_BOT_TOKEN`) y el identificador de chat (`TELEGRAM_CHAT_ID`) desde las variables de entorno.
- **Petición HTTP a Telegram Bot API:** Realiza una solicitud POST a `https://api.telegram.org/bot<token>/sendMessage` con un tiempo de espera de 10 segundos.
- **Espejado Automático a la Consola del Dashboard:** Para garantizar la consistencia visual y de auditoría, cada mensaje emitido hacia Telegram es espejado automáticamente en `canal_usuario.json` como un mensaje del tipo `mensaje_dashboard`. De esta forma, el operador que visualiza el dashboard web observa exactamente las mismas comunicaciones enviadas al dispositivo móvil del usuario.

### 2.2. Modo Daemon Receptor (`daemon_mode`)
Bucle continuo en segundo plano diseñado para ejecutarse como un servicio autónomo:
- **Verificación de Entorno:** Valida la disponibilidad del token de Telegram antes de iniciar el ciclo; si no está configurado, finaliza de manera limpia sin generar bloqueos.
- **Sondeo Largo (*Long Polling*):** Realiza solicitudes sucesivas a `getUpdates` con un timeout de 30 segundos y control de offset secuencial para asegurar la entrega de mensajes sin duplicaciones.
- **Inyección en Memoria del Sistema:** Al capturar un mensaje de texto enviado por el usuario, invoca `publicar_mensaje` con los siguientes parámetros:
  - `de`: `"usuario"`
  - `para`: `"Agente_Orquestador"`
  - `tipo`: `"mensaje_telegram"`
  - `canal_tipo`: `"usuario"`
- El mensaje queda disponible de inmediato para que el bucle de escucha (`base_listener.py`) despierte al orquestador e inicie el procesamiento de la orden.

---

## 3. Variables de Entorno Requeridas

| Variable | Descripción | Obligatoria |
|---|---|:---:|
| `TELEGRAM_BOT_TOKEN` | Token de autenticación provisto por el BotFather de Telegram | Sí (para operación activa) |
| `TELEGRAM_CHAT_ID` | Identificador numérico único del chat o usuario destinatario | Sí (para envíos salientes) |

---

## 4. Ejecución del Servicio

El servicio puede levantarse de forma independiente en un proceso dedicado:
```bash
python Agente_Orquestador/telegram_bridge.py
```
- Registra en consola cada orden capturada y maneja reconexiones automáticas con esperas progresivas ante contingencias o pérdidas momentáneas de conectividad a internet.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
