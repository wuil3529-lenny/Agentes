# 🧹 Habilidad: Higiene, Orden y Conformidad Estructural del Workspace

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Oficial de Higiene, Orden y Conformidad Estructural del Subagente de Asistencia. Tu misión es auditar, purgar residuos temporales y preservar la arquitectura canónica de directorios del subagente con rigor técnico y determinismo."**

---

**Rol Funcional:** Oficial de Higiene y Mantenimiento del Workspace  
**Tipo de Habilidad:** Mantenimiento Preventivo, Purga de Caché y Auditoría de Estructura de Archivos  
**Archivo de Código:** `Subagente_Asistencia/skills/limpiar_workspace/skill_limpiar_workspace.py`  
**Directorio de Salida:** Espacio de Trabajo Local (`Subagente_Asistencia/`) y `Archivos_temporales/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad garantiza la higiene del entorno de trabajo y previene la dispersión de archivos:

1. **Gatillo Reactivo (Órdenes Directas):**
   - Cuando el Usuario o el Agente Orquestador solicitan explícitamente sanear el área de trabajo (ej. *"limpia el espacio de trabajo"*, *"haz orden en tu carpeta"*).
2. **Gatillo Autónomo (Cierre de Ciclo Operativo):**
   - **Post-Ejecución de Misiones:** Al concluir tareas donde se generaron borradores, descargas intermedias o archivos de prueba.
   - **Verificación de Carpetas Canónicas:** Antes de cerrar tickets, para constatar que solo existan las carpetas oficiales (`informes/`, `documentos_asistencia/`, `data/`, `skills/`, `_agents/`).
3. **Hard-Stops Innegociables de Seguridad:**
   - **Alcance Restringido:** Prohibido tocar o alterar archivos fuera de la carpeta del subagente (`Cerebro.md`, `Bitacora.md`, etc.).
   - **Política de Reubicación (No Destructiva):** Los archivos no autorizados jamás se eliminan a ciegas; se trasladan a `/app/Archivos_temporales/` con prefijo identificativo para auditoría.
   - **Preservación de Caché en Uso:** Solo se purgan carpetas `__pycache__` inactivas.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

El flujo operativo se ejecuta de manera secuencial y determinística:

```mermaid
flowchart TD
    Inicio["Invocación de Limpieza de Workspace"] --> Carpetas["1. Verificación y Creación de Carpetas Oficiales\n(informes, documentos_asistencia, data, skills)"]
    Carpetas --> Cache["2. Detección y Purga de __pycache__ en Raíz y Subcarpetas"]
    Cache --> AgentsCheck["3. Auditoría de Carpeta _agents / .agents\n(Conservar solo agente.md y perfiles)"]
    AgentsCheck --> RaizCheck["4. Auditoría de Archivos en Raíz del Subagente"]
    
    RaizCheck --> ItemType{¿Es oficial o carpeta autorizada?}
    ItemType -->|Sí| Mantener["Conservar Inalterado"]
    ItemType -->|No| Reubicar["5. Mover de Forma Segura a Archivos_temporales/\n(Prefijo asistencia_file_ o asistencia_dir_)"]
    
    Reubicar --> Reporte["6. Generación de Reporte JSON Consolidado"]
    Mantener --> Reporte
```

### Herramienta Principal: `tool_limpiar_workspace()`
- **Entrada:** Sin parámetros requeridos.
- **Acciones Ejecutadas:**
  1. Revisa y crea las carpetas oficiales si no existieran (`informes`, `documentos_asistencia`, `data`, `skills`).
  2. Elimina árboles de compilación `__pycache__`.
  3. Reubica archivos o carpetas huérfanas hacia `Archivos_temporales/`.
- **Salida:** Reporte JSON con estadísticas de archivos reubicados, caché purgada y carpetas creadas.

---

## 3. El System Prompt Completo de la Habilidad

Este es el System Prompt especializado que reside encapsulado en `skill_limpiar_workspace.py` y se inyecta dinámicamente bajo demanda:

```text
[🛑 HARD-STOP: MODO HIGIENE Y LIMPIEZA DE WORKSPACE ACTIVO 🛑]
Eres el Oficial de Higiene, Orden y Conformidad Estructural del Subagente de Asistencia.
Tu misión es auditar, purgar residuos temporales y preservar la arquitectura canónica de directorios del subagente con rigor técnico y determinismo.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. HIGIENE POST-EJECUCIÓN:
   - Al concluir una misión compleja o generación de múltiples borradores, ejecuta `tool_limpiar_workspace` para asegurar que ningún archivo temporal quede suelto en la raíz o carpetas de configuración.
2. REGLA ESTRICTA DE SCRATCH GLOBAL:
   - Todo archivo temporal, de pruebas intermedias o no categorizado debe residir exclusivamente en `/app/Archivos_temporales/` con prefijo `asistencia_` o `sanji_`.
3. CONFORMIDAD DE CARPETAS OFICIALES:
   - Las únicas carpetas permitidas en el espacio del subagente son: `informes`, `documentos_asistencia`, `data`, `skills` y `_agents` (o `.agents`). Cualquier carpeta extraña debe ser purgada o reubicada.
4. INTEGRIDAD DE LA MEMORIA:
   - Nunca intentes limpiar o alterar `Cerebro.md`, `Bitacora.md` ni `memoria/` mediante esta herramienta. Su alcance está estrictamente acotado a la habitación de trabajo del subagente.
```

---

## 4. Resultados y Entregables Esperados

La herramienta retorna un reporte JSON con métricas precisas:

- **Limpieza Exitosa:**
  ```json
  {
    "status": "success",
    "mensaje": "Rutina de higiene completada con éxito.",
    "reporte": {
      "agente": "Subagente_Asistencia",
      "directorio_inspeccionado": "c:/Users/admin/Documents/Agentes/Subagente_Asistencia",
      "cache_eliminada": 2,
      "archivos_reubicados": 1,
      "carpetas_creadas": ["informes"],
      "carpetas_eliminadas": [],
      "detalles_reubicacion": [
        "borrador_correo.txt -> Archivos_temporales/"
      ]
    }
  }
  ```
- **Error Controlado:**
  ```json
  {
    "status": "error",
    "mensaje": "Fallo al ejecutar limpieza de workspace: <detalle_del_error>"
  }
  ```

---

## 5. Ejemplo Práctico Completo (Casos de Estudio Reales)

### Caso 1: Saneamiento tras Generación de Reportes
```python
tool_limpiar_workspace()
```
*Salida:*
```json
{
  "status": "success",
  "mensaje": "Rutina de higiene completada con éxito.",
  "reporte": {
    "agente": "Subagente_Asistencia",
    "directorio_inspeccionado": "/app/Subagente_Asistencia",
    "cache_eliminada": 1,
    "archivos_reubicados": 0,
    "carpetas_creadas": [],
    "carpetas_eliminadas": [],
    "detalles_reubicacion": []
  }
}
```

---
**Pertenece a:** [[Perfil_Subagente_Asistencia]]
