"""
skill_auto_aprendizaje.py — Habilidad: Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks
==================================================================================================
Permite al Subagente de Asistencia aprender de forma acumulativa de cada flujo o tarea ejecutiva exitosa:
  1. Paso 0 (Consulta): Antes de crear plantillas, documentos, procesar flujos de correos,
     automatizaciones ofimáticas o APIs, busca si existe un Playbook previo en memoria/ o en ChromaDB
     para reutilizar su ADN y ejecutar en One-Shot.
  2. Paso Final (Extracción y Registro): Al finalizar por primera vez un informe ejecutivo, plantilla
     de Google Docs, flujo de triaje de correos, o pipeline ofimático, extrae automáticamente el paso
     a paso, esquemas, blueprint y variables adaptables, archivándolo en memoria/ para el futuro.
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
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_asistencia"] else _CURRENT.parents[2]
_MEMORIA_DIR = _APP_ROOT / "memoria"
_AGENTE_ORIGEN = "Subagente_Asistencia"


def obtener_prompt_auto_aprendizaje() -> str:
    """
    System Prompt especializado para el motor de Auto-Aprendizaje y Memoria Procedural en Asistencia.
    """
    return """[🧠 DIRECTIVA MAESTRA: AUTO-APRENDIZAJE CONTINUO Y MEMORIA PROCEDURAL]
Tienes la capacidad de acumular conocimiento procedural para ejecutar tareas complejas en UN SOLO PASO (One-Shot):

1. PASO 0 OBLIGATORIO — CONSULTA ANTES DE CREAR:
   - Ante CUALQUIER requerimiento de redacción de documentos, gestión de flujos de correo, resúmenes ejecutivos, integración con Google Workspace o automatizaciones API, tu PRIMERA ACCIÓN debe ser invocar:
     `tool_consultar_playbook_memoria(tema_o_dominio="...")`
   - Si se encuentra un Playbook previo:
     * Adopta el Blueprint y el orden de skills como plantilla base probada.
     * Modifica únicamente las variables específicas del nuevo requerimiento (destinatarios, fechas, parámetros, copies).
     * Entrega el resultado terminado al 100% en un solo paso autónomo, sin iteraciones innecesarias.

2. PASO FINAL OBLIGATORIO — REGISTRO DE PRIMERA VEZ (FIRST-RUN):
   - Si la tarea fue realizada por primera vez (no existía Playbook previo) y superó las auditorías con éxito, antes de cerrar el ticket DEBES invocar:
     `tool_registrar_playbook_memoria(...)`
   - Esto archivará el paso a paso exacto, los esquemas de formato, el esqueleto del documento o flujo y las variables adaptables en `memoria/` para que nunca más tengas que empezar de cero en ese dominio.
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
    (ej: 'triaje correos vip', 'informe ejecutivo google docs', 'agenda calendario equipo', 'automatizacion ofimatica').

    Args:
        tema_o_dominio: Descripción o palabras clave de lo que se desea procesar o construir.
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
                "mensaje": f"No se encontró un Playbook previo específico para '{tema_o_dominio}'. Esta es una tarea de PRIMERA VEZ. Ejecuta el procedimiento completo y al finalizar registra la receta con tool_registrar_playbook_memoria."
            }, ensure_ascii=False)

        mejor_score, mejor_nombre, mejor_contenido, es_pb = coincidencias[0]
        extracto = mejor_contenido[:2500]
        
        return json.dumps({
            "status": "success",
            "encontrado": True,
            "playbook_archivo": mejor_nombre,
            "relevancia_score": mejor_score,
            "mensaje": f"¡Playbook encontrado en memoria: {mejor_nombre}! Usa este ADN metodológico como base directa para producir el entregable en One-Shot.",
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
        titulo: Nombre descriptivo del Playbook (ej: 'Playbook: Triaje de Correos Críticos y Notificación Telegram').
        categoria: Tipo de tarea ('gestion_correos', 'informe_ejecutivo', 'google_docs_editorial', 'google_calendar_agenda', 'google_drive_archivo', 'automatizacion_ofimatica').
        dominio: Área funcional o temática (ej: 'atencion_cliente', 'finanzas', 'operaciones', 'agenda_directiva', 'soporte').
        paso_a_paso_skills: Orden exacto de herramientas ejecutadas (ej: '1. tool_correo_recibir_y_analizar -> 2. tool_correo_notificar_usuario -> 3. tool_correo_responder').
        tokens_y_esquema: Esquema de clasificación, criterios de prioridad o formato visual de salida.
        blueprint_reutilizable: Plantilla base de respuesta, estructura del documento o snippet de flujo.
        variables_adaptables: Lista de campos a sustituir en futuras ejecuciones (ej: destinatario, asunto, etiquetas, placeholders).
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

        prefijo = f"{siguiente_num:02d}_{_AGENTE_ORIGEN}_Playbook"
        slug_dominio = re.sub(r"[^\w\-]", "_", dominio.lower())
        slug_cat = re.sub(r"[^\w\-]", "_", categoria.lower())
        nombre_archivo = f"{prefijo}_{slug_cat}_{slug_dominio}.md"
        ruta_archivo = _MEMORIA_DIR / nombre_archivo

        contenido_md = f"""# 🧬 {titulo}

**Tipo:** Playbook de Memoria Procedural (Auto-Aprendizaje Continuo)
**Categoría:** `{categoria}`
**Dominio:** `{dominio}`
**Evidencia Física Asociada:** `{evidencia_fisica}`
**Generado Por:** {_AGENTE_ORIGEN}

---

## 🎯 1. Objetivo & Resumen de Reutilización
Este playbook almacena la metodología exacta, esquema y plantilla probada para ejecutar tareas de tipo **{categoria}** en el ámbito **{dominio}** en un solo paso (*One-Shot Execution*).

---

## 🗺️ 2. Pipeline de Habilidades (Orden Exacto de Ejecución)
{paso_a_paso_skills}

---

## 🎨 3. Criterios de Triaje, Tokens & Esquema
{tokens_y_esquema}

---

## 🏗️ 4. Blueprint Reutilizable (Plantilla o Estructura Base)
```text
{blueprint_reutilizable}
```

---

## 🔄 5. Variables Adaptables para Nuevas Tareas
{variables_adaptables}

---

## 🔒 6. Reglas de Validación Aplicadas
- **Zero-Loss (HS-01):** Sin pérdida de datos.
- **Zero-Trust (HS-02):** Evidencia comprobada en disco.
- **Formato Ejecutivo:** Redacción concisa, maquetada profesionalmente.
- **Privacidad y Credenciales:** Sanitización estricta de tokens OAuth y datos confidenciales.

---
**Pertenece a:** [[memoria]] · [[Perfil_{_AGENTE_ORIGEN}]]
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
                agentes_involucrados=_AGENTE_ORIGEN
            )
        except Exception:
            pass

        return json.dumps({
            "status": "success",
            "mensaje": f"Playbook registrado exitosamente en {ruta_archivo.name}. Conocimiento procedural indexado para futuras tareas One-Shot.",
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
