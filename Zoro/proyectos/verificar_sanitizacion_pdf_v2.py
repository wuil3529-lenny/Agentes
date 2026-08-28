"""
Script de verificación final de sanitización del skill_leer_pdf_sanji.py
Corregido: excluye docstrings de la búsqueda de rutas absolutas.
"""
import ast
import re
import sys

RUTA_ARCHIVO = "/app/Sanji/skills/skill_leer_pdf_sanji.py"

def main():
    with open(RUTA_ARCHIVO, "r", encoding="utf-8") as f:
        contenido = f.read()

    # 1. Compilar
    try:
        ast.parse(contenido)
        print("COMPILA_OK: Sintaxis válida")
    except SyntaxError as e:
        print(f"ERROR_SINTAXIS: {e}")
        sys.exit(1)

    # 2. Patrones inseguros en TODO el archivo
    patrones_inseguros = ["str(e)", "traceback", "exc_info", "format_exc"]
    encontrados = [p for p in patrones_inseguros if p in contenido]
    if encontrados:
        print(f"PATRONES_INSEGUROS_ENCONTRADOS: {encontrados}")
        sys.exit(1)
    print("PATRONES_INSEGUROS: NINGUNO")

    # 3. Constantes de mensajes genéricos
    constantes = ["_MSG_LIBRERIA_NO_DISPONIBLE", "_MSG_ARCHIVO_NO_ENCONTRADO",
                  "_MSG_EXTENSION_INVALIDA", "_MSG_ERROR_GENERICO"]
    for c in constantes:
        assert c in contenido, f"Falta constante {c}"
    print("CONSTANTES_GENERICAS: TODAS PRESENTES")

    # 4. Funciones tool
    funciones = ["tool_leer_pdf_texto", "tool_leer_pdf_pagina", "tool_leer_pdf_metadatos"]
    for f in funciones:
        assert f in contenido, f"Falta función {f}"
    print("FUNCIONES_TOOL: LAS 3 PRESENTES")

    # 5. Verificar que los mensajes de error NO contienen rutas absolutas.
    #    Buscar solo en las constantes de mensajes (no en docstrings).
    #    Extraer las constantes _MSG_* y verificar que no tengan rutas.
    for const in constantes:
        # Buscar el valor de la constante
        match = re.search(rf'{const}\s*=\s*\(?\s*["\'](.+?)["\']', contenido, re.DOTALL)
        if match:
            valor = match.group(1)
            # Buscar patrones de rutas en el valor
            rutas = re.findall(r'/[A-Za-z0-9_\-/]+', valor)
            if rutas:
                print(f"RUTA_EN_CONSTANTE {const}: {rutas}")
                sys.exit(1)
    print("MENSAJES_ERROR_SIN_RUTAS: VERIFICADO")

    # 6. Verificar que los except usan mensajes genéricos (no str(e))
    #    Buscar todos los bloques except Exception
    arbol = ast.parse(contenido)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ExceptHandler):
            # Verificar que no haya llamadas a str() con la excepción
            for sub in ast.walk(nodo):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "str":
                    print(f"STR() ENCONTRADO EN EXCEPT: línea {sub.lineno}")
                    sys.exit(1)
    print("EXCEPT_SIN_STR(e): VERIFICADO")

    print("\n=== VERIFICACION FINAL: TODAS LAS COMPROBACIONES PASARON ===")
    print("exit_code: 0")
    sys.exit(0)

if __name__ == "__main__":
    main()
