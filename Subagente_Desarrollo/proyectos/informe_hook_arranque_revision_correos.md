# 📄 Informe Técnico — Hook de Arranque de Flota: Revisión de Correos de Valor

**Ticket:** TKT-DEV-20261014002
**Responsable:** Subagente_Desarrollo
**Fecha:** 2026-10-14
**Estado:** COMPLETADO


---

## 1. Objetivo

Garantizar que **cada vez que se encienda el ecosistema** (contenedor Docker) se ejecute
automáticamente **una sola vez** una revisión de correos de valor en el buzón
`[CORREO_MONITOREADO]`, de forma **Zero-Token** (sin polling LLM), cumpliendo dos acciones:

1. **Reanudar** el vigilante `REC-VIGILANTED-003` si quedó `PAUSADA` tras el reinicio.
2. **Disparar** una evaluación inmediata del sensor v2.1 para detectar correos nuevos de
   valor (importantes) y notificar al usuario vía ticket en `Bitacora.md`.

---

## 2. Diagnóstico Previo

- `start.sh` original solo levantaba `base_listener.py` (Luffy) + `telegram_bridge.py`.
- **No existía** ninguna revisión de correos al arranque.
- El reinicio de la flota **pausa los vigilantes** y deja el cursor del sensor en su último
  valor persistido, por lo que sin un hook explícito la revisión no se ejecutaba al encender.

---

## 3. Arquitectura de la Solución

Se optó por la **opción más robusta y no bloqueante**: un **hook Python dedicado** que
orquesta las dos acciones y se invoca desde `start.sh` con `timeout` duro y captura de error.

```
start.sh
  ├── base_listener.py (Luffy)          [background]
  ├── telegram_bridge.py                [background]
  └── HOOK: hook_arranque_revision_correos.py   [foreground, timeout 60s, || tolerante]
        ├── (1) reanudar_tarea_si_pausada()  → REC-VIGILANTED-003 PAUSADA→ACTIVA
        ├── (2) ejecutar_sensor_v2()         → sensor_correo_imap_prioridad_v2.py (0 tokens)
        └── (3) inyectar_ticket_bitacora()   → si disparar==true → ticket Subagente_Asistencia
  └── wait -n $PID_LUFFY $BRIDGE_PID     [mantiene el contenedor vivo]
```

### ¿Por qué un hook dedicado y no `disparar_ahora` del motor de tareas?

La acción `disparar_ahora` de `tool_modificar_estado_tarea_repetitiva` **solo inyecta un
ticket genérico** ("Disparo manual forzado por el usuario") **sin ejecutar el sensor**. Por
tanto, no cumpliría el requisito de "detectar correos nuevos de valor". El hook dedicado:

- Ejecuta el **sensor v2.1 real** (Python puro, 0 tokens LLM).
- Inyecta el ticket **con los datos reales del evento** (remitente, asunto, categoría, uid).
- Reanuda la tarea manipulando el JSON de estado directamente (idempotente, sin LLM).

---

## 4. Componentes Entregados

| Componente | Ruta | Descripción |
|---|---|---|
| Hook de arranque | `/app/Subagente_Desarrollo/proyectos/hook_arranque_revision_correos.py` | Orquestador idempotente y tolerante a fallos |
| `start.sh` modificado | `/app/start.sh` | Bloque de hook insertado tras el bridge, antes de `wait -n` |
| Respaldo HS-01 | `/app/start.sh.BACKUP_pre_hook` | Copia íntegra del `start.sh` previo a la modificación |
| Informe técnico | `/app/Subagente_Desarrollo/proyectos/informe_hook_arranque_revision_correos.md` | Este documento |

---

## 5. Garantías de Robustez

1. **Zero-Token en espera:** el sensor es Python puro; no se invoca ningún LLM para vigilar.
2. **Idempotente:** re-ejecutar el hook no duplica tickets ni corrompe el estado de la tarea.
3. **Tolerante a fallos:** el hook **jamás** propaga excepción al shell (`sys.exit(0)` siempre).
   Si el sensor, IMAP o la red fallan, se registra una advertencia y el arranque continúa.
4. **No bloqueante:** `timeout 60` en `start.sh` + `TIMEOUT_SENSOR=45s` interno evitan que un
   IMAP colgado congele el arranque del contenedor.
5. **No rompe la lógica existente:** se preservan listener, bridge, `trap cleanup` y `wait -n`.
6. **Logs:** salida a `docker logs` y a `/app/logs/hook_arranque_correos.log`.

---

## 6. Pruebas Ejecutadas (5/5 PASS)

| Prueba | Descripción | Resultado |
|---|---|---|
| T1 | Reanudar tarea `PAUSADA` → `ACTIVA` | ✅ PASS |
| T2 | Inyección de ticket en `Bitacora.md` con payload simulado | ✅ PASS |
| T2b | Conexiones `Cerebro` preservadas (sin duplicar pie) | ✅ PASS |
| T3 | Idempotencia: re-ejecutar `reanudar` no altera estado | ✅ PASS |
| T4 | Tolerancia a fallos: sensor ausente → `{}` sin excepción | ✅ PASS |

**Prueba de integración en shell real** (`set -euo pipefail`): el bloque del hook se ejecuta,
retorna `HOOK_BLOCK_OK` y el arranque continúa (`ARRANQUE_CONTINUA_OK`).

**Validación sintáctica:** `bash -n /app/start.sh` → `SYNTAX_OK`.

---

## 7. Flujo de Operación al Encender la Flota

1. Docker arranca el contenedor → ejecuta `start.sh`.
2. Se levantan `base_listener.py` y `telegram_bridge.py` en background.
3. Se ejecuta el hook (una sola vez):
   - Si `REC-VIGILANTED-003` está `PAUSADA` → se marca `ACTIVA` y se recalcula `proxima_verificacion`.
   - Se ejecuta el sensor v2.1 (lectura pura, 0 tokens).
   - Si `disparar == true` → se inyecta ticket `TKT-REC-VIGILANTED-003-BOOT-<timestamp>` en
     `Bitacora.md` para `Subagente_Asistencia` con los correos de valor detectados.
4. `wait -n` mantiene el contenedor vivo; si un proceso muere, Docker reinicia según política.

---

## 8. Variables Adaptables (para reutilización)

- `TAREA_ID`: ID del vigilante a reanudar (por defecto `REC-VIGILANTED-003`).
- `RESPONSABLE`: subagente destinatario del ticket (por defecto `Subagente_Asistencia`).
- `SENSOR_V2`: ruta del sensor Python puro a ejecutar.
- `TIMEOUT_SENSOR`: timeout interno del sensor (por defecto 45s).
- `HOOK_CORREOS`: ruta del hook en `start.sh` (por defecto en `proyectos/`).

---

**Evidencia Física:**
- `/app/start.sh` (modificado con el hook)
- `/app/Subagente_Desarrollo/proyectos/hook_arranque_revision_correos.py`
- `/app/start.sh.BACKUP_pre_hook` (respaldo HS-01)

---
**Conexiones:** [[proyectos_desarrollo]]
