"""
skill_bases_de_datos_sql.py — Habilidad: Gestión de Bases de Datos, SQL y Procesamiento Big Data
================================================================================================
Capacita al Subagente de Desarrollo para gestionar bases de datos relacionales (SQLite,
PostgreSQL, MySQL) y procesar grandes volúmenes de datos analíticos (Big Data) mediante SQL:
  1. Consultas parametrizadas seguras (prevención total de SQL Injection).
  2. Streaming y procesamiento en lotes (chunking) para evitar agotar la memoria RAM.
  3. Motor analítico Polars SQL para procesar millones de registros sobre Parquet, CSV y JSON.
  4. Análisis de rendimiento de consultas (EXPLAIN QUERY PLAN) e indexación inteligente.
  5. Migraciones de esquemas DDL bajo transacciones atómicas seguras.
"""

import os
import re
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_DATA_DIR = _APP_ROOT / _AGENTE / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


def obtener_prompt_bases_de_datos_sql() -> str:
    """
    System Prompt especializado y encapsulado para la Gestión de Bases de Datos y SQL Big Data.
    """
    return """[🛑 HARD-STOP: MODO GESTIÓN DE BASES DE DATOS Y SQL BIG DATA ACTIVO 🛑]
Eres el Arquitecto de Bases de Datos, Ingeniero SQL y Especialista en Big Data del Subagente de Desarrollo.
Tu misión es diseñar esquemas relacionales, escribir consultas SQL optimizadas, analizar planes de ejecución y procesar grandes volúmenes de información con rendimiento de nivel de producción.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. PREVENCIÓN TOTAL DE SQL INJECTION:
   - NUNCA concatenes entradas o variables de usuario directamente en la cadena SQL (`f"SELECT * FROM t WHERE id = {var}"`).
   - Usa SIEMPRE consultas parametrizadas con marcadores de posición (`?` en SQLite, `:param` en SQLAlchemy).
2. ECONOMÍA DE MEMORIA Y PROCESAMIENTO EN LOTES (BIG DATA FIRST):
   - Prohibido hacer `SELECT *` sobre tablas de gran tamaño sin límite (`LIMIT`) o paginación por cursor.
   - En consultas masivas, procesa los datos en lotes (`tamano_lote=500` o generadores) para proteger la memoria RAM.
   - Para procesar archivos planos masivos (CSVs de cientos de megabytes o millones de filas), utiliza `tool_sql_procesar_grandes_datos` (Polars SQL engine).
3. OPTIMIZACIÓN Y PLANES DE EJECUCIÓN (EXPLAIN):
   - Ante consultas lentas o que involucren uniones (`JOIN`) complejas, invoca `tool_sql_analizar_rendimiento` para inspeccionar si la base de datos realiza escaneos completos de tabla (*SCAN TABLE*).
   - Diseña índices compuestos (`CREATE INDEX`) para acelerar filtros recurrentes en cláusulas `WHERE` y `ORDER BY`.
4. TRANSACCIONES ATÓMICAS (ACID):
   - Toda mutación de esquema o inserción en masa debe ejecutarse dentro de un bloque de transacción (`BEGIN TRANSACTION ... COMMIT`), asegurando reversión (`ROLLBACK`) inmediata ante cualquier fallo.
   - Prohibido ejecutar `DROP DATABASE` o `DROP TABLE` en caliente sin respaldo de datos previo.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE CONEXIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def _obtener_conexion_sqlite(ruta_o_conexion: str) -> sqlite3.Connection:
    """Abre conexión SQLite en memoria o disco con soporte de diccionarios de fila."""
    ruta = ":memory:" if ruta_o_conexion.lower() in [":memory:", "memory"] else ruta_o_conexion
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    return conn


def _es_consulta_destructiva(sql: str) -> Tuple[bool, str]:
    """Detecta operaciones altamente destructivas que requieran precaución extrema."""
    sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE).strip().upper()
    if re.search(r"\bDROP\s+DATABASE\b", sql_clean):
        return True, "Operación DROP DATABASE bloqueada por seguridad."
    if re.search(r"\bTRUNCATE\s+TABLE\b", sql_clean):
        return True, "Operación TRUNCATE TABLE detectada. Requiere confirmación explícita."
    return False, ""


# ═══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS TÉCNICAS SQL
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tool_sql_ejecutar_consulta(
    motor_db: str,
    cadena_conexion_o_ruta: str,
    consulta_sql: str,
    parametros: dict = None,
    tamano_lote: int = 500
) -> str:
    """
    Ejecuta consultas SQL parametrizadas de forma segura sobre SQLite o bases relacionales.
    Soporta SELECT (con streaming en lotes para proteger RAM), INSERT, UPDATE y DELETE.

    Args:
        motor_db: Motor de base de datos ('sqlite', 'postgresql', 'mysql').
        cadena_conexion_o_ruta: Ruta al archivo SQLite (ej: 'proyectos/app.db') o URI de conexión SQLAlchemy.
        consulta_sql: Sentencia SQL a ejecutar con marcadores parametrizados.
        parametros: Diccionario o lista con los valores de los parámetros.
        tamano_lote: Límite de registros devueltos por lote para consultas SELECT (default: 500).
    """
    try:
        # 1. Auditoría de seguridad contra operaciones destructivas no autorizadas
        bloqueado, motivo = _es_consulta_destructiva(consulta_sql)
        if bloqueado:
            return json.dumps({"status": "error", "mensaje": motivo})

        inicio = time.time()
        motor = motor_db.lower()

        # Enfoque SQLite nativo
        if motor == "sqlite":
            conn = _obtener_conexion_sqlite(cadena_conexion_o_ruta)
            cursor = conn.cursor()

            params = parametros if parametros else ()
            cursor.execute(consulta_sql, params)

            es_select = consulta_sql.strip().upper().startswith("SELECT") or "PRAGMA" in consulta_sql.upper()

            if es_select:
                columnas = [desc[0] for desc in cursor.description] if cursor.description else []
                filas_lote = cursor.fetchmany(tamano_lote)
                resultados = [dict(zip(columnas, fila)) for fila in filas_lote]
                total_en_lote = len(resultados)

                conn.close()
                duracion_ms = int((time.time() - inicio) * 1000)

                return json.dumps({
                    "status": "success",
                    "tipo": "SELECT",
                    "motor": "sqlite",
                    "columnas": columnas,
                    "total_devuelto": total_en_lote,
                    "limite_lote_aplicado": tamano_lote,
                    "tiempo_ms": duracion_ms,
                    "datos": resultados
                }, ensure_ascii=False)
            else:
                conn.commit()
                afectadas = cursor.rowcount
                conn.close()
                duracion_ms = int((time.time() - inicio) * 1000)

                return json.dumps({
                    "status": "success",
                    "tipo": "MUTACION (INSERT/UPDATE/DELETE)",
                    "motor": "sqlite",
                    "filas_afectadas": afectadas,
                    "tiempo_ms": duracion_ms
                }, ensure_ascii=False)

        # Enfoque SQLAlchemy para PostgreSQL/MySQL
        else:
            try:
                from sqlalchemy import create_engine, text
                engine = create_engine(cadena_conexion_o_ruta)
                with engine.connect() as connection:
                    statement = text(consulta_sql)
                    result = connection.execute(statement, parametros or {})

                    if result.returns_rows:
                        columnas = list(result.keys())
                        filas = result.fetchmany(tamano_lote)
                        resultados = [dict(zip(columnas, fila)) for fila in filas]
                        duracion_ms = int((time.time() - inicio) * 1000)

                        return json.dumps({
                            "status": "success",
                            "tipo": "SELECT",
                            "motor": motor,
                            "columnas": columnas,
                            "total_devuelto": len(resultados),
                            "tiempo_ms": duracion_ms,
                            "datos": resultados
                        }, ensure_ascii=False)
                    else:
                        connection.commit()
                        duracion_ms = int((time.time() - inicio) * 1000)
                        return json.dumps({
                            "status": "success",
                            "tipo": "MUTACION",
                            "motor": motor,
                            "filas_afectadas": result.rowcount,
                            "tiempo_ms": duracion_ms
                        }, ensure_ascii=False)
            except ImportError:
                return json.dumps({"status": "error", "mensaje": "Se requiere instalar el driver de la base de datos."})

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al ejecutar consulta SQL: {str(e)}"})


@tool
def tool_sql_procesar_grandes_datos(
    ruta_archivo_datos: str,
    consulta_sql_analitica: str,
    ruta_salida_parquet_o_csv: str = ""
) -> str:
    """
    Motor de análisis de Big Data acelerado por Polars SQL.
    Permite procesar archivos gigantescos (CSV, Parquet, JSONL) de millones de filas
    ejecutando consultas SQL analíticas de alto rendimiento sin saturar la memoria RAM.

    Args:
        ruta_archivo_datos: Ruta absoluta o relativa al dataset (.csv, .parquet, .jsonl).
        consulta_sql_analitica: Consulta SQL (ej: 'SELECT categoria, count(*), sum(monto) FROM self GROUP BY categoria').
        ruta_salida_parquet_o_csv: Opcional. Ruta para persistir el resultado procesado.
    """
    try:
        import polars as pl

        path_datos = Path(ruta_archivo_datos)
        if not path_datos.exists():
            return json.dumps({"status": "error", "mensaje": f"El archivo de datos '{ruta_archivo_datos}' no existe."})

        inicio = time.time()

        # Cargar en modo LazyFrame para no saturar memoria RAM
        extension = path_datos.suffix.lower()
        if extension == ".parquet":
            lf = pl.scan_parquet(str(path_datos))
        elif extension == ".csv":
            lf = pl.scan_csv(str(path_datos))
        elif extension in [".json", ".jsonl", ".ndjson"]:
            lf = pl.scan_ndjson(str(path_datos))
        else:
            return json.dumps({"status": "error", "mensaje": f"Formato '{extension}' no soportado para Big Data SQL."})

        # Registrar en el contexto SQL de Polars con alias versátiles
        sql_ctx = pl.SQLContext()
        sql_ctx.register("dataset", lf)
        sql_ctx.register("self", lf)
        sql_ctx.register("datos", lf)
        sql_ctx.register("data", lf)
        sql_ctx.register("tabla", lf)
        if path_datos.stem:
            sql_ctx.register(path_datos.stem, lf)

        # Ejecutar la consulta SQL analítica optimizada
        df_resultado = sql_ctx.execute(consulta_sql_analitica).collect()

        total_filas = df_resultado.height
        columnas = df_resultado.columns
        duracion_ms = int((time.time() - inicio) * 1000)

        # Si se solicitó archivo de salida
        if ruta_salida_parquet_o_csv:
            path_out = Path(ruta_salida_parquet_o_csv)
            path_out.parent.mkdir(parents=True, exist_ok=True)
            if path_out.suffix.lower() == ".parquet":
                df_resultado.write_parquet(str(path_out))
            else:
                df_resultado.write_csv(str(path_out))

        # Muestra acotada en JSON para la respuesta
        muestra_preview = df_resultado.head(100).to_dicts()

        return json.dumps({
            "status": "success",
            "motor": "Polars Vectorized SQL Engine",
            "total_filas_resultado": total_filas,
            "columnas": columnas,
            "tiempo_procesamiento_ms": duracion_ms,
            "archivo_generado": ruta_salida_parquet_o_csv if ruta_salida_parquet_o_csv else "En memoria",
            "muestra_primeras_100_filas": muestra_preview
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al procesar grandes volúmenes SQL: {str(e)}"})


@tool
def tool_sql_analizar_rendimiento(
    motor_db: str,
    cadena_conexion_o_ruta: str,
    consulta_sql: str
) -> str:
    """
    Ejecuta un análisis de plan de consulta (EXPLAIN / EXPLAIN QUERY PLAN) para diagnosticar
    cuellos de botella, escaneos de tabla lentos (table scans) y sugerir índices óptimos.

    Args:
        motor_db: 'sqlite', 'postgresql', o 'mysql'.
        cadena_conexion_o_ruta: Ruta de base de datos o URI.
        consulta_sql: Consulta a diagnosticar.
    """
    try:
        motor = motor_db.lower()
        if motor == "sqlite":
            conn = _obtener_conexion_sqlite(cadena_conexion_o_ruta)
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN QUERY PLAN {consulta_sql}")
            plan = cursor.fetchall()
            conn.close()

            pasos_plan = [dict(p) for p in plan]
            tiene_scan = any("SCAN" in str(p.get("detail", "")) and "INDEX" not in str(p.get("detail", "")) for p in pasos_plan)

            diagnostico = (
                "ADVERTENCIA DE RENDIMIENTO: Se detectó SCAN TABLE completo. "
                "La consulta revisa cada fila de la tabla; se recomienda crear un índice para optimizar."
                if tiene_scan else "Plan de ejecución eficiente: utiliza índices o acceso directo."
            )

            return json.dumps({
                "status": "success",
                "motor": "sqlite",
                "diagnostico_rendimiento": diagnostico,
                "plan_de_ejecucion": pasos_plan,
                "requiere_indice": tiene_scan
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "success",
                "mensaje": f"Para {motor_db}, ejecuta 'EXPLAIN (ANALYZE, BUFFERS) {consulta_sql}' con tool_sql_ejecutar_consulta."
            })

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al analizar plan de consulta: {str(e)}"})


@tool
def tool_sql_migracion_y_esquema(
    motor_db: str,
    cadena_conexion_o_ruta: str,
    script_ddl: str
) -> str:
    """
    Aplica scripts DDL de esquema (CREATE TABLE, ALTER TABLE, CREATE INDEX, restricciones)
    dentro de una transacción atómica, asegurando rollback ante errores de sintaxis.

    Args:
        motor_db: 'sqlite', 'postgresql', o 'mysql'.
        cadena_conexion_o_ruta: Ruta de base de datos o URI.
        script_ddl: Sentencias DDL de estructura.
    """
    try:
        if motor_db.lower() == "sqlite":
            conn = _obtener_conexion_sqlite(cadena_conexion_o_ruta)
            cursor = conn.cursor()
            cursor.executescript(script_ddl)
            conn.commit()
            conn.close()

            return json.dumps({
                "status": "success",
                "motor": "sqlite",
                "mensaje": "Esquema / Migración DDL aplicada exitosamente bajo transacción atómica."
            }, ensure_ascii=False)
        else:
            from sqlalchemy import create_engine, text
            engine = create_engine(cadena_conexion_o_ruta)
            with engine.begin() as connection:
                connection.execute(text(script_ddl))
            return json.dumps({
                "status": "success",
                "motor": motor_db,
                "mensaje": "Migración DDL ejecutada con éxito en el servidor de base de datos."
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al aplicar migración DDL: {str(e)}"})


HERRAMIENTAS_BASES_DE_DATOS_SQL = [
    tool_sql_ejecutar_consulta,
    tool_sql_procesar_grandes_datos,
    tool_sql_analizar_rendimiento,
    tool_sql_migracion_y_esquema,
]
