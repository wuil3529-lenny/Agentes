"""
Script de verificación: Validación de tamaño máximo de PDF (50MB) en skill_leer_pdf_sanji.py
Ticket: TKT-ZORO-SEC-002
Hallazgo: PDF-02 del reporte_001.md
"""
import sys
import os
import tempfile
from pathlib import Path

# Agregar el directorio de skills al path
SKILLS_DIR = Path("/app/Sanji/skills")
sys.path.insert(0, str(SKILLS_DIR))

# Importar el módulo
import skill_leer_pdf_sanji as skill

def verificar_constantes():
    """Verifica que las constantes de tamaño máximo existan y sean correctas."""
    print("=== 1. Verificación de constantes ===")
    
    assert hasattr(skill, '_TAMANO_MAXIMO_PDF_BYTES'), "FALTA constante _TAMANO_MAXIMO_PDF_BYTES"
    tamano = skill._TAMANO_MAXIMO_PDF_BYTES
    esperado = 50 * 1024 * 1024
    assert tamano == esperado, f"Tamaño incorrecto: {tamano} != {esperado}"
    print(f"  [OK] _TAMANO_MAXIMO_PDF_BYTES = {tamano} bytes ({tamano / (1024*1024):.0f} MB)")
    
    assert hasattr(skill, '_MSG_ARCHIVO_DEMASIADO_GRANDE'), "FALTA mensaje _MSG_ARCHIVO_DEMASIADO_GRANDE"
    print(f"  [OK] Mensaje de error definido: '{skill._MSG_ARCHIVO_DEMASIADO_GRANDE[:60]}...'")
    return True

def verificar_funcion_obtener_reader():
    """Verifica que _obtener_reader() tenga la validación de tamaño."""
    print("\n=== 2. Verificación de _obtener_reader() ===")
    
    import inspect
    fuente = inspect.getsource(skill._obtener_reader)
    
    # Verificar que use stat().st_size
    assert 'stat()' in fuente and 'st_size' in fuente, "No usa ruta.stat().st_size"
    print("  [OK] Usa ruta.stat().st_size para obtener el tamaño")
    
    # Verificar que compare contra _TAMANO_MAXIMO_PDF_BYTES
    assert '_TAMANO_MAXIMO_PDF_BYTES' in fuente, "No compara contra _TAMANO_MAXIMO_PDF_BYTES"
    print("  [OK] Compara contra _TAMANO_MAXIMO_PDF_BYTES")
    
    # Verificar que lance ValueError
    assert 'ValueError' in fuente, "No lanza ValueError"
    print("  [OK] Lanza ValueError cuando excede el límite")
    
    # Verificar que la validación ocurra ANTES de crear el PdfReader
    pos_validacion = fuente.find('tamano_bytes')
    pos_reader = fuente.find('PdfReader(')
    assert pos_validacion != -1 and pos_reader != -1, "No se encontraron las posiciones"
    assert pos_validacion < pos_reader, "La validación NO ocurre antes de crear el PdfReader"
    print("  [OK] La validación ocurre ANTES de crear el PdfReader")
    return True

def verificar_comportamiento_archivo_grande():
    """Crea un archivo PDF falso de más de 50MB y verifica que se rechace."""
    print("\n=== 3. Verificación de comportamiento con archivo grande ===")
    
    # Crear un archivo temporal con extensión .pdf de más de 50MB
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        # Escribir 51MB de datos
        f.write(b'\x00' * (51 * 1024 * 1024))
        ruta_temp = f.name
    
    try:
        # Llamar a _obtener_reader directamente
        try:
            skill._obtener_reader(ruta_temp)
            print("  [FALLO] No se lanzó excepción para archivo > 50MB")
            return False
        except ValueError as e:
            assert skill._MSG_ARCHIVO_DEMASIADO_GRANDE in str(e), f"Mensaje incorrecto: {e}"
            print(f"  [OK] Se lanzó ValueError con mensaje correcto: '{str(e)[:60]}...'")
        except Exception as e:
            print(f"  [FALLO] Excepción inesperada: {type(e).__name__}: {e}")
            return False
        return True
    finally:
        os.unlink(ruta_temp)

def verificar_comportamiento_archivo_pequeno():
    """Verifica que un archivo pequeño pase la validación de tamaño."""
    print("\n=== 4. Verificación con archivo pequeño (no debe fallar por tamaño) ===")
    
    # Crear un archivo temporal pequeño con extensión .pdf
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.4\n% test small file\n')
        ruta_temp = f.name
    
    try:
        # Llamar a _obtener_reader - debería pasar la validación de tamaño
        # y fallar en PdfReader (porque no es un PDF válido), pero NO por tamaño
        try:
            skill._obtener_reader(ruta_temp)
            print("  [INFO] El archivo pasó la validación de tamaño (esperado)")
        except ValueError as e:
            if skill._MSG_ARCHIVO_DEMASIADO_GRANDE in str(e):
                print("  [FALLO] Archivo pequeño rechazado por tamaño")
                return False
            else:
                print(f"  [OK] Pasó validación de tamaño. Error posterior: {str(e)[:50]}...")
        except Exception as e:
            print(f"  [OK] Pasó validación de tamaño. Error posterior (esperado): {type(e).__name__}")
        return True
    finally:
        os.unlink(ruta_temp)

def main():
    print("=" * 60)
    print("VERIFICACIÓN: Validación de tamaño PDF (50MB) - TKT-ZORO-SEC-002")
    print("=" * 60)
    
    resultados = []
    resultados.append(("constantes", verificar_constantes()))
    resultados.append(("funcion_reader", verificar_funcion_obtener_reader()))
    resultados.append(("archivo_grande", verificar_comportamiento_archivo_grande()))
    resultados.append(("archivo_pequeno", verificar_comportamiento_archivo_pequeno()))
    
    print("\n" + "=" * 60)
    print("RESULTADOS FINALES")
    print("=" * 60)
    todos_ok = True
    for nombre, ok in resultados:
        estado = "PASS" if ok else "FAIL"
        print(f"  [{estado}] {nombre}")
        if not ok:
            todos_ok = False
    
    if todos_ok:
        print("\n[RESULTADO] TODAS LAS VERIFICACIONES PASARON CORRECTAMENTE")
        print("La validación de tamaño máximo de PDF (50MB) está implementada y funcional.")
    else:
        print("\n[RESULTADO] HAY VERIFICACIONES FALLIDAS")
    
    return 0 if todos_ok else 1

if __name__ == "__main__":
    sys.exit(main())
