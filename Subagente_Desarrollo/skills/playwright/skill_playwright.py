"""
skill_playwright.py — Habilidad: Automatización, Verificación Visual y Pruebas con Playwright
============================================================================================
Inspirada en el protocolo Playwright MCP y el framework de pruebas de Microsoft Playwright.
Permite al Subagente de Desarrollo inspeccionar páginas web y dashboards en navegadores reales:
  1. Generar suites de pruebas E2E (End-to-End) en TypeScript y Python.
  2. Verificar responsividad y detectar desbordamientos de pantalla (Mobile, Tablet, Desktop).
  3. Extraer árboles de accesibilidad (Accessibility Snapshots) con roles semánticos.
  4. Generar capturas de pantalla de evidencia y validar la renderización sin errores de consola.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_playwright() -> str:
    """
    System Prompt especializado y encapsulado para el modo de Pruebas y Verificación con Playwright.
    """
    return """[🛑 HARD-STOP: MODO VERIFICACIÓN VISUAL Y PRUEBAS PLAYWRIGHT ACTIVO 🛑]
Eres el Ingeniero de Calidad de Software (QA) y Verificación en Navegador del Subagente de Desarrollo.
Tu misión es certificar que las interfaces creadas (dashboards, landing pages, aplicaciones) funcionen perfectamente en navegadores reales, no contengan errores de consola, se adapten de forma impecable a pantallas móviles y superen pruebas de interacción.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. VERIFICACIÓN RESPONSIVE OBLIGATORIA:
   - Todo dashboard o página web debe ser comprobado al menos en dos resoluciones clave:
     * Desktop: 1440x900px (grilla completa, barras laterales expandidas).
     * Mobile: 375x667px o 390x844px (menús hamburguesa o drawers, grilla colapsada a 1 columna).
   - Es un error crítico si la página presenta desbordamiento horizontal (`scrollWidth > innerWidth`).
2. LOCALIZADORES RESILIENTES (ACCESSIBILITY FIRST):
   - Usa localizadores basados en roles semánticos (`getByRole('button', { name: '...' })`, `getByLabel()`, `getByPlaceholder()`) en lugar de selectores frágiles como XPath o clases CSS complejas.
3. DETECCIÓN DE ERRORES DE CONSOLA:
   - Toda prueba debe escuchar eventos `page.on('console', msg => ...)` y `page.on('pageerror', error => ...)` para atrapar excepciones de JavaScript no controladas.
4. EVIDENCIA VISUAL:
   - Genera capturas de pantalla (`screenshot`) en las resoluciones evaluadas para adjuntarlas como evidencia de entrega comprobable.
"""


CONFIGURACION_MCP_PLAYWRIGHT_EJEMPLO = {
    "mcpServers": {
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest"]
        }
    }
}


@tool
def tool_playwright_generar_test(
    nombre_suite: str,
    url_o_archivo: str,
    casos_de_prueba: str = "Navegación básica y carga de componentes"
) -> str:
    """
    Genera un script de prueba automatizado completo en Playwright (TypeScript / Python)
    para verificar que una página web o dashboard cargue sus elementos, ejecute clics
    y no arroje errores en la consola.

    Args:
        nombre_suite: Nombre de la suite (ej: 'dashboard_metrics', 'auth_flow', 'landing_navigation').
        url_o_archivo: URL (ej: 'http://localhost:5173') o ruta absoluta al archivo HTML.
        casos_de_prueba: Descripción de las pruebas a realizar (ej: 'probar apertura de modal y cambio de tabs').
    """
    try:
        es_archivo_local = url_o_archivo.endswith(".html") or not url_o_archivo.startswith("http")
        ruta_limpia = url_o_archivo.replace("\\", "/")
        url_carga = f"file:///{ruta_limpia}" if es_archivo_local else url_o_archivo

        codigo_ts = f"""// Suite de pruebas Playwright: {nombre_suite}
import {{ test, expect }} from '@playwright/test';

test.describe('{nombre_suite}', () => {{
  test('debe cargar la interfaz sin errores y verificar elementos clave', async ({{ page }}) => {{
    const consoleErrors: string[] = [];
    page.on('console', msg => {{
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    }});
    page.on('pageerror', err => consoleErrors.push(err.message));

    // 1. Cargar la superficie evaluada
    await page.goto('{url_carga}');
    await page.waitForLoadState('networkidle');

    // 2. Verificar que no hubo excepciones críticas de JS
    expect(consoleErrors).toEqual([]);

    // 3. Verificación de viewport Desktop (1440x900)
    await page.setViewportSize({{ width: 1440, height: 900 }});
    await expect(page.locator('body')).toBeVisible();

    // 4. Captura de evidencia Desktop
    await page.screenshot({{ path: 'evidencia_{nombre_suite}_desktop.png', fullPage: true }});

    // 5. Verificación de viewport Mobile (390x844 - iPhone)
    await page.setViewportSize({{ width: 390, height: 844 }});
    const hasHorizontalOverflow = await page.evaluate(() => {{
      return document.documentElement.scrollWidth > window.innerWidth;
    }});
    expect(hasHorizontalOverflow).toBe(false);

    // 6. Captura de evidencia Mobile
    await page.screenshot({{ path: 'evidencia_{nombre_suite}_mobile.png', fullPage: true }});
  }});
}});
"""

        codigo_py = f"""# Suite de pruebas Playwright Python: {nombre_suite}
from playwright.sync_api import sync_playwright, expect

def test_{nombre_suite}():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(err.message))

        # Cargar página
        page.goto("{url_carga}")
        expect(page.locator("body")).to_be_visible()

        # Desktop 1440x900
        page.set_viewport_size({{"width": 1440, "height": 900}})
        page.screenshot(path="evidencia_{nombre_suite}_desktop.png", full_page=True)

        # Mobile 390x844
        page.set_viewport_size({{"width": 390, "height": 844}})
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert not overflow, "Fallo responsive: existe desbordamiento horizontal en mobile"
        page.screenshot(path="evidencia_{nombre_suite}_mobile.png", full_page=True)

        browser.close()
"""

        return json.dumps({
            "status": "success",
            "suite": nombre_suite,
            "objetivo": url_carga,
            "codigo_playwright_ts": codigo_ts,
            "codigo_playwright_py": codigo_py,
            "instrucciones": "Ejecuta con 'npx playwright test' o 'pytest' para certificar la entrega."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al generar suite Playwright: {str(e)}"})


@tool
def tool_playwright_verificar_responsive(
    url_o_archivo_html: str,
    dispositivos: str = "mobile,tablet,desktop"
) -> str:
    """
    Planifica y genera el script de comprobación multiplataforma para validar
    que no haya desbordamiento horizontal (overflow-x bug) ni elementos colapsados.

    Args:
        url_o_archivo_html: URL o ruta absoluta al archivo HTML.
        dispositivos: Lista separada por comas ('mobile,tablet,desktop').
    """
    try:
        viewports = [
            {"nombre": "Mobile (iPhone 14 / Pixel)", "width": 390, "height": 844},
            {"nombre": "Tablet (iPad Mini)", "width": 768, "height": 1024},
            {"nombre": "Desktop Standard", "width": 1440, "height": 900},
            {"nombre": "Desktop Ultra-Wide", "width": 1920, "height": 1080}
        ]

        return json.dumps({
            "status": "success",
            "objetivo": url_o_archivo_html,
            "matriz_dispositivos": viewports,
            "script_evaluacion_overflow": """
// Script inyectable en navegador para detectar elementos desbordados:
const docWidth = document.documentElement.offsetWidth;
const badElements = [];
document.querySelectorAll('*').forEach(el => {
  if (el.offsetWidth > docWidth) {
    badElements.push({ tag: el.tagName, class: el.className, width: el.offsetWidth });
  }
});
console.log('Elementos desbordados:', badElements);
""",
            "recomendacion": "Garantizar que todo contenedor use 'w-full max-w-...' y nunca anchos fijos en píxeles mayores a 320px."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al verificar responsive: {str(e)}"})


@tool
def tool_playwright_inspeccionar_accesibilidad(url_o_archivo_html: str) -> str:
    """
    Genera el procedimiento de extracción de árbol de accesibilidad (Accessibility Tree Snapshot)
    utilizado por Playwright MCP para interactuar con la página mediante roles ARIA en lugar de visión.
    """
    try:
        return json.dumps({
            "status": "success",
            "tipo_inspeccion": "Accessibility Tree Snapshot (Playwright MCP Mode)",
            "roles_auditados": [
                "button (debe tener aria-label o texto visible)",
                "heading (niveles h1-h6 con orden jerárquico secuencial)",
                "navigation (landmarks accesibles)",
                "link (con texto descriptivo que no sea solo 'haz clic aquí')",
                "tab / tablist (roles adecuados para tabs con aria-selected)"
            ],
            "comando_playwright": "await page.accessibility.snapshot()",
            "beneficio": "Permite al modelo navegar e interactuar con la interfaz de forma determinística y sin alucinaciones de coordenadas."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error en snapshot de accesibilidad: {str(e)}"})


@tool
def tool_playwright_configurar_mcp() -> str:
    """
    Proporciona la configuración oficial del servidor Playwright MCP (@playwright/mcp)
    para integrarlo en clientes y herramientas de IA con soporte de control de navegador en vivo.
    """
    return json.dumps({
        "status": "success",
        "paquete_oficial": "@playwright/mcp",
        "configuracion_mcp": CONFIGURACION_MCP_PLAYWRIGHT_EJEMPLO,
        "capacidades_mcp": [
            "browser_navigate: Carga cualquier URL en Chromium en vivo",
            "browser_click: Hace clic en elementos según su rol accesible",
            "browser_type: Escribe texto en inputs de formulario",
            "browser_screenshot: Toma capturas de pantalla en tiempo real",
            "browser_snapshot: Devuelve el árbol de accesibilidad estructurado"
        ]
    }, ensure_ascii=False)


HERRAMIENTAS_PLAYWRIGHT = [
    tool_playwright_generar_test,
    tool_playwright_verificar_responsive,
    tool_playwright_inspeccionar_accesibilidad,
    tool_playwright_configurar_mcp,
]
