# Informe de Remediación — TKT-SEC-20261020190613

**Hallazgo:** H-01 (ALTO) — Permisos `0o777` en `/app/.env` exponen credenciales de toda la flota
**Responsable:** Subagente_Desarrollo
**Fecha:** 2026-10-20 20:20
**Estado:** BLOQUEADO — requiere acción en el HOST (bloqueante externo estructural)

---

## 1. Diagnóstico Técnico (Causa Raíz — CORREGIDA en Intento 3)

> **Corrección importante:** el diagnóstico de los intentos 1 y 2 atribuía el bloqueo a un
> *bind-mount de Docker*. La verificación física real demuestra que el entorno es **WSL2 con
> montaje 9p/drvfs**, lo cual es aún más restrictivo. Se documenta la evidencia cruda.

### 1.1 Evidencia física recolectada

```
$ stat -c '%a %U:%G %n' /app/.env
777 root:root /app/.env

$ id
uid=1001(tripulacion) gid=1001(tripulacion) groups=1001(tripulacion)

$ grep -E ' /app ' /proc/mounts
C:\134 /app 9p rw,noatime,aname=drvfs;path=C:\;uid=0;gid=0;metadata;symlinkroot=/mnt/host/,cache=0x5,access=client,msize=65536,trans=fd,rfd=5,wfd=5 0 0

$ grep -E 'CapEff|CapBnd' /proc/self/status
CapEff: 0000000000000000
CapBnd: 00000000a80425fb

$ cat /proc/1/cgroup
0::/

$ chmod 600 /app/.env
chmod: changing permissions of '/app/.env': Operation not permitted
```

### 1.2 Causa raíz confirmada (doble capa de bloqueo)

| Capa | Evidencia | Efecto |
|------|-----------|--------|
| **1. Montaje 9p/drvfs (WSL2)** | `/proc/mounts` muestra `9p ... aname=drvfs;path=C:\` | `/app` es la unidad `C:` de Windows expuesta vía drvfs. Los permisos POSIX son una *emulación* del driver 9p, no metadatos reales de un filesystem Linux. |
| **2. Cero capabilities efectivas** | `CapEff: 0000000000000000` | El proceso no posee **ninguna** capability: ni `CAP_FOWNER` ni `CAP_CHOWN`. Aunque el archivo fuera local, `chmod` sobre un archivo de otro propietario (`root`) fallaría igual. |

**Conclusión:** `chmod` desde el interior es **imposible por diseño**, no por un defecto de
implementación. El bloqueo es estructural y de doble origen. No existe `sudo` en el entorno.

### 1.3 Nota sobre `docker-compose.yml`

El archivo `docker-compose.yml` **sí declara** `type: bind, source: ., target: /app` (línea 59-61),
pero el montaje efectivo observado en `/proc/mounts` es 9p/drvfs. Esto indica que el contenedor
corre sobre Docker Desktop con backend WSL2, donde el bind-mount del host Windows se materializa
como drvfs. Ambos hechos son coherentes: el origen último es el filesystem NTFS de Windows.

---

## 2. Acciones Ejecutadas y Verificadas en Disco

| # | Acción | Resultado | Verificación |
|---|--------|-----------|--------------|
| 1 | Diagnóstico de permisos/propietario de `/app/.env` | ✅ `777 root:root` | `stat` OK |
| 2 | Intento de `chmod 600` directo | ❌ EPERM | `chmod` retorna 1 |
| 3 | Verificación de capabilities | ✅ `CapEff=0` | `/proc/self/status` |
| 4 | Identificación del tipo de montaje | ✅ 9p/drvfs WSL2 | `/proc/mounts` |
| 5 | Auditoría `Dockerfile` (búsqueda de `chmod 777`) | ✅ Sin hallazgos | `USER tripulacion` + `chown -R` build-time |
| 6 | Auditoría `start.sh` (bloque de permisos) | ✅ FAIL-LOUD presente | `grep` líneas 51-106 |
| 7 | Respaldo `start.sh.BACKUP_pre_tkt_sec_20261020190613` | ✅ 14917 bytes | `ls -la` OK |
| 8 | Parche `start.sh` → alerta FAIL-LOUD | ✅ Aplicado | 16965 bytes |
| 9 | Validación sintáctica `bash -n start.sh` | ✅ Sin errores (rc=0) | ejecución OK |
| 10 | Script de remediación para el host | ✅ 2650 bytes | contenido revisado |
| 11 | Informe técnico de remediación | ✅ Este archivo | en disco |
| 12 | Notificación a Subagente_Ciberseguridad | ✅ Enviada | msg-1792541168917 |
| 13 | `chmod 600` real sobre `/app/.env` | ⏳ **Requiere HOST** | bloqueante externo |

---

## 3. Remediación por Código Aplicada (`start.sh`)

La función `endurecer_permisos()` fue reescrita de modo **silencioso → FAIL-LOUD**:

- Emite **banner de ALERTA CRÍTICA** con archivo, permisos, propietario, proceso, causa, riesgo y acción requerida.
- **Persiste el hallazgo** en `/app/logs/seguridad_permisos.log` para auditoría del Subagente_Ciberseguridad.
- Retorna código 1 (detectable) pero **NO aborta el arranque** (tolerante a fallos).
- Incluye referencia al script de remediación del host.

---

## 4. Acción Pendiente en el HOST (BLOQUEANTE EXTERNO)

El permiso `0o777` **persiste** porque el archivo reside en el filesystem de Windows.

**Windows (PowerShell como Administrador) — RECOMENDADO:**
```powershell
icacls .env /inheritance:r /grant:r "$env:USERNAME:(R)"
```

**WSL2 (terminal con root sobre drvfs):**
```bash
sudo chmod 600 /app/.env
# o bien:
sudo bash Subagente_Desarrollo/proyectos/remediar_permisos_env.sh
```

**Linux / macOS (si aplica):**
```bash
chmod 600 .env
```

**Post-remediación (verificación):**
```bash
docker compose restart
docker exec tripulacion_ia_v3 stat -c '%a %U:%G' /app/.env
# Esperado: 600
```

---

## 5. Evaluación de Riesgo Residual

| Vector | Antes | Tras parche | Tras fix host |
|--------|-------|-------------|---------------|
| Lectura por otros procesos | 🔴 Posible (777) | 🔴 Posible (777) | 🟢 Bloqueado (600) |
| **Modificación / envenenamiento** | 🔴 Posible (777) | 🔴 Posible (777) | 🟢 Bloqueado (600) |
| Detección del fallo | 🟡 Silenciosa | 🟢 Alerta crítica + log | 🟢 N/A (resuelto) |

> **Nota:** El parche de `start.sh` **no reduce** la exposición mientras el archivo siga en 777;
> su valor es **garantizar visibilidad y trazabilidad** del hallazgo en cada arranque hasta que se
> corrija en el host.

---

## 6. Escalamiento

- Ticket de auxilio **TKT-REQ-20261020200017** registrado en Pizarra (destinatario: usuario, responsable: Agente_Orquestador).
- Re-auditoría de cierre H-01 solicitada a Subagente_Ciberseguridad, **condicionada** a la ejecución del `chmod` en el host.
- **Estado del Intento 3:** Bloqueo estructural reconfirmado y **corregido el diagnóstico** (9p/drvfs + cero capabilities). No existe acción adicional posible desde el interior. Se mantiene **BLOQUEADO** a la espera de la acción del usuario en el host.

---

## 7. Evidencia Física

- `/app/Subagente_Desarrollo/proyectos/informe_remediacion_TKT-SEC-20261020190613.md` (este informe)
- `/app/Subagente_Desarrollo/proyectos/remediar_permisos_env.sh`
- `/app/start.sh` (parcheado, 16965 bytes, `bash -n` OK)
- `/app/start.sh.BACKUP_pre_tkt_sec_20261020190613` (respaldo, 14917 bytes)
- `/app/memoria/57_Subagente_Desarrollo_Playbook_conector_mcp_ciberseguridad_infraestructura.md`

---
**Conexiones:** [[proyectos_desarrollo]]
