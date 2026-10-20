# Informe de Corrección — Sensor de Correo IMAP

**Ticket:** TKT-DEV-20261014001
**Responsable:** Subagente_Desarrollo
**Fecha:** 2026-10-14
**Archivo intervenido:** `/app/Agente_Orquestador/data/sensores/sensor_correo_imap.py`

---

## 1. Diagnóstico (Causa Raíz)

El sensor cargaba el archivo `.env` mediante `os.environ.setdefault(clave, valor)`.
La semántica de `setdefault` es **no sobreescribir** una variable que ya exista en
`os.environ`. Como el proceso del sensor heredaba del entorno una variable
`KEEP_APP_PASSWORD` con la **contraseña de aplicación de Gmail antigua**, el valor
fresco del `.env` nunca se aplicaba y el login IMAP fallaba.

### Evidencia del defecto (hashes SHA-256 truncados, sin exponer secretos)

| Origen | Longitud | Hash (12) |
|---|---|---|
| `os.environ['KEEP_APP_PASSWORD']` (obsoleto) | 19 | `ee4c236f14ba` |
| `.env` → `KEEP_APP_PASSWORD` (fresco) | 19 | `8d8e36d26910` |

`SON_IGUALES = False` → el entorno contenía una credencial distinta (obsoleta) que
`setdefault` impedía reemplazar.

---

## 2. Corrección Aplicada

Se reemplazó la carga pasiva por una **carga forzada con override**:

```python
def _cargar_env(override=True):
    env_path = Path("/app/.env")
    if not env_path.exists():
        env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        for linea in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if override:
                os.environ[clave] = valor      # <-- OVERRIDE FORZADO
            else:
                os.environ.setdefault(clave, valor)

_cargar_env(override=True)
```

**Garantías:**
- El `.env` es ahora la **fuente de verdad** y SIEMPRE sobreescribe el entorno.
- **No se hardcodeó** ninguna credencial; se lee del `.env`.
- **No se modificó** la lógica de detección de correos ni el formato de salida JSON
  (`{"disparar": true/false, "datos_evento": {...}}`).

---

## 3. Prueba de Login IMAP Real (Salida Cruda)

Se ejecutó una prueba que **inyecta una credencial obsoleta** en `os.environ` antes
de importar el sensor, reproduciendo el escenario del bug, y luego valida el override
y el login real contra `imap.gmail.com:993`.

```
[SETUP] Credencial obsoleta inyectada en os.environ (hash=60dd5f8716ba)
[POST-IMPORT] KEEP_APP_PASSWORD en entorno tras override (hash=8d8e36d26910)
[POST-IMPORT] EMAIL_USER=Wuil3529@gmail.com
[POST-IMPORT] IMAP_HOST=imap.gmail.com:993
[CHECK] Override OK: la credencial obsoleta fue reemplazada por la del .env
[IMAP] LOGIN EXITOSO -> respuesta del servidor: ('OK', [b'wuil3529@gmail.com authenticated (Success)'])
[IMAP] SELECT INBOX -> status=OK, total_mensajes=1166
[IMAP] Correos NO leidos (UNSEEN): 1106
[RESULTADO] PRUEBA DE LOGIN IMAP: EXITOSA
```

**Conclusión:** El override reemplaza la credencial obsoleta (`60dd5f8716ba` →
`8d8e36d26910`) y la autenticación IMAP es **EXITOSA**.

---

## 4. Prueba End-to-End del Sensor (Formato JSON Intacto)

Ejecución directa del sensor corregido:

```
$ python3 /app/Agente_Orquestador/data/sensores/sensor_correo_imap.py
{"disparar": true, "datos_evento": {"total_nuevos": 5, "correos": [{"uid": "1159",
 "remitente": "\"Equipo de Computrabajo\" <empleos_ve@computrabajo.com>",
 "asunto": "Nuevas vacantes de Desarrollo listas para postularte",
 "fecha": "13 Oct 2026 23:03:40 +0000", "cuerpo": "<!DOCTYPE html>..."}]}}
```

- Compilación sintáctica: `python3 -m py_compile` → **SYNTAX_OK**.
- Formato de salida JSON: **preservado** (`disparar` / `datos_evento`).

---

## 5. Archivos y Evidencia

| Artefacto | Ruta |
|---|---|
| Script corregido (en producción) | `/app/Agente_Orquestador/data/sensores/sensor_correo_imap.py` |
| Copia de respaldo del corregido | `/app/Subagente_Desarrollo/proyectos/sensor_correo_imap_corregido.py` |
| Script de prueba de login IMAP | `/app/Archivos_temporales/desarrollo_test_login_imap.py` |
| Este informe | `/app/Subagente_Desarrollo/informes/informe_correccion_sensor_correo_imap.md` |

---
**Conexiones:** [[proyectos_desarrollo]]
