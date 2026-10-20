# 🔐 Reporte de Seguridad — Auditoría Preventiva de Seguridad en Arranque de Flota (TKT-SEC-BOOT-20261019180153)

**Fecha:** 2026-10-19 18:14  
**Área auditada:** `Ecosistema multi-agente completo /app (218 archivos auditables): SAST de código fuente, detección de secretos, integridad Git, permisos de archivos sensibles, perímetro de red y postura del Dashboard SOC.`  
**Nivel global:** ⚪ **ALERTA**  
**Responsable:** Subagente_Ciberseguridad (Robin)  

---

## 📋 Resumen Ejecutivo

| Nivel | Total Hallazgos |
|:---|:---:|
| 🔴 CRÍTICO | 0 |
| 🟠 ALTO    | 0 |
| 🟡 MEDIO   | 0 |
| 🟢 BAJO    | 8 |
| ✅ OK      | 0 |

---

## 🔎 Hallazgos Detallados

### 🟢 [BAJO] Hallazgo #1: H-01

- **Tipo:** Vulnerabilidad  
- **Descripción:** El archivo de variables de entorno raíz tiene permisos 0o777: lectura y ESCRITURA para cualquier usuario del sistema. Contiene credenciales de producción (N8N_API_KEY JWT, N8N_BASIC_AUTH_PASSWORD, claves LLM). Cualquier proceso comprometido podría leer o ALTERAR secretos, permitiendo escalada o envenenamiento de configuración.  
- **Ubicación:** `/app/.env`  

### 🟢 [BAJO] Hallazgo #2: H-02

- **Tipo:** Vulnerabilidad  
- **Descripción:** Archivos de credenciales OAuth/Google con permisos world-readable y world-writable (0o777). Riesgo de exfiltración y manipulación de tokens de acceso.  
- **Ubicación:** `/app/Agente_Orquestador/data/credentials.json, /app/Agente_Orquestador/data/token.json`  

### 🟢 [BAJO] Hallazgo #3: H-03

- **Tipo:** Vulnerabilidad  
- **Descripción:** La cobertura de .gitignore protege .env, .env.* y *.env.*, pero el chequeo reporta .env.local como no cubierto de forma explícita. Un archivo .env.local con secretos podría terminar versionado.  
- **Ubicación:** `/app/.gitignore`  

### 🟢 [BAJO] Hallazgo #4: H-04

- **Tipo:** Vulnerabilidad  
- **Descripción:** Múltiples invocaciones de subprocess con shell=True, algunas con interpolación de variables (f-strings con task_name/batch_path). Si algún parámetro proviene de entrada de usuario o de la cola de comandos remotos, habilita inyección de comandos (RCE). El firewall determinístico mitiga parcialmente, pero el patrón es riesgoso.  
- **Ubicación:** `dashboard/puente_manos_ojos.py (líneas 185-1038), conector_remoto.py (116,141), dashboard/app.py (2111,2113), skills/*/skill_base.py, skills/n8n, skills/ngrok, skills/web, skills/mobile, skills/software`  

### 🟢 [BAJO] Hallazgo #5: H-05

- **Tipo:** Vulnerabilidad  
- **Descripción:** Verificación manual línea a línea: TODOS los hallazgos del detector corresponden a lecturas seguras de os.getenv()/os.environ.get()/_leer_env_valor() o a variables locales derivadas. NO existe ninguna credencial literal hardcodeada en el código fuente. El detector marca por nombre de variable (api_key=, token=, password=), no por valor literal.  
- **Ubicación:** `agente_orquestador_agent.py, base_listener.py, costos_tracker.py, skill_voz.py, telegram_bridge.py, subagente_*_agent.py, skill_n8n.py, skill_ngrok.py, skill_ia_creativa.py, skill_video.py, skill_escaneo.py`  

### 🟢 [BAJO] Hallazgo #6: H-06

- **Tipo:** Vulnerabilidad  
- **Descripción:** Sin puertos críticos en escucha (n8n:5678, Ollama:11434, ngrok:4040 inactivos). ngrok no está corriendo. N8N_BASIC_AUTH_ACTIVE=true con usuario y contraseña configurados.  
- **Ubicación:** `Sistema local`  

### 🟢 [BAJO] Hallazgo #7: H-07

- **Tipo:** Vulnerabilidad  
- **Descripción:** Puntuación defensiva 100/100 (EXCELENTE). CONSOLE_AUTH_ACTIVE activo, 1/1 usuarios con hash Bcrypt, whitelist ALLOWED_IPS activa (127.0.0.1, ::1, 192.168.0.*, 10.2.0.*), cola de comandos remotos limpia, alarma perimetral inactiva e historial de incidentes vacío.  
- **Ubicación:** `/app/dashboard`  

### 🟢 [BAJO] Hallazgo #8: H-08

- **Tipo:** Vulnerabilidad  
- **Descripción:** Repositorio Git presente. .env, *.key, *.pem, secrets.json, credentials.json, token.json y memoria/ correctamente ignorados. No se detectaron claves privadas ni credenciales versionadas.  
- **Ubicación:** `/app/.gitignore`  

---

## ✅ Recomendaciones y Plan de Remediación

1. **[MEDIA]** CRÍTICO DE HIGIENE: Ejecutar chmod 600 sobre /app/.env, /app/Agente_Orquestador/data/credentials.json y /app/Agente_Orquestador/data/token.json; chmod 700 sobre el directorio data/.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

2. **[MEDIA]** Añadir '.env.local' explícito al .gitignore como defensa en profundidad.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

3. **[MEDIA]** Refactorizar las 31 llamadas subprocess con shell=True hacia listas de argumentos (shell=False) o shlex.quote en las variables interpoladas, priorizando dashboard/puente_manos_ojos.py y conector_remoto.py.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

4. **[MEDIA]** Refinar el patrón del detector de secretos para excluir asignaciones desde os.getenv/os.environ y eliminar los 30 falsos positivos recurrentes.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

5. **[MEDIA]** Mantener N8N_BASIC_AUTH_ACTIVE=true y no exponer ngrok sin --basic-auth.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

6. **[MEDIA]** Conservar la postura 100/100 del Dashboard y revisar incidentes periódicamente.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

---


*Reporte compilado automáticamente bajo el estándar Zero-Trust de la tripulación — 2026-10-19 18:14*

---
**Conexiones:** [[reportes_ciberseguridad]]
