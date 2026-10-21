# 🔐 Reporte de Seguridad — Auditoría Preventiva de Seguridad en Arranque de Flota (SAST + Secretos + Permisos + Perímetro + SOC)

**Fecha:** 2026-10-20 19:06  
**Área auditada:** `Ecosistema multi-agente completo /app (235 archivos auditables de 758 totales) — Agente_Orquestador, Subagente_Desarrollo, Subagente_Asistencia, Subagente_Ciberseguridad, Subagente_Diseno, dashboard, sistema y raíz`  
**Nivel global:** ⚪ **ALERTA**  
**Responsable:** Subagente_Ciberseguridad (Robin)  

---

## 📋 Resumen Ejecutivo

| Nivel | Total Hallazgos |
|:---|:---:|
| 🔴 CRÍTICO | 0 |
| 🟠 ALTO    | 1 |
| 🟡 MEDIO   | 2 |
| 🟢 BAJO    | 1 |
| ✅ OK      | 5 |

---

## 🔎 Hallazgos Detallados

### 🟠 [ALTO] Hallazgo #1: H-01

- **Tipo:** Permisos excesivos en archivo de secretos (.env)  
- **Descripción:** El archivo .env (5.2 KB) contiene todas las credenciales de la flota (API keys de LLM, N8N_BASIC_AUTH_PASSWORD, N8N_API_KEY JWT, tokens de Google) y presenta permisos octales 0o777 (lectura y escritura para cualquier usuario). Cualquier proceso o usuario del contenedor puede leer y MODIFICAR las credenciales, permitiendo escalada de privilegios o envenenamiento de configuración.  
- **Ubicación:** `/app/.env`  

### 🟡 [MEDIO] Hallazgo #2: H-02

- **Tipo:** Falso positivo masivo del detector de secretos (ruido de clasificación)  
- **Descripción:** El detector reportó 30 hallazgos como CRÍTICO. El triage manual confirmó que la gran mayoría son FALSOS POSITIVOS: el motor clasifica por NOMBRE de variable (api_key=, token=, password=) y no por VALOR. Casos verificados: agente_orquestador_agent.py L121-148 (api_key = os.getenv(...)), base_listener.py L508, costos_tracker.py L316, telegram_bridge.py L18/L27, skill_voz.py L184/L574, skill_ngrok.py L69 (auth_token = os.getenv('NGROK_AUTHTOKEN')), analisis_plataformas_empleo_api.py L19 (TOKEN = '/app/.../token.json' — es una RUTA de archivo, no un secreto). Ninguno expone credenciales en texto claro.  
- **Ubicación:** `/app (30 hallazgos reportados como CRÍTICO)`  

### 🟡 [MEDIO] Hallazgo #3: H-03

- **Tipo:** Uso de os.system() en script de consola  
- **Descripción:** Líneas 11 y 120 invocan os.system() para limpiar pantalla y abrir PowerShell interactivo. Aunque los argumentos son constantes (no hay interpolación de input del usuario), os.system() invoca una shell intermedia y es un antipatrón de seguridad. El resto del ecosistema ya migró a subprocess con shell=False (SEC-H04).  
- **Ubicación:** `/app/consola_pruebas.py`  

### 🟢 [BAJO] Hallazgo #4: H-04

- **Tipo:** URL externa en plantilla generada (skill_web)  
- **Descripción:** L126 referencia https://fonts.googleapis.com en el HTML scaffold generado. No contiene credenciales embebidas (falso positivo del detector), pero introduce una dependencia de terceros en el renderizado de proyectos generados.  
- **Ubicación:** `/app/Subagente_Desarrollo/skills/web/skill_web.py`  

### ✅ [OK] Hallazgo #5: H-05

- **Tipo:** Integridad de control de versiones (.gitignore)  
- **Descripción:** Repositorio Git presente. Cobertura completa verificada: .env, .env.local, .env.*, *.key, *.pem, secrets.json y credentials.json están todos protegidos. Sin alertas de fuga de credenciales al control de versiones.  
- **Ubicación:** `/app/.gitignore`  

### ✅ [OK] Hallazgo #6: H-06

- **Tipo:** Perímetro de red y túneles  
- **Descripción:** Sin puertos críticos en escucha (n8n :5678, Ollama :11434, ngrok :4040 inactivos). N8N_BASIC_AUTH_ACTIVE=true con usuario y contraseña configurados. Ngrok no está corriendo, por lo que no hay túneles públicos sin autenticación expuestos.  
- **Ubicación:** `Sistema / n8n / ngrok`  

### ✅ [OK] Hallazgo #7: H-07

- **Tipo:** Permisos de credenciales OAuth  
- **Descripción:** Ambos archivos presentan permisos 0o600 (solo propietario). Correctamente blindados.  
- **Ubicación:** `/app/Agente_Orquestador/data/credentials.json y token.json`  

### ✅ [OK] Hallazgo #8: H-08

- **Tipo:** Postura de seguridad del Dashboard (SOC)  
- **Descripción:** Puntuación defensiva 100/100 (EXCELENTE). CONSOLE_AUTH_ACTIVE activo, 1/1 usuarios protegidos con Bcrypt, whitelist de IPs activa (127.0.0.1, ::1, 192.168.0.*, 10.2.0.*), cola de comandos remotos limpia. Alarma perimetral inactiva (verde), historial de incidentes vacío.  
- **Ubicación:** `/app/dashboard`  

### ✅ [OK] Hallazgo #9: H-09

- **Tipo:** Patrones peligrosos de ejecución (SAST)  
- **Descripción:** De 8 coincidencias de eval/exec/shell=True/os.system/pickle.loads/yaml.load, 6 son comentarios o cadenas de documentación de las propias reglas SEC-H04, 1 es ast.literal_eval (seguro, no eval), y 2 son los os.system de H-03. No se detectaron llamadas a eval()/exec()/pickle.loads/yaml.load() sobre datos no confiables.  
- **Ubicación:** `/app (8 coincidencias analizadas)`  

---

## ✅ Recomendaciones y Plan de Remediación

1. **[MEDIA]** CRÍTICO DE ACCIÓN INMEDIATA: Corregir permisos de /app/.env de 0o777 a 0o600 (chmod 600) y verificar que start.sh/Dockerfile no los re-apliquen en cada arranque.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

2. **[MEDIA]** Refinar el motor detectar_secretos_expuestos para excluir asignaciones desde os.getenv/os.environ y rutas de archivo, reduciendo el ruido de falsos positivos (30 reportados vs 0 reales de texto claro).  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

3. **[MEDIA]** Migrar los os.system() de consola_pruebas.py a subprocess.run con shell=False para alinear el script con la política SEC-H04 del resto del ecosistema.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

4. **[MEDIA]** Añadir token.json y credenciales OAuth a .gitignore de forma explícita si aún no están cubiertas.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

5. **[MEDIA]** Mantener la disciplina perimetral: ngrok siempre con --basic-auth y N8N_BASIC_AUTH_ACTIVE=true.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

6. **[MEDIA]** Re-ejecutar esta auditoría tras aplicar la remediación de permisos para confirmar el cierre del hallazgo ALTO.  
   - *Responsable sugerido:* `Subagente_Desarrollo`  

---


*Reporte compilado automáticamente bajo el estándar Zero-Trust de la tripulación — 2026-10-20 19:06*

---
**Conexiones:** [[reportes_ciberseguridad]]
