# Arquitectura del Sistema (Antigravity 2.0)

El ecosistema multi-agente está diseñado como un **Gemelo Digital Vivo (RAG + Obsidian)**, operando bajo la estricta **Arquitectura de Nodos y Órbitas**. Queda prohibida la comunicación asíncrona no rastreable.

## 1. El Capitán (Orquestador)
**Luffy** actúa como el núcleo orquestador. Él es el responsable global del sistema y mantiene amarrados los nodos globales (Bitácora, Cerebro, Protocolos, Sistema) a su perfil en Obsidian. Los demás agentes (Zoro, Nami, Robin, Sanji) operan como sub-nodos especializados.

## 2. El Gemelo Digital (La Memoria Bifocal)
El ecosistema sincroniza la información simultáneamente en dos frentes matemáticamente idénticos mediante `sync_cerebro.py`:
1. **La Vista Humana (Grafo de Obsidian):** Cada agente tiene su archivo `Perfil_Agente.md`. Las herramientas (`skills`) y archivos manuales se enlazan orgánicamente a cada agente.
2. **El Subconsciente LLM (ChromaDB Vector RAG):** Al mismo tiempo, esos nodos Markdown se inyectan a la base de datos vectorial (`all-MiniLM-L6-v2`), permitiendo que los agentes entiendan su propia estructura, herramientas y perfiles sin alucinar.

## 3. Protocolo de Coordinación (La Pizarra)
**La Pizarra (`La_Pizarra.md`):** Único punto de encuentro y gestión operativa. Las delegaciones se escriben físicamente aquí como "Tickets" (ej. `## TKT-XXX`).

## 4. Estructura de Directorios (Mundo Físico)
Los agentes viven confinados en sus propias carpetas, manteniendo una estructura estricta (`.agents`, `skills`, `informes`). Todo archivo Markdown (`.md`) suelto dentro de estas carpetas es atrapado automáticamente por el script de sincronización y amarrado a la gravedad de ese agente.

---



---
**Pertenece a:** [[Perfil_Luffy]]
