"""
gestor_procedimientos.py — Motor de Aprendizaje por Demostración y Repetición Autónoma de Tareas
================================================================================================
Permite a la Flota de Agentes:
  1. MODO ENSEÑANZA / GRABACIÓN (Interactive Learning):
     - El usuario guía a la flota paso a paso para realizar una tarea ("Te voy a enseñar a...").
     - La flota prueba cada acción con Manos y Ojos, y la registra en la memoria procedural de recetas.
     - O en modo One-Shot: El usuario define los pasos y el agente los estructura y archiva de inmediato.
  2. MODO REPETICIÓN / EJECUCIÓN AUTÓNOMA (Autonomous Replay):
     - En el futuro, el usuario dice: "Luffy, repite la tarea X" o "haz lo que te enseñé de YouTube".
     - La flota recupera la receta aprendida de `memoria/procedimientos_aprendidos.json`.
     - Ejecuta cada paso de forma secuencial, determinista y verificada, sustituyendo variables dinámicas
       si el usuario lo pide, con CERO alucinación y CERO desperdicio de tokens.
"""

import os
import sys
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

# Localización de carpetas de memoria
_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["agente_orquestador"] else _CURRENT.parents[2]
_MEMORIA_DIR = _APP_ROOT / "memoria"
_PROCEDIMIENTOS_FILE = _MEMORIA_DIR / "procedimientos_aprendidos.json"
_SESION_ACTIVA_FILE = _MEMORIA_DIR / "sesion_aprendizaje_activa.json"
_RECETAS_DIR = _MEMORIA_DIR / "recetas_guiadas"


def _asegurar_directorios():
    _MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
    _RECETAS_DIR.mkdir(parents=True, exist_ok=True)


def _cargar_catalogo_procedimientos() -> Dict[str, Any]:
    """Carga el catálogo completo de procedimientos aprendidos."""
    _asegurar_directorios()
    if not _PROCEDIMIENTOS_FILE.exists():
        data_inicial = {
            "version": "1.0",
            "descripcion": "Catálogo de procedimientos y tareas aprendidas por demostración del usuario",
            "procedimientos": {}
        }
        _PROCEDIMIENTOS_FILE.write_text(json.dumps(data_inicial, indent=2, ensure_ascii=False), encoding="utf-8")
        return data_inicial
    try:
        return json.loads(_PROCEDIMIENTOS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "1.0", "procedimientos": {}}


def _guardar_catalogo_procedimientos(catalogo: Dict[str, Any]):
    """Guarda en disco el catálogo actualizado."""
    _asegurar_directorios()
    _PROCEDIMIENTOS_FILE.write_text(json.dumps(catalogo, indent=2, ensure_ascii=False), encoding="utf-8")


def _generar_slug(texto: str) -> str:
    """Convierte un nombre en un identificador limpio (slug)."""
    s = texto.lower().strip()
    s = re.sub(r"[áàäâ]", "a", s)
    s = re.sub(r"[éèëê]", "e", s)
    s = re.sub(r"[íìïî]", "i", s)
    s = re.sub(r"[óòöô]", "o", s)
    s = re.sub(r"[úùüû]", "u", s)
    s = re.sub(r"[ñ]", "n", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s.strip("_") or f"tarea_{int(time.time())}"


def _generar_documento_markdown_receta(proc: Dict[str, Any]) -> Path:
    """Genera un archivo Markdown legible en memoria/recetas_guiadas/ para inspección humana."""
    _asegurar_directorios()
    ruta_md = _RECETAS_DIR / f"{proc['id']}.md"
    
    lineas_pasos = []
    for p in proc.get("pasos", []):
        params_str = json.dumps(p.get("parametros", {}), ensure_ascii=False)
        lineas_pasos.append(
            f"### Paso {p.get('orden', 1)}: {p.get('descripcion', '')}\n"
            f"- **Herramienta:** `{p.get('herramienta', '')}`\n"
            f"- **Parámetros:** `{params_str}`\n"
            f"- **Pausa posterior:** `{p.get('pausa_segundos', 1.0)}s`\n"
        )

    disparadores_str = ", ".join(f"`{d}`" for d in proc.get("disparadores", []))
    vars_str = "\n".join(f"- `{{{v.get('nombre')}}}`: {v.get('descripcion', '')} (Defecto: '{v.get('valor_por_defecto', '')}')" for v in proc.get("parametros_variables", [])) or "Ninguna (determinista)"

    contenido = f"""# 📋 Receta Procedural: {proc.get('nombre')}

**ID:** `{proc.get('id')}`  
**Fecha de Aprendizaje:** `{proc.get('fecha_creacion')}`  
**Veces Ejecutado:** `{proc.get('veces_ejecutado', 0)}`  
**Última Ejecución:** `{proc.get('ultima_ejecucion', 'Nunca')}`  
**Disparadores de Activación:** {disparadores_str}

---

## 🎯 Descripción y Objetivo
{proc.get('descripcion', 'Sin descripción')}

## 🔄 Parámetros Dinámicos
{vars_str}

## 🏁 Resultado Esperado
{proc.get('resultado_esperado', 'Ejecución exitosa de todos los pasos')}

---

## 🛠️ Secuencia de Pasos Grabada

{chr(10).join(lineas_pasos)}

---
*Generado automáticamente por el Gestor de Procedimientos de la Tripulación IA.*
"""
    ruta_md.write_text(contenido, encoding="utf-8")
    return ruta_md


def buscar_procedimiento_en_catalogo(criterio: str) -> Optional[Dict[str, Any]]:
    """Busca una receta por ID exacto, por nombre o por coincidencia en disparadores."""
    catalogo = _cargar_catalogo_procedimientos()
    procs = catalogo.get("procedimientos", {})
    crit_limpio = criterio.lower().strip()
    slug_crit = _generar_slug(crit_limpio)

    # 1. Búsqueda exacta por ID
    if slug_crit in procs:
        return procs[slug_crit]
    if crit_limpio in procs:
        return procs[crit_limpio]

    # 2. Búsqueda por nombre
    for pid, p in procs.items():
        if p.get("nombre", "").lower().strip() == crit_limpio or pid.lower() == crit_limpio:
            return p

    # 3. Búsqueda por disparadores
    for pid, p in procs.items():
        for disp in p.get("disparadores", []):
            if disp.lower().strip() in crit_limpio or crit_limpio in disp.lower().strip():
                return p

    # 4. Búsqueda difusa por palabras clave
    palabras = [w for w in re.split(r"[\s_]+", crit_limpio) if len(w) > 3]
    mejor_proc = None
    mejor_score = 0
    for pid, p in procs.items():
        texto_busqueda = f"{pid} {p.get('nombre', '')} {' '.join(p.get('disparadores', []))} {p.get('descripcion', '')}".lower()
        score = sum(1 for w in palabras if w in texto_busqueda)
        if score > mejor_score and score >= max(1, len(palabras) // 2):
            mejor_score = score
            mejor_proc = p

    return mejor_proc


def _reemplazar_variables(params: Any, variables: Dict[str, Any]) -> Any:
    """Sustituye plantillas tipo {{variable}} recursivamente en diccionarios, listas y strings."""
    if isinstance(params, str):
        res = params
        for k, v in variables.items():
            patron = r"\{\{\s*" + re.escape(k) + r"\s*\}\}"
            res = re.sub(patron, str(v), res)
        return res
    elif isinstance(params, dict):
        return {k: _reemplazar_variables(v, variables) for k, v in params.items()}
    elif isinstance(params, list):
        return [_reemplazar_variables(item, variables) for item in params]
    return params


def resolver_herramienta(nombre_tool: str):
    """Resuelve la función ejecutable de una herramienta del ecosistema."""
    # 1. Herramientas de Manos y Ojos
    tools_candidatas = []
    try:
        from manos_y_ojos.skill_manos_y_ojos import HERRAMIENTAS_MANOS_Y_OJOS
        tools_candidatas.extend(HERRAMIENTAS_MANOS_Y_OJOS)
    except Exception:
        try:
            from skills.manos_y_ojos.skill_manos_y_ojos import HERRAMIENTAS_MANOS_Y_OJOS
            tools_candidatas.extend(HERRAMIENTAS_MANOS_Y_OJOS)
        except Exception:
            pass

    # 2. Herramientas Base del Sistema
    try:
        from base.skill_base import crear_archivo, leer_archivo, listar_directorio, ejecutar_comando
        tools_candidatas.extend([crear_archivo, leer_archivo, listar_directorio, ejecutar_comando])
    except Exception:
        try:
            from skills.base.skill_base import crear_archivo, leer_archivo, listar_directorio, ejecutar_comando
            tools_candidatas.extend([crear_archivo, leer_archivo, listar_directorio, ejecutar_comando])
        except Exception:
            pass

    # 3. Herramientas de Voz
    try:
        from voz.skill_voz import tool_hablar_por_cornetas, tool_enviar_nota_voz
        tools_candidatas.extend([tool_hablar_por_cornetas, tool_enviar_nota_voz])
    except Exception:
        try:
            from skills.voz.skill_voz import tool_hablar_por_cornetas, tool_enviar_nota_voz
            tools_candidatas.extend([tool_hablar_por_cornetas, tool_enviar_nota_voz])
        except Exception:
            pass

    for h in tools_candidatas:
        if getattr(h, "name", "") == nombre_tool:
            return h

    return None



def ejecutar_procedimiento_en_sistema(
    proc: Dict[str, Any],
    variables_usuario: Optional[Dict[str, Any]] = None,
    ejecutor_externo=None
) -> Dict[str, Any]:
    """
    Ejecuta paso a paso un procedimiento aprendido de forma determinista y segura.
    """
    pasos = proc.get("pasos", [])
    if not pasos:
        return {"status": "error", "mensaje": f"El procedimiento '{proc.get('nombre')}' no contiene pasos para ejecutar."}

    # Combinar valores por defecto con las variables enviadas por el usuario
    variables_finales = {}
    for var_def in proc.get("parametros_variables", []):
        nombre_var = var_def.get("nombre")
        if nombre_var:
            variables_finales[nombre_var] = var_def.get("valor_por_defecto", "")
    if variables_usuario:
        variables_finales.update(variables_usuario)

    print(f"\n[Procedimientos] 🚀 Iniciando ejecución de '{proc.get('nombre')}' ({len(pasos)} pasos)...")
    logs_ejecucion = []
    pasos_completados = 0

    for idx, paso in enumerate(pasos, 1):
        nombre_tool = paso.get("herramienta", "")
        desc_paso = paso.get("descripcion", f"Paso {idx}")
        params = paso.get("parametros", {})
        pausa = paso.get("pausa_segundos", 1.0)

        # Sustitución de variables
        params_resueltos = _reemplazar_variables(params, variables_finales)
        print(f"[Procedimientos]  -> Paso {idx}/{len(pasos)}: {desc_paso} [{nombre_tool}]")

        resultado_paso = None
        error_paso = None

        try:
            if ejecutor_externo:
                resultado_paso = ejecutor_externo(nombre_tool, params_resueltos)
            else:
                tool_func = resolver_herramienta(nombre_tool)
                if tool_func:
                    resultado_paso = tool_func.invoke(params_resueltos)
                else:
                    error_paso = f"Herramienta '{nombre_tool}' no disponible en el entorno."
        except Exception as e:
            error_paso = f"Excepción ejecutando {nombre_tool}: {str(e)}"

        # Verificar respuesta
        exito_paso = True
        if error_paso:
            exito_paso = False
        elif isinstance(resultado_paso, str):
            try:
                res_obj = json.loads(resultado_paso)
                if isinstance(res_obj, dict) and res_obj.get("status") == "error":
                    exito_paso = False
                    error_paso = res_obj.get("mensaje", "Fallo reportado por la herramienta")
            except Exception:
                pass
        elif isinstance(resultado_paso, dict) and resultado_paso.get("status") == "error":
            exito_paso = False
            error_paso = resultado_paso.get("mensaje", "Fallo reportado por la herramienta")

        logs_ejecucion.append({
            "paso": idx,
            "descripcion": desc_paso,
            "herramienta": nombre_tool,
            "parametros": params_resueltos,
            "exito": exito_paso,
            "resultado": resultado_paso if exito_paso else error_paso
        })

        if not exito_paso:
            print(f"[Procedimientos] ⚠️ Error en Paso {idx}: {error_paso}")
            return {
                "status": "error",
                "procedimiento": proc.get("nombre"),
                "paso_fallido": idx,
                "error": error_paso,
                "pasos_completados": pasos_completados,
                "total_pasos": len(pasos),
                "detalles": logs_ejecucion
            }

        pasos_completados += 1
        if pausa > 0 and idx < len(pasos):
            time.sleep(pausa)

    # Actualizar estadísticas de ejecución en el catálogo
    catalogo = _cargar_catalogo_procedimientos()
    proc_id = proc.get("id")
    if proc_id and proc_id in catalogo.get("procedimientos", {}):
        catalogo["procedimientos"][proc_id]["veces_ejecutado"] = catalogo["procedimientos"][proc_id].get("veces_ejecutado", 0) + 1
        catalogo["procedimientos"][proc_id]["ultima_ejecucion"] = datetime.now().isoformat()
        _guardar_catalogo_procedimientos(catalogo)

    print(f"[Procedimientos] ✅ Ejecución completada exitosamente ({pasos_completados}/{len(pasos)} pasos).")
    return {
        "status": "success",
        "mensaje": f"Procedimiento '{proc.get('nombre')}' ejecutado con éxito total ({pasos_completados}/{len(pasos)} pasos).",
        "resultado_esperado": proc.get("resultado_esperado", ""),
        "total_pasos": len(pasos),
        "detalles": logs_ejecucion
    }


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS LANGCHAIN (@tool) PARA LA FLOTA DE AGENTES
# ══════════════════════════════════════════════════════════════════════════════

@tool
def tool_iniciar_aprendizaje_tarea(nombre_tarea: str, descripcion: str, disparadores: str = "") -> str:
    """
    MODO ENSEÑANZA: Inicia una sesión interactiva de grabación guiada paso a paso.
    Usa esta herramienta cuando el usuario diga que te va a enseñar a realizar una nueva tarea
    o cuando quieras grabar un procedimiento guiado.
    A partir de este momento, cada paso que ejecutes se irá registrando con `tool_registrar_paso_aprendizaje`.

    Args:
        nombre_tarea: Título descriptivo (ej: 'Poner video de YouTube a pantalla completa', 'Llenar formulario de ventas').
        descripcion: Qué logra este procedimiento y para qué sirve.
        disparadores: Frases separadas por coma con las que el usuario pedirá repetir esta tarea en el futuro
                     (ej: 'reproduce youtube, pon pantalla completa en youtube, youtube relax').
    """
    _asegurar_directorios()
    slug_id = _generar_slug(nombre_tarea)

    lista_disparadores = [d.strip() for d in disparadores.split(",") if d.strip()]
    if nombre_tarea.lower() not in [d.lower() for d in lista_disparadores]:
        lista_disparadores.append(nombre_tarea.lower())

    sesion = {
        "id": slug_id,
        "nombre": nombre_tarea,
        "descripcion": descripcion,
        "disparadores": lista_disparadores,
        "inicio": datetime.now().isoformat(),
        "pasos": [],
        "parametros_variables": []
    }

    _SESION_ACTIVA_FILE.write_text(json.dumps(sesion, indent=2, ensure_ascii=False), encoding="utf-8")

    return json.dumps({
        "status": "success",
        "modo": "grabacion_activa",
        "mensaje": (
            f"🎬 ¡Sesión de aprendizaje iniciada para '{nombre_tarea}' (ID: `{slug_id}`)!\n"
            f"A partir de ahora, cada acción que el usuario te indique debes ejecutarla con tus herramientas "
            f"y registrarla invocando `tool_registrar_paso_aprendizaje`. "
            f"Cuando terminen todos los pasos, invoca `tool_finalizar_aprendizaje_tarea` para consolidar la memoria."
        ),
        "disparadores_registrados": lista_disparadores
    }, ensure_ascii=False)


@tool
def tool_registrar_paso_aprendizaje(
    descripcion_paso: str,
    herramienta: str,
    parametros_json: str,
    pausa_segundos: float = 1.0
) -> str:
    """
    MODO ENSEÑANZA: Agrega un paso completado a la sesión de grabación activa.
    Se debe invocar después de haber ejecutado y verificado cada acción individual en la PC o navegador.

    Args:
        descripcion_paso: Explicación de lo que hace este paso (ej: 'Navegar a la página de YouTube').
        herramienta: Nombre exacto de la herramienta ejecutada (ej: 'tool_navegar_web', 'tool_controlar_media_web', 'tool_hacer_clic_pc').
        parametros_json: Parámetros JSON que se le pasaron a la herramienta (ej: '{"url": "https://youtube.com", "visible": true}').
        pausa_segundos: Segundos recomendados de espera tras este paso para que la interfaz o video responda.
    """
    _asegurar_directorios()
    if not _SESION_ACTIVA_FILE.exists():
        return json.dumps({
            "status": "error",
            "mensaje": "No hay ninguna sesión de aprendizaje activa. Inicia una primero con `tool_iniciar_aprendizaje_tarea`."
        }, ensure_ascii=False)

    try:
        sesion = json.loads(_SESION_ACTIVA_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error leyendo sesión activa: {str(e)}"})

    try:
        params_obj = json.loads(parametros_json) if isinstance(parametros_json, str) else parametros_json
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"parametros_json no es un JSON válido: {str(e)}"})

    orden_actual = len(sesion.get("pasos", [])) + 1
    nuevo_paso = {
        "orden": orden_actual,
        "descripcion": descripcion_paso,
        "herramienta": herramienta,
        "parametros": params_obj,
        "pausa_segundos": float(pausa_segundos)
    }

    # Detectar variables {{variable}} en los parámetros
    cadena_params = json.dumps(params_obj)
    matches_vars = re.findall(r"\{\{\s*(\w+)\s*\}\}", cadena_params)
    vars_existentes = {v.get("nombre") for v in sesion.get("parametros_variables", [])}
    for var in matches_vars:
        if var not in vars_existentes:
            sesion.setdefault("parametros_variables", []).append({
                "nombre": var,
                "descripcion": f"Parámetro dinámico extraído de {descripcion_paso}",
                "valor_por_defecto": ""
            })
            vars_existentes.add(var)

    sesion.setdefault("pasos", []).append(nuevo_paso)
    _SESION_ACTIVA_FILE.write_text(json.dumps(sesion, indent=2, ensure_ascii=False), encoding="utf-8")

    return json.dumps({
        "status": "success",
        "mensaje": f"Paso {orden_actual} registrado con éxito: '{descripcion_paso}' [{herramienta}].",
        "total_pasos_grabados": orden_actual
    }, ensure_ascii=False)


@tool
def tool_finalizar_aprendizaje_tarea(resultado_esperado: str = "") -> str:
    """
    MODO ENSEÑANZA: Finaliza la sesión de grabación activa, compila la receta procedural,
    la archiva permanentemente en memoria y genera el documento markdown de referencia.
    A partir de este momento la flota puede reproducir la tarea por sí sola de forma autónoma.

    Args:
        resultado_esperado: Qué resultado físico o visual debe quedar al culminar la tarea
                           (ej: 'Video de YouTube reproduciéndose en pantalla completa en el monitor principal').
    """
    _asegurar_directorios()
    if not _SESION_ACTIVA_FILE.exists():
        return json.dumps({
            "status": "error",
            "mensaje": "No hay ninguna sesión de grabación activa para finalizar."
        }, ensure_ascii=False)

    try:
        sesion = json.loads(_SESION_ACTIVA_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error leyendo sesión: {str(e)}"})

    pasos = sesion.get("pasos", [])
    if not pasos:
        return json.dumps({
            "status": "error",
            "mensaje": "No se puede finalizar una sesión sin pasos grabados. Registra al menos un paso antes."
        }, ensure_ascii=False)

    catalogo = _cargar_catalogo_procedimientos()
    proc_id = sesion["id"]

    procedimiento_final = {
        "id": proc_id,
        "nombre": sesion.get("nombre"),
        "descripcion": sesion.get("descripcion"),
        "disparadores": sesion.get("disparadores", []),
        "parametros_variables": sesion.get("parametros_variables", []),
        "pasos": pasos,
        "resultado_esperado": resultado_esperado or f"Ejecución exitosa de los {len(pasos)} pasos de '{sesion.get('nombre')}'.",
        "fecha_creacion": datetime.now().isoformat(),
        "veces_ejecutado": 0,
        "ultima_ejecucion": None
    }

    catalogo.setdefault("procedimientos", {})[proc_id] = procedimiento_final
    _guardar_catalogo_procedimientos(catalogo)

    # Generar Markdown en memoria/recetas_guiadas/
    ruta_md = _generar_documento_markdown_receta(procedimiento_final)

    # Eliminar sesión activa
    try:
        _SESION_ACTIVA_FILE.unlink()
    except Exception:
        pass

    return json.dumps({
        "status": "success",
        "mensaje": (
            f"🎉 ¡Procedimiento '{procedimiento_final['nombre']}' aprendido y archivado con éxito!\n"
            f"- Total de pasos: {len(pasos)}\n"
            f"- Disparadores: {', '.join(procedimiento_final['disparadores'])}\n"
            f"- Documentación generada: {ruta_md.name}\n"
            f"Ahora el usuario puede pedir en cualquier momento: 'repite la tarea {proc_id}' o usar sus disparadores "
            f"y la flota lo ejecutará completamente sola."
        ),
        "id_procedimiento": proc_id,
        "documento_memoria": str(ruta_md)
    }, ensure_ascii=False)


@tool
def tool_guardar_procedimiento_aprendido(
    nombre: str,
    descripcion: str,
    disparadores: str,
    pasos_json: str,
    resultado_esperado: str = "",
    parametros_variables_json: str = "[]"
) -> str:
    """
    MODO ONE-SHOT / DIRECTO: Guarda y archiva un procedimiento completo en un solo paso
    sin necesidad de abrir una sesión interactiva.
    Usa esto cuando el usuario te describa todos los pasos de una vez o cuando ya tengas
    la lista de pasos estructurada.

    Args:
        nombre: Título del procedimiento (ej: 'Buscar y reproducir lofi en YouTube').
        descripcion: Qué hace la tarea y cuándo debe utilizarse.
        disparadores: Frases separadas por coma que activarán este procedimiento.
        pasos_json: Lista JSON de pasos con formato:
                   '[{"orden": 1, "descripcion": "...", "herramienta": "tool_...", "parametros": {...}, "pausa_segundos": 1.0}, ...]'
        resultado_esperado: Criterio de verificación final (ej: 'Video reproduciéndose en pantalla completa').
        parametros_variables_json: Lista JSON opcional de variables adaptables:
                                  '[{"nombre": "tema", "descripcion": "Canción a buscar", "valor_por_defecto": "lofi"}]'
    """
    _asegurar_directorios()
    proc_id = _generar_slug(nombre)

    try:
        pasos = json.loads(pasos_json) if isinstance(pasos_json, str) else pasos_json
        if not isinstance(pasos, list) or not pasos:
            return json.dumps({"status": "error", "mensaje": "pasos_json debe ser una lista JSON no vacía de pasos."})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"pasos_json inválido: {str(e)}"})

    try:
        vars_dinamicas = json.loads(parametros_variables_json) if isinstance(parametros_variables_json, str) else parametros_variables_json
        if not isinstance(vars_dinamicas, list):
            vars_dinamicas = []
    except Exception:
        vars_dinamicas = []

    lista_disparadores = [d.strip() for d in disparadores.split(",") if d.strip()]
    if nombre.lower() not in [d.lower() for d in lista_disparadores]:
        lista_disparadores.append(nombre.lower())

    catalogo = _cargar_catalogo_procedimientos()
    procedimiento = {
        "id": proc_id,
        "nombre": nombre,
        "descripcion": descripcion,
        "disparadores": lista_disparadores,
        "parametros_variables": vars_dinamicas,
        "pasos": pasos,
        "resultado_esperado": resultado_esperado or f"Ejecución exitosa de '{nombre}'",
        "fecha_creacion": datetime.now().isoformat(),
        "veces_ejecutado": 0,
        "ultima_ejecucion": None
    }

    catalogo.setdefault("procedimientos", {})[proc_id] = procedimiento
    _guardar_catalogo_procedimientos(catalogo)
    ruta_md = _generar_documento_markdown_receta(procedimiento)

    return json.dumps({
        "status": "success",
        "mensaje": f"Procedimiento '{nombre}' guardado e indexado exitosamente ({len(pasos)} pasos).",
        "id_procedimiento": proc_id,
        "documento_memoria": str(ruta_md)
    }, ensure_ascii=False)


@tool
def tool_ejecutar_tarea_aprendida(nombre_o_disparador: str, parametros_json: str = "{}") -> str:
    """
    MODO REPETICIÓN AUTÓNOMA: Busca un procedimiento previamente aprendido por el usuario
    y lo ejecuta paso a paso sin necesidad de instrucciones adicionales.
    Usa esta herramienta cuando el usuario te pida 'repite la tarea X', 'ejecuta el procedimiento X',
    o diga cualquiera de las frases de activación de una tarea aprendida.

    Args:
        nombre_o_disparador: Nombre, ID o frase disparadora del procedimiento a repetir.
        parametros_json: Diccionario JSON opcional con variables específicas para esta ejecución
                        (ej: '{"tema": "synthwave radio"}').
    """
    _asegurar_directorios()
    proc = buscar_procedimiento_en_catalogo(nombre_o_disparador)
    if not proc:
        return json.dumps({
            "status": "error",
            "mensaje": f"No se encontró ningún procedimiento aprendido que coincida con '{nombre_o_disparador}'. Usa `tool_listar_tareas_aprendidas` para ver las disponibles."
        }, ensure_ascii=False)

    try:
        vars_usuario = json.loads(parametros_json) if isinstance(parametros_json, str) else (parametros_json or {})
    except Exception:
        vars_usuario = {}

    resultado = ejecutar_procedimiento_en_sistema(proc, variables_usuario=vars_usuario)
    return json.dumps(resultado, ensure_ascii=False)


@tool
def tool_listar_tareas_aprendidas() -> str:
    """
    Consulta y lista todos los procedimientos y tareas que la flota ha aprendido por demostración del usuario.
    Muestra sus IDs, nombres, disparadores, número de pasos y estadísticas de ejecución.
    """
    _asegurar_directorios()
    catalogo = _cargar_catalogo_procedimientos()
    procs = catalogo.get("procedimientos", {})

    if not procs:
        return json.dumps({
            "status": "success",
            "total": 0,
            "mensaje": "Aún no hay procedimientos aprendidos en la memoria. Puedes enseñarle una tarea a la flota con `tool_iniciar_aprendizaje_tarea` o `tool_guardar_procedimiento_aprendido`."
        }, ensure_ascii=False)

    resumen = []
    for pid, p in procs.items():
        resumen.append({
            "id": pid,
            "nombre": p.get("nombre"),
            "descripcion": p.get("descripcion"),
            "disparadores": p.get("disparadores", []),
            "total_pasos": len(p.get("pasos", [])),
            "veces_ejecutado": p.get("veces_ejecutado", 0),
            "ultima_ejecucion": p.get("ultima_ejecucion")
        })

    return json.dumps({
        "status": "success",
        "total": len(resumen),
        "procedimientos": resumen
    }, ensure_ascii=False)


def eliminar_procedimiento_de_catalogo(nombre_o_id: str) -> Dict[str, Any]:
    """Elimina físicamente un procedimiento del catálogo y su markdown asociado."""
    _asegurar_directorios()
    catalogo = _cargar_catalogo_procedimientos()
    procs = catalogo.get("procedimientos", {})

    proc = buscar_procedimiento_en_catalogo(nombre_o_id)
    if not proc:
        return {"status": "error", "mensaje": f"Procedimiento '{nombre_o_id}' no encontrado."}

    proc_id = proc.get("id")
    if proc_id in procs:
        del procs[proc_id]
        _guardar_catalogo_procedimientos(catalogo)

    # Eliminar markdown asociado
    ruta_md = _RECETAS_DIR / f"{proc_id}.md"
    if ruta_md.exists():
        try:
            ruta_md.unlink()
        except Exception:
            pass

    return {
        "status": "success",
        "mensaje": f"Procedimiento '{proc.get('nombre')}' (ID: `{proc_id}`) eliminado exitosamente de la memoria."
    }


@tool
def tool_eliminar_tarea_aprendida(nombre_o_id: str) -> str:
    """
    Elimina un procedimiento aprendido de la memoria y su archivo markdown correspondiente.

    Args:
        nombre_o_id: Nombre o ID del procedimiento a borrar.
    """
    res = eliminar_procedimiento_de_catalogo(nombre_o_id)
    return json.dumps(res, ensure_ascii=False)



HERRAMIENTAS_PROCEDIMIENTOS = [
    tool_iniciar_aprendizaje_tarea,
    tool_registrar_paso_aprendizaje,
    tool_finalizar_aprendizaje_tarea,
    tool_guardar_procedimiento_aprendido,
    tool_ejecutar_tarea_aprendida,
    tool_listar_tareas_aprendidas,
    tool_eliminar_tarea_aprendida
]
