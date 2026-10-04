"""
skill_auto_aprendizaje.py — Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks
==================================================================================================
Permite al Subagente de Desarrollo aprender de forma acumulativa de cada proyecto exitoso:
  1. Paso 0 (Consulta): Antes de diseñar o codificar, busca si existe un Playbook o receta
     previa en la carpeta memoria/ o en ChromaDB para reutilizar su ADN y ejecutar en One-Shot.
  2. Paso Final (Extracción y Registro): Al finalizar por primera vez un diseño web, dashboard,
     modelo 3D, workflow en n8n, conexión MCP o API, extrae automáticamente el paso a paso,
     tokens, blueprint y variables adaptables, archivándolo en memoria/ para el futuro.
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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_MEMORIA_DIR = _APP_ROOT / "memoria"


def obtener_prompt_auto_aprendizaje() -> str:
    """
    System Prompt especializado para el motor de Auto-Aprendizaje y Memoria Procedural.
    """
    return """[🧠 DIRECTIVA MAESTRA: AUTO-APRENDIZAJE CONTINUO Y MEMORIA PROCEDURAL]
Tienes la capacidad de acumular conocimiento procedural para ejecutar tareas complejas en UN SOLO PASO (One-Shot):

1. PASO 0 OBLIGATORIO — CONSULTA ANTES DE CREAR:
   - Ante CUALQUIER solicitud de diseño web, dashboard, experiencia 3D, workflow en n8n, conexión MCP o API, tu PRIMERA ACCIÓN debe ser invocar:
     `tool_consultar_playbook_memoria(tema_o_dominio="...")`
   - Si se encuentra un Playbook previo:
     * Adopta el Blueprint y el orden de skills como plantilla base probada.
     * Modifica únicamente las variables específicas del nuevo cliente/orden (nombre, copies, colores de acento, endpoints).
     * Entrega el proyecto terminado al 100% en un solo paso autónomo, sin iteraciones innecesarias.

2. PASO FINAL OBLIGATORIO — REGISTRO DE PRIMERA VEZ (FIRST-RUN):
   - Si la tarea fue realizada por primera vez (no existía Playbook previo) y superó las auditorías con éxito, antes de cerrar el ticket DEBES invocar:
     `tool_registrar_playbook_memoria(...)`
   - Esto archivará el paso a paso exacto, los tokens de diseño, el esqueleto del código y las variables adaptables en `memoria/` para que nunca más tengas que empezar de cero en ese dominio.
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
    un Playbook o receta paso a paso de proyectos similares completados anteriormente
    (ej: 'dashboard pizzeria', 'web odontologia 3d', 'workflow n8n pizza dental', 'conector mcp').

    Args:
        tema_o_dominio: Descripción o palabras clave de lo que se desea construir.
    """
    try:
        stopwords = {"para", "como", "con", "una", "uno", "unos", "unas", "del", "las", "los", "que", "por", "sobre", "local", "cosas", "cositas", "donde"}
        keywords = [k.lower().strip() for k in re.split(r'[\s,_\-]+', tema_o_dominio) if len(k) > 2 and k.lower() not in stopwords]
        archivos = _obtener_archivos_memoria()
        
        coincidencias = []
        for arch in archivos:
            try:
                es_playbook = "playbook" in arch.name.lower()
                contenido = arch.read_text(encoding="utf-8", errors="replace")
                score = 0
                for kw in keywords:
                    if kw in arch.name.lower():
                        score += 5
                    if kw in contenido.lower():
                        score += 1
                
                # Bonificación para archivos Playbook y penalización si no es playbook
                if es_playbook and score > 0:
                    score += 10
                elif not es_playbook and score < 4:
                    # Descartar coincidencias espurias en archivos de sistema que no son playbooks
                    score = 0

                if score >= 3:
                    coincidencias.append((score, arch.name, contenido, es_playbook))
            except Exception:
                continue

        coincidencias.sort(key=lambda x: x[0], reverse=True)

        if not coincidencias:
            return json.dumps({
                "status": "success",
                "encontrado": False,
                "mensaje": f"No se encontró un Playbook previo específico para '{tema_o_dominio}'. Esta es una tarea de PRIMERA VEZ. Ejecuta el pipeline completo y al finalizar registra la receta con tool_registrar_playbook_memoria."
            }, ensure_ascii=False)

        mejor_score, mejor_nombre, mejor_contenido, es_pb = coincidencias[0]

        # Extraer secciones clave si existen
        extracto = mejor_contenido[:2500]
        
        return json.dumps({
            "status": "success",
            "encontrado": True,
            "playbook_archivo": mejor_nombre,
            "relevancia_score": mejor_score,
            "mensaje": f"¡Playbook encontrado en memoria: {mejor_nombre}! Usa este ADN metodológico como base directa para producir el proyecto en One-Shot.",
            "contenido_playbook": extracto
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error consultando memoria procedural: {str(e)}"
        }, ensure_ascii=False)


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
    Paso Final Obligatorio: Extrae y archiva el ADN metodológico de una solución exitosa
    realizada por primera vez, guardando una receta completa en memoria/ para su reutilización futura.

    Args:
        titulo: Nombre descriptivo del Playbook (ej: 'Playbook: Dashboard Dark Neo-Bento para Pizzería').
        categoria: Tipo de artefacto ('web_landing', 'dashboard', 'web_3d', 'n8n_workflow', 'conector_mcp', 'conexion_api', 'sql_big_data').
        dominio: Sector de negocio o tecnología (ej: 'gastronomia', 'odontologia', 'salud', 'crm', 'fintech').
        paso_a_paso_skills: Orden exacto de herramientas ejecutadas (ej: '1. Taste -> 2. Impeccable -> 3. Animate -> 4. WebGL/Scaffold -> 5. Playwright -> 6. Cyber Audit').
        tokens_y_esquema: Paleta cromática, fuentes tipográficas, schemas JSON o mapas de nodos.
        blueprint_reutilizable: Esqueleto o snippet clave del código/flujo reutilizable.
        variables_adaptables: Lista de campos a sustituir en un nuevo cliente (ej: nombre de marca, items de menú, duración de citas, credenciales).
        evidencia_fisica: Ruta del archivo generado y validado en disco.
    """
    try:
        _MEMORIA_DIR.mkdir(parents=True, exist_ok=True)

        # Determinar índice consecutivo
        archivos_existentes = list(_MEMORIA_DIR.glob("[0-9][0-9]_*.md"))
        siguiente_num = 1
        if archivos_existentes:
            numeros = []
            for a in archivos_existentes:
                m = re.match(r"^(\d+)_", a.name)
                if m:
                    numeros.append(int(m.group(1)))
            if numeros:
                siguiente_num = max(numeros) + 1

        prefijo = f"{siguiente_num:02d}_Subagente_Desarrollo_Playbook"
        slug_dominio = re.sub(r"[^\w\-]", "_", dominio.lower())
        slug_cat = re.sub(r"[^\w\-]", "_", categoria.lower())
        nombre_archivo = f"{prefijo}_{slug_cat}_{slug_dominio}.md"
        ruta_archivo = _MEMORIA_DIR / nombre_archivo

        contenido_md = f"""# 🧬 {titulo}

**Tipo:** Playbook de Memoria Procedural (Auto-Aprendizaje Continuo)
**Categoría:** `{categoria}`
**Dominio:** `{dominio}`
**Evidencia Física Asociada:** `{evidencia_fisica}`
**Generado Por:** Subagente_Desarrollo

---

## 🎯 1. Objetivo & Resumen de Reutilización
Este playbook almacena la metodología exacta, arquitectura y código probado para desplegar proyectos de tipo **{categoria}** en el sector **{dominio}** en un solo paso (*One-Shot Execution*).

---

## 🗺️ 2. Pipeline de Habilidades (Orden Exacto de Ejecución)
{paso_a_paso_skills}

---

## 🎨 3. Design DNA, Tokens & Esquema
{tokens_y_esquema}

---

## 🏗️ 4. Blueprint Reutilizable (Esqueleto Base)
```text
{blueprint_reutilizable}
```

---

## 🔄 5. Variables Adaptables para Nuevos Clientes
{variables_adaptables}

---

## 🔒 6. Reglas de Validación y Certificación Aplicadas
- **Anti-Slop (Taste):** Cero degradados morados, cero componentes idénticos, tipografías intencionales de autor.
- **Impeccable UI:** Modos de superficie respetados, control de desbordamiento de texto.
- **Motion UI:** Físicas de Emil Kowalski (<280ms interactivos, curvas spring, GPU-only).
- **Responsive:** Verificado en Desktop (1440x900) y Mobile (390x844) sin desbordamiento horizontal.
- **Ciberseguridad:** SAST aprobado, sanitización de entradas, cero secretos expuestos.

---
**Pertenece a:** [[memoria]] · [[Perfil_Subagente_Desarrollo]]
"""

        ruta_archivo.write_text(contenido_md, encoding="utf-8")

        # Replicar en ChromaDB si está disponible
        try:
            memoria_vectorial_path = _APP_ROOT / "Agente_Orquestador" / "skills" / "memoria_vectorial"
            if str(memoria_vectorial_path) not in sys.path:
                sys.path.insert(0, str(memoria_vectorial_path))
            from skill_memoria_vectorial import tool_guardar_solucion
            tool_guardar_solucion(
                ticket_id=f"PLAYBOOK-{categoria.upper()}-{dominio.upper()}",
                descripcion=f"Playbook metodológico reutilizable: {titulo}",
                contenido=contenido_md,
                herramientas_usadas="tool_registrar_playbook_memoria",
                decisiones_clave="Extracción automática de ADN metodológico para ejecución One-Shot en un solo prompt",
                evidencia_fisica=str(ruta_archivo),
                agentes_involucrados="Subagente_Desarrollo"
            )
        except Exception:
            pass

        return json.dumps({
            "status": "success",
            "mensaje": f"Playbook registrado exitosamente en {ruta_archivo.name}. Conocimiento procedural indexado para futuras generaciones automáticas.",
            "archivo_guardado": str(ruta_archivo)
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error registrando playbook en memoria: {str(e)}"
        }, ensure_ascii=False)


HERRAMIENTAS_AUTO_APRENDIZAJE = [
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
]
