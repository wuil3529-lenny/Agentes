"""
Script de prueba para la validación de ruta permitida (Hallazgo PDF-03)
en skill_leer_pdf_sanji.py de Sanji.

Prueba que _validar_ruta_permitida() rechaza rutas fuera de los directorios
permitidos (path traversal) y acepta rutas dentro de los directorios permitidos.
"""
import sys
import os

# Agregar la ruta del skill al path
sys.path.insert(0, "/app/Sanji/skills")

from pathlib import Path
from skill_leer_pdf_sanji import (
    _validar_ruta_permitida,
    _DIRECTORIOS_PERMITIDOS,
    _MSG_RUTA_NO_PERMITIDA,
)

PASS = 0
FAIL = 0

def check(nombre, condicion, detalle=""):
    global PASS, FAIL
    if condicion:
        PASS += 1
        print(f"  [PASS] {nombre}")
    else:
        FAIL += 1
        print(f"  [FAIL] {nombre} {detalle}")

print("=" * 60)
print("PRUEBAS DE VALIDACIÓN DE RUTA PERMITIDA (PDF-03)")
print("=" * 60)

# --- Prueba 1: Directorios permitidos configurados ---
print("\n[1] Directorios permitidos configurados")
check("Hay al menos 1 directorio permitido", len(_DIRECTORIOS_PERMITIDOS) >= 1)
check("Los directorios están resueltos (absolutos)", all(p.is_absolute() for p in _DIRECTORIOS_PERMITIDOS))
for p in _DIRECTORIOS_PERMITIDOS:
    print(f"      -> {p}")

# --- Prueba 2: Ruta dentro de directorio permitido ---
print("\n[2] Ruta dentro de directorio permitido")
ruta_valida = _DIRECTORIOS_PERMITIDOS[0] / "documento.pdf"
try:
    _validar_ruta_permitida(ruta_valida)
    check("Ruta en /app/Sanji/data aceptada", True)
except PermissionError as e:
    check("Ruta en /app/Sanji/data aceptada", False, f"-> {e}")

# --- Prueba 3: Ruta fuera de directorio permitido ---
print("\n[3] Ruta fuera de directorio permitido")
ruta_invalida = Path("/etc/passwd")
try:
    _validar_ruta_permitida(ruta_invalida)
    check("Ruta /etc/passwd rechazada", False, "-> fue aceptada (VULNERABLE)")
except PermissionError as e:
    check("Ruta /etc/passwd rechazada", True)
    check("Mensaje de error correcto", str(e) == _MSG_RUTA_NO_PERMITIDA, f"-> {e}")

# --- Prueba 4: Path traversal con '..' ---
print("\n[4] Path traversal con '..'")
ruta_traversal = Path("/app/Sanji/data/../../../../etc/passwd")
try:
    _validar_ruta_permitida(ruta_traversal)
    check("Path traversal rechazado", False, "-> fue aceptada (VULNERABLE)")
except PermissionError as e:
    check("Path traversal rechazado", True)

# --- Prueba 5: Ruta en otro directorio del sistema ---
print("\n[5] Ruta en otro directorio del sistema")
ruta_otro = Path("/app/Zoro/proyectos/archivo.pdf")
try:
    _validar_ruta_permitida(ruta_otro)
    check("Ruta en /app/Zoro rechazada", False, "-> fue aceptada (VULNERABLE)")
except PermissionError as e:
    check("Ruta en /app/Zoro rechazada", True)

# --- Prueba 6: Ruta en directorio permitido con subdirectorio ---
print("\n[6] Ruta en subdirectorio de directorio permitido")
ruta_sub = _DIRECTORIOS_PERMITIDOS[0] / "subdir" / "archivo.pdf"
try:
    _validar_ruta_permitida(ruta_sub)
    check("Ruta en subdirectorio permitido aceptada", True)
except PermissionError as e:
    check("Ruta en subdirectorio permitido aceptada", False, f"-> {e}")

# --- Prueba 7: Ruta con symlink que escapa del directorio permitido ---
print("\n[7] Ruta con symlink que escapa del directorio permitido")
try:
    # Crear un symlink temporal que apunte fuera del directorio permitido
    link_path = _DIRECTORIOS_PERMITIDOS[0] / "link_escapado.pdf"
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    os.symlink("/etc/passwd", str(link_path))
    try:
        _validar_ruta_permitida(link_path)
        check("Symlink que escapa rechazado", False, "-> fue aceptada (VULNERABLE)")
    except PermissionError:
        check("Symlink que escapa rechazado", True)
    finally:
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
except (OSError, NotImplementedError) as e:
    print(f"      [SKIP] No se pudo crear symlink: {e}")

print("\n" + "=" * 60)
print(f"RESULTADO: {PASS} PASS / {FAIL} FAIL")
print("=" * 60)

if FAIL > 0:
    sys.exit(1)
sys.exit(0)
