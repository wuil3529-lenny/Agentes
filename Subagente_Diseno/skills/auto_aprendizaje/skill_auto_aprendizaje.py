"""
skill_auto_aprendizaje.py — Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks
==================================================================================================
Permite al Subagente de Diseño aprender de forma acumulativa de cada diseño o prototipo exitoso:
  1. Paso 0 (Consulta): Antes de maquetar una interfaz, presentación, carrusel o guion audiovisual,
     busca si existe un Playbook previo en memoria/ para reutilizar su arquitectura y ejecutar en One-Shot.
  2. Paso Final (Extracción y Registro): Al culminar con éxito un diseño pionero, extrae automáticamente
     los tokens, estructura de componentes, blueprint y variables adaptables en memoria/ para el futuro.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_MEMORIA_DIR = _APP_ROOT / "memoria"
_AGENTE_ORIGEN = "Subagente_Diseno"


def obtener_prompt_auto_aprendizaje() -> str:
    """
    Retorna el System Prompt especializado para el motor de Auto-Aprendizaje y Memoria Procedural en Diseño.
    """
    return """[🧠 DIRECTIVA MAESTRA: AUTO-APRENDIZAJE CONTINUO Y MEMORIA PROCEDURAL]
Tienes la capacidad de acumular conocimiento procedural para ejecutar diseños y prototipos interactivos en UN SOLO PASO (One-Shot):

1. PASO 0 OBLIGATORIO — CONSULTA ANTES DE DISEÑAR:
   - Ante CUALQUIER requerimiento de diseño de interfaz, landing page, dashboard, presentación Marp, carrusel o guion de video, tu PRIMERA ACCIÓN debe ser invocar:
     `tool_consultar_playbook_memoria(tema_o_dominio="...")`
   - Si se encuentra un Playbook previo:
     * Adopta la estructura de componentes, tokens y blueprint probado.
     * Adapta únicamente las variables específicas del nuevo proyecto (título, colores de marca, textos).
     * Entrega el prototipo HTML y assets en un solo paso autónomo, sin rodeos exploratorios.

2. PASO FINAL OBLIGATORIO — REGISTRO DE PRIMERA VEZ (FIRST-RUN):
   - Si el diseño o prototipo se realizó por primera vez (no existía Playbook previo) y superó las verificaciones con éxito, antes de cerrar la tarea DEBES invocar:
     `tool_registrar_playbook_memoria(...)`
   - Esto archivará los tokens, el código base, el blueprint de Tailwind y las variables adaptables en `memoria/` para que nunca más tengas que empezar de cero en ese estilo.
"""


def _obtener_archivos_memoria() -> List[Path]:
    if not _MEMORIA_DIR.exists():
        return []
    return sorted(list(_MEMORIA_DIR.glob("*.md")))


@tool
def tool_consultar_playbook_memoria(tema_o_dominio: str) -> str:
    """
    Paso 0 Obligatorio: Consulta la carpeta memoria/ para recuperar un Playbook o receta
    procedural probada de diseño (ej. 'dashboard tailwind bento grid', 'landing page saas', 'carrusel instagram tipografia').
    """
    print(f"\n[{_AGENTE_ORIGEN}] Paso 0: Consultando memoria procedural para: '{tema_o_dominio}'...")
    try:
        coincidencias = []
        palabras_clave = [p.lower() for p in re.split(r"[\s,_\-]+", tema_o_dominio) if len(p) > 2]

        archivos = _obtener_archivos_memoria()
        for arch in archivos:
            nombre = arch.name.lower()
            contenido = ""
            try:
                contenido = arch.read_text(encoding="utf-8", errors="replace")[:3000].lower()
            except Exception:
                continue

            score = 0
            if "playbook" in nombre or "blueprint" in nombre:
                score += 3
            if _AGENTE_ORIGEN.lower() in nombre or "diseno" in nombre or "nami" in nombre:
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
                    f"Se encontró un Playbook de diseño en memoria ({mejor['archivo']}). "
                    "Adopta esta arquitectura base y compila el prototipo en One-Shot adaptando las variables requeridas."
                )
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "encontrado": False,
            "mensaje": f"No se encontró un Playbook previo para '{tema_o_dominio}'. Procede con diseño pionero.",
            "directiva": (
                "Al finalizar con éxito y verificar que el prototipo o entregable exista en disco, "
                "debes ejecutar 'tool_registrar_playbook_memoria' para archivar el nuevo patrón visual."
            )
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


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
    Paso Final Obligatorio: Extrae y archiva un Playbook de diseño probado en memoria/
    para habilitar la ejecución One-Shot en futuras tareas similares.
    """
    print(f"\n[{_AGENTE_ORIGEN}] Paso Final: Registrando Playbook en memoria: '{titulo}'...")
    try:
        _MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9_]+", "_", f"{categoria}_{dominio}_{titulo}".lower().strip())[:50]
        nombre_archivo = f"playbook_diseno_{slug}.md"
        ruta_playbook = _MEMORIA_DIR / nombre_archivo

        contenido_md = f"""# 🎨 Playbook de Diseño: {titulo}

> **Tipo:** Memoria Procedural One-Shot  
> **Agente Creador:** `{_AGENTE_ORIGEN}`  
> **Categoría:** `{categoria}`  
> **Dominio:** `{dominio}`  
> **Evidencia Física Verificada:** `{evidencia_fisica}`  

---

## 1. Paso a Paso de Habilidades (Workflow)
{paso_a_paso_skills}

---

## 2. Tokens y Esquema de Diseño
{tokens_y_esquema}

---

## 3. Blueprint Reutilizable
```html
{blueprint_reutilizable}
```

---

## 4. Variables Adaptables para Futuras Ejecuciones
{variables_adaptables}

---
**Conexiones:** [[memoria]]
"""

        ruta_playbook.write_text(contenido_md, encoding="utf-8")

        return json.dumps({
            "status": "success",
            "archivo_creado": nombre_archivo,
            "ruta_absoluta": str(ruta_playbook).replace("\\", "/"),
            "mensaje": f"Playbook '{titulo}' archivado con éxito en memoria/. Patrón visual listo para One-Shot."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False)


HERRAMIENTAS_AUTO_APRENDIZAJE = [
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria
]
