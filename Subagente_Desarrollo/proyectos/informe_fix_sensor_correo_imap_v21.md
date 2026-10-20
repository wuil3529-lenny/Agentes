# Informe Técnico: Fix del Sensor de Correos IMAP v2.1 (Anti-Re-Disparo)

**Ticket:** TKT-DEV-20261014001
**Responsable:** Subagente_Desarrollo
**Fecha:** 2026-10-14
**Evidencia Física:** `/app/Agente_Orquestador/data/sensores/sensor_correo_imap_prioridad_v2.py`

---

## 1. Causa Raíz del Bug de Re-Disparo

El sensor v2 original presentaba **3 defectos estructurales** que producían el spam de notificaciones duplicadas (patrón C001–C008):

| # | Defecto | Efecto |
|---|---------|--------|
| (a) | `candidatos = posteriores + anteriores` re-escaneaba el **backlog histórico completo** en cada ciclo | Los mismos correos no leídos volvían a entrar como candidatos cada 60s (499, 449, 399, 349 "nuevos" en ciclos consecutivos) |
| (b) | El estado `uids_procesados` crecía sin límite y era la **única barrera** anti-duplicado | Si se recortaba o reseteaba, todo el backlog re-disparaba |
| (c) | El `\Seen` y el avance del cursor `ultimo_uid_procesado` ocurrían **en el instante del escaneo**, ANTES de que Asistencia confirmara | Violaba el mecanismo solicitado por el usuario |

---

## 2. Solución Implementada (v2.1)

Se implementó el mecanismo exacto solicitado por el usuario: **un correo se marca como procesado/notificado SOLO DESPUÉS de que Asistencia lo catalogó y notificó**, y el sensor lee **únicamente los correos POSTERIORES al último UID procesado**.

### Cambios aplicados:

1. **Lectura estrictamente posterior al cursor** — Se eliminó por completo el re-escaneo del backlog (`anteriores`). El sensor solo considera `UID > ultimo_uid_procesado`.

2. **Sensor 100% de solo-lectura** — El sensor **NO marca `\Seen`** ni **avanza el cursor** por su cuenta. Un correo permanece UNSEEN y candidato hasta que Asistencia confirme. Esto elimina la ventana de desincronización entre escaneo y confirmación.

3. **Fuente única de verdad** — `correos_notificados.json` con `uids_notificados` + `ultimo_uid_procesado`. Se eliminó la dependencia del estado `uids_procesados` (y las funciones muertas `_cargar_estado`/`_guardar_estado`).

4. **Confirmación explícita (CLI `--marcar-notificado <uid...>`)** — Único punto que: agrega UIDs a `uids_notificados`, avanza el cursor al max UID confirmado, y ejecuta `store +FLAGS \Seen` en IMAP.

5. **`uids_silenciados` en el payload** — Los correos de bajo valor (promos/otros) también se reportan para que Asistencia pueda confirmarlos y el cursor avance, evitando el re-escaneo indefinido del backlog.

6. **`MAX_CORREOS` default 200** — Lote acotado por ciclo para no saturar el LLM con payloads gigantes.

---

## 3. Verificación Determinística (Zero-Trust)

Se construyó un harness que mockea el servidor IMAP y ejecuta la lógica REAL del sensor:

**Test v2.1b (`desarrollo_test_sensor_v21b.py`):**
```
[CICLO 1] disparar=True importantes=['100','102','104'] silenciados=['101','103']
[CONFIRMA] Asistencia marca notificados: ['100','102','104','101','103']
[CICLO 2] disparar=False importantes=[] (backlog drenado)
=== RESULTADO ===
TEST_V21B_PASS: backlog drenado, CERO re-disparos, cursor=104, 5 UIDs persistidos.
```

**Ejecución real end-to-end contra el buzón IMAP:**
```json
{"disparar": false, "datos_evento": {"total_unseen": 0, "total_nuevos": 0,
 "total_importantes": 0, "total_silenciados": 0, "uids_silenciados": [],
 "ultimo_uid_procesado": 0, ...}}
```

---

## 4. Archivos Entregados

| Archivo | Rol |
|---------|-----|
| `/app/Agente_Orquestador/data/sensores/sensor_correo_imap_prioridad_v2.py` | **Sensor corregido en producción (v2.1)** |
| `/app/Subagente_Desarrollo/proyectos/sensor_correo_imap_prioridad_v2_fixed.py` | Copia canónica del fix |
| `/app/Subagente_Desarrollo/proyectos/sensor_correo_imap_prioridad_v2_BACKUP_pre_fix.py` | Respaldo del original (HS-01 ZERO-LOSS) |
| `/app/Archivos_temporales/desarrollo_test_sensor_v21b.py` | Harness de verificación determinística |

---

## 5. Contrato de Integración con Subagente_Asistencia

Tras catalogar y notificar los correos, Asistencia debe invocar:
```bash
python /app/Agente_Orquestador/data/sensores/sensor_correo_imap_prioridad_v2.py \
  --marcar-notificado <uid1> <uid2> ... <uidN>
```
Incluyendo tanto los UIDs importantes como los `uids_silenciados` del payload, para avanzar el cursor y drenar el backlog.

---
**Conexiones:** [[proyectos_desarrollo]]
