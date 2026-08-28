# Configuración del Sistema (Antigravity 2.0)

El ecosistema centraliza su configuración en las carpetas base de los agentes y en la carpeta `.agents` de cada uno, donde viven sus perfiles JSON y reglas internas.

## 1. LLM y Proveedor
Los agentes de Antigravity operan localmente o usando las credenciales inyectadas al entorno `.env`.

## 2. Motor de Sincronización (sync_cerebro.py)
* **¿Qué hace?** Es el puente que une el mundo de los archivos físicos, Obsidian y ChromaDB.
* **Auto-escaneo:** El script hace un `rglob("*.md")` por todo el ecosistema. Asigna dinámicamente cada archivo de documentación a su agente dueño (ej. inyectando ``).
* **Sincronización RAG:** Toda nota procesada se inyecta en la base de datos de memoria vectorial de los agentes para que aprendan su funcionamiento interno.

## 3. Seguridad
La exposición de tokens en código o el uso de shells sin sanitización son automáticamente bloqueados y reportados al Capitán.

---



---
**Pertenece a:** [[Perfil_Luffy]]
