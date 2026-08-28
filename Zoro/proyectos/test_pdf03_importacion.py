"""
Verificación de importación y funcionalidad básica de skill_leer_pdf_sanji.py
tras agregar la validación de ruta permitida (Hallazgo PDF-03).
"""
import sys
sys.path.insert(0, "/app/Sanji/skills")

# Importar el módulo completo para verificar que no hay errores de sintaxis
import skill_leer_pdf_sanji as skill

# Verificar que las funciones públicas existen
assert hasattr(skill, "tool_leer_pdf_texto"), "tool_leer_pdf_texto no existe"
assert hasattr(skill, "tool_leer_pdf_pagina"), "tool_leer_pdf_pagina no existe"
assert hasattr(skill, "tool_leer_pdf_metadatos"), "tool_leer_pdf_metadatos no existe"

# Verificar que la función de validación existe
assert hasattr(skill, "_validar_ruta_permitida"), "_validar_ruta_permitida no existe"
assert hasattr(skill, "_DIRECTORIOS_PERMITIDOS"), "_DIRECTORIOS_PERMITIDOS no existe"

# Verificar que _obtener_reader llama a la validación
import inspect
source = inspect.getsource(skill._obtener_reader)
assert "_validar_ruta_permitida" in source, "_obtener_reader no llama a _validar_ruta_permitida"

print("IMPORTACION OK: módulo importado correctamente")
print(f"  - tool_leer_pdf_texto: {skill.tool_leer_pdf_texto.name}")
print(f"  - tool_leer_pdf_pagina: {skill.tool_leer_pdf_pagina.name}")
print(f"  - tool_leer_pdf_metadatos: {skill.tool_leer_pdf_metadatos.name}")
print(f"  - Directorios permitidos: {len(skill._DIRECTORIOS_PERMITIDOS)}")
print("  - _obtener_reader() incluye llamada a _validar_ruta_permitida: OK")
print("EXIT CODE 0 - TODO OK")
