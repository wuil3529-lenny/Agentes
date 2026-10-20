# 🏴‍☠️ Tripulación IA (Arquitectura Multi-Agente V3)

![Sistema](https://img.shields.io/badge/Sistema-MultiAgente%20Aut%C3%B3nomo-blue?style=flat-square)
![Arquitectura](https://img.shields.io/badge/Arquitectura-LangGraph%20%7C%20Docker%20Sandbox-orange?style=flat-square)
![Memoria](https://img.shields.io/badge/Memoria-Obsidian%20Fractal%20%2B%20ChromaDB-purple?style=flat-square)
![Dashboard](https://img.shields.io/badge/UI-Cyberpunk%20Real--Time%20Dashboard-00f0ff?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Healthy-brightgreen?style=flat-square)

Bienvenido al repositorio central de la **Tripulación IA (Arquitectura V3)**, un ecosistema multi-agente hiper-especializado diseñado para automatizar desarrollo de software, diseño de interfaces, auditoría de seguridad, automatizaciones DevOps y asistencia técnica, operando bajo un entorno coordinado de orquestación autónoma.

---

## 🧠 Arquitectura del Sistema

El ecosistema opera bajo un modelo de alta confiabilidad y confinamiento estricto:

1. **Orquestación Asíncrona On-Demand (Spawn $\rightarrow$ Exec $\rightarrow$ Kill):** Ejecutado en Docker (`tripulacion_ia_v3`) mediante LangGraph. Los subagentes no consumen recursos en bucles ociosos continuos; son instanciados dinámicamente cuando existe un ticket activo en la Pizarra y finalizan al entregar evidencia física verificada.
2. **Memoria Fractal Bifocal (Obsidian + ChromaDB):** 
   - **Vista Humana:** Grafo relacional visual en Markdown donde cada agente, habilidad, proyecto y reporte conforma un nodo interconectado (0 enlaces rotos).
   - **Subconsciente LLM:** Inyección vectorial automática en ChromaDB (`all-MiniLM-L6-v2`) para consultas semánticas y RAG de habilidades.
3. **Patrón de Punteros Lógicos y Evidencia Física:** Para sortear los límites de contexto de los modelos LLM, los agentes nunca transmiten código masivo en JSON. Trabajan directamente sobre archivos en el disco y devuelven rutas físicas absolutas (`/app/...`) como comprobante de entrega.
4. **Hard Stop Estricto (Confinamiento de Rutas):** Políticas a nivel de ejecución que impiden que los subagentes escriban fuera de sus carpetas asignadas, previniendo sobreescrituras accidentales y contención de fallos.
5. **Auditoría Gherkin y Auto-Curación:** Pruebas de calidad y bucles de auto-diagnóstico con recarga en caliente de módulos ante excepciones controladas.

---

## 👥 Estructura Oficial de la Tripulación

El sistema utiliza nombres canónicos funcionales y profesionales, manteniendo compatibilidad transparente con los alias históricos del proyecto:

| Agente Canónico | Carpeta Oficial | Rol Principal y Especialidad | Alias Histórico |
| :--- | :--- | :--- | :--- |
| **Agente Orquestador** | [`Agente_Orquestador/`](file:///c:/Users/admin/Documents/Agentes/Agente_Orquestador) | Dirección estratégica, descomposición de proyectos, gestión de la Pizarra, validación de evidencia y comunicación con el usuario. | *Luffy* |
| **Subagente de Desarrollo** | [`Subagente_Desarrollo/`](file:///c:/Users/admin/Documents/Agentes/Subagente_Desarrollo) | Desarrollo Full-Stack, backend en Python, flujos avanzados en n8n, integración de APIs, bases de datos SQLite y scripting DevOps. | *Zoro* |
| **Subagente de Diseño** | [`Subagente_Diseno/`](file:///c:/Users/admin/Documents/Agentes/Subagente_Diseno) | Arquitectura Frontend, UI/UX, prototipos web autocontenidos (`index.html`), guiones audiovisuales multiplataforma y dirección artística con IA. | *Nami* |
| **Subagente de Ciberseguridad** | [`Subagente_Ciberseguridad/`](file:///c:/Users/admin/Documents/Agentes/Subagente_Ciberseguridad) | Auditoría de vulnerabilidades, análisis estático, detección de secretos, saneamiento de `.gitignore` y cumplimiento de seguridad. | *Robin* |
| **Subagente de Asistencia** | [`Subagente_Asistencia/`](file:///c:/Users/admin/Documents/Agentes/Subagente_Asistencia) | Procesamiento y lectura segura de PDFs (con sanitización contra path traversal), Google Workspace, clima y base de conocimiento. | *Sanji* |

---

## 📂 Estructura de Directorios

```plaintext
Agentes/
├── Agente_Orquestador/          # Núcleo director (base_listener, memory, sync_cerebro, qa_gherkin, bucle_autocorreccion)
│   ├── _agents/                 # Identidad maestra canónica (agente.md)
│   └── skills/                  # Habilidades estratégicas (entrevistador, plan, supervisor, sentry)
├── Subagente_Desarrollo/        # Entorno de desarrollo de software (subagente_desarrollo_agent, 21 skills)
│   ├── _agents/                 # Identidad maestra canónica (agente.md)
│   ├── proyectos/               # Entregables de código y aplicaciones construidas
│   └── skills/                  # Habilidades de software, git, web, n8n, frontend y sentry
├── Subagente_Diseno/            # Entorno de UI/UX y producción multimedia (subagente_diseno_agent, 12 skills)
│   ├── _agents/                 # Identidad maestra canónica (agente.md)
│   ├── informes/                # Entregables visuales, feeds, vídeo, Marp y brand book
│   └── skills/                  # Habilidades de renderizado local, vídeo, edición y presentaciones
├── Subagente_Ciberseguridad/    # Entorno de seguridad, SAST y SOC (subagente_ciberseguridad_agent, 9 skills)
│   ├── _agents/                 # Identidad maestra canónica (agente.md)
│   ├── reportes/                # Dictámenes e informes formales de auditoría y análisis de riesgos
│   └── skills/                  # Escáneres de seguridad, auditoría SAST/SCA y contención
├── Subagente_Asistencia/        # Entorno de asistencia ejecutiva y Workspace (subagente_asistencia_agent, 13 skills)
│   ├── _agents/                 # Identidad maestra canónica (agente.md)
│   ├── documentos_asistencia/   # Documentos ejecutivos, minutas técnicas y resúmenes ofimáticos
│   └── skills/                  # Lector de PDFs, Google Workspace, clima y mensajería
├── dashboard/                   # Panel de control web (FastAPI, WebSockets, Tailwind UI)
├── memoria/                     # Base de conocimiento persistente (Tickets_Archivados, Perfil de wuil, memoria, Memoria_Viva_Errores)
├── protocolo/                   # Directivas, reglas de conducta y protocolos inter-agente
├── sistema/                     # Biblioteca de documentación de arquitectura, seguridad y scripts
├── Bitacora.md                  # La Pizarra: gestor de tareas y tickets activos
├── Cerebro.md                   # Índice cronológico central de memoria viva
├── docker-compose.yml           # Configuración del contenedor aislado tripulacion_ia_v3
├── Dockerfile                   # Imagen base Debian Bookworm Thin + Python 3.11 + Node.js
└── start.sh                     # Script de arranque y monitorización del ecosistema
```

---

## 🎛️ Panel de Control Cibernético (Dashboard)

El sistema incluye una interfaz web operativa en tiempo real:
- **Tecnología:** FastAPI + WebSockets con frecuencia de refresco de 1 segundo.
- **Estilo Visual:** Paleta cibernética de alto contraste (fondo oscuro con acentos cian, fucsia y cobalto) optimizada para sesiones operativas intensivas.
- **Módulos:**
  - Pizarra de tickets interactiva (creación, asignación y auditoría de estado).
  - Estado en vivo de cada uno de los 5 agentes (activo, en espera, trabajando).
  - Monitoreo de recursos del sistema (CPU, memoria, GPU).
  - Historial de incidentes de seguridad y alertas en tiempo real.
  - Métricas de consumo de tokens y presupuesto financiero mensual.

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/wuil3529-lenny/Agentes.git
cd Agentes
```

### 2. Configurar variables de entorno
Crea un archivo `.env` en la raíz del proyecto basándote en las claves necesarias:
```env
# API Keys LLM
NVIDIA_API_KEY_LUFFY=tu_api_key_aqui
NVIDIA_API_KEY_ZORO=tu_api_key_aqui
NVIDIA_API_KEY_NAMI=tu_api_key_aqui
NVIDIA_API_KEY_ROBIN=tu_api_key_aqui
NVIDIA_API_KEY_SANJI=tu_api_key_aqui

# Integraciones Opcionales
TELEGRAM_BOT_TOKEN=tu_token_telegram
N8N_BASE_URL=http://host.docker.internal:5678
```

### 3. Iniciar el Sandbox en Docker
Asegúrate de que Docker Desktop esté en ejecución y lanza:
```bash
docker compose up -d
```
Verifica que el contenedor esté saludable:
```bash
docker compose ps
```

### 4. Iniciar el Dashboard Web
En la máquina host (Windows), ejecuta el panel de control:
```bash
python dashboard/app.py
```
Accede desde tu navegador a `http://127.0.0.1:8000`.

### 5. Sincronizar el Grafo de Obsidian (Opcional)
Para regenerar los enlaces del grafo y la memoria vectorial en cualquier momento:
```bash
python Agente_Orquestador/sync_cerebro.py
```

---

## 🔒 Protocolo de Seguridad y Buenas Prácticas

- **Secretos:** Queda terminantemente prohibido versionar archivos `.env`, tokens privados o claves de API.
- **Aislamiento:** Todo script generado por los agentes se ejecuta en el contenedor Docker bajo un usuario no-root (`tripulacion`).
- **Sanitización de Archivos:** Las herramientas de lectura de archivos e ingesta de PDFs validan límites de tamaño (50 MB) y pertenencia a directorios autorizados, neutralizando ataques de Path Traversal.

---

*Desarrollado y mantenido por Wuilfredo en colaboración con el sistema multi-agente Antigravity 2.0.*

---
**Conexiones:** [[sistema]]
