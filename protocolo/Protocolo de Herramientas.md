# Protocolo para Crear e Integrar Nuevas Skills/Herramientas

Este documento establece el estándar obligatorio para añadir capacidades al Gemelo Digital (El ecosistema RAG + Obsidian).

## Paso 1: Definición de la Herramienta (Código)
Toda herramienta es un script funcional en Python (ej. `skill_video.py`) que debe vivir en la carpeta `skills/` del agente correspondiente (Ej. `Agentes/Nami/skills/`). La función debe estar rigurosamente tipada y jamás arrojar excepciones no controladas.

## Paso 2: El Reflejo Visual y de Memoria (Automático)
Una vez que dejas el archivo `.py` correctamente estructurado en su carpeta, **¡no tienes que crear el nodo de Obsidian a mano!**
El motor `sync_cerebro.py` escaneará automáticamente la carpeta en el próximo reinicio, encontrará tu nueva skill, generará el archivo espejo visual (Ej. `Skill_Video_Nami.md`), y lo enlazará automáticamente a `[[Perfil_Nami]]` para que orbite a su alrededor en Obsidian. Al mismo tiempo lo insertará en el RAG para que Nami sea consciente de él.

## Paso 3: Catálogo Few-Shot (Perfil JSON)
Abre el perfil interno del agente (`.agents/nami_perfil.json`) y documenta allí el uso de la herramienta. Describe exactamente bajo qué circunstancias el agente debe usarla para evitar alucinaciones, y provee un ejemplo claro del "gatillo" en el sistema.

---



---
**Pertenece a:** [[Perfil_Luffy]]
