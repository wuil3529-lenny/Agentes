import os
from langchain_core.tools import tool

@tool
def tool_leer_archivo(ruta: str) -> str:
    """
    Lee y devuelve el contenido completo de un archivo de código fuente.
    Útil para inspeccionar el código donde ocurrió una excepción.
    """
    try:
        if not os.path.exists(ruta):
            return f"Error: El archivo {ruta} no existe."
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        # Agregar números de línea para facilitar el parcheo
        lineas = contenido.split('\n')
        contenido_numerado = '\n'.join([f"{i+1}: {linea}" for i, linea in enumerate(lineas)])
        return f"--- Contenido de {ruta} ---\n{contenido_numerado}\n--- Fin de archivo ---"
    except Exception as e:
        return f"Error al leer el archivo {ruta}: {e}"

@tool
def tool_parchear_archivo(ruta: str, buscar: str, reemplazar: str) -> str:
    """
    Reemplaza un bloque EXACTO de código en un archivo por otro bloque (hot-patching).
    El texto en 'buscar' debe coincidir caracter por caracter (incluyendo indentación) con el contenido original.
    Devuelve un mensaje de éxito o el error si no se encuentra el bloque.
    """
    try:
        if not os.path.exists(ruta):
            return f"Error: El archivo {ruta} no existe."
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
            
        if buscar not in contenido:
            return "Error de Parcheo: El bloque de texto especificado en 'buscar' no se encuentra exactamente en el archivo. Asegúrate de respetar los espacios y saltos de línea."
            
        nuevo_contenido = contenido.replace(buscar, reemplazar)
        
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(nuevo_contenido)
            
        return f"¡Hot-Patch exitoso en {ruta}!"
    except Exception as e:
        return f"Error al aplicar el parche en {ruta}: {e}"

HERRAMIENTAS_CURADOR = [
    tool_leer_archivo,
    tool_parchear_archivo
]
