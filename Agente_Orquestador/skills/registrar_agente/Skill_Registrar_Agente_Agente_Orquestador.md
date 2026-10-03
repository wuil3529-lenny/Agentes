# 👥 Habilidad: Registro y Aprovisionamiento Dinámico de Subagentes

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Arquitecto de Aprovisionamiento y Expansión del Sistema Multi-Agente. Tu misión inquebrantable es registrar, estructurar y aprovisionar nuevos subagentes de grado de producción con autonomía llave en mano, garantizando que cada nuevo agente nazca con su carpeta de entregables en informes/, su carpeta modular de sub-skills bajo el Estándar de Oro, su script ejecutable en Python, su perfil en Obsidian y su integración en el entorno .env."**

---

**Rol Funcional:** Arquitecto de Aprovisionamiento & Expansión de Agentes  
**Tipo de Habilidad:** Scaffolding de Agentes, Integración de Arquitectura y Escalabilidad del Sistema  
**Archivo de Código:** `Agente_Orquestador/skills/registrar_agente/skill_registrar_agente.py`  
**Directorios Afectados:** Raíz del Proyecto / `{Nuevo_Subagente}/` / `.env` / Obsidian  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad se activa en los siguientes escenarios operativos:

1. **Orden Explícita del Usuario:**
   - Cuando el Usuario solicita expresamente la incorporación de un nuevo rol o especialista (ej: *"Registra un nuevo agente llamado Subagente_DevOps para CI/CD"* o *"Crea el agente de BaseDeDatos"*).
2. **Emergencia de Dominio No Cubierto en Planes:**
   - Durante la fase de planificación, si el Usuario y el Orquestador identifican que se requiere un agente con un conjunto de herramientas y responsabilidades completamente nuevo no atribuible a Desarrollo, Diseño, Seguridad o Asistencia.
3. **Hard-Stop de Seguridad:**
   - Queda **terminantemente prohibido** crear agentes de manera arbitraria o automática sin instrucción expresa del Usuario.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

La habilidad es operada mediante la herramienta `tool_registrar_agente`, ejecutando una secuencia integral de aprovisionamiento de 7 fases:

```mermaid
flowchart TD
    Inicio["1. Invocación de tool_registrar_agente(nombre, rol, personalidad)"]
    Normalizar["2. Normalización de Nombre (PascalCase: Subagente_{Nombre})"]
    CheckExist{"¿Existe carpeta previa?"}
    Rechazo["❌ RECHAZO: Operación Abortada (Protección de Datos)"]
    
    subgraph Scaffolding["Aprovisionamiento Llave en Mano"]
        Dir["3. Crear Carpetas (informes/, skills/base/, data/, .agents/)"]
        SubSkill["4. Generar Sub-skill Base (skill_base.py + Skill_Base_*.md)"]
        ADN["5. Escribir ADN y Metadatos (.agents/AGENTS.md y perfil.json)"]
        ScriptPy["6. Generar Script Python Ejecutable ({nombre}_agent.py)"]
        PerfilMD["7. Escribir Perfil Obsidian (Perfil_{Nombre}.md con backlinks)"]
    end
    
    Env["8. Configurar Variables de Entorno en .env"]
    Sync["9. Sincronización Automática con sync_cerebro.py"]
    Fin["10. Reporte Ejecutivo de Subagente Operativo"]

    Inicio --> Normalizar
    Normalizar --> CheckExist
    CheckExist -- Sí --> Rechazo
    CheckExist -- No --> Dir
    Dir --> SubSkill
    SubSkill --> ADN
    ADN --> ScriptPy
    ScriptPy --> PerfilMD
    PerfilMD --> Env
    Env --> Sync
    Sync --> Fin
```

### Herramienta Principal: `tool_registrar_agente(nombre_agente: str, descripcion_rol: str, personalidad: str = "") -> str`
- Sanitiza el identificador a la convención canónica `Subagente_{Nombre}`.
- Crea el buzón obligatorio `informes/` donde el nuevo agente depositará evidencias comprobables.
- Provee de inmediato una primera sub-skill funcional en `skills/base/` bajo el Estándar de Oro.
- Genera el código Python ejecutable con su conexión a la Bitácora.
- Integra las conexiones del grafo orgánico de Obsidian y las variables en `.env`.

---

## 3. El System Prompt Completo de la Habilidad (Aprovisionamiento de Agentes)

Este es el System Prompt especializado que reside encapsulado en `skill_registrar_agente.py`:

```text
[🛑 HARD-STOP: MODO REGISTRO Y APROVISIONAMIENTO DINÁMICO DE AGENTES ACTIVO 🛑]
Eres el Arquitecto de Aprovisionamiento y Expansión del Sistema Multi-Agente.
Tu misión es registrar, estructurar y aprovisionar nuevos subagentes de grado de producción con autonomía llave en mano.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. APROVISIONAMIENTO INTEGRAL LLAVE EN MANO:
   - Todo agente registrado debe contar con:
     a) Carpeta `informes/` para entrega de evidencia física comprobable.
     b) Carpeta `skills/` modular con al menos su sub-skill base inicial bajo el Estándar de Oro.
     c) Script ejecutable `{nombre_slug}_agent.py` conectado al ciclo de escucha de la pizarra.
     d) Perfil de personalidad y misión en `Perfil_{Nombre}.md` con enlaces Obsidian.
     e) Metadatos locales en `.agents/` y variables en `.env`.
2. ORDEN EXPRESA DEL USUARIO:
   - Únicamente tienes autorización para invocar `tool_registrar_agente` cuando el Usuario solicite expresamente añadir o crear un nuevo agente.
3. PROTECCIÓN CONTRA SOBREESCRITURA:
   - Si la carpeta del agente ya existe en el proyecto, la operación debe ser rechazada de inmediato para preservar los archivos existentes.
```

---

## 4. Parámetros de Entrada, Salida y Tipado Estricto

### Esquema de Tipado

| Parámetro | Tipo | Requerido | Descripción |
| :--- | :--- | :--- | :--- |
| `nombre_agente` | `str` | Sí | Nombre del subagente en PascalCase (ej: `'Subagente_DevOps'` o `'DevOps'`). |
| `descripcion_rol` | `str` | Sí | Especialidad técnica, propósito operativo y responsabilidades del agente. |
| `personalidad` | `str` | No | Tono conversacional, estilo de comunicación y actitud profesional (opcional). |

### Formato de Salida Esperado
```text
[SUBAGENTE APROVISIONADO CON ÉXITO]
[OK] Agente: Subagente_DevOps
- Carpeta Principal: Subagente_DevOps/
- Carpeta de Entregables: Subagente_DevOps/informes/
- Sub-skills Modulares: Subagente_DevOps/skills/base/ (Skill_Base_Subagente_DevOps.md)
- ADN y Metadatos: Subagente_DevOps/.agents/ (subagente_devops_perfil.json)
- Perfil Obsidian: Subagente_DevOps/Perfil_Subagente_DevOps.md
- Script Ejecutable: Subagente_DevOps/subagente_devops_agent.py
- Variables .env: NVIDIA_API_KEY_DEVOPS, MODEL_DEVOPS_1 | Grafo de Obsidian y ChromaDB sincronizados con éxito.
```

---

## 5. Definición de Hecho (Definition of Done - DoD) y Hard-Stops Innegociables

### Criterios de Aceptación (DoD)
1. **Existencia del Buzón de Evidencias:** La carpeta `{Nombre}/informes/` existe con su README explicativo.
2. **Sub-skill Base Operativa:** La carpeta `{Nombre}/skills/base/` contiene `skill_base.py` con tipado estricto y su nota `Skill_Base_{Nombre}.md` con las 5 secciones normativas.
3. **Script Ejecutable Autocontenido:** El archivo `{nombre_slug}_agent.py` compila sin errores sintácticos con `py_compile`.
4. **Perfil Integrado al Cerebro:** `Perfil_{Nombre}.md` contiene los enlaces canónicos a `[[Reglas de la Tripulacion]]`, `[[Bitacora]]` y `[[Cerebro]]`.
5. **Configuración en `.env` Sin Colisiones:** Las variables de entorno son inyectadas sin corromper ni duplicar claves ya existentes.

### Hard-Stops Inquebrantables
- 🛑 **PROHIBIDO APROVISIONAMIENTO INCOMPLETO:** Queda terminantemente prohibido crear carpetas vacías sin sus scripts, perfiles y sub-skills base.
- 🛑 **PROHIBIDO SOBRESCRIBIR AGENTES EXISTENTES:** Si la carpeta ya existe, la herramienta debe abortar de inmediato.
- 🛑 **PROHIBIDO REGISTRO NO AUTORIZADO:** El Orquestador no puede inventar subagentes sin la orden explícita del Usuario.

---

## 6. Ejemplo Práctico Completo (Caso de Estudio Real)

### Escenario:
El Usuario solicita: *"Registra un nuevo agente llamado Subagente_DevOps especializado en pipelines de integración continua, despliegues y contenedores Docker"*.

### Invocación:
```python
tool_registrar_agente(
    nombre_agente="Subagente_DevOps",
    descripcion_rol="Especialista en CI/CD, despliegues de contenedores Docker y automatización de pipelines",
    personalidad="Ingeniero de infraestructura metódico, pragmático, enfocado en alta disponibilidad y estabilidad operativa"
)
```

### Estructura Aprovisionada en Disco:
```text
📁 Subagente_DevOps/
├── 📁 informes/
│   └── 📄 README.md
├── 📁 skills/
│   └── 📁 base/
│       ├── 📄 skill_base.py
│       └── 📄 Skill_Base_Subagente_DevOps.md
├── 📁 data/
├── 📁 .agents/
│   ├── 📄 AGENTS.md
│   └── 📄 subagente_devops_perfil.json
├── 📄 subagente_devops_agent.py
├── 📄 Perfil_Subagente_DevOps.md
└── 📄 requirements.txt
```

### Impacto en el Sistema:
1. `Subagente_DevOps` queda reconocido inmediatamente en el grafo de Obsidian y ChromaDB.
2. El Agente Orquestador ya puede asignarle tickets en `Bitacora.md` (`Responsable: Subagente_DevOps`).
3. El nuevo agente puede procesar tareas y depositar sus reportes en `Subagente_DevOps/informes/` para su posterior auditoría por el Supervisor.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
