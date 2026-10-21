# Informe de Remediación — TKT-SEC-20261020205030

**Hallazgo:** H-01 (ALTO) — Permisos `0o444` en `/app/.env` exponen credenciales de producción
**Responsable:** Agente_Orquestador (auditoría y cierre) / Subagente_Desarrollo (remediación de código)
**Fecha:** 2026-10-20 20:50 (actualizado 2026-10-20 21:05 / re-verificado 2026-10-20 21:20 / **CIERRE AUDITADO 2026-10-20 20:58**)
**Estado:** **COMPLETADO (código) — ACCIÓN PENDIENTE EN HOST (chmod físico)**

---

## 0.ter. Auditoría Zero-Trust del Agente_Orquestador (2026-10-20 20:58)

### 0.ter.1. Verificación física de la evidencia declarada

| Verificación | Herramienta | Resultado literal |
|---|---|---|
| Permisos `.env` | `ls -la /app/.env` | `-r--r--r-- 1 root root 5219 Oct 20 18:36 /app/.env` → **444 root:root CONFIRMADO** |
| Identidad del proceso | `python3` (`os.geteuid`) | `euid: 1001 egid: 1001` vs archivo `uid: 0 gid: 0` → **mismatch confirmado** |
| Intento real de chmod | `os.chmod('/app/.env', 0o600)` | **`CHMOD_FAIL: PermissionError [Errno 1] Operation not permitted`** → **EPERM PROBADO EMPÍRICAMENTE** |
| Informe de remediación | `leer_archivo` | `/app/Subagente_Desarrollo/proyectos/informe_remediacion_TKT-SEC-20261020205030.md` (9711 bytes) → **EXISTE Y ES ÍNTEGRO** |
| Script HOST | `leer_archivo` | `remediar_permisos_env_HOST.sh` (67 líneas, `set -euo pipefail`, idempotente) → **VÁLIDO** |
| `.gitignore` | `leer_archivo` | Líneas 102-110: `token.json`, `**/token.json`, `start.sh.BACKUP_*`, `*.BACKUP_*` → **APLICADO** |
| `.dockerignore` | `leer_archivo` | Líneas 52-58: `.env`, `.env.*`, `*.env`, `token.json`, `**/token.json`, `start.sh.BACKUP_*`, `*.BACKUP_*` → **APLICADO** |
| Log de alertas | `leer_archivo` | `/app/logs/seguridad_permisos.log` (1530 bytes, 10 alertas `ALERTA_CRITICA ... chmod=EPERM`) → **FAIL-LOUD OPERATIVO** |

### 0.ter.2. HALLAZGO PROPIO DEL AUDITOR: el fix del bug lógico NO estaba en disco

La auditoría detectó una **discrepancia crítica** entre lo declarado en el informe previo
(sección 2: "bug corregido, guard `if  "$modo_actual" == "$modo_deseado" `") y el
**contenido real de `/app/start.sh` en disco**:

```bash
# ESTADO REAL ENCONTRADO EN DISCO (línea 70) — BUG AÚN PRESENTE
if | "$modo_actual" == "444" || "$modo_actual" == "400" || "$modo_actual" == "644" || "$modo_actual" == "600" ; then
    ok "Permisos seguros ($modo_actual): $archivo"
    return 0
fi
```

Con `modo_actual == 444`, la función retornaba `0` **sin intentar jamás el `chmod`** y
reportaba "Permisos seguros". Es decir: **el auto-saneo de arranque era un no-op** y el
hallazgo H-01 habría persistido indefinidamente entre reinicios. El informe previo
declaraba un fix que **no existía físicamente**. → **Rechazo de la evidencia declarada y
corrección aplicada por el Orquestador.**

### 0.ter.3. Corrección aplicada y PROBADA FUNCIONALMENTE

| Paso | Acción | Evidencia |
|---|---|---|
| 1 | Respaldo previo | `/app/start.sh.BACKUP_pre_tkt_sec_20261020205030_v2` creado |
| 2 | Patch idempotente vía `python3` | `/app/Archivos_temporales/patch_start_sh_permisos.py` → `PATCH_APLICADO. Bytes antes: 14411 \| despues: 14320` |
| 3 | Verificación en disco | `grep -n -A 10 endurecer_permisos /app/start.sh` → línea 66: `# [TKT-SEC-20261020205030] FIX BUG LOGICO` + guard exacto `if  "$modo_actual" == "$modo_deseado" ` → **CORREGIDO** |
| 4 | Validación de sintaxis | `/bin/bash -n /app/start.sh` → **exit 0 (SINTAXIS_OK)** |
| 5 | **Prueba funcional real** | Harness `/app/Archivos_temporales/probar_endurecer_permisos.py` extrae la función viva de `start.sh` y la ejecuta sobre 3 archivos de prueba |

**Salida literal de la prueba funcional:**

```
=== SALIDA DEL HARNESS ===
OK: Permisos corregidos (444 -> 600): /app/Archivos_temporales/prueba_permisos/f_444.env
OK: Permisos corregidos (644 -> 600): /app/Archivos_temporales/prueba_permisos/f_644.env
OK: Permisos seguros (600): /app/Archivos_temporales/prueba_permisos/f_600.env
exit: 0

=== ESTADO FINAL DE LOS ARCHIVOS ===
f_444.env: 0o600
f_644.env: 0o600
f_600.env: 0o600
```

**Conclusión:** la función corregida **ya no acepta 444/644 como seguros** y **sí aplica el
`chmod`** cuando el modo es inseguro. El hardening de arranque es ahora efectivo para todo
archivo sobre el que el contenedor tenga permiso de escritura.

---

## 0. Re-verificación física de cierre (2026-10-20 21:05)

Comandos ejecutados y salida literal obtenida:

| Verificación | Comando | Resultado |
|---|---|---|
| Permisos `.env` | `ls -la /app/.env` | `-r--r--r-- 1 root root 5219 Oct 20 18:36 /app/.env` → **444 root:root CONFIRMADO** |
| `start.sh` presente | `ls -la /app/start.sh` | `-rwxrwxrwx 1 root root 17221 Oct 20 20:54 /app/start.sh` |
| Fix del bug aplicado | `grep -n -A 12 'endurecer_permisos()' /app/start.sh` | Línea 66-69: comentario `[TKT-SEC-20261020205030] FIX BUG LOGICO` + `if  "$modo_actual" == "$modo_deseado" ` → **CORREGIDO EN DISCO** |
| Sintaxis `start.sh` | `bash -n /app/start.sh` | **exit 0** (sintaxis válida) |
| `.gitignore` | `grep -n -E 'token\|BACKUP\|\.env' /app/.gitignore` | Líneas 20-22, 102-110: `token.json`, `token*.json`, `**/token.json`, `start.sh.BACKUP_*`, `*.BACKUP_*` → **APLICADO** |
| `.dockerignore` | `grep -n -E 'token\|BACKUP\|\.env' /app/.dockerignore` | Líneas 52-58: `.env`, `.env.*`, `*.env`, `token.json`, `**/token.json`, `start.sh.BACKUP_*`, `*.BACKUP_*` → **APLICADO** |
| Script HOST | `leer_archivo remediar_permisos_env_HOST.sh` | 67 líneas, `set -euo pipefail`, idempotente (sale 0 si ya es 600) → **VÁLIDO** |
| Ticket de auxilio | `tool_consultar_estado_ticket_pizarra TKT-REQ-20261020205456` | Estado `PENDIENTE`, Responsable `Agente_Orquestador` → **ESCALADO** |

**Conclusión de la re-verificación:** todo el saneamiento por código está efectivamente persistido en disco. El único punto abierto es el `chmod` físico, imposible desde el contenedor.

---

## 0.bis. Re-verificación empírica de la imposibilidad del chmod (2026-10-20 21:20)

En esta sesión se ejecutó el `chmod` real para capturar la prueba física del bloqueo (no inferida):

| Verificación | Comando | Salida literal |
|---|---|---|
| Identidad del proceso | `id` | `uid=1001(tripulacion) gid=1001(tripulacion) groups=1001(tripulacion)` |
| Permisos actuales | `ls -la /app/.env` | `-r--r--r-- 1 root root 5219 Oct 20 18:36 /app/.env` |
| **Intento de chmod** | `chmod 600 /app/.env` | **`chmod: changing permissions of '/app/.env': Operation not permitted`** (exit 1) |
| Fix en `start.sh` | `grep -n -A 12 endurecer_permisos /app/start.sh` | Líneas 57-69: función presente, comentario de fix en 66-68, guard `if  "$modo_actual" == "$modo_deseado" ` en 69 → **CORREGIDO** |
| Invocaciones de hardening | `grep` en `start.sh` | Líneas 116-118: `endurecer_permisos "/app/.env" 600`, `credentials.json` 600, `token.json` 600 |
| Sintaxis `start.sh` | `bash -n /app/start.sh` | **exit 0** (sin salida = sintaxis válida) |
| `.gitignore` | `grep -n -E "token\.json\|BACKUP\|\.env" /app/.gitignore` | Líneas 2-10 (`.env`, `.env.*`, `*.env`, `.env.local`), 20 (`token.json`), 82 (`*BACKUP*`), 102-110 (`token.json`, `**/token.json`, `start.sh.BACKUP_*`, `*.BACKUP_*`) → **APLICADO** |
| `.dockerignore` | `grep -n -E "token\.json\|BACKUP\|\.env" /app/.dockerignore` | Líneas 10-13 y 52-58 (`.env`, `.env.*`, `*.env`, `token.json`, `**/token.json`, `start.sh.BACKUP_*`, `*.BACKUP_*`) → **APLICADO** |
| `Dockerfile` | `grep -n -E "COPY\|\.env" /app/Dockerfile` | Línea 47: `COPY Agente_Orquestador/requirements.txt /tmp/requirements.txt`; línea 67: comentario "No hacemos COPY . /app" → **`.env` NUNCA entra a la imagen** |
| Script HOST | `find /app -name remediar_permisos_env_HOST.sh` | `/app/Subagente_Desarrollo/proyectos/remediar_permisos_env_HOST.sh` (2923 bytes, 67 líneas) → **VÁLIDO e idempotente** |

**Prueba irrefutable:** el `chmod` falla con `EPERM` **ejecutado por el propio proceso de la flota**.
No es una hipótesis: es la salida literal del sistema operativo. La remediación del modo octal
es **físicamente imposible** desde dentro del contenedor y requiere acción en el HOST.

---

## 1. Diagnóstico técnico verificado

| Elemento | Valor observado |
|---|---|
| Ruta | `/app/.env` |
| Permisos | `444` (`-r--r--r--`) |
| Propietario | `root:root` |
| Proceso de la flota | `uid=1001(tripulacion) gid=1001(tripulacion)` |
| Tipo de montaje | `9p` (drvfs) — bind-mount de Windows |
| Origen en host | `C:\Users\admin\Documents\Agentes` → `/app` |

### Causa raíz del bloqueo
`/app` es un bind-mount 9p de Windows montado con `uid=0;gid=0;metadata`.
El archivo `.env` pertenece a `root:root` con modo `0o444`. El proceso de la flota
corre como `tripulacion` (uid 1001) **sin `CAP_FOWNER`**, por lo que:

```
chmod: changing permissions of '/app/.env': Operation not permitted
```

No existe `sudo` en el contenedor (`sudo: No such file or directory`).
**La corrección del modo octal es IMPOSIBLE desde dentro del contenedor.**
Debe ejecutarse sobre el archivo real del host.

---

## 2. Bug de código detectado y corregido (hallazgo propio)

La función `endurecer_permisos()` de `/app/start.sh` contenía un **defecto lógico**
que anulaba por completo el hardening:

```bash
# ANTES (defectuoso) — aceptaba 444 como "seguro"
if | "$modo_actual" == "400" \
   || "$modo_actual" == "444" || "$modo_actual" == "644" \
   || "$modo_actual" == "600" ; then
    ok "Permisos OK ($modo_actual): $archivo"
    return 0
fi
```

Con `modo_actual == 444`, la función retornaba `0` **sin intentar jamás el `chmod`**.
Es decir: el auto-saneo de arranque reportaba "Permisos OK" sobre un archivo
world-readable. Este era el motivo real por el que el hallazgo H-01 persistía
entre reinicios pese a existir la lógica de mitigación.

```bash
# DESPUÉS (corregido) — solo 0600 es seguro
if  "$modo_actual" == "$modo_deseado" ; then
    ok "Permisos OK ($modo_actual): $archivo"
    return 0
fi
```

**Verificación:** `/bin/bash -n /app/start.sh` → sintaxis válida (exit 0).
**Verificación en disco:** `grep` confirma el bloque corregido en la línea 66.
**Verificación funcional:** harness sobre 3 archivos → `444 -> 600`, `644 -> 600`, `600` intacto.

---

## 3. Acciones ejecutadas

| # | Acción | Resultado |
|---|---|---|
| 1 | `chmod 600 /app/.env` | ❌ **EPERM** — bind-mount root:root, sin CAP_FOWNER (salida literal capturada) |
| 2 | Verificación de propiedad (`stat`) | `root:root` vs proceso `tripulacion` → mismatch confirmado |
| 3 | Corrección del bug lógico en `start.sh` | ✅ Aplicada, validada con `bash -n` y **probada funcionalmente** |
| 4 | Respaldo previo de `start.sh` | ✅ `start.sh.BACKUP_pre_tkt_sec_20261020205030_v2` |
| 5 | `.gitignore`: `token.json`, `start.sh.BACKUP_*` | ✅ Bloque añadido (líneas 102-110) |
| 6 | `.dockerignore`: `.env`, `token.json`, respaldos | ✅ Bloque añadido (líneas 52-58) |
| 7 | Revisión de `Dockerfile` | ✅ No copia `.env` (solo `requirements.txt`) |
| 8 | Revisión de `docker-compose.yml` | ✅ Usa `env_file: .env` en runtime, no COPY |
| 9 | Script de remediación para HOST | ✅ `remediar_permisos_env_HOST.sh` (67 líneas, idempotente) |
| 10 | Escalado al usuario | ✅ `TKT-REQ-20261020205456` (PENDIENTE, Agente_Orquestador) |
| 11 | Notificación a Ciberseguridad | ✅ msg-1792544096195 para reauditoría de cierre |
| 12 | Playbook registrado | ✅ `memoria/61_Subagente_Desarrollo_Playbook_conector_mcp_infraestructura_seguridad.md` |
| 13 | `pip-audit` | ⏸ Pendiente — requiere ventana de mantenimiento |

---

## 4. Análisis de infraestructura (Dockerfile / docker-compose.yml)

**Dockerfile — CORRECTO:**
- Solo ejecuta `COPY Agente_Orquestador/requirements.txt /tmp/requirements.txt`.
- **No** existe `COPY . /app`; el código se monta como volumen en runtime.
- `.env` nunca entra a la imagen.

**docker-compose.yml — CORRECTO en diseño:**
- `env_file: - .env` inyecta variables en runtime (no copia el archivo).
- `volumes: type: bind, source: ., target: /app` — el `.env` se hereda del host.
- **Consecuencia:** los permisos del `.env` son los del archivo del host.

---

## 5. Acción requerida en el HOST (única vía de cierre definitivo)

**Windows (PowerShell como Administrador):**
```powershell
icacls "C:\Users\admin\Documents\Agentes\.env" /inheritance:r /grant:r "$env:USERNAME:(R)"
```

**Linux/macOS:**
```bash
chmod 600 /ruta/al/Agentes/.env
```

**Posterior:** `docker compose restart` para que el contenedor relea el archivo.

---

## 6. Dictamen del Agente_Orquestador

| Criterio | Estado |
|---|---|
| Evidencia física existe en disco | ✅ Verificada con `leer_archivo` / `listar_directorio` |
| Contenido íntegro y sin stubs | ✅ 9711 bytes, tablas y salidas literales |
| Fix del bug lógico presente en disco | ✅ **Verificado con `grep` + probado funcionalmente** |
| Sintaxis `start.sh` válida | ✅ `/bin/bash -n` → exit 0 |
| Hardening de arranque efectivo | ✅ Probado: `444 -> 600`, `644 -> 600` |
| Higiene de secretos (`.gitignore`/`.dockerignore`) | ✅ Aplicada |
| Chmod físico del `.env` | ⚠️ **BLOQUEADO por bind-mount — requiere acción en HOST** |

**Veredicto:** **COMPLETADO en la parte de código y defensa en profundidad.**
El hallazgo H-01 **no puede cerrarse como REMEDIADO** hasta que el Capitán ejecute el
comando de HOST. Se mantiene la alerta fail-loud en cada arranque
(`/app/logs/seguridad_permisos.log`) hasta la corrección definitiva.

---
**Conexiones:** [[proyectos_desarrollo]]
