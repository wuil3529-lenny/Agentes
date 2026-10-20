"""
skill_auto_aprendizaje.py — Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks
==================================================================================================
Permite al Subagente de Ciberseguridad aprender de forma acumulativa de cada auditoría o escaneo exitoso:
  1. Paso 0 (Consulta): Antes de auditar código, flujos n8n, puertos, dependencias o APIs,
     busca si existe un Playbook o Checklist previo en memoria/ o en ChromaDB para reutilizar su ADN
     y ejecutar la auditoría en One-Shot.
  2. Paso Final (Extracción y Registro): Al finalizar por primera vez una auditoría pionera exitosa,
     extrae automáticamente el paso a paso de herramientas, patrones de detección, blueprint y
     variables adaptables, archivándolo en memoria/ para el futuro.
"""

import os
import sys
import re
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_MEMORIA_DIR = _APP_ROOT / "memoria"
_AGENTE_ORIGEN = "Subagente_Ciberseguridad"


def obtener_prompt_auto_aprendizaje() -> str:
    """
    System Prompt especializado para el motor de Auto-Aprendizaje y Memoria Procedural en Ciberseguridad.
    """
    return """[🧠 DIRECTIVA MAESTRA: AUTO-APRENDIZAJE CONTINUO Y MEMORIA PROCEDURAL]
Tienes la capacidad de acumular conocimiento procedural para ejecutar auditorías y escaneos de seguridad en UN SOLO PASO (One-Shot):

1. PASO 0 OBLIGATORIO — CONSULTA ANTES DE AUDITAR:
   - Ante CUALQUIER requerimiento de auditoría de código, escaneo de dependencias, análisis de puertos, flujos n8n o conectores API, tu PRIMERA ACCIÓN debe ser invocar:
     `tool_consultar_playbook_memoria(tema_o_dominio="...")`
   - Si se encuentra un Playbook previo:
     * Adopta el Checklist, orden de herramientas y patrones de escaneo como receta base probada.
     * Modifica únicamente las variables específicas del nuevo proyecto auditado (rutas, endpoints, dependencias).
     * Entrega el informe de seguridad y tickets necesarios al 100% en un solo paso autónomo, sin rodeos exploratorios.

2. PASO FINAL OBLIGATORIO — REGISTRO DE PRIMERA VEZ (FIRST-RUN):
   - Si la auditoría o análisis perimetral se realizó por primera vez (no existía Playbook previo) y superó las verificaciones con éxito, antes de cerrar el ticket DEBES invocar:
     `tool_registrar_playbook_memoria(...)`
   - Esto archivará el paso a paso exacto, los patrones de búsqueda, el blueprint del reporte y las variables adaptables en `memoria/` y ChromaDB para que nunca más tengas que empezar de cero en ese dominio.
"""


def _obtener_archivos_memoria() -> List[Path]:
    """Recupera todos los archivos de memoria existentes ordenados."""
    if not _MEMORIA_DIR.exists():
        return []
    return sorted(list(_MEMORIA_DIR.glob("*.md")))


@tool
def tool_consultar_playbook_memoria(tema_o_dominio: str) -> str:
    """
    Paso 0 Obligatorio: Consulta la carpeta memoria/ y la memoria vectorial para recuperar
    un Playbook o receta procedural probada sobre un tema o dominio de seguridad (ej. 'auditoria n8n',
    'escaneo cves python', 'deteccion secretos', 'puertos perimetrales').
    """
    print(f"\n[{_AGENTE_ORIGEN}] Paso 0: Consultando memoria procedural para: '{tema_o_dominio}'...")
    try:
        coincidencias = []
        palabras_clave = [p.lower() for p in re.split(r"[\s,_\-]+", tema_o_dominio) if len(p) > 2]

        # 1. Búsqueda en archivos físicos en memoria/
        archivos = _obtener_archivos_memoria()
        for arch in archivos:
            nombre = arch.name.lower()
            contenido = ""
            try:
                contenido = arch.read_text(encoding="utf-8", errors="replace")[:3000].lower()
            except Exception:
                continue

            score = 0
            if "playbook" in nombre or "receta" in nombre or "blueprint" in nombre:
                score += 3
            if _AGENTE_ORIGEN.lower() in nombre:
                score += 2

            for kw in palabras_clave:
                if kw in nombre:
                    score += 3
                if kw in contenido:
                    score += 1

            if score >= 3:
                coincidencias.append({
                    "archivo": arch.name,
                    "score": score,
                    "ruta": str(arch),
                    "es_playbook": "playbook" in nombre
                })

        coincidencias = sorted(coincidencias, key=lambda x: x["score"], reverse=True)

        if coincidencias:
            mejor = coincidencias[0]
            contenido_completo = Path(mejor["ruta"]).read_text(encoding="utf-8", errors="replace")
            return json.dumps({
                "status": "success",
                "encontrado": True,
                "playbook_archivo": mejor["archivo"],
                "relevancia_score": mejor["score"],
                "contenido_playbook": contenido_completo[:4000],
                "instruccion": (
                    f"Se encontró un Playbook previo en memoria ({mejor['archivo']}). "
                    "Adopta este Blueprint como base probada y ejecuta la auditoría en One-Shot "
                    "adaptando únicamente las variables específicas requeridas."
                )
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "encontrado": False,
            "mensaje": f"No se encontró un Playbook previo para '{tema_o_dominio}'. Procede con auditoría pionera.",
            "directiva": (
                "Al finalizar con éxito y verificar que el reporte sea válido en disco, "
                "debes ejecutar obligatoriamente 'tool_registrar_playbook_memoria' "
                "para archivar la receta aprendida."
            )
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def tool_registrar_playbook_memoria(
    titulo: str,
    categoria: str,
    dominio: str,
    paso_a_paso_skills: str,
    tokens_y_esquema: str,
    blueprint_reutilizable: str,
    variables_adaptables: str,
    evidencia_fisica: str
) -> str:
    """
    Paso Final Obligatorio: Extrae y archiva la receta metodológica completa (Playbook)
    de una auditoría o escaneo realizado por primera vez con éxito en memoria/ y ChromaDB.
    """
    print(f"\n[{_AGENTE_ORIGEN}] Paso Final: Registrando nuevo Playbook: '{titulo}'...")
    try:
        _MEMORIA_DIR.mkdir(parents=True, exist_ok=True)

        # Calcular número correlativo
        max_num = 0
        for f in _MEMORIA_DIR.glob("*.md"):
            m = re.match(r"^(\d+)_", f.name)
            if m:
                val = int(m.group(1))
                if val > max_num:
                    max_num = val
        siguiente_num = f"{max_num + 1:02d}"

        # Nombre de archivo estandarizado
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{categoria}_{dominio}").strip("_").lower()
        nombre_archivo = f"{siguiente_num}_{_AGENTE_ORIGEN}_Playbook_{slug}.md"
        ruta_archivo = _MEMORIA_DIR / nombre_archivo

        timestamp = os.popen("date /t").read().strip() if sys.platform == "win32" else ""

        contenido_playbook = f"""# Playbook de Ciberseguridad: {titulo}

**Identificador:** `{slug}`  
**Categoría:** `{categoria}`  
**Dominio Técnico:** `{dominio}`  
**Agente Creador:** `{_AGENTE_ORIGEN}`  
**Evidencia Física Validada:** `{evidencia_fisica}`  

---

## 1. Misión y Propósito del Playbook
Proporciona la arquitectura metodológica probada para auditar y proteger proyectos en el dominio `{dominio}`.
Permite a cualquier agente ejecutar revisiones de seguridad equivalentes en modo **One-Shot**.

---

## 2. Pipeline de Habilidades y Herramientas (Paso a Paso)
{paso_a_paso_skills}

---

## 3. Esquema de Vulnerabilidades y Patrones de Detección
{tokens_y_esquema}

---

## 4. Blueprint Reutilizable de Reporte / Auditoría
```markdown
{blueprint_reutilizable}
```

---

## 5. Variables Adaptables para Futuras Misiones
{variables_adaptables}

---
**Conexiones:** [[memoria]]
"""

        ruta_archivo.write_text(contenido_playbook, encoding="utf-8")

        # Indexar en ChromaDB si está disponible
        try:
            memoria_vectorial_path = _APP_ROOT / "Agente_Orquestador" / "skills" / "memoria_vectorial"
            if str(memoria_vectorial_path) not in sys.path:
                sys.path.insert(0, str(memoria_vectorial_path))
            from skill_memoria_vectorial import tool_guardar_solucion
            tool_guardar_solucion.invoke({
                "tema": f"Playbook Ciberseguridad: {titulo}",
                "problema": f"Auditoría y protección en dominio {dominio} ({categoria})",
                "solucion": f"Archivo: {nombre_archivo}\nPipeline: {paso_a_paso_skills}\nVariables: {variables_adaptables}"
            })
        except Exception:
            pass

        return json.dumps({
            "status": "success",
            "playbook_creado": nombre_archivo,
            "ruta_absoluta": str(ruta_archivo),
            "mensaje": f"Playbook archivado exitosamente en memoria/ con número {siguiente_num}."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_AUTO_APRENDIZAJE = [
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
]
