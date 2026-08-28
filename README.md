# 🏴‍☠️ Tripulación IA (Arquitectura V3)

![Tripulación IA](https://img.shields.io/badge/Sistema-MultiAgente-blue)
![Arquitectura](https://img.shields.io/badge/Arquitectura-LangGraph%20%7C%20Docker-orange)
![Memoria](https://img.shields.io/badge/Memoria-Obsidian%20RAG-purple)

Bienvenido al repositorio central de la **Tripulación IA (V3)**, un ecosistema multi-agente hiper-especializado diseñado para automatizar desarrollo, diseño, seguridad, DevOps y tareas administrativas, orquestado bajo el concepto de la tripulación de los Sombrero de Paja.

## 🧠 Arquitectura del Sistema
Este ecosistema ya no opera mediante llamadas aisladas; ha evolucionado a la **Arquitectura V3**, que se caracteriza por:
1. **Orquestador Asíncrono**: Ejecutado en Docker (`tripulacion_ia_v3`), gestionando grafos conversacionales asíncronos mediante LangGraph.
2. **Memoria Fractal (Obsidian RAG)**: Los agentes se comunican de forma asíncrona leyendo y escribiendo en archivos `.md`. Obsidian actúa como una red neuronal visual donde los agentes conectan nodos conceptuales, bitácoras de errores e informes.
3. **Punteros Lógicos**: Para sortear los límites de tokens, los agentes no se envían el código entero. Se pasan rutas locales de archivos ("punteros") y modifican el código directamente en el disco.

## 👥 Miembros de la Tripulación

Cada agente tiene su propia carpeta, herramientas exclusivas (Skills), y un perfil JSON protegido:

* 👒 **Luffy (El Capitán - Orquestador)**: Encargado de hablar con el usuario, diseccionar el proyecto, evaluar qué agente debe intervenir (basado en sus perfiles JSON dinámicos) y gestionar el plan maestro. No programa, dirige.
* ⚔️ **Zoro (El Espadachín - Desarrollador Backend/DevOps)**: El hacker. Domina Python, Docker, automatización, n8n, manejo de APIs, integraciones y bases de datos. Si rompe el código, Sanji o Robin lo corrigen.
* 🗺️ **Nami (La Navegante - Frontend & UI/UX)**: Especialista en diseño visual, TailwindCSS, prototipos web autocontenidos (`index.html`) y búsqueda de referencias visuales. Sus interfaces siempre deben poder previsualizarse.
* 🚬 **Sanji (El Cocinero - QA & Automatización de Oficina)**: Maestro en el escaneo de correos, gestión de Google Calendar, Google Docs y revisión de PDFs. También se encarga de probar que el código de Zoro no esté en llamas.
* 📚 **Robin (La Arqueóloga - Arquitectura & Seguridad)**: Auditora profunda del sistema. Vela por las buenas prácticas, escanea vulnerabilidades, protege secretos en `.gitignore` y diseña arquitecturas complejas de software.
* 🎯 **Usop (El Francotirador - Marketing / Growth)**: (En desarrollo) Tareas de posicionamiento, SEO y marketing orgánico.

## 🛠️ Herramientas (Skills)
El poder real de la tripulación radica en el sistema de **Skills**. Cada agente tiene su carpeta `/skills/` donde viven herramientas altamente específicas (como buscar en DuckDuckGo, crear Nodos en Obsidian, interactuar con el CLI de ngrok, etc.).

El script `sync_cerebro.py` escaneará estas habilidades y generará los nodos `.md` automáticamente en el grafo de Obsidian, atándolos al ADN del agente correspondiente.

## 🚀 Instalación y Despliegue

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/wuil3529-lenny/Agentes.git
   cd Agentes
   ```
2. **Configurar el Entorno**:
   Crea un archivo `.env` en la raíz (está ignorado en git por seguridad) usando las llaves necesarias:
   ```env
   # Ejemplo
   NVIDIA_API_KEY_LUFFY=your_key_here
   NVIDIA_API_KEY_ZORO=your_key_here
   # ...
   ```
3. **Arrancar el Motor (Docker)**:
   Asegúrate de que Docker Desktop esté encendido y corre:
   ```bash
   docker-compose up -d
   ```
4. **Sincronizar Cerebro (Opcional)**:
   ```bash
   python Luffy/sync_cerebro.py
   ```

## 🔒 Seguridad (Protocolo Robin)
Los siguientes elementos **JAMÁS** deben subirse a este repositorio:
* Archivos `.env` o credenciales.
* Perfiles personales del usuario (`memoria_compartida/perfiles/Perfil de wuil.*`).
* La carpeta `memoria_compartida/` ni `Archivos_temporales/`.
* Bases de datos locales de los agentes.

---
*Este repositorio es mantenido de forma conjunta por el usuario humano (Capitán Wuilfredo) y el sistema Antigravity / Ygris.*
