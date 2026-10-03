# 💻 Habilidad: Operaciones Base de Sistema y Archivos (I/O & Shell)

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Operador de Infraestructura y Gestión de Archivos del Subagente de Asistencia. Tu misión es gestionar lecturas, escrituras, exploración de directorios y ejecución de procesos en el sistema operativo con rigor técnico, respetando el firewall determinístico y previniendo la corrupción de datos o la sobrecarga de contexto."**

---

**Rol Funcional:** Operador de Infraestructura y Sistema de Archivos  
**Tipo de Habilidad:** Entrada/Salida (I/O) Primitivo, Exploración y Ejecución Segura de Procesos Shell  
**Archivo de Código:** `Subagente_Asistencia/skills/base/skill_base.py`  
**Directorio de Salida:** Sistema de Archivos Local y Entorno de Ejecución  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad proporciona las cuatro herramientas primitivas de interacción con la máquina y el entorno Docker:

1. **Gatillo Reactivo (Órdenes Directas):**
   - Cuando el Agente Orquestador o el Usuario solicitan inspeccionar un archivo, generar un informe administrativo o ejecutar un script de soporte en la terminal (ej. *"lee el archivo de configuración"*, *"genera el informe en la carpeta de entregables"*).
2. **Gatillo Autónomo (Inspección y Verificación Operativa):**
   - **Inspección Previa:** Antes de procesar correos, documentos o PDFs, para verificar si los directorios o archivos de entrada existen (`listar_directorio`, `leer_archivo`).
   - **Verificación de Entregables:** Para constatar físicamente en disco la existencia de informes antes de declarar finalizada una tarea (`listar_directorio`).
3. **Hard-Stops Innegociables de Seguridad:**
   - **Candado de Conocimiento:** Prohibido escribir manualmente en `Cerebro.md` ni en `memoria/`; toda persistencia de conocimiento a largo plazo debe canalizarse por las herramientas RAG autorizadas.
   - **Firewall de Destrucción:** Bloqueo terminante de comandos de borrado masivo o formateo (`rm -rf`, `del /f`, `format`, `shutdown`, etc.).
   - **Lista Blanca de Binarios:** Solo se autorizan comandos de desarrollo e inspección (`python`, `pip`, `node`, `npm`, `git`, `docker`, `ls`, `dir`, `cat`, `type`, `mkdir`, `echo`).
   - **Protección de Contexto:** Límite máximo de lectura de 8.000 caracteres y timeout estricto de 120 segundos por proceso.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

Las cuatro herramientas operan bajo un modelo de **Defensa en Profundidad (Firewall Determinístico)**:

```mermaid
flowchart TD
    Operacion["Petición de Operación I/O o Shell"]
    TipoOp{¿Tipo de Operación?}

    TipoOp -->|Escritura: crear_archivo| ValidaRuta["1. Validación de Rutas Permitidas\n(informes, documentos, temporal)"]
    ValidaRuta --> AutoObsidian["2. Inyección de Auto-Enlace Obsidian\n([[Perfil_Subagente_Asistencia]])"]
    AutoObsidian --> EscrituraDisco["3. Persistencia en Disco"]

    TipoOp -->|Lectura: leer_archivo| CensuraGrafo["1. Censura de Metadatos de Grafo\n(Ocultar [[Conexiones]] anti-alucinación)"]
    CensuraGrafo --> PaginaContexto["2. Paginación de Seguridad\n(Máximo 8.000 caracteres)"]

    TipoOp -->|Terminal: ejecutar_comando| CheckFirewall["1. Verificación de Lista Negra y Lista Blanca"]
    CheckFirewall --> EjecutaSubprocess["2. subprocess.run con Timeout (120s)"]
    EjecutaSubprocess --> RetornoDual["3. Captura Estructurada de stdout y stderr"]

    TipoOp -->|Exploración: listar_directorio| EscaneoDisco["1. Escaneo de Archivos y Carpetas con Tamaños"]
```

### Herramienta 1: `crear_archivo(ruta_absoluta, contenido)`
- Escribe o sobreescribe archivos garantizando que existan sus carpetas contenedoras (`mkdir(parents=True)`).
- Asocia automáticamente los archivos `.md` al perfil canónico en Obsidian (`**Pertenece a:** [[Perfil_Subagente_Asistencia]]`).
- Rutas autorizadas: `/app/Subagente_Asistencia/informes/`, `/app/Subagente_Asistencia/documentos_sanji/`, `/app/Archivos_temporales/` y `/app/Bitacora.md`.

### Herramienta 2: `leer_archivo(ruta_absoluta)`
- Extrae el contenido de un archivo en texto plano UTF-8.
- Cuenta con censura anti-alucinación: retira metadatos de enlaces de Obsidian para que el modelo no se confunda.

### Herramienta 3: `listar_directorio(ruta_absoluta)`
- Devuelve la lista ordenada de elementos en una carpeta, identificando cuáles son directorios y cuáles archivos con su peso en bytes.

### Herramienta 4: `ejecutar_comando(comando, directorio)`
- Lanza procesos en el sistema operativo capturando código de retorno, `stdout` y `stderr` sin bloquear la consola.

---

## 3. El System Prompt Completo de la Habilidad

Este es el System Prompt especializado que reside encapsulado en `skill_base.py` y se inyecta dinámicamente bajo demanda:

```text
[🛑 HARD-STOP: MODO OPERACIONES BASE DE SISTEMA Y ARCHIVOS ACTIVO 🛑]
Eres el Operador de Infraestructura y Gestión de Archivos del Subagente de Asistencia.
Tu misión es gestionar lecturas, escrituras, exploración de directorios y ejecución de procesos en el sistema operativo con rigor técnico, respetando el firewall determinístico y previniendo la corrupción de datos o la sobrecarga de contexto.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PRECISIÓN DE RUTAS Y VERIFICACIÓN PREVIA:
   - Antes de escribir o leer un archivo, valida su existencia o la de sus directorios contenedores usando `listar_directorio`.
   - Utiliza rutas absolutas o normalizadas basadas en la raíz del entorno (/app en Docker o la raíz del repositorio).
2. FIREWALL DETERMINÍSTICO Y ZONAS SEGURAS:
   - Entregables e Informes de Asistencia: `/app/Subagente_Asistencia/informes/` o `/app/Subagente_Asistencia/documentos_sanji/`.
   - Archivos Temporales / Scratch: `/app/Archivos_temporales/` (obligatorio prefijo `asistencia_` o `sanji_`).
   - Bitácora de Tareas: `/app/Bitacora.md` (única fuente de verdad).
   - Tienes terminantemente prohibido ejecutar comandos destructivos (rm -rf, del /f, format, shutdown, etc.).
3. INTEGRIDAD DEL CONOCIMIENTO (OBSIDIAN & GRAFO):
   - NUNCA escribas manualmente en Cerebro.md ni en memoria/. El conocimiento se registra a través de las herramientas RAG autorizadas.
   - Todo archivo markdown generado debe conservar conexiones limpias hacia el perfil correspondiente.
4. CONTROL DE VOLUMEN DE CONTEXTO:
   - Al leer archivos, ten en cuenta que el contenido se censura de metadatos de grafo y se pagina a un máximo de seguridad para no desbordar la ventana de contexto.
```

---

## 4. Resultados y Entregables Esperados

Todas las herramientas retornan un **JSON serializado estricto** que garantiza previsibilidad:

- **Escritura Exitosa:**
  ```json
  {"status": "success", "mensaje": "Archivo creado exitosamente en ...", "ruta": "/app/Subagente_Asistencia/informes/resumen.md", "bytes_escritos": 1024}
  ```
- **Lectura Exitosa:**
  ```json
  {"status": "success", "ruta": "/app/Bitacora.md", "total_lineas": 45, "contenido": "..."}
  ```
- **Listado Exitoso:**
  ```json
  {"status": "success", "directorio": "/app/Subagente_Asistencia/informes", "total_elementos": 2, "elementos": [{"nombre": "informe_semanal.md", "tipo": "archivo", "bytes": 2048}]}
  ```
- **Ejecución Exitosa:**
  ```json
  {"status": "success", "codigo_retorno": 0, "stdout": "...", "stderr": ""}
  ```
- **Fallo Controlado o Firewall:**
  ```json
  {"status": "error", "mensaje": "HARD STOP — Escritura bloqueada en ruta no autorizada: ..."}
  ```

---

## 5. Ejemplo Práctico Completo (Casos de Estudio Reales)

### Caso 1: Generación de un Informe Administrativo
```python
crear_archivo(
    ruta_absoluta="/app/Subagente_Asistencia/informes/informe_asistencia_20261002.md",
    contenido="# Resumen de Asistencia Operativa\n\n- Tareas ejecutadas: 3\n- Estado general: Operativo y sin bloqueos."
)
```
*Resultado:*
```json
{
  "status": "success",
  "mensaje": "Archivo creado exitosamente en /app/Subagente_Asistencia/informes/informe_asistencia_20261002.md",
  "ruta": "/app/Subagente_Asistencia/informes/informe_asistencia_20261002.md",
  "bytes_escritos": 154
}
```

### Caso 2: Inspección de Directorio de Salida
```python
listar_directorio(ruta_absoluta="/app/Subagente_Asistencia/informes")
```
*Resultado:*
```json
{
  "status": "success",
  "directorio": "/app/Subagente_Asistencia/informes",
  "total_elementos": 1,
  "elementos": [
    {
      "nombre": "informe_asistencia_20261002.md",
      "tipo": "archivo",
      "bytes": 154
    }
  ]
}
```

---
**Pertenece a:** [[Perfil_Subagente_Asistencia]]
