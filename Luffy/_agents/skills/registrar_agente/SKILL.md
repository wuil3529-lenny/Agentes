---
name: registrar-agente
description: Guía y protocolo paso a paso para registrar un nuevo agente en la tripulación (V3).
---

# 📝 Cómo Registrar un Agente

## Cuándo usar esta habilidad (Gatillo)
Debes usar esta habilidad **únicamente** cuando el usuario (Capitán Wuilfredo) te ordene explícitamente añadir, crear, invocar o registrar un nuevo agente para la tripulación (por ejemplo: "Luffy, registra un nuevo agente llamado Franky").

## Cómo usarla
1. Asegúrate de tener el nombre del agente en PascalCase (Ej. `Franky`) y una breve descripción de sus capacidades o rol.
2. Invoca la herramienta `tool_registrar_agente(nombre_agente="Franky", descripcion_rol="Ingeniero y constructor de barcos")` desde tu archivo `luffy_agent.py`.
3. La herramienta se encargará automáticamente de crear las carpetas, los perfiles y el archivo de instrucciones base.
4. Una vez que la herramienta responda, notifica al usuario que el agente ha sido registrado con éxito y que debe agregarlo al motor de ejecución.

---
*(A continuación, el protocolo interno que ejecuta la herramienta bajo el capó en la Arquitectura V3)*

Para añadir un nuevo agente a la tripulación, la arquitectura exige los siguientes pasos. Todo funciona a base de carpetas y lectura de memoria (RAG / JSON).

## 1. Crear el Espacio Local del Agente
1. Ve a la raíz del sistema `C:\Users\admin\Documents\Agentes\`.
2. Crea una carpeta nueva con el Nombre exacto del Agente en PascalCase (ej. `Franky\`).
3. Crea la subcarpeta `.agents\` dentro de la carpeta del agente.
4. Crea el archivo `.agents\AGENTS.md` para que Antigravity cargue el contexto correcto.

## 2. Crear su ADN (Perfil)
1. Dentro de `.agents\`, crea el archivo JSON de sus capacidades (ej. `franky_perfil.json`).
2. En la misma carpeta `.agents\`, crea el nodo interno en mayúsculas (ej. `FRANKY.md`).
3. En la **raíz de la carpeta del agente**, crea su perfil principal (ej. `Perfil_Franky.md`) con las conexiones a `[[Reglas de la Tripulacion]]`, `[[Bitacora]]` y `[[Cerebro]]`. Este archivo será leído por `sync_cerebro.py`.

## 3. Configurar el `.env`
Añade las variables de API key y modelos del agente en `C:\Users\admin\Documents\Agentes\.env`.

## 4. Actualizar el Motor (Tripulacion IA V3)
El motor de Docker (`tripulacion_ia_v3`) debe reiniciarse. Además, el script principal del agente (`franky_agent.py`) debe crearse basándose en las plantillas de LangGraph que usan los otros agentes.

---
**Pertenece a:** [[Perfil_Luffy]]
