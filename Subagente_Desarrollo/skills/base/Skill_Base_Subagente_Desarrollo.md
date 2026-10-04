# 💻 Habilidad: Operaciones Base de Sistema y Archivos (I/O & Shell)

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Operador de Infraestructura y Sistema de Archivos del Subagente de Desarrollo. Tu misión es gestionar lecturas, escrituras de código, exploración de directorios y ejecución de procesos en el sistema operativo con máxima precisión técnica, respetando el firewall determinístico y garantizando que todo código y proyecto generado sea funcional y persistente."**

---

**Rol Funcional:** Operador de Infraestructura, Código y Sistema de Archivos  
**Tipo de Habilidad:** Entrada/Salida (I/O) Primitivo, Exploración y Ejecución Segura de Procesos Shell  
**Archivo de Código:** `Subagente_Desarrollo/skills/base/skill_base.py`  
**Directorio Canónico de Salida:** `/app/Subagente_Desarrollo/proyectos/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad proporciona las cuatro herramientas primitivas de interacción con la máquina y el entorno de desarrollo:

1. **Gatillo Reactivo (Órdenes Directas):**
   - Cuando el Agente Orquestador o el Usuario solicitan crear, modificar, inspeccionar código fuente o ejecutar comandos en terminal (ej. *"crea el script principal en la carpeta de proyectos"*, *"inspecciona el package.json"*, *"ejecuta las pruebas unitarias con pytest"*).
2. **Gatillo Autónomo (Inspección y Verificación Operativa):**
   - **Inspección Previa:** Antes de editar o refactorizar proyectos, para verificar la estructura de archivos existente (`listar_directorio`, `leer_archivo`).
   - **Verificación de Entregables:** Para constatar físicamente en disco la presencia y contenido de los archivos de código creados antes de declarar completada una tarea (`listar_directorio`, `leer_archivo`).
3. **Hard-Stops Innegociables de Seguridad:**
   - **Candado de Conocimiento:** Prohibido escribir manualmente en `Cerebro.md` ni en `memoria/`; toda persistencia de conocimiento debe canalizarse a través de las herramientas RAG autorizadas.
   - **Firewall de Destrucción:** Bloqueo terminante de comandos de borrado masivo o formateo (`rm -rf /`, `del /f /s /q c:\`, `format`, `shutdown`, `drop database`).
   - **Control de Rutas:** Prohibido escribir código fuera de `/app/Subagente_Desarrollo/proyectos/` o temporales fuera de `/app/Archivos_temporales/`.
   - **Protección de Contexto:** Censura automática de enlaces de grafos de Obsidian en lecturas y paginación de seguridad para evitar desbordar la ventana de inferencia.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

Las cuatro herramientas operan bajo un modelo de **Defensa en Profundidad (Firewall Determinístico)**:

```mermaid
flowchart TD
    Operacion["Petición de Operación I/O o Shell"]
    TipoOp{¿Tipo de Operación?}

    TipoOp -->|Escritura: crear_archivo| ValidaRuta["1. Validación de Firewall de Rutas\n(proyectos, skills, temporales)"]
    ValidaRuta --> AutoObsidian["2. Inyección de Auto-Enlace Obsidian\n(si es archivo .md: [[proyectos]])"]
    AutoObsidian --> EscrituraDisco["3. Persistencia Segura en Disco"]

    TipoOp -->|Lectura: leer_archivo| CensuraGrafo["1. Censura de Metadatos de Grafo\n(Ocultar [[Conexiones]] anti-alucinación)"]
    CensuraGrafo --> PaginaContexto["2. Paginación de Seguridad\n(Máximo 12.000 caracteres)"]

    TipoOp -->|Terminal: ejecutar_comando| CheckFirewall["1. Verificación de Lista Negra Anti-Destrucción"]
    CheckFirewall --> EjecutaSubprocess["2. subprocess.run con Timeout (300s)"]
    EjecutaSubprocess --> RetornoDual["3. Captura Estructurada de stdout y stderr"]

    TipoOp -->|Exploración: listar_directorio| EscaneoDisco["1. Escaneo de Archivos y Carpetas con Pesos en Bytes"]
```

### Herramienta 1: `crear_archivo(ruta_absoluta, contenido)`
- Escribe o sobreescribe archivos garantizando que existan sus carpetas contenedoras (`mkdir(parents=True)`).
- Asocia automáticamente los archivos `.md` al perfil en Obsidian (`**Pertenece a:** [[proyectos]]`).
- Rutas autorizadas: `/app/Subagente_Desarrollo/proyectos/`, `/app/Subagente_Desarrollo/skills/`, `/app/Archivos_temporales/` y `/app/Bitacora.md`.

### Herramienta 2: `leer_archivo(ruta_absoluta)`
- Extrae el contenido de un archivo en texto plano UTF-8.
- Cuenta con censura anti-alucinación: retira metadatos de enlaces de Obsidian para evitar interferencias cognitivas.

### Herramienta 3: `listar_directorio(ruta_absoluta)`
- Devuelve la lista ordenada de elementos en una carpeta, identificando cuáles son directorios y cuáles archivos con su peso en bytes.

### Herramienta 4: `ejecutar_comando(comando, directorio)`
- Lanza procesos en el sistema operativo capturando código de retorno, `stdout` y `stderr` sin colgar el contenedor.

---

## 3. El System Prompt Completo de la Habilidad

Este es el System Prompt especializado que reside encapsulado en `skill_base.py` y se inyecta dinámicamente bajo demanda:

```text
[🛑 HARD-STOP: MODO OPERACIONES BASE DE SISTEMA Y ARCHIVOS ACTIVO 🛑]
Eres el Operador de Infraestructura y Sistema de Archivos del Subagente de Desarrollo.
Tu misión es gestionar lecturas, escrituras de código, exploración de directorios y ejecución de procesos en el sistema operativo con máxima precisión técnica, respetando el firewall determinístico y garantizando que todo código y proyecto generado sea funcional y persistente.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida la existencia del directorio contenedor usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y ZONAS SEGURAS DE DESARROLLO:
   - Proyectos de Software y Código: `/app/Subagente_Desarrollo/proyectos/` (directorio canónico de desarrollo).
   - Habilidades y Herramientas: `/app/Subagente_Desarrollo/skills/` (únicamente para mantenimiento y extensión autorizada de skills).
   - Archivos Temporales / Scratch / Compilaciones intermedias: `/app/Archivos_temporales/` (obligatorio prefijo `desarrollo_`).
   - Bitácora de Tareas: `/app/Bitacora.md` (actualización de estados de tickets asignados).
   - Tienes terminantemente prohibido ejecutar comandos destructivos (`rm -rf`, `del /f`, `format`, `shutdown`, `drop database`, etc.).
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - NUNCA escribas manualmente en `Cerebro.md` ni en `memoria/`. El conocimiento se registra a través de las herramientas de aprendizaje autorizadas.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil correspondiente (`[[proyectos]]` o `[[Perfil_Subagente_Desarrollo]]`).
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos de código fuente grandes, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina para evitar saturar la ventana de contexto.
```

---

## 4. Resultados y Entregables Esperados

Toda operación base debe generar resultados verificables:
1. **Archivos de Código:** Ubicados estrictamente bajo `/app/Subagente_Desarrollo/proyectos/<nombre_proyecto>/`.
2. **Archivos Temporales o Logs de Prueba:** Ubicados en `/app/Archivos_temporales/` con prefijo `desarrollo_`.
3. **Salidas de Comandos:** Respuestas JSON estructuradas con `codigo_retorno`, `stdout` y `stderr` para auditoría inmediata.

---

## 5. Ejemplos Prácticos Completos (Few-Shot)

### Ejemplo 1: Creación de Módulo Python en Proyectos
```python
# Invocación de herramienta:
crear_archivo(
    ruta_absoluta="/app/Subagente_Desarrollo/proyectos/api_pagos/service.py",
    contenido="""import math

def calcular_comision(monto: float) -> float:
    return round(monto * 0.025, 2)
"""
)
# Respuesta esperada:
# {"status": "success", "archivo": "/app/Subagente_Desarrollo/proyectos/api_pagos/service.py", "bytes_escritos": 105}
```

### Ejemplo 2: Ejecución Segura de Pruebas Unitarias
```python
# Invocación de herramienta:
ejecutar_comando(
    comando="python -m unittest discover tests",
    directorio="/app/Subagente_Desarrollo/proyectos/api_pagos"
)
# Respuesta esperada:
# {"status": "success", "codigo_retorno": 0, "stdout": "Ran 4 tests in 0.012s\n\nOK", "stderr": ""}
```

---

## 6. Conexiones y Referencias en el Grafo

- **Perfil Maestro del Agente:** [[Perfil_Subagente_Desarrollo]]
- **Reglamento Operativo:** [[Reglas de la Tripulacion]]
- **Carpeta de Entregables:** [[proyectos]]

---
**Pertenece a:** [[Perfil_Subagente_Desarrollo]]
