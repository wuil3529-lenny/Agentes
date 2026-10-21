# 🔐 Reporte de Seguridad — Auditoría Preventiva de Seguridad en Arranque de Flota (SAST + Secretos + Perímetro + SOC)

**Fecha:** 2026-10-21 09:19  
**Área auditada:** `Ecosistema multi-agente completo (/app): 221 archivos auditables de 792 totales. Código Python de los 5 agentes, archivos .env, credenciales OAuth, .gitignore, perímetro de red (n8n/ngrok/puertos) y postura del Dashboard SOC.`  
**Nivel global:** ⚪ **APROBADO**  
**Responsable:** Subagente_Ciberseguridad (Robin)  

---

## 📋 Resumen Ejecutivo

| Nivel | Total Hallazgos |
|:---|:---:|
| 🔴 CRÍTICO | 0 |
| 🟠 ALTO    | 0 |
| 🟡 MEDIO   | 0 |
| 🟢 BAJO    | 0 |
| ✅ OK      | 7 |

---

## 🔎 Hallazgos Detallados

### ✅ [OK] Hallazgo #1: H-01

- **Tipo:** Detección de secretos expuestos (30 coincidencias brutas)  
- **Descripción:** El escáner detectar_secretos_expuestos reportó 30 coincidencias iniciales con nivel_global CRÍTICO. Tras TRIAGE MANUAL OBLIGATORIO de cada caso (leer_archivo_seguro), se confirmó que el 100% son FALSOS POSITIVOS: el detector marca por NOMBRE de variable (api_key=, token=, password=), no por valor. Casos verificados: agente_orquestador_agent.py L121-148 usan os.getenv(); skill_ngrok.py L69 usa os.getenv('NGROK_AUTHTOKEN'); skill_n8n.py L61/L70 usan os.getenv; analisis_plataformas_empleo_api.py L19 TOKEN es una RUTA a token.json (no un secreto); skill_escaneo.py L410 password es un literal de bytes de prueba; skill_web.py L126 es una URL de Google Fonts sin credenciales. NO se detectaron credenciales reales en texto claro en el código fuente.  
- **Ubicación:** `Múltiples (ver triage)`  

### ✅ [OK] Hallazgo #2: H-02

- **Tipo:** Integridad de control de versiones (.gitignore)  
- **Descripción:** Repositorio Git presente. Cobertura de .gitignore verificada: .env, .env.local, .env.*, *.key, *.pem, secrets.json y credentials.json están TODOS protegidos. Sin alertas de fuga de secretos al control de versiones.  
- **Ubicación:** `/app/.gitignore`  

### ✅ [OK] Hallazgo #3: H-03

- **Tipo:** Patrones de código peligrosos (eval/exec/shell=True/os.system/pickle/yaml.load)  
- **Descripción:** Búsqueda SAST de patrones peligrosos: 6 coincidencias, TODAS benignas. 4 son comentarios/documentación de remediación (skill_base.py L13/L62, skill_auditoria.py L81, skill_escaneo.py L51), 1 es un patrón regex de detección en skill_conectores_mcp_api.py L69, y 1 es ast.literal_eval() en skill_n8n.py L84 (evaluación segura de literales, no ejecución arbitraria). No se detectó uso de shell=True, os.system, eval() ni exec() reales.  
- **Ubicación:** `Múltiples (6 coincidencias)`  

### ✅ [OK] Hallazgo #4: H-04

- **Tipo:** Exposición perimetral de puertos y servicios  
- **Descripción:** verificar_puertos_locales no detectó puertos críticos activos (n8n :5678, Ollama :11434, ngrok :4040) en escucha. verificar_auth_ngrok confirma que el proceso ngrok NO está activo (sin túneles públicos expuestos). Superficie de ataque perimetral nula en el momento del arranque.  
- **Ubicación:** `Perímetro de red local`  

### ✅ [OK] Hallazgo #5: H-05

- **Tipo:** Autenticación de instancia n8n  
- **Descripción:** N8N_BASIC_AUTH_ACTIVE=true, N8N_BASIC_AUTH_USER configurado y N8N_BASIC_AUTH_PASSWORD configurado (valor enmascarado: ZR***). N8N_API_KEY presente como JWT (eyJhbGci***, enmascarado). La instancia n8n está correctamente protegida con autenticación básica.  
- **Ubicación:** `/app/.env`  

### ✅ [OK] Hallazgo #6: H-06

- **Tipo:** Permisos de archivos sensibles  
- **Descripción:** analizar_permisos_archivo confirma permisos 0o600 (lectura/escritura exclusiva del propietario) en /app/.env, /app/Agente_Orquestador/data/credentials.json y /app/Agente_Orquestador/data/token.json. Ningún archivo sensible presenta permisos excesivos (no hay 0o777 ni lectura global).  
- **Ubicación:** `.env, credentials.json, token.json`  

### ✅ [OK] Hallazgo #7: H-07

- **Tipo:** Postura de seguridad del Dashboard SOC  
- **Descripción:** tool_auditar_postura_dashboard emite puntuación defensiva 100/100 (EXCELENTE). CONSOLE_AUTH_ACTIVE activado, whitelist ALLOWED_IPS activa (127.0.0.1, ::1, 192.168.0.*, 10.2.0.*), 1 usuario registrado protegido con Bcrypt, cola de comandos remotos limpia. tool_verificar_estado_alarma_dashboard: alarma inactiva (verde), historial de incidentes vacío.  
- **Ubicación:** `dashboard/`  

---

## ✅ Recomendaciones y Plan de Remediación

1. **[MEDIA]** Refinar el patrón regex de detectar_secretos_expuestos para excluir asignaciones desde os.getenv/os.environ y rutas de archivo, eliminando el ruido de falsos positivos (30/30 en esta auditoría).  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

2. **[MEDIA]** Añadir *.token y token.json al .gitignore como defensa en profundidad para credenciales OAuth de Google.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

3. **[MEDIA]** Exigir siempre la bandera --basic-auth al iniciar túneles ngrok y validar con verificar_auth_ngrok antes de exponer servicios públicos.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

4. **[MEDIA]** Rotar periódicamente N8N_API_KEY y la contraseña de Basic Auth de n8n; evaluar migración a Header Auth/JWT nativo.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

5. **[MEDIA]** Mantener la política de permisos 0o600 en todos los archivos de credenciales (.env, credentials.json, token.json) y auditar que nuevos archivos hereden estos permisos.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

6. **[MEDIA]** Ejecutar esta auditoría de arranque de forma automatizada en cada reinicio de la flota mediante el Hook de Arranque.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

---


*Reporte compilado automáticamente bajo el estándar Zero-Trust de la tripulación — 2026-10-21 09:19*

---
**Conexiones:** [[reportes_ciberseguridad]]
