import os
import sys
import json
import time
import urllib.request
import subprocess

BRIDGE_URL = "http://127.0.0.1:8000"

def limpiar():
    os.system('cls' if os.name == 'nt' else 'clear')

def peticion(endpoint, data=None):
    try:
        url = f"{BRIDGE_URL}{endpoint}"
        payload = json.dumps(data or {}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=35) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def verificar_estado():
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}/api/manos_ojos/estado")
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except Exception:
        return False

def menu():
    while True:
        limpiar()
        estado_bridge = "[ACTIVO]" if verificar_estado() else "[DESCONECTADO - Verificando...]"
        
        print("=" * 75)
        print("  🏴‍☠️ CONSOLA DE PRUEBAS INTERACTIVA — FLOTA DE AGENTES (MANOS Y OJOS)")
        print("=" * 75)
        print(f"  • Estado del Puente Host (8000): {estado_bridge}")
        print("  • Pantalla de ejecución: WinSta0\\Default (Monitor Físico del Usuario)")
        print("=" * 75)
        print("  [1] ✋ MANOS: Abrir YouTube en Microsoft Edge visible")
        print("  [2] ✋ MANOS: Navegar a una URL personalizada")
        print("  [3] 👁️ OJOS: Capturar pantalla completa y analizar con Llama 3.2 Vision (NVIDIA NIM)")
        print("  [4] ✋ MANOS: Hacer clic en botón, texto o selector web")
        print("  [5] ✋ MANOS: Rellenar campos en formulario web")
        print("  [6] ✋ MANOS: Abrir aplicación del sistema (Notepad, Calc, etc.)")
        print("  [7] 🌐 ABRIR Dashboard Web en el navegador (http://localhost:8000)")
        print("  [8] 💻 Consola libre de PowerShell")
        print("  [0] Salir")
        print("=" * 75)
        
        opc = input("\n👉 Ingresa una opción (0-8): ").strip()
        
        if opc == "1":
            print("\n⏳ Abriendo YouTube en pantalla interactiva...")
            res = peticion("/api/manos_ojos/web/navegar", {"url": "https://www.youtube.com", "visible": True})
            print("\n[Resultado]:", json.dumps(res, indent=2, ensure_ascii=False))
            input("\nPresiona Enter para continuar...")
            
        elif opc == "2":
            url = input("\nIngresa la URL a visitar (ej: https://www.wikipedia.org): ").strip()
            if url:
                print(f"\n⏳ Navegando a {url}...")
                res = peticion("/api/manos_ojos/web/navegar", {"url": url, "visible": True})
                print("\n[Resultado]:", json.dumps(res, indent=2, ensure_ascii=False))
            input("\nPresiona Enter para continuar...")
            
        elif opc == "3":
            pregunta = input("\nPregunta o instrucción para los ojos IA (Enter para predeterminada): ").strip()
            if not pregunta:
                pregunta = "¿Qué ventanas, aplicaciones, botones o elementos se ven en la pantalla?"
            print("\n⏳ Capturando pantalla y enviando a NVIDIA NIM Vision...")
            res = peticion("/api/manos_ojos/pc/analizar", {"instruccion": pregunta})
            print("\n" + "=" * 50)
            print("👁️ ANÁLISIS VISUAL DE LA PANTALLA:")
            print("=" * 50)
            if res.get("status") == "success":
                print(res.get("analisis_visual", "Sin respuesta"))
                print("\nCaptura guardada en:", res.get("imagen_analizada"))
            else:
                print("Error:", res.get("mensaje"))
            print("=" * 50)
            input("\nPresiona Enter para continuar...")
            
        elif opc == "4":
            elem = input("\nIngresa el texto visible o selector del botón/enlace a presionar: ").strip()
            if elem:
                print(f"\n⏳ Haciendo clic en '{elem}'...")
                res = peticion("/api/manos_ojos/web/clic", {"selector_o_texto": elem})
                print("\n[Resultado]:", json.dumps(res, indent=2, ensure_ascii=False))
            input("\nPresiona Enter para continuar...")
            
        elif opc == "5":
            selector = input("\nNombre o selector del campo (ej: 'Buscar' o '#search'): ").strip()
            val = input("Texto a escribir: ").strip()
            if selector and val:
                print("\n⏳ Rellenando campo...")
                res = peticion("/api/manos_ojos/web/rellenar", {"campos": {selector: val}})
                print("\n[Resultado]:", json.dumps(res, indent=2, ensure_ascii=False))
            input("\nPresiona Enter para continuar...")
            
        elif opc == "6":
            app = input("\nNombre del ejecutable a abrir (ej: notepad.exe, calc.exe): ").strip()
            if app:
                print(f"\n⏳ Abriendo {app} en pantalla...")
                res = peticion("/api/manos_ojos/pc/app", {"comando": app})
                print("\n[Resultado]:", json.dumps(res, indent=2, ensure_ascii=False))
            input("\nPresiona Enter para continuar...")
            
        elif opc == "7":
            print("\n⏳ Abriendo Dashboard en tu navegador...")
            # SEC-H04: apertura del navegador sin subproceso ni shell intermedio
            import webbrowser
            webbrowser.open("http://localhost:8000")
            time.sleep(1)
            
        elif opc == "8":
            print("\nAbriendo PowerShell interactivo... Escribe 'exit' para volver al menú.\n")
            os.system("powershell")
            
        elif opc == "0":
            print("\n👋 Cerrando consola de pruebas.")
            break
        else:
            print("\n❌ Opción inválida.")
            time.sleep(1)

if __name__ == "__main__":
    menu()
