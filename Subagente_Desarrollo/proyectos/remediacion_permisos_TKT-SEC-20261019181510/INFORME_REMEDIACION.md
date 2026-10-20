# Informe de Remediación — TKT-SEC-20261019181510 (H-01, H-02)

**Revisión:** 4 (CIERRE DEFINITIVO)
**Fecha:** 2026-10-19 18:35
**Responsable:** Subagente_Desarrollo
**Estado:** ✅ COMPLETADO — 5/5 objetivos verificados en disco

---

## 1. Resumen Ejecutivo

La remediación de permisos `0o777` sobre `.env` y credenciales OAuth queda **cerrada al 100%**.
El objetivo que permanecía bloqueado en la rev.3 (`chmod 700 /app/Agente_Orquestador/data/`) fue
**atendido por el escalado `TKT-REQ-20261019182237`** ejecutado con uid 0, y su resultado fue
**verificado empíricamente en disco** en esta revisión.

---

## 2. Estado Final Verificado en Disco (evidencia física)

| # | Objetivo | Estado esperado | Estado real | Resultado |
|---|----------|-----------------|-------------|-----------|
| 1 | `/app/.env` | `0600` | `600 tripulacion:tripulacion` (4367 bytes) | ✅ PASS |
| 2 | `data/credentials.json` | `0600` | `600 tripulacion:tripulacion` | ✅ PASS |
| 3 | `data/token.json` | `0600` | `600 tripulacion:tripulacion` | ✅ PASS |
| 4 | `umask 077` en `/app/start.sh` | presente | línea 26, `bash -n` rc=0 | ✅ PASS |
| 5 | `/app/Agente_Orquestador/data/` | `0700` | `700 tripulacion:tripulacion` | ✅ PASS |

**Subdirectorios verificados:**
- `data/chroma_db/` → `700 tripulacion:tripulacion` ✅
- `data/sensores/` → `700 tripulacion:tripulacion` ✅

**Barrido de residuos `0777`:** `find /app/Agente_Orquestador/data -perm 777` → **0 resultados**.
No queda ningún inodo con permisos mundiales dentro del árbol de datos.

---

## 3. Verificación de Integridad de Datos (HS-01 ZERO-LOSS)

| Comprobación | Resultado |
|--------------|-----------|
| Asignaciones en `/app/.env` | **57** (idéntico al valor pre-remediación) |
| `credentials.json` parseable como JSON | ✅ OK |
| `token.json` parseable como JSON | ✅ OK |
| `tareas_programadas.json` parseable como JSON | ✅ OK |
| Entradas en `data/` | **8** (chroma_db, credentials.json, docs_temp_id.txt, inbox_report_doc_id.txt, sensores, tareas_programadas.json, telegram_last_update.txt, token.json) |
| Residuos de prueba (`data.tmp_swap_*`) | **0** — purgados |
| Archivos renombrados en pruebas | restaurados a su nombre original |

**Conclusión:** cero pérdida de datos. Ningún archivo fue eliminado ni alterado en contenido;
solo se modificaron bits de permiso.

---

## 4. Causa Raíz y Matriz de Capacidades del Driver (rev.3, vigente)

El entorno `/app` reside en un **bind-mount 9p/drvfs sobre C:\ de Windows**. La matriz de 10 pruebas
aisladas de la rev.3 estableció la regla real del driver:

- **(a)** `chmod` sobre inodo ajeno (`root:root`) → **EPERM siempre** (requiere owner o `CAP_FOWNER`).
- **(b)** `chmod` sobre inodo propio → **PERMITIDO**.
- **(c)** `rename` de un **ARCHIVO** `root:root` en directorio escribible → **PERMITIDO**.
- **(d)** `rename` de un **DIRECTORIO** `root:root` → **EACCES siempre**, aunque el padre sea `0777`.

**Consecuencia:** `chmod 700 data/` era inalcanzable desde uid 1001 por cualquier vía → requería
**uid 0 inexorablemente**. Esto motivó el escalado `TKT-REQ-20261019182237`, ahora resuelto.

---

## 5. Mitigación Compensatoria Permanente

`umask 077` en `/app/start.sh` (línea 26) garantiza que **todo artefacto nuevo** creado por la flota
(tokens refrescados, logs, `.env` regenerados, archivos de estado) nazca en `0600`/`0700`.
Backup del original: `/app/Archivos_temporales/desarrollo_start.sh.bak_20261019`.

---

## 6. Recomendación Estructural (no bloqueante)

Migrar `/app` a un **volumen Docker nativo (ext4/overlayfs)** donde los permisos POSIX sean reales y
persistentes. En bind-mount Windows los `chmod` de build-time no persisten, por lo que cualquier
corrección debe reaplicarse en el entrypoint en cada arranque. El script `remediar_permisos_root.sh`
es idempotente y apto para invocarse desde el entrypoint con uid 0.

---

## 7. Entregables

| Archivo | Descripción |
|---------|-------------|
| `remediar_permisos_root.sh` | Script de cierre idempotente (valida uid 0, backup HS-01, verificación PASS/FAIL) |
| `INFORME_REMEDIACION.md` | Este informe técnico (rev.4) |
| `/app/.env` | Remediado a `600` |
| `/app/start.sh` | Parcheado con `umask 077` |
| `/app/Archivos_temporales/desarrollo_start.sh.bak_20261019` | Backup del `start.sh` original |

**Receta RAG:** `SOL-Subagente_Desarrollo-CCE22C14` (matriz de capacidades del driver 9p/drvfs).

---
**Conexiones:** [[proyectos_desarrollo]]
