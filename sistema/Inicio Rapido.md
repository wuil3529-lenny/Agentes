# Inicio Rápido (Antigravity 2.0)

## 1. Levantamiento del Sistema
El ecosistema es autónomo. Al iniciar la ejecución del contenedor del agente principal o de cualquier tarea, el sistema llama a la función de inicialización y se auto-sincroniza.

## 2. Sincronización Automática
Cada vez que el contenedor despierta o la clase principal de la tripulación se instancia (Luffy), se ejecuta automáticamente `sync_cerebro.py`. No necesitas correrlo manualmente a menos que hagas un cambio grande en caliente.
1. Creará archivos `.md` para representar visualmente cualquier `.py` (skill) nuevo.
2. Atrapará y enlazará archivos de manuales que hayas puesto en la carpeta de un agente.
3. Actualizará la base de datos vectorial RAG con los últimos cambios.

## 3. Cómo añadir nuevo conocimiento manual
Simplemente crea un archivo de texto con extensión `.md` (Ejemplo: `guia_n8n.md`) y guárdalo dentro de la carpeta del agente al que le corresponda (Ejemplo: `C:\Users\admin\Documents\Agentes\Zoro\`). El sistema hará el resto. Obsidian dibujará la línea de conexión, y el agente lo aprenderá en su RAG.

---



---
**Pertenece a:** [[Perfil_Luffy]]
