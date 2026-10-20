"""
skill_supabase.py — Habilidad: Gestión Integral de Supabase y Auditoría de Seguridad RLS
========================================================================================
Capacita al Subagente de Desarrollo (Zoro) para interactuar con la infraestructura
de Supabase a nivel de cuenta y proyecto:
  1. Ejecución de consultas SQL directas (DDL, DML, migraciones) vía Management API.
  2. Auditoría exhaustiva de Row Level Security (RLS) en tablas públicas.
  3. Modificación de políticas RLS y activación/desactivación de seguridad a nivel de fila.
  4. Operaciones de lectura e inserción directa en tablas.
  5. Inspección del parque de proyectos y organizaciones en la cuenta de Supabase.
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

# Carga de variables de entorno si no estuvieran presentes
try:
    from dotenv import load_dotenv
    _APP_ROOT = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=_APP_ROOT / ".env")
except Exception:
    pass

MANAGEMENT_API_BASE = "https://api.supabase.com/v1"


def _obtener_token_acceso() -> str:
    """Recupera el Personal Access Token de Supabase desde el entorno."""
    return os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()


def _obtener_project_ref_defecto() -> str:
    """Recupera el project ref configurado desde las variables de entorno."""
    return os.getenv("SUPABASE_PROJECT_REF", "").strip()


def _ejecutar_api_management(metodo: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper para enviar peticiones autenticadas a la Management API de Supabase."""
    token = _obtener_token_acceso()
    if not token:
        return {"error": "SUPABASE_ACCESS_TOKEN no está configurado en las variables de entorno."}

    url = f"{MANAGEMENT_API_BASE}{endpoint}" if endpoint.startswith("/") else f"{MANAGEMENT_API_BASE}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=metodo)

    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            contenido = res.read().decode("utf-8")
            if contenido:
                try:
                    return json.loads(contenido)
                except json.JSONDecodeError:
                    return {"resultado_raw": contenido}
            return {"status": "ok", "code": res.status}
    except urllib.error.HTTPError as e:
        detalles = ""
        try:
            detalles = e.read().decode("utf-8")
        except Exception:
            pass
        return {"error": f"HTTP {e.code}: {e.reason}", "detalles": detalles}
    except Exception as e:
        return {"error": str(e)}


def obtener_prompt_supabase() -> str:
    """
    System Prompt especializado y encapsulado para la habilidad Supabase.
    Cumple con la Regla de Oro 4 (Inyección Dinámica de Prompts).
    """
    return """[🛑 HARD-STOP: MODO ADMINISTRACIÓN Y AUDITORÍA DE SUPABASE ACTIVO 🛑]
Eres el Arquitecto de Infraestructura Cloud y DBA de Supabase del Subagente de Desarrollo.
Tu misión es gestionar las bases de datos de Supabase, auditar y blindar las políticas RLS
(Row Level Security), ejecutar migraciones SQL y garantizar la resiliencia de la persistencia de datos.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. SEGURIDAD Y AUDITORÍA RLS PRIMERO:
   - Toda tabla pública en Supabase DEBE tener habilitado Row Level Security (RLS).
   - Utiliza `tool_supabase_auditar_seguridad_rls` para validar el estado de `rowsecurity` y las políticas vigentes.
   - Ante tablas desprotegidas (`rowsecurity: false`), utiliza `tool_supabase_modificar_rls` para blindarlas.
2. EJECUCIÓN SQL SEGURA Y ATÓMICA:
   - Usa `tool_supabase_ejecutar_sql` para consultas complejas, creación de tablas y reglas.
   - Prohibido ejecutar comandos destructivos (`DROP TABLE`, `TRUNCATE`) sin autorización explícita del Capitán.
3. AISLAMIENTO DE CREDENCIALES:
   - Nunca expongas tokens ni claves en los mensajes o logs. Todo acceso se realiza mediante las variables del entorno.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS DE LA HABILIDAD (CUMPLEN CON LA REGLA DE ORO 2: DECORADAS CON @tool)
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tool_supabase_listar_proyectos() -> Dict[str, Any]:
    """
    Lista todos los proyectos de Supabase asociados a la cuenta, indicando
    su ID, nombre, estado (ACTIVE_HEALTHY, PAUSED, etc.), versión de PostgreSQL y host.
    """
    res = _ejecutar_api_management("GET", "/projects")
    if isinstance(res, list):
        proyectos = []
        for p in res:
            proyectos.append({
                "id": p.get("id"),
                "ref": p.get("ref"),
                "name": p.get("name"),
                "status": p.get("status"),
                "region": p.get("region"),
                "host": p.get("database", {}).get("host"),
                "postgres_engine": p.get("database", {}).get("postgres_engine")
            })
        return {"status": "ok", "total_proyectos": len(proyectos), "proyectos": proyectos}
    return res


@tool
def tool_supabase_ejecutar_sql(query: str, project_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Ejecuta una consulta o comando SQL arbitrario en la base de datos de Supabase
    (DDL, DML, SELECT, ALTER TABLE, CREATE POLICY, etc.) a través de la Management API.

    Args:
        query: Consulta SQL completa a ejecutar.
        project_ref: Identificador del proyecto (opcional; si se omite, usa el proyecto por defecto de la flota).
    """
    ref = project_ref or _obtener_project_ref_defecto()
    if not ref:
        return {"error": "No se especificó project_ref y no hay uno configurado por defecto."}

    endpoint = f"/projects/{ref}/database/query"
    res = _ejecutar_api_management("POST", endpoint, {"query": query})
    if isinstance(res, list):
        return {"status": "ok", "filas_retornadas": len(res), "datos": res}
    return res


@tool
def tool_supabase_auditar_seguridad_rls(project_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Audita exhaustivamente el estado de Row Level Security (RLS) en todas las tablas
    del esquema 'public' del proyecto Supabase, listando qué tablas tienen RLS activo
    y cuáles políticas de seguridad específicas están configuradas.

    Args:
        project_ref: Identificador del proyecto a auditar (opcional).
    """
    ref = project_ref or _obtener_project_ref_defecto()
    
    # 1. Consultar estado de RLS en pg_tables
    sql_tables = "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
    res_tables = tool_supabase_ejecutar_sql.invoke({"query": sql_tables, "project_ref": ref})
    
    if "error" in res_tables:
        return {"error": "Error al consultar pg_tables", "detalles": res_tables}

    tablas = res_tables.get("datos", [])
    
    # 2. Consultar políticas existentes en pg_policies
    sql_policies = "SELECT tablename, policyname, roles, cmd, permissive FROM pg_policies WHERE schemaname = 'public' ORDER BY tablename, policyname;"
    res_policies = tool_supabase_ejecutar_sql.invoke({"query": sql_policies, "project_ref": ref})
    politicas = res_policies.get("datos", []) if "datos" in res_policies else []

    # Mapear políticas por tabla
    mapa_politicas: Dict[str, List[Dict[str, Any]]] = {}
    for pol in politicas:
        tname = pol.get("tablename")
        if tname not in mapa_politicas:
            mapa_politicas[tname] = []
        mapa_politicas[tname].append(pol)

    resultado_auditoria = []
    tablas_desprotegidas = []

    for t in tablas:
        nombre_tabla = t.get("tablename")
        rls_activo = bool(t.get("rowsecurity"))
        pols = mapa_politicas.get(nombre_tabla, [])
        
        info_tabla = {
            "tabla": nombre_tabla,
            "rls_activo": rls_activo,
            "total_politicas": len(pols),
            "politicas": pols
        }
        resultado_auditoria.append(info_tabla)
        if not rls_activo:
            tablas_desprotegidas.append(nombre_tabla)

    veredicto = "PASS_SEGURO" if not tablas_desprotegidas else "ALERTA_TABLAS_EXPUESTAS"

    return {
        "status": "ok",
        "project_ref": ref,
        "veredicto_seguridad": veredicto,
        "total_tablas_auditadas": len(tablas),
        "tablas_desprotegidas": tablas_desprotegidas,
        "auditoria_detallada": resultado_auditoria
    }


@tool
def tool_supabase_modificar_rls(tabla: str, habilitar: bool = True, project_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Habilita o deshabilita Row Level Security (RLS) en una tabla específica de Supabase.

    Args:
        tabla: Nombre de la tabla en el esquema público (ej. 'tasks', 'users').
        habilitar: True para activar RLS ('ENABLE ROW LEVEL SECURITY'), False para desactivarlo.
        project_ref: Identificador del proyecto (opcional).
    """
    accion = "ENABLE" if habilitar else "DISABLE"
    sql = f"ALTER TABLE public.\"{tabla}\" {accion} ROW LEVEL SECURITY;"
    res = tool_supabase_ejecutar_sql.invoke({"query": sql, "project_ref": project_ref})
    if "error" in res:
        return {"status": "error", "mensaje": f"No se pudo modificar RLS en '{tabla}'", "detalles": res}
    return {
        "status": "ok",
        "mensaje": f"Row Level Security {accion} ejecutado con éxito en la tabla '{tabla}'."
    }


@tool
def tool_supabase_crear_politica_rls(
    tabla: str,
    nombre_politica: str,
    comando: str = "ALL",
    roles: str = "authenticated",
    using_expr: str = "true",
    with_check_expr: Optional[str] = None,
    project_ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crea una política de seguridad RLS en una tabla de Supabase.

    Args:
        tabla: Nombre de la tabla.
        nombre_politica: Nombre descriptivo de la política (ej. 'permitir_lectura_autenticados').
        comando: Comando afectado (SELECT, INSERT, UPDATE, DELETE o ALL).
        roles: Rol de Supabase (anon, authenticated, o public).
        using_expr: Expresión booleana SQL para la cláusula USING (ej. 'auth.uid() = user_id' o 'true').
        with_check_expr: Expresión SQL opcional para la cláusula WITH CHECK.
        project_ref: Identificador del proyecto (opcional).
    """
    clausula_with_check = f" WITH CHECK ({with_check_expr})" if with_check_expr else ""
    sql = (
        f"CREATE POLICY \"{nombre_politica}\" ON public.\"{tabla}\" "
        f"FOR {comando} TO {roles} USING ({using_expr}){clausula_with_check};"
    )
    res = tool_supabase_ejecutar_sql.invoke({"query": sql, "project_ref": project_ref})
    if "error" in res:
        return {"status": "error", "mensaje": f"Error al crear política '{nombre_politica}'", "detalles": res}
    return {
        "status": "ok",
        "mensaje": f"Política RLS '{nombre_politica}' creada con éxito en la tabla '{tabla}'."
    }


@tool
def tool_supabase_consultar_tabla(
    tabla: str,
    columnas: str = "*",
    filtros: Optional[Dict[str, Any]] = None,
    limite: int = 50,
    project_ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Consulta registros de una tabla de Supabase utilizando el cliente Supabase con la service_role key
    o fallback a consulta SQL directa.

    Args:
        tabla: Nombre de la tabla a consultar.
        columnas: Columnas a seleccionar separadas por comas (por defecto '*').
        filtros: Diccionario opcional de igualdad clave-valor para filtrar filas.
        limite: Cantidad máxima de filas a retornar (por defecto 50).
        project_ref: Identificador del proyecto (opcional).
    """
    # Intentar consulta vía SQL seguro con límite estricto
    condiciones = []
    if filtros:
        for k, v in filtros.items():
            if isinstance(v, (int, float)):
                condiciones.append(f"\"{k}\" = {v}")
            else:
                val_escaped = str(v).replace("'", "''")
                condiciones.append(f"\"{k}\" = '{val_escaped}'")
    
    where_clause = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    sql = f"SELECT {columnas} FROM public.\"{tabla}\"{where_clause} LIMIT {limite};"
    
    return tool_supabase_ejecutar_sql.invoke({"query": sql, "project_ref": project_ref})


@tool
def tool_supabase_insertar_registro(
    tabla: str,
    registro: Dict[str, Any],
    project_ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inserta un nuevo registro en una tabla de Supabase.

    Args:
        tabla: Nombre de la tabla destino.
        registro: Diccionario con los campos y valores a insertar.
        project_ref: Identificador del proyecto (opcional).
    """
    if not registro:
        return {"error": "El registro a insertar está vacío."}

    cols = list(registro.keys())
    vals = list(registro.values())

    cols_str = ", ".join([f"\"{c}\"" for c in cols])
    vals_escaped = []
    for v in vals:
        if v is None:
            vals_escaped.append("NULL")
        elif isinstance(v, (int, float)):
            vals_escaped.append(str(v))
        elif isinstance(v, bool):
            vals_escaped.append("TRUE" if v else "FALSE")
        elif isinstance(v, (dict, list)):
            j_str = json.dumps(v).replace("'", "''")
            vals_escaped.append(f"'{j_str}'::jsonb")
        else:
            s_str = str(v).replace("'", "''")
            vals_escaped.append(f"'{s_str}'")

    vals_str = ", ".join(vals_escaped)
    sql = f"INSERT INTO public.\"{tabla}\" ({cols_str}) VALUES ({vals_str}) RETURNING *;"
    return tool_supabase_ejecutar_sql.invoke({"query": sql, "project_ref": project_ref})


# Lista canónica exportada de herramientas de la habilidad
HERRAMIENTAS_SUPABASE = [
    tool_supabase_listar_proyectos,
    tool_supabase_ejecutar_sql,
    tool_supabase_auditar_seguridad_rls,
    tool_supabase_modificar_rls,
    tool_supabase_crear_politica_rls,
    tool_supabase_consultar_tabla,
    tool_supabase_insertar_registro,
]
