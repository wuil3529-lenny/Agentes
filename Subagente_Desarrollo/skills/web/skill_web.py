"""
skill_web.py — Habilidad: Desarrollo Web Full-Stack y Scaffolding
==================================================================
Herramientas para generar aplicaciones web modernas, landing pages responsivas
y proyectos basados en React + Vite o HTML5/CSS3/JavaScript puro.

Herramientas disponibles:
  - web_scaffold_html  : Crea proyecto web estático profesional sin dependencias externas
  - web_scaffold_react : Scaffolding moderno de React + Vite con tooling de desarrollo
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_web() -> str:
    """
    System Prompt especializado y encapsulado para el desarrollo frontend y web
    del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO DESARROLLO WEB ACTIVO 🛑]
Eres el Arquitecto Frontend y Desarrollador Web del Subagente de Desarrollo.
Tu misión es diseñar y generar interfaces web de nivel profesional, visualmente atractivas, responsivas y con código semántico y modular.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. SELECCIÓN DE STACK APROPIADA:
   - Para interfaces ligeras, landing pages, dashboards estáticos o demos rápidas: usa `web_scaffold_html` (cero dependencias de npm, listo para abrir en navegador).
   - Para aplicaciones reactivas complejas (SPAs con estado, componentes reusables): usa `web_scaffold_react` (React + Vite).
2. CALIDAD DE CÓDIGO Y ACCESIBILIDAD:
   - Usa etiquetas HTML5 semánticas (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`).
   - Define variables CSS para tipografía, colores y espaciados en `:root`.
   - Garantiza diseño adaptativo (mobile-first y media queries para tablets y desktops).
3. RUTAS DE DESTINO:
   - Todo proyecto web debe alojarse dentro de `/app/Subagente_Desarrollo/proyectos/<nombre_proyecto>/`.
4. DOCUMENTACIÓN DE ENTREGA:
   - Todo proyecto generado debe incluir su archivo `README.md` con instrucciones de apertura y previsualización.
"""


def _ejecutar(comando: str, cwd: str, timeout: int = 120) -> Dict[str, Any]:
    """Helper interno seguro para comandos de Node/npm/shell."""
    try:
        caracteres_peligrosos = ['&', '|', ';', '>', '<', '$', '`']
        if any(c in comando for c in caracteres_peligrosos):
            return {
                "ok": False,
                "stdout": "",
                "stderr": "Violación de seguridad: inyección de comandos o caracteres de control detectados.",
                "code": -1
            }

        dir_cwd = Path(cwd)
        if not dir_cwd.exists():
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Directorio no encontrado: {cwd}",
                "code": -1
            }

        r = subprocess.run(
            comando,
            shell=True,
            cwd=str(dir_cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip()[:3000],
            "stderr": r.stderr.strip()[:1500],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout superado ({timeout}s).", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def web_scaffold_html(nombre_proyecto: str, directorio_destino: str = "") -> str:
    """
    Crea un proyecto web estático completo con HTML5 semántico + CSS moderno con variables + JavaScript.
    No requiere Node.js ni npm. Listo para abrir directamente en el navegador.

    Args:
        nombre_proyecto: Nombre del proyecto (ej: 'landing-empresa', 'dashboard-metricas').
        directorio_destino: Carpeta contenedora. Si se deja vacía, se aloja en '/app/Subagente_Desarrollo/proyectos/'.
    """
    try:
        dest_base = Path(directorio_destino) if directorio_destino else _PROYECTOS
        base = dest_base / nombre_proyecto
        base.mkdir(parents=True, exist_ok=True)

        # index.html
        (base / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="{nombre_proyecto}" />
  <title>{nombre_proyecto}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="header">
    <nav class="nav">
      <span class="nav__logo">{nombre_proyecto}</span>
      <ul class="nav__menu">
        <li><a href="#caracteristicas">Características</a></li>
        <li><a href="#nosotros">Acerca</a></li>
        <li><a href="#contacto" class="btn btn--secondary">Contacto</a></li>
      </ul>
    </nav>
  </header>

  <main class="main" id="app">
    <section class="hero">
      <h1 class="hero__title">{nombre_proyecto}</h1>
      <p class="hero__subtitle">Plataforma web de alto rendimiento desarrollada por la flota de agentes autónomos.</p>
      <div class="hero__actions">
        <a href="#caracteristicas" class="btn btn--primary">Explorar Sistema</a>
      </div>
    </section>

    <section id="caracteristicas" class="features">
      <div class="card">
        <h3>⚡ Arquitectura Ágil</h3>
        <p>Estructura modular optimizada para tiempos de carga ultrarrápidos y bajo consumo de recursos.</p>
      </div>
      <div class="card">
        <h3>🎨 Diseño Adaptativo</h3>
        <p>Experiencia fluida y consistente en cualquier dispositivo móvil o de escritorio.</p>
      </div>
      <div class="card">
        <h3>🔒 Blindaje y Seguridad</h3>
        <p>Estándares de seguridad de datos y buenas prácticas de ingeniería de software.</p>
      </div>
    </section>
  </main>

  <footer class="footer">
    <p>&copy; 2026 {nombre_proyecto}. Desarrollado con excelencia técnica.</p>
  </footer>

  <script src="main.js"></script>
</body>
</html>
""", encoding="utf-8")

        # style.css
        (base / "style.css").write_text("""/* =========================================
   Reset y Variables de Diseño
   ========================================= */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --color-bg:        #0d1117;
  --color-surface:   #161b22;
  --color-border:    #30363d;
  --color-primary:   #58a6ff;
  --color-secondary: #238636;
  --color-text:      #c9d1d9;
  --color-text-bold: #f0f6fc;
  --color-muted:     #8b949e;
  --font-main:       'Inter', system-ui, -apple-system, sans-serif;
  --radius:          8px;
  --shadow:          0 4px 20px rgba(0, 0, 0, 0.35);
  --transition:      0.2s ease-in-out;
}

html { scroll-behavior: smooth; }
body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-main);
  min-height: 100vh;
  line-height: 1.6;
}

/* Header & Nav */
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(13, 17, 23, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
  padding: 1rem 2rem;
}
.nav {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nav__logo {
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--color-primary);
}
.nav__menu {
  list-style: none;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.nav__menu a {
  color: var(--color-text);
  text-decoration: none;
  font-size: 0.95rem;
  transition: color var(--transition);
}
.nav__menu a:hover { color: var(--color-primary); }

/* Hero */
.hero {
  max-width: 1200px;
  margin: 0 auto;
  min-height: 70vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4rem 2rem;
  gap: 1.5rem;
}
.hero__title {
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  font-weight: 700;
  color: var(--color-text-bold);
  line-height: 1.15;
}
.hero__subtitle {
  font-size: 1.2rem;
  color: var(--color-muted);
  max-width: 600px;
}
.hero__actions { display: flex; gap: 1rem; margin-top: 1rem; }

/* Botones */
.btn {
  display: inline-block;
  padding: 0.75rem 1.75rem;
  border-radius: var(--radius);
  font-size: 0.95rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  border: none;
  transition: transform var(--transition), opacity var(--transition);
}
.btn:hover { transform: translateY(-2px); opacity: 0.92; }
.btn--primary { background: var(--color-primary); color: #0d1117; }
.btn--secondary { background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text); }

/* Features */
.features {
  max-width: 1200px;
  margin: 0 auto 5rem;
  padding: 0 2rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 2rem;
  box-shadow: var(--shadow);
}
.card h3 { color: var(--color-text-bold); margin-bottom: 0.75rem; }
.card p { color: var(--color-muted); font-size: 0.95rem; }

/* Footer */
.footer {
  text-align: center;
  padding: 2.5rem;
  color: var(--color-muted);
  font-size: 0.875rem;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .nav__menu { display: none; }
  .features { grid-template-columns: 1fr; }
}
""", encoding="utf-8")

        # main.js
        (base / "main.js").write_text(f"""'use strict';
// {nombre_proyecto} — main.js
document.addEventListener('DOMContentLoaded', () => {{
  console.log('[{nombre_proyecto}] Interfaz iniciada correctamente.');
}});
""", encoding="utf-8")

        # README.md
        (base / "README.md").write_text(f"""# {nombre_proyecto}

Proyecto web estático modular generado por **Subagente_Desarrollo**.

## Estructura de Archivos
- `index.html`: Estructura HTML5 semántica y accesible.
- `style.css`: Sistema de diseño basado en variables CSS con modo oscuro integrado y diseño adaptativo.
- `main.js`: Lógica funcional de interacción.

## Instrucciones de Previsualización
Puedes abrir directamente el archivo `index.html` en cualquier navegador web o servirlo localmente mediante:
```bash
python -m http.server 8080 --directory "{base}"
```
""", encoding="utf-8")

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "ruta": str(base),
            "archivos_creados": ["index.html", "style.css", "main.js", "README.md"],
            "mensaje": f"Proyecto web estático creado exitosamente en {base}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def web_scaffold_react(nombre_proyecto: str, directorio_destino: str = "") -> str:
    """
    Crea un proyecto React moderno utilizando Vite como bundler.
    Requiere Node.js y npm en el entorno.

    Args:
        nombre_proyecto: Nombre del proyecto React (ej: 'dashboard-analytics', 'portal-clientes').
        directorio_destino: Carpeta contenedora. Si se deja vacía, se aloja en '/app/Subagente_Desarrollo/proyectos/'.
    """
    try:
        dest_base = Path(directorio_destino) if directorio_destino else _PROYECTOS
        dest_base.mkdir(parents=True, exist_ok=True)
        proyecto_path = dest_base / nombre_proyecto

        cmd = f"npm create vite@latest {nombre_proyecto} -- --template react"
        r = _ejecutar(cmd, str(dest_base), timeout=120)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": f"No se pudo crear el proyecto Vite. Verifica si Node.js y npm están disponibles: {r['stderr']}",
                "alternativa": "Usa web_scaffold_html si se requiere una solución inmediata sin dependencias de Node.js."
            })

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "ruta": str(proyecto_path),
            "siguiente_paso": [
                f"cd {proyecto_path}",
                "npm install",
                "npm run dev"
            ],
            "stdout": r["stdout"][:500]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_WEB = [
    web_scaffold_html,
    web_scaffold_react
]
