#!/usr/bin/env python3
"""
prueba_rapida.py
================
Script de prueba rápida para validar el entorno de desarrollo.
Cumple con el ticket TKT-TEST-ZORO: crear un archivo de prueba básico.

Autor: Zoro (Primer Oficial)
Fecha: 2025
"""

import sys
import platform
import datetime


def verificar_entorno() -> dict:
    """Verifica el entorno de ejecución de Python."""
    return {
        "version_python": sys.version.split()[0],
        "plataforma": platform.system(),
        "arquitectura": platform.machine(),
        "fecha_hora": datetime.datetime.now().isoformat(),
    }


def suma(a: int, b: int) -> int:
    """Función de prueba: suma dos números."""
    return a + b


def main() -> int:
    """Punto de entrada principal."""
    print("=" * 60)
    print("PRUEBA RÁPIDA - TKT-TEST-ZORO")
    print("=" * 60)

    # 1. Verificar entorno
    env = verificar_entorno()
    print("\n[1] Entorno de ejecución:")
    for clave, valor in env.items():
        print(f"    {clave}: {valor}")

    # 2. Probar función suma
    resultado = suma(3, 4)
    print(f"\n[2] Prueba de función suma(3, 4) = {resultado}")
    assert resultado == 7, "La suma falló"

    # 3. Probar operaciones básicas
    lista = [i**2 for i in range(5)]
    print(f"[3] Lista de cuadrados: {lista}")
    assert len(lista) == 5, "La lista no tiene 5 elementos"

    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())


