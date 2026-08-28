# Bot-Bitcoin-N8N
**Última Actualización:** 2026-08-27 03:19:36
**Contexto Origen:** CTX-20260827022941

---

# PLAN: Bot de Bitcoin con n8n

## Contexto
El Capitán quiere un bot automatizado que lea el precio de Bitcoin cada hora y envíe un informe diario por Telegram a las 6:00pm (hora de Caracas, Venezuela). El informe debe incluir:
- Máximo y mínimo del día
- Comparativa con el día anterior
- Comparativa Bitcoin vs USD con porcentaje de cambio

Se usará una API gratuita para obtener el precio de Bitcoin.

---

## FASE 1: Diseño y Arquitectura del Flujo n8n
**Responsable:** Robin
**Dependencias:** Ninguna

- Diseñar el blueprint del flujo n8n (nodos, triggers, conexiones).
- Definir el esquema de datos del informe (máximo, mínimo, comparativa, % cambio).
- Documentar la arquitectura del workflow.

---

## FASE 2: Configuración del Entorno n8n
**Responsable:** Zoro
**Dependencias:** Fase 1

- Instalar/configurar n8n (local o Docker).
- Configurar credenciales de Telegram (bot token y chat ID).
- Verificar acceso a la API gratuita de Bitcoin (ej. CoinGecko, CoinDesk, Binance).

---

## FASE 3: Construcción del Workflow n8n
**Responsable:** Zoro
**Dependencias:** Fase 2

- Nodo Schedule Trigger: ejecución cada hora (lectura de precio).
- Nodo HTTP Request: consulta a la API gratuita de Bitcoin.
- Nodo Function/Code: cálculo de máximo, mínimo, comparativa vs día anterior y % de cambio.
- Nodo de almacenamiento de datos históricos (para comparativa diaria).
- Nodo Telegram: envío del informe a las 6:00pm hora de Caracas (timezone America/Caracas).

---

## FASE 4: Pruebas y Validación
**Responsable:** Zoro
**Dependencias:** Fase 3

- Probar el flujo con datos reales de la API.
- Validar el formato y contenido del informe en Telegram.
- Verificar el horario de ejecución (6:00pm Caracas).
- Probar casos borde (API caída, datos nulos, etc.).

---

## FASE 5: Despliegue y Documentación
**Responsable:** Sanji
**Dependencias:** Fase 4

- Documentar el proceso de despliegue (Docker, credenciales, variables de entorno).
- Crear guía de mantenimiento y troubleshooting.
- Entregar manual de uso al Capitán.

---

## Criterios de Aceptación
- El bot envía informe diario por Telegram a las 6:00pm hora de Caracas.
- El informe incluye máximo, mínimo del día, comparativa vs día anterior y % de cambio BTC/USD.
- El flujo usa una API gratuita.
- El sistema tolera fallos de API sin romper el flujo.
- Documentación completa entregada.
