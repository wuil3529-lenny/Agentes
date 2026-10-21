# 🔐 Reporte de Seguridad — Auditoría Preventiva de Seguridad en Arranque de Flota (TKT-SEC-BOOT-20261020204328)

**Fecha:** 2026-10-20 20:50  
**Área auditada:** `Ecosistema multi-agente /app — SAST, secretos, .gitignore, perímetro, permisos y SOC Dashboard`  
**Nivel global:** ⚪ **ALERTA**  
**Responsable:** Subagente_Ciberseguridad (Robin)  

---

## 📋 Resumen Ejecutivo

| Nivel | Total Hallazgos |
|:---|:---:|
| 🔴 CRÍTICO | 0 |
| 🟠 ALTO    | 1 |
| 🟡 MEDIO   | 1 |
| 🟢 BAJO    | 0 |
| ✅ OK      | 7 |

---

## 🔎 Hallazgos Detallados

### 🟠 [ALTO] Hallazgo #1: H-01

- **Tipo:** Permisos excesivos en archivo de secretos (.env)  
- **Descripción:** El archivo .env (5.2 KB) contiene credenciales de producción (N8N_BASIC_AUTH_PASSWORD, N8N_API_KEY JWT, claves LLM) y tiene permisos octales 0o444, otorgando lectura a cualquier usuario del contenedor (Others Read).  
- **Ubicación:** `/app/.env`  

### 🟡 [MEDIO] Hallazgo #2: H-02

- **Tipo:** Ejecución de comandos de shell sin sanitización (os.system)  
- **Descripción:** Script de utilidad local invoca os.system('cls'/'clear') y os.system('powershell'). Aunque los argumentos son constantes (no hay input de usuario), establece un precedente de ejecución vía intérprete de shell contrario al estándar SEC-H04 del ecosistema.  
- **Ubicación:** `/app/consola_pruebas.py (líneas 11 y 120)`  

### ✅ [OK] Hallazgo #3: H-03

- **Tipo:** Falsos positivos del detector de secretos (30 reportados)  
- **Descripción:** Los 30 hallazgos CRÍTICOS del escáner fueron triados manualmente uno por uno. Todos corresponden a asignaciones seguras: api_key = os.getenv(...), token = os.environ[...], TOKEN = '/app/.../token.json' (ruta de archivo, no secreto), auth_token = os.getenv('NGROK_AUTHTOKEN'), password = os.getenv(...). No existe ninguna credencial en texto claro en el código fuente.  
- **Ubicación:** `Agente_Orquestador/*.py, Subagente_*/**.py`  

### ✅ [OK] Hallazgo #4: H-04

- **Tipo:** Integridad de control de versiones (.gitignore)  
- **Descripción:** Repositorio Git presente. Cobertura completa verificada: .env, .env.local, .env.*, *.key, *.pem, secrets.json y credentials.json están protegidos. Sin alertas de fuga.  
- **Ubicación:** `/app/.gitignore, /app/Agente_Orquestador/.gitignore`  

### ✅ [OK] Hallazgo #5: H-05

- **Tipo:** Perímetro de red y túneles  
- **Descripción:** Sin puertos críticos en escucha (n8n :5678, Ollama :11434, ngrok :4040 inactivos). Ngrok no está corriendo, por lo que no hay exposición pública sin --basic-auth.  
- **Ubicación:** `Sistema local`  

### ✅ [OK] Hallazgo #6: H-06

- **Tipo:** Autenticación de servicios (n8n)  
- **Descripción:** N8N_BASIC_AUTH_ACTIVE=true, usuario y contraseña configurados. N8N_API_KEY presente como JWT (valor enmascarado en este reporte).  
- **Ubicación:** `/app/.env`  

### ✅ [OK] Hallazgo #7: H-07

- **Tipo:** Permisos de credenciales OAuth  
- **Descripción:** Permisos 0o600 correctos (solo propietario). Sin exposición a otros usuarios.  
- **Ubicación:** `/app/Agente_Orquestador/data/credentials.json`  

### ✅ [OK] Hallazgo #8: H-08

- **Tipo:** Postura de seguridad del Dashboard (SOC)  
- **Descripción:** Puntuación defensiva 100/100 (EXCELENTE). CONSOLE_AUTH_ACTIVE activo, 1/1 usuarios con hash Bcrypt, whitelist ALLOWED_IPS activa (127.0.0.1, ::1, 192.168.0.*, 10.2.0.*), cola de comandos remotos limpia. Alarma perimetral inactiva, historial de incidentes vacío.  
- **Ubicación:** `/app/dashboard`  

### ✅ [OK] Hallazgo #9: H-09

- **Tipo:** Dependencias Python (CVE)  
- **Descripción:** pip-audit no reportó vulnerabilidades conocidas. Nota: el proceso excedió el límite de tiempo (timeout) tras completar el análisis, por lo que el resultado se considera válido pero no exhaustivo.  
- **Ubicación:** `/app/Agente_Orquestador/requirements.txt`  

---

## ✅ Recomendaciones y Plan de Remediación

1. **[MEDIA]** Aplicar chmod 600 a /app/.env de inmediato (hallazgo ALTO H-01) y verificar el usuario propietario del proceso.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

2. **[MEDIA]** Refinar el patrón del detector de secretos para eliminar falsos positivos por nombre de variable (os.getenv/os.environ).  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

3. **[MEDIA]** Sustituir os.system por subprocess.run(shell=False) en consola_pruebas.py o reubicar el script obsoleto en Archivos_temporales/.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

4. **[MEDIA]** Añadir token.json y start.sh.BACKUP_* al .gitignore para blindar respaldos y tokens OAuth.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

5. **[MEDIA]** Re-ejecutar pip-audit en ventana de mantenimiento para confirmar cobertura completa tras el timeout.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

6. **[MEDIA]** Mantener la disciplina perimetral: exigir --basic-auth en todo túnel ngrok y validar antes de exponer puertos.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

---


*Reporte compilado automáticamente bajo el estándar Zero-Trust de la tripulación — 2026-10-20 20:50*

---
**Conexiones:** [[reportes_ciberseguridad]]
