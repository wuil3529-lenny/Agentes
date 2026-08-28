"""
Script de verificación de sanitización del skill_leer_pdf_sanji.py
Verifica que no queden patrones inseguros y que el archivo compile.
"""
import ast
import sys

RUTA_ARCHIVO = "/app/Sanji/skills/skill_leer_pdf_sanji.py"

def main():
    # 1. Verificar que el archivo existe
    try:
        with open(RUTA_ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo {RUTA_ARCHIVO}")
        sys.exit(1)

    # 2. Verificar que compila (sintaxis válida)
    try:
        ast.parse(contenido)
        print("COMPILA_OK: Sintaxis válida")
    except SyntaxError as e:
        print(f"ERROR_SINTAXIS: {e}")
        sys.exit(1)

    # 3. Verificar patrones inseguros
    patrones_inseguros = [
        "str(e)",
        "traceback",
        "exc_info",
        "format_exc",
        "sys.exc_info",
        "traceback.format",
        "traceback.print",
    ]
    encontrados = []
    for patron in patrones_inseguros:
        if patron in contenido:
            encontrados.append(patron)

    if encontrados:
        print(f"PATRONES_INSEGUROS_ENCONTRADOS: {encontrados}")
        sys.exit(1)
    else:
        print("PATRONES_INSEGUROS: NINGUNO")

    # 4. Verificar que los mensajes genéricos están presentes
    mensajes_esperados = [
        "_MSG_LIBRERIA_NO_DISPONIBLE",
        "_MSG_ARCHIVO_NO_ENCONTRADO",
        "_MSG_EXTENSION_INVALIDA",
        "_MSG_ERROR_GENERICO",
    ]
    for msg in mensajes_esperados:
        if msg in contenido:
            print(f"CONSTANTE_OK: {msg}")
        else:
            print(f"CONSTANTE_FALTANTE: {msg}")
            sys.exit(1)

    # 5. Verificar que las 3 funciones tool existen
    funciones_esperadas = [
        "tool_leer_pdf_texto",
        "tool_leer_pdf_pagina",
        "tool_leer_pdf_metadatos",
    ]
    for fn in funciones_esperadas:
        if fn in contenido:
            print(f"FUNCION_OK: {fn}")
        else:
            print(f"FUNCION_FALTANTE: {fn}")
            sys.exit(1)

    # 6. Verificar que no hay rutas absolutas expuestas en mensajes de error
    #    (buscar patrones de rutas en strings de error)
    import re
    rutas_absolutas = re.findall(r'/[A-Za-z0-9_\-/]+\.pdf', contenido)
    if rutas_absolutas:
        print(f"RUTAS_ABSOLUTAS_EN_MENSAJES: {rutas_absolutas}")
        sys.exit(1)
    else:
        print("RUTAS_ABSOLUTAS_EN_MENSAJES: NINGUNA")

    print("\n=== VERIFICACION COMPLETA: TODAS LAS COMPROBACIONES PASARON ===")
    print(f"exit_code: 0")
    sys.exit(0)

if __name__ == "__main__":
    main()
