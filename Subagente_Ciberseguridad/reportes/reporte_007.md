# 🔐 Reporte de Seguridad #007 — Auditoría de Seguridad Multi-Repositorio GitHub (`wuil3529-lenny`)
> **Responsable:** Subagente_Ciberseguridad (Robin)  
> **Fecha:** 2026-10-20 15:55  
> **Alcance:** 9 Repositorios públicos en la cuenta GitHub oficial del Capitán  
> **Veredicto:** 🟡 **PASS OPERATIVO CON 1 REPOSITORIO EN OBSERVACIÓN (automatizaciones_n8n)**

---

## 📋 1. Resumen Ejecutivo del Parque de Repositorios

En cumplimiento de la orden prioritaria del Capitán y bajo el **Modo Centinela**, Robin ejecutó una inspección exhaustiva de análisis estático (SAST), detección de tokens, credenciales y fuga de PII en los 9 repositorios públicos de la cuenta:

| Repositorio | Visibilidad | Archivos | Estado | Diagnóstico de Robin |
| :--- | :---: | :---: | :---: | :--- |
| **`Agentes`** | Pública | 430 | ✅ **100% LIMPIO** | Saneado, blindado con las 5 Reglas de Oro y sincronizado. |
| **`zoro_asistente_programacion`** | Pública | 7 | ✅ **100% LIMPIO** | Sin claves, tokens ni dependencias inseguras. |
| **`analisis_de_producto_en_mercado_libre`** | Pública | 14 | ✅ **100% LIMPIO** | Modelos y scripts de scraping/ML sin credenciales. |
| **`modelos_ia`** | Pública | 2 | ✅ **100% LIMPIO** | Repositorio de artefactos sin secretos. |
| **`Graficos_de_entrenamientos`** | Pública | 0 código | ✅ **100% LIMPIO** | Métricas y curvas de entrenamiento sin código ejecutable. |
| **`Data_set`** | Pública | Dataset | ✅ **100% LIMPIO** | Imágenes de visión artificial sin código ni secretos. |
| **`wuil3529-lenny.github.io`** | Pública | 1 | 🟢 **INFO** | Portafolio web público (contacto visible: email y teléfono intencionales). |
| **`plataforma-industrial`** | Pública | 66 | 🟢 **INFO** | Cadena de conexión dummy/placeholder (`usuario:contraseña@localhost`). Sin claves reales. |
| **`automatizaciones_n8n`** | Pública | 20 | ⚠️ **ALERTA** | **Tokens JWT de Supabase** (`anon key`, proyecto `xkxjocoaqtiaevjbdwhe`) exportados en 2 flujos JSON. |

---

## 🔎 2. Análisis Detallado del Hallazgo en `automatizaciones_n8n`

Robin detectó la presencia de tokens JWT embebidos en texto plano dentro de dos workflows exportados de n8n:

1. **`06_Generador_Copy_Telegram/copy_generator_telegram.json`** (Líneas 415, 419, 495, 580, etc.):
   - Token JWT asignado a un header de autorización:
     ```text
     eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhreGpvY29hcXRpYWV2amJkd2hlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwODI4MDEsImV4cCI6MjA5MDY1ODgwMX0...
     ```
2. **`02_Agente_Telegram/agente_telegram_pepito.json`** y `agente_telegram_pepito_backup.json`:
   - 12 repeticiones del mismo token JWT en nodos de inserción y consulta a Supabase.
   - **Triage Criptográfico de Robin:** El payload decodificado confirma que es una clave pública/anónima (`role: "anon"`). No es la `service_role_key` (que otorgaría bypass administrativo total), pero al ser un repositorio público, expone el endpoint y referencia del proyecto a escaneos automatizados de bots en GitHub.

---

## 🛡️ 3. Recomendaciones y Acciones Correctivas de Robin

1. **Para `automatizaciones_n8n`:**
   - **Opción A (Recomendada):** Sustituir en los archivos JSON de n8n el token quemado por la referencia a variables de credenciales de n8n: `{{ $env.SUPABASE_ANON_KEY }}` o usar nodos nativos de Supabase con credenciales gestionadas en lugar de llamadas HTTP crudas con el Bearer hardcodeado.
   - **Opción B:** Si el proyecto Supabase ya no está activo o es de prueba, rotar la API key desde el panel de Supabase o cambiar la visibilidad del repositorio a Privado.
2. **Para `plataforma-industrial`:**
   - Mantener como buena práctica la parametrización estricta sin fallback de contraseña quemada en `backend_fastapi_main.py`.
3. **Estado del Modo Centinela:** **ACTIVO Y VIGILANTE**. Toda la flota y el perímetro multi-repositorio permanecen monitorizados.

---
**Conexiones:** [[reportes_ciberseguridad]] [[Perfil_Subagente_Ciberseguridad]] [[sistema]] [[Bitacora]]
