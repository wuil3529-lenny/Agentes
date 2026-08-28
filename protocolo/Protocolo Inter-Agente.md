# Protocolo Inter-Agente

## 1. La Pizarra (La_Pizarra.md)
Es el único punto de encuentro y el tablero central de tareas formales (Tickets). Ningún agente asume tareas ocultas.
- **Creación:** Principalmente el Capitán (Luffy) o el Orquestador crea tickets estructurados (ID, Tarea, Responsable, Estado).
- **Comunicación Integrada:** Si un agente tiene dudas, documenta su bloqueo o hallazgo dentro del mismo ticket en la Pizarra.

## 2. El Cerebro (Memoria RAG + Obsidian)
Cuando un agente resuelve un ticket complejo y aprende algo (ej. usando la skill de la memoria viva), genera conocimiento permanente.
La comunicación de ese nuevo conocimiento NO se hace mediante un JSON flotante hacia el otro agente. Se materializa:
1. Creando un nodo Markdown con `**Conexiones:** [[Perfil_Agente]]`.
2. Inyectándolo simultáneamente a ChromaDB.
¡Se escribe en piedra visual (Markdown) para el usuario, y se vectoriza para la memoria colectiva de los LLMs!

## 3. Delegación Limpia y Cierre
Al terminar un trabajo, el subagente (ej. Zoro) cambia el estado en la Pizarra y avisa. El Capitán es el único autorizado a cambiar un ticket a `COMPLETADO` tras verificar estrictamente la evidencia física generada.

---



---
**Pertenece a:** [[Perfil_Luffy]]
