import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Añadir la raíz de Agentes al path para poder importar luffy_agent
_APP_ROOT = Path(__file__).resolve().parents[3]
_LUFFY_DIR = str(_APP_ROOT / "Luffy")
if _LUFFY_DIR not in sys.path:
    sys.path.insert(0, _LUFFY_DIR)

from luffy_agent import crear_llm
from langchain_core.messages import SystemMessage, HumanMessage

def limpiar_bloques_markdown(texto: str) -> str:
    """Elimina las etiquetas de bloque de código markdown si el LLM las incluyó."""
    if texto.startswith("```"):
        lineas = texto.split("\n")
        if len(lineas) > 1 and lineas[0].startswith("```"):
            lineas = lineas[1:]
        if len(lineas) > 0 and lineas[-1].strip().startswith("```"):
            lineas = lineas[:-1]
        return "\n".join(lineas)
    return texto

def validar_y_corregir_codigo(codigo_html: str, llm) -> dict:
    """
    Revisa el código generado. Si encuentra problemas estructurales obvios, le pide al LLM que se auto-corrija.
    Retorna el código final.
    """
    print("[Stitch Validator] Ejecutando validación de código...")
    
    # Validaciones heurísticas básicas
    errores = []
    if "<html" not in codigo_html.lower():
        errores.append("No se encontró la etiqueta <html>.")
    if "<body" not in codigo_html.lower():
        errores.append("No se encontró la etiqueta <body>.")
    if "class=" not in codigo_html:
        errores.append("No se detectaron clases (Tailwind) en el código.")
        
    if not errores:
        return {"status": "success", "codigo": codigo_html, "corregido": False}
        
    print(f"[Stitch Validator] Errores detectados: {errores}. Solicitando auto-corrección...")
    
    prompt_correccion = f"""
Eres un validador experto de Frontend (HTML y Tailwind).
El siguiente código generado tiene los siguientes problemas detectados por el parser:
{', '.join(errores)}

CÓDIGO ACTUAL:
{codigo_html}

Tu tarea es CORREGIR el código. Devuelve ÚNICAMENTE el código HTML/Tailwind corregido y completo, sin explicaciones, sin bloques markdown de código (```html).
"""
    try:
        respuesta = llm.invoke([HumanMessage(content=prompt_correccion)])
        codigo_corregido = limpiar_bloques_markdown(respuesta.content.strip())
        return {"status": "success", "codigo": codigo_corregido, "corregido": True}
    except Exception as e:
        return {"status": "error", "mensaje": f"Fallo en la auto-corrección: {e}", "codigo": codigo_html}

def generar_codigo_ui(prompt_diseno: str) -> str:
    """
    Simula el entorno 'Stitch'. Toma el prompt maestro de diseño de Nami
    y utiliza el LLM (Deepseek) configurado como experto Frontend para generar el HTML/Tailwind.
    Luego valida y corrige el código antes de guardarlo.
    """
    print(f"\n[Stitch Bridge] Iniciando generación de UI a partir del diseño de Nami...")
    
    llm = crear_llm(temperatura=0.2, agente="NAMI")
    
    prompt_sistema = """
Eres "Stitch", un generador automatizado de código Frontend altamente capacitado.
Tu único propósito es tomar especificaciones de diseño (Wireframes, UX/UI, Componentes)
y convertirlas en código de producción funcional utilizando HTML semántico y Tailwind CSS.

REGLAS ESTRICTAS:
1. Solo utiliza Tailwind CSS para los estilos. No uses CSS personalizado a menos que sea absolutamente indispensable.
2. Todo el código debe estar en un solo archivo HTML (embebiendo configuraciones de Tailwind o usando el CDN oficial).
3. Asegúrate de que el diseño sea completamente responsivo.
4. Devuelve ÚNICAMENTE el código. No escribas texto explicativo, ni saludos.
5. NO envuelvas tu respuesta en bloques markdown (```html). Comienza directamente con <!DOCTYPE html>.
"""

    prompt_usuario = f"""
Aquí tienes el Prompt Maestro de Diseño generado por Nami:

{prompt_diseno}

Genera el código HTML/Tailwind ahora.
"""

    try:
        # Generación inicial
        print(f"[Stitch Bridge] Solicitando generación al LLM (Stitch)...")
        respuesta = llm.invoke([
            SystemMessage(content=prompt_sistema),
            HumanMessage(content=prompt_usuario)
        ])
        
        codigo_inicial = limpiar_bloques_markdown(respuesta.content.strip())
        
        # Validación y Corrección
        resultado_validacion = validar_y_corregir_codigo(codigo_inicial, llm)
        if resultado_validacion["status"] == "error":
            codigo_final = resultado_validacion["codigo"] # Guardamos lo que tengamos
            print(f"[Stitch Bridge] Advertencia: Error en validación ({resultado_validacion['mensaje']})")
        else:
            codigo_final = resultado_validacion["codigo"]
            if resultado_validacion["corregido"]:
                print(f"[Stitch Bridge] El código fue auto-corregido por el validador.")
            else:
                print(f"[Stitch Bridge] El código pasó la validación inicial sin problemas.")

        # Guardar en disco en la carpeta de informes de Nami
        directorio_informes = _APP_ROOT / "Nami" / "informes"
        directorio_informes.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"prototipo_ui_{timestamp}.html"
        ruta_archivo = directorio_informes / nombre_archivo
        
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(codigo_final)
            
        print(f"[Stitch Bridge] Prototipo guardado exitosamente en: {ruta_archivo}")
        
        payload = {
            "status": "success",
            "mensaje": "Prototipo HTML/Tailwind generado y validado con éxito.",
            "ruta_archivo": str(ruta_archivo),
            "codigo_snippet": codigo_final[:200] + "..." # Mostrar solo el inicio en el log
        }
        return json.dumps(payload, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error en la generación automatizada de Stitch: {e}"
        print(f"[Stitch Bridge] ❌ {error_msg}")
        return json.dumps({"status": "error", "mensaje": error_msg}, ensure_ascii=False)

if __name__ == "__main__":
    # Test manual
    test_prompt = "Genera una tarjeta de perfil de usuario oscura con neón azul."
    res = generar_codigo_ui(test_prompt)
    print("Resultado Test:", res)
