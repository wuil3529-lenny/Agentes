# Configuración del Sistema (Antigravity 2.0)

El ecosistema centraliza su configuración operativa en variables de entorno (`.env`), en los archivos de identidad maestros (`_agents/agente.md`) de cada agente y en los protocolos globales de gobernanza.

---

## 1. Variables de Entorno y Conectividad (`.env`)

Los agentes operan de manera agnóstica respecto al proveedor de inteligencia artificial gracias al soporte multi-modelo:
- **Proveedores LLM Soportados:** OpenAI (`gpt-4o`, `gpt-4o-mini`), DeepSeek (`deepseek-chat`, `deepseek-reasoner`), NVIDIA NIM, Ollama local.
- **Rutas Base:** Configuración de paths de ejecución unificados compatibles con Windows y Linux (`/app/` en contenedores Docker).
- **Ruta de Memoria:** Variable `MEMORIA_DIR` configurada estrictamente apuntando a `memoria/` (sustituyendo de forma permanente cualquier referencia a `memoria_compartida`).
- **Credenciales Externas:** Tokens de Telegram, credenciales de servicios Cloud (Google Workspace), Sentry DSN y webhooks de n8n.

---

## 2. Fuente Única de Verdad de Identidad (`_agents/agente.md`)

Cada agente posee un archivo Markdown canónico que define su personalidad, restricciones y rol:
- **Ubicación Canónica:** `<Nombre_Agente>/_agents/agente.md` (o fallback `.agents/agente.md`).
- **Cargador Dinámico (`identidad_agentes.py`):** Lee en tiempo real el nombre asignado por el usuario, el rol profesional y los alias de enrutamiento para la Pizarra y la consola web.
- **Cero Acoplamiento:** Permite renombrar a los agentes sin alterar la lógica interna de los scripts ni las rutas físicas de trabajo.

---

## 3. Motor de Calidad y Resiliencia (`Agente_Orquestador/`)

La flota cuenta con capas transversales de control configuradas de manera predeterminada:
- **`qa_gherkin.py`:** Doble validación obligatoria (Capa 1: Red/Infraestructura y Capa 2: Contenido/Cumplimiento de objetivos del ticket).
- **`bucle_autocorreccion.py`:** Filtro anti-bucle (Pilar 3) que congela herramientas invocadas repetitivamente con los mismos argumentos, clasificador de causa raíz (`_clasificar_error`) y escalado automático al tercer reintento fallido.

---

## 4. Motor de Sincronización (`sync_cerebro.py`)

- **¿Qué hace?** Es el puente que une los archivos físicos en disco, el grafo de conocimiento en Obsidian y la memoria vectorial en ChromaDB.
- **Auto-escaneo:** Realiza un escaneo recursivo (`rglob("*.md")`) de la tripulación, saneando enlaces rotos y asignando la gravedad jerárquica de cada nota a su agente responsable.
- **Sincronización RAG:** Si la variable `ENABLE_RAG_SYNC=1` está activa, vectoriza los documentos técnicos para permitir recuperación semántica de *Playbooks* por similitud de cosenos.

---

## 5. Gobernanza y Seguridad Zero-Trust

- **Firewall de Rutas:** Restricción estricta de escritura a las carpetas autorizadas de cada agente (`proyectos/`, `informes/`, `reportes/`, `documentos_asistencia/`, `memoria/`, `Archivos_temporales/`).
- **Detección de Secretos:** Bloqueo y saneamiento de credenciales expuestas en texto plano antes de persistir o reportar evidencia.
- **Auditoría Física Obligatoria:** Ningún ticket pasa a estado `CERRADO` sin inspección física en disco del archivo de entrega y comprobación de su marca temporal de modificación.

---
**Conexiones:** [[sistema]]
