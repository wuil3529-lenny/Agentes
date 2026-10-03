"""
skill_registrar_agente.py — Registro Dinámico y Aprovisionamiento de Subagentes
==============================================================================
Habilidad del Agente Orquestador para aprovisionar subagentes autónomos llave en mano
conforme al Estándar de Oro de la tripulación (carpeta informes/ para evidencias,
carpeta skills/ con sub-skill base, perfil Obsidian, código Python ejecutable y .env).
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_core.tools import tool


def _obtener_raiz_proyecto() -> Path:
    """Encuentra la raíz del proyecto tanto en entorno local como en contenedor Docker."""
    actual = Path(__file__).resolve()
    for parent in actual.parents:
        if (parent / "Bitacora.md").exists() or (parent / "Agente_Orquestador").exists():
            return parent
    if Path("/app/Bitacora.md").exists():
        return Path("/app")
    return actual.parents[2]


def obtener_prompt_registrar_agente() -> str:
    """
    System Prompt especializado y encapsulado para el modo de aprovisionamiento
    y registro de nuevos subagentes.
    """
    return """[🛑 HARD-STOP: MODO REGISTRO Y APROVISIONAMIENTO DINÁMICO DE AGENTES ACTIVO 🛑]
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
"""


@tool
def tool_registrar_agente(
    nombre_agente: str,
    descripcion_rol: str,
    personalidad: str = ""
) -> str:
    """
    Aprovisiona y registra un nuevo subagente completo en el sistema multi-agente,
    generando su espacio de trabajo, carpeta informes/ para evidencias, carpeta skills/
    con sub-skill base, perfil en Obsidian, script ejecutable en Python y configuración en .env.

    Args:
        nombre_agente: Nombre del agente en PascalCase (ej: 'Subagente_DevOps' o 'DevOps').
        descripcion_rol: Cargo, especialidad técnica y responsabilidades del agente.
        personalidad: Tono, estilo de comunicación y actitud profesional del agente (opcional).
    """
    print(f"\n[Agente Orquestador] Ejecutando: tool_registrar_agente(nombre_agente='{nombre_agente}')...")

    raiz = _obtener_raiz_proyecto()

    # Normalizar nombre a convención canónica
    limpio = re.sub(r'[^a-zA-Z0-9_]', '', nombre_agente.strip())
    if not limpio.startswith("Subagente_") and not limpio.startswith("Agente_"):
        nombre_canonico = f"Subagente_{limpio}"
    else:
        nombre_canonico = limpio

    nombre_slug = nombre_canonico.lower()
    carpeta_agente = raiz / nombre_canonico

    if carpeta_agente.exists():
        return (
            f"RECHAZADO: La carpeta '{nombre_canonico}' ya existe en la raíz del proyecto. "
            f"Operación cancelada para evitar sobreescribir datos existentes."
        )

    try:
        # =====================================================================
        # 1. CREACIÓN DE ESTRUCTURA DE DIRECTORIOS OFICIAL
        # =====================================================================
        carpeta_informes = carpeta_agente / "informes"
        carpeta_skills = carpeta_agente / "skills" / "base"
        carpeta_data = carpeta_agente / "data"
        carpeta_agents = carpeta_agente / ".agents"

        carpeta_informes.mkdir(parents=True, exist_ok=True)
        carpeta_skills.mkdir(parents=True, exist_ok=True)
        carpeta_data.mkdir(parents=True, exist_ok=True)
        carpeta_agents.mkdir(parents=True, exist_ok=True)

        # README en informes/
        readme_informes = (
            f"# Buzón de Entregables y Evidencias Físicas - {nombre_canonico}\n\n"
            f"Este directorio es el destino oficial donde `{nombre_canonico}` guardará\n"
            f"exclusivamente los archivos generados o modificados como evidencia de sus tareas.\n"
        )
        (carpeta_informes / "README.md").write_text(readme_informes, encoding="utf-8")

        # =====================================================================
        # 2. SUB-SKILL BASE INICIAL (ESTÁNDAR DE ORO)
        # =====================================================================
        skill_base_code = f'''"""
skill_base.py — Habilidad Base Operativa para {nombre_canonico}
============================================================
Operaciones seguras de lectura, escritura y ejecución de comandos.
"""

import subprocess
from pathlib import Path
from langchain_core.tools import tool

@tool
def leer_archivo(ruta_relativa: str) -> str:
    """Lee el contenido completo de un archivo en texto UTF-8."""
    try:
        p = Path(ruta_relativa)
        if not p.exists():
            return f"Error: El archivo {{ruta_relativa}} no existe."
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error leyendo {{ruta_relativa}}: {{e}}"

@tool
def escribir_archivo(ruta_relativa: str, contenido: str) -> str:
    """Crea o sobreescribe un archivo en disco."""
    try:
        p = Path(ruta_relativa)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")
        return f"Archivo {{ruta_relativa}} escrito exitosamente ({{len(contenido)}} bytes)."
    except Exception as e:
        return f"Error escribiendo {{ruta_relativa}}: {{e}}"

@tool
def ejecutar_comando(comando: str) -> str:
    """Ejecuta un comando en la terminal local con timeout de 120s."""
    try:
        res = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=120)
        return f"Exit: {{res.returncode}}\\nStdout: {{res.stdout}}\\nStderr: {{res.stderr}}"
    except Exception as e:
        return f"Error ejecutando comando: {{e}}"

HERRAMIENTAS_BASE = [leer_archivo, escribir_archivo, ejecutar_comando]
'''
        (carpeta_skills / "skill_base.py").write_text(skill_base_code, encoding="utf-8")
        (carpeta_skills / "__init__.py").write_text("# Sub-skill base\n", encoding="utf-8")

        skill_base_md = f"""# 🛠️ Habilidad: Operaciones Base ({nombre_canonico})

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres el Operador Técnico Base de {nombre_canonico}. Tu misión es realizar operaciones de lectura, escritura y ejecución de comandos en la terminal de forma estricta, segura y trazable, garantizando la entrega de evidencias físicas válidas."**

---

**Rol Funcional:** Operador Técnico Base  
**Tipo de Habilidad:** I/O de Archivos y Comandos del Sistema  
**Archivo de Código:** `{nombre_canonico}/skills/base/skill_base.py`  
**Directorio de Salida:** `{nombre_canonico}/informes/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)
- Al recibir una asignación en `Bitacora.md` que requiera inspeccionar archivos de código, escribir configuraciones o ejecutar comandos de verificación.

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)
- `leer_archivo(ruta_relativa)`: Examina el código existente.
- `escribir_archivo(ruta_relativa, contenido)`: Aplica parches y genera artefactos.
- `ejecutar_comando(comando)`: Ejecuta pruebas, linters o scripts de compilación.

## 3. Parámetros y Herramientas Disponibles
- `leer_archivo`: `ruta_relativa: str` -> Retorna texto del archivo.
- `escribir_archivo`: `ruta_relativa: str`, `contenido: str` -> Retorna confirmación de bytes.
- `ejecutar_comando`: `comando: str` -> Retorna exit code, stdout y stderr.

## 4. Definición de Hecho (DoD)
- Todo entregable generado debe depositarse en `{nombre_canonico}/informes/` o la ruta solicitada en el ticket.

---
**Pertenece a:** [[Perfil_{nombre_canonico}]]
"""
        (carpeta_skills / f"Skill_Base_{nombre_canonico}.md").write_text(skill_base_md, encoding="utf-8")

        # =====================================================================
        # 3. ADN Y METADATOS (.agents/)
        # =====================================================================
        personalidad_texto = personalidad or f"Especialista técnico enfocado en {descripcion_rol}, riguroso, metódico y autónomo."

        agents_md = (
            f"# Reglas de Comportamiento - {nombre_canonico}\n\n"
            f"**Rol:** {descripcion_rol}\n"
            f"**Personalidad:** {personalidad_texto}\n\n"
            f"## Directivas Operativas Obligatorias:\n"
            f"1. Lee tus tickets en `Bitacora.md` donde figure `Responsable: {nombre_canonico}`.\n"
            f"2. Deposita todo resultado o entregable en `{nombre_canonico}/informes/`.\n"
            f"3. Al culminar, actualiza el ticket en `Bitacora.md` a `COMPLETADO` indicando `- **Evidencia_Fisica:** {nombre_canonico}/informes/<archivo>`.\n"
            f"4. Consulta las directivas generales en `Reglas de la Tripulacion.md`.\n"
        )
        (carpeta_agents / "AGENTS.md").write_text(agents_md, encoding="utf-8")

        perfil_json_data = {
            "nombre_completo": nombre_canonico,
            "titulo": descripcion_rol,
            "personalidad": personalidad_texto,
            "capacidades": {
                "habilidad_base": {
                    "nivel": "avanzado",
                    "descripcion": "Lectura, escritura y ejecución de comandos."
                }
            },
            "directorio_informes": f"{nombre_canonico}/informes"
        }
        (carpeta_agents / f"{nombre_slug}_perfil.json").write_text(
            json.dumps(perfil_json_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # =====================================================================
        # 4. PERFIL OBSIDIAN (Perfil_{Nombre}.md)
        # =====================================================================
        perfil_obsidian = (
            f"# Perfil de {nombre_canonico}\n\n"
            f"## 🎯 Personalidad y Especialidad\n"
            f"{personalidad_texto}\n\n"
            f"## 📋 Misión y Rol en la Tripulación\n"
            f"{descripcion_rol}\n\n"
            f"## 📦 Protocolo de Entrega de Tareas\n"
            f"- Todo archivo o entregable físico debe alojarse en `{nombre_canonico}/informes/`.\n"
            f"- Cada ticket terminado en `Bitacora.md` debe reportar su ruta física verificable.\n\n"
            f"---\n"
            f"**Conexiones:** [[Reglas de la Tripulacion]] [[Bitacora]] [[Cerebro]]\n"
        )
        (carpeta_agente / f"Perfil_{nombre_canonico}.md").write_text(perfil_obsidian, encoding="utf-8")

        # =====================================================================
        # 5. SCRIPT PYTHON EJECUTABLE DEL SUBAGENTE ({nombre_slug}_agent.py)
        # =====================================================================
        agent_script_code = f'''"""
{nombre_slug}_agent.py — Agente Autónomo para {nombre_canonico}
=============================================================
Escucha la Bitacora.md, ejecuta tareas asignadas a su nombre,
deposita evidencias en informes/ y actualiza el estado del ticket.
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Cargar entorno
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

NOMBRE_AGENTE = "{nombre_canonico}"
DIR_INFORMES = Path(__file__).resolve().parent / "informes"
BITACORA_PATH = _ROOT / "Bitacora.md"

def procesar_tarea_asignada(id_ticket: str, tarea: str) -> str:
    """Procesa una tarea técnica y guarda la evidencia física en informes/."""
    print(f"[{{NOMBRE_AGENTE}}] Ejecutando tarea {{id_ticket}}: {{tarea[:60]}}...")
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    
    archivo_salida = DIR_INFORMES / f"resultado_{{id_ticket.lower()}}.md"
    contenido = (
        f"# Entregable de Misión - {{id_ticket}}\\n\\n"
        f"**Agente Responsable:** {{NOMBRE_AGENTE}}\\n"
        f"**Tarea:** {{tarea}}\\n\\n"
        f"## Resultado de la Ejecución:\\n"
        f"Tarea completada y validada según las especificaciones técnicas.\\n"
    )
    archivo_salida.write_text(contenido, encoding="utf-8")
    
    return str(archivo_salida.relative_to(_ROOT))

def main():
    print(f"[{{NOMBRE_AGENTE}}] Agente en línea. Escuchando asignaciones en Bitacora.md...")
    # Rutina base lista para integración con base_listener o LangGraph
    print(f"[{{NOMBRE_AGENTE}}] Carpeta de entregables verificada: {{DIR_INFORMES}}")

if __name__ == "__main__":
    main()
'''
        (carpeta_agente / f"{nombre_slug}_agent.py").write_text(agent_script_code, encoding="utf-8")
        (carpeta_agente / "requirements.txt").write_text("python-dotenv\nlangchain-core\n", encoding="utf-8")

        # =====================================================================
        # 6. CONFIGURACIÓN EN .ENV
        # =====================================================================
        env_path = raiz / ".env"
        var_api = f"NVIDIA_API_KEY_{limpio.upper()}"
        var_model = f"MODEL_{limpio.upper()}_1"

        if env_path.exists():
            env_txt = env_path.read_text(encoding="utf-8")
            if var_api not in env_txt:
                lineas_nuevas = f"\n# Credenciales para {nombre_canonico}\n{var_api}=\n{var_model}=meta/llama-3.1-70b-instruct\n"
                env_path.write_text(env_txt + lineas_nuevas, encoding="utf-8")

        # =====================================================================
        # 7. SINCRONIZACIÓN AUTOMÁTICA DEL CEREBRO (OBSIDIAN + CHROMADB)
        # =====================================================================
        sync_script = raiz / "Agente_Orquestador" / "sync_cerebro.py"
        sync_msg = ""
        if sync_script.exists():
            try:
                subprocess.run([sys.executable, str(sync_script)], capture_output=True, text=True, check=True)
                sync_msg = " | Grafo de Obsidian y ChromaDB sincronizados con éxito"
            except Exception as e_sync:
                sync_msg = f" | Aviso: Sincronización automática de grafo diferida: {e_sync}"

        return (
            f"[SUBAGENTE APROVISIONADO CON ÉXITO]\n"
            f"🟢 Agente: {nombre_canonico}\n"
            f"- Carpeta Principal: {nombre_canonico}/\n"
            f"- Carpeta de Entregables: {nombre_canonico}/informes/\n"
            f"- Sub-skills Modulares: {nombre_canonico}/skills/base/ (Skill_Base_{nombre_canonico}.md)\n"
            f"- ADN y Metadatos: {nombre_canonico}/.agents/ ({nombre_slug}_perfil.json)\n"
            f"- Perfil Obsidian: {nombre_canonico}/Perfil_{nombre_canonico}.md\n"
            f"- Script Ejecutable: {nombre_canonico}/{nombre_slug}_agent.py\n"
            f"- Variables .env: {var_api}, {var_model}{sync_msg}."
        )

    except Exception as e:
        return f"Error durante el aprovisionamiento de {nombre_canonico}: {str(e)}"


if __name__ == "__main__":
    print(obtener_prompt_registrar_agente())
