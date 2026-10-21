# 🔐 Reporte de Seguridad — Auditoría Preventiva de Seguridad en Arranque de Flota (SAST + Secretos + Perímetro + SOC)

**Fecha:** 2026-10-21 08:57  
**Área auditada:** `Ecosistema multi-agente completo /app (237 archivos auditables de 797 totales) — Agente_Orquestador, Subagente_Desarrollo, Subagente_Asistencia, Subagente_Ciberseguridad, Subagente_Diseno, dashboard, conector_remoto.py, start.sh, .env`  
**Nivel global:** ⚪ **ALERTA**  
**Responsable:** Subagente_Ciberseguridad (Robin)  

---

## 📋 Resumen Ejecutivo

| Nivel | Total Hallazgos |
|:---|:---:|
| 🔴 CRÍTICO | 0 |
| 🟠 ALTO    | 1 |
| 🟡 MEDIO   | 0 |
| 🟢 BAJO    | 0 |
| ✅ OK      | 6 |

---

## 🔎 Hallazgos Detallados

### 🟠 [ALTO] Hallazgo #1: H-01

- **Tipo:** Permisos excesivos en archivo de secretos (.env World Writable)  
- **Descripción:** El archivo .env que contiene TODAS las credenciales de la flota (API keys de LLM, N8N_BASIC_AUTH_PASSWORD, N8N_API_KEY JWT, KEEP_APP_PASSWORD de Gmail, SUPABASE_ACCESS_TOKEN, NGROK_AUTHTOKEN) posee permisos octales 0o777 (lectura/escritura/ejecución para propietario, grupo y OTROS). Cualquier proceso o usuario del contenedor puede leer y MODIFICAR las credenciales, permitiendo escalada de privilegios, robo de tokens y envenenamiento de configuración.  
- **Ubicación:** `/app/.env`  

### ✅ [OK] Hallazgo #2: H-02

- **Tipo:** Falsos positivos de secretos hardcodeados (30 reportados por detector)  
- **Descripción:** El detector de secretos reportó 30 hallazgos clasificados inicialmente como CRÍTICO. El triage manual (obligatorio según playbook) confirmó que TODOS son falsos positivos: el detector marca por NOMBRE de variable (api_key=, token=, password=) y no por valor. En todos los casos verificados la asignación proviene de os.getenv()/os.environ (ej. api_key = os.getenv('DEEPSEEK_API_KEY'), password = os.getenv('N8N_BASIC_AUTH_PASSWORD'), auth_token = os.getenv('NGROK_AUTHTOKEN')), de rutas de archivo (TOKEN = '/app/.../token.json') o de URLs públicas de Google Fonts. No existe ninguna credencial en texto claro en el código fuente.  
- **Ubicación:** `Agente_Orquestador/agente_orquestador_agent.py, base_listener.py, costos_tracker.py, telegram_bridge.py, skill_voz.py, Subagente_Asistencia/subagente_asistencia_agent.py, Subagente_Ciberseguridad/subagente_ciberseguridad_agent.py, Subagente_Desarrollo/subagente_desarrollo_agent.py, skills/n8n, skills/ngrok, skills/supabase, skills/escaneo, sensores IMAP`  

### ✅ [OK] Hallazgo #3: H-03

- **Tipo:** Integridad de control de versiones (.gitignore)  
- **Descripción:** Repositorio Git presente. Cobertura de .gitignore verificada y correcta: .env, .env.local, .env.*, *.key, *.pem, secrets.json y credentials.json están todos protegidos. Sin alertas de fuga de credenciales al control de versiones.  
- **Ubicación:** `/app/.gitignore, /app/Agente_Orquestador/.gitignore`  

### ✅ [OK] Hallazgo #4: H-04

- **Tipo:** Patrones peligrosos de ejecución (SAST)  
- **Descripción:** Búsqueda de eval(), exec(), shell=True, os.system, pickle.loads y yaml.load() arrojó 6 coincidencias, TODAS benignas: 4 son comentarios/documentación que describen la remediación SEC-H04 (prohibición de shell=True), 1 es un patrón regex de detección dentro de un escáner de seguridad, y 1 es ast.literal_eval() (evaluación segura de literales, no ejecuta código arbitrario). No se detectó ninguna llamada insegura real. Los módulos de ejecución usan subprocess con shell=False y listas de argumentos tokenizadas con shlex.split().  
- **Ubicación:** `Agente_Orquestador/skills/base/skill_base.py, Subagente_Ciberseguridad/skills/escaneo/skill_escaneo.py, Subagente_Desarrollo/skills/n8n/skill_n8n.py, Subagente_Desarrollo/skills/conectores_mcp_api/skill_conectores_mcp_api.py`  

### ✅ [OK] Hallazgo #5: H-05

- **Tipo:** Exposición perimetral de puertos y túneles  
- **Descripción:** verificar_puertos_locales no detectó puertos críticos activos (0 alertas). ngrok NO está en ejecución (sin túneles públicos expuestos). n8n: N8N_BASIC_AUTH_ACTIVE=true, usuario 'admin' configurado y contraseña presente (enmascarada ZR***). Autenticación básica correctamente habilitada.  
- **Ubicación:** `Sistema local / n8n / ngrok`  

### ✅ [OK] Hallazgo #6: H-06

- **Tipo:** Permisos de archivos sensibles secundarios  
- **Descripción:** credentials.json (OAuth2 Google) y token.json presentan permisos 0o600 (solo propietario lectura/escritura). Correctamente blindados.  
- **Ubicación:** `/app/Agente_Orquestador/data/credentials.json, /app/Agente_Orquestador/data/token.json`  

### ✅ [OK] Hallazgo #7: H-07

- **Tipo:** Postura de seguridad del Dashboard / SOC  
- **Descripción:** Puntuación defensiva 100/100 (EXCELENTE). CONSOLE_AUTH_ACTIVE activado con usuario+contraseña, whitelist de IPs activa (127.0.0.1, ::1, 192.168.0.*, 10.2.0.*), 1/1 usuarios protegidos con Bcrypt, cola de comandos remotos limpia. Alarma perimetral inactiva (verde), historial de incidentes vacío, 0 IPs bloqueadas activas.  
- **Ubicación:** `dashboard/ (consola web)`  

---

## ✅ Recomendaciones y Plan de Remediación

1. **[MEDIA]** CRÍTICO/ALTO: Corregir de inmediato los permisos de /app/.env con 'chmod 600 /app/.env' para eliminar la escritura pública sobre el archivo que concentra todas las credenciales de la flota.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

2. **[MEDIA]** Añadir al hook de arranque (start.sh) una verificación automática de permisos del .env que aborte o alerte si detecta 0o777 u otro permiso excesivo.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

3. **[MEDIA]** Refinar el patrón regex de detectar_secretos_expuestos para excluir asignaciones con os.getenv/os.environ y rutas de archivo, reduciendo falsos positivos (30 en esta auditoría).  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

4. **[MEDIA]** Añadir *.token y token.json al .gitignore como defensa en profundidad, aunque ya están fuera de control de versiones.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

5. **[MEDIA]** Mantener la política SEC-H04 (shell=False + lista blanca de binarios) en todos los módulos nuevos; el SAST no detectó ejecuciones inseguras reales.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

6. **[MEDIA]** Al exponer túneles ngrok, exigir siempre --basic-auth; actualmente ngrok no está activo, lo cual es correcto.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

7. **[MEDIA]** Mantener N8N_BASIC_AUTH_ACTIVE=true y la whitelist de IPs del Dashboard (postura actual 100/100).  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

---


*Reporte compilado automáticamente bajo el estándar Zero-Trust de la tripulación — 2026-10-21 08:57*

---
**Conexiones:** [[reportes_ciberseguridad]]
