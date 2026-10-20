# 📧 Informe de Migración: Skill de Correo de Gmail API (OAuth) a IMAP Puro

**Ticket:** TKT-DEV-20261014002
**Responsable:** Subagente_Desarrollo
**Fecha:** 2026-10-14
**Estado:** COMPLETADO


---

## 🎯 1. Objetivo

Refactorizar `Subagente_Asistencia/skills/correo_electronico/skill_correo_electronico.py` para que la **lectura** de correos use **IMAP puro** (`imap.gmail.com:993`) en lugar de la Gmail API con OAuth, eliminando la dependencia estructural de `token.json` (incidencia TKT-MEM-26).

---

## 🗺️ 2. Pipeline de Ejecución (Skills Aplicadas)

1. `tool_consultar_playbook_memoria` (Paso 0) — Recuperación del playbook de gestión de correos.
2. `leer_archivo` — Lectura del sensor de referencia `Agente_Orquestador/data/sensores/sensor_correo_imap.py` y de la skill objetivo.
3. `crear_archivo` — Generación del script de patch quirúrgico en `Archivos_temporales/`.
4. `python_ejecutar_script` — Ejecución del patch → genera `proyectos/skill_correo_electronico_imap.py`.
5. `ejecutar_comando` (`py_compile`) — Validación sintáctica.
6. `python_ejecutar_script` — Test real de login IMAP.
7. `ejecutar_comando` (`cp`) — Backup + despliegue del patch sobre la skill real.
8. `python_ejecutar_script` — Test E2E de `tool_correo_recibir_y_analizar`.

---

## 🔧 3. Cambios Técnicos Aplicados

### 3.1 Imports añadidos
```python
import imaplib
import email
from email.header import decode_header
```

### 3.2 Nuevos helpers IMAP (reutilizados del sensor probado)
- `_cargar_env(override=True)`: Carga el `.env` con **override forzado**, garantizando credenciales frescas y evitando heredar una contraseña de aplicación obsoleta del entorno del proceso.
- `_decodificar_header(valor)`: Decodifica cabeceras MIME a texto legible.
- `_cuerpo_texto_imap(msg)`: Extrae el cuerpo en texto plano (multipart y simple).
- `_leer_correos_imap(max_correos, solo_no_leidos)`: Conecta a `imap.gmail.com:993`, autentica con `KEEP_EMAIL` / `KEEP_APP_PASSWORD`, selecciona `INBOX`, busca `UNSEEN`/`ALL` y devuelve los últimos N correos con `{id, uid, de, asunto, fecha, cuerpo, message_id, in_reply_to}`.

### 3.3 Refactor de `tool_correo_recibir_y_analizar`
- **Firma pública preservada** (sin cambios): `(max_correos=10, solo_no_leidos=True, notificar_prioritarios=True) -> str`.
- Ahora lee vía `_leer_correos_imap(...)` en lugar de `service.users().messages().list(...)`.
- **Fallback seguro**: si IMAP falla, intenta `_recibir_via_gmail_api(...)` (legacy OAuth) y, si tampoco está disponible, retorna JSON de error controlado sin romper el flujo.
- Respuesta incluye nuevo campo `"origen": "imap"` para trazabilidad.
- Se preserva intacta la lógica de clasificación (`_clasificar_correo`), persistencia (`_registrar_correo_procesado`), seguimiento (`_agregar_seguimiento`) y notificación Telegram (`_notificar_mensajeria`).

### 3.4 Herramientas NO modificadas (siguen usando Gmail API para envío)
- `tool_correo_consultar_detalle`, `tool_correo_responder`, `tool_correo_notificar_usuario`, `tool_correo_seguimiento_pendientes`. La migración solicitada era exclusivamente de **lectura**.

---

## ✅ 4. Evidencia de Pruebas

### 4.1 Compilación
```
$ python -m py_compile skill_correo_electronico.py
DEPLOY_PY_COMPILE_OK
```

### 4.2 Login IMAP real
```
[TEST] Host=imap.gmail.com:993  User=SET  Pass=SET
[TEST] LOGIN_OK
[TEST] Total correos en INBOX: 1167
  - UID 1165 | De: Google <no-reply@accounts.google.com> | Asunto: Alerta de seguridad
  - UID 1166 | De: Google <no-reply@accounts.google.com> | Asunto: Alerta de seguridad
  - UID 1167 | De: Alertas de empleo de LinkedIn | Asunto: Desarrollador Python Junior - Trabajo Remoto en BairesDev
[TEST] LOGOUT_OK
```

### 4.3 Test E2E de la herramienta desplegada
```
[E2E] status: success
[E2E] origen: imap
[E2E] total_analizados: 3
   - [CRÍTICA] Google <no-reply@accounts.google.com> | Alerta de seguridad
   - [CRÍTICA] Google <no-reply@accounts.google.com> | Alerta de seguridad
   - [BAJA] Alertas de empleo de LinkedIn | Desarrollador Python Junior - Trabajo Remoto en Ba
```

**Conclusión:** La lectura de correos funciona 100% por IMAP sin requerir `token.json` ni OAuth. La clasificación de prioridades opera correctamente.

---

## 🛡️ 5. Cumplimiento de Directrices

| Directriz | Estado |
|---|---|
| NO hardcodear credenciales (leer de `.env`) | ✅ `_cargar_env(override=True)` + `os.getenv` |
| Preservar firma pública de `tool_correo_recibir_y_analizar` | ✅ Sin cambios |
| Mantener fallback seguro si IMAP falla | ✅ `_recibir_via_gmail_api` + error controlado |
| Compilar con `py_compile` | ✅ OK |
| Probar login IMAP real | ✅ LOGIN_OK (1167 correos) |
| Aplicar patch vía `cp` desde `proyectos/` | ✅ Backup + cp ejecutado |

---

## 📂 6. Artefactos Generados

- **Skill desplegada:** `/app/Subagente_Asistencia/skills/correo_electronico/skill_correo_electronico.py`
- **Patch fuente:** `/app/Subagente_Desarrollo/proyectos/skill_correo_electronico_imap.py`
- **Backup original:** `/app/Archivos_temporales/desarrollo_backup_skill_correo_original.py`
- **Script de patch:** `/app/Archivos_temporales/desarrollo_patch_skill_correo_imap.py`
- **Test login:** `/app/Archivos_temporales/desarrollo_test_imap_login.py`
- **Test E2E:** `/app/Archivos_temporales/desarrollo_test_e2e_skill_correo.py`

---

## 🔄 7. Rollback

En caso de requerir reversión:
```bash
cp /app/Archivos_temporales/desarrollo_backup_skill_correo_original.py \
   /app/Subagente_Asistencia/skills/correo_electronico/skill_correo_electronico.py
```

---
**Conexiones:** [[proyectos_desarrollo]]
