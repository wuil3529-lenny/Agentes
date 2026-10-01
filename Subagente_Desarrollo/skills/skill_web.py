"""
skill_web.py — Habilidad: Desarrollo Web Full-Stack
====================================================
Herramientas especializadas para crear páginas web y aplicaciones web modernas.

Stack soportado:
  - HTML5 + CSS Vanilla + JavaScript puro  → web_scaffold_html()
  - React + Vite (SPA moderna)             → web_scaffold_react()  [requiere Node.js]

Flujo típico de uso:
  1. Luffy delega "crea una landing page para X"
  2. Zoro llama web_scaffold_html() para crear la estructura base
  3. Zoro usa crear_archivo() de skill_base para añadir contenido personalizado
  4. Zoro reporta la ruta del proyecto a Luffy

Documentación en Obsidian: agentes/Zoro_Skills.md
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]

import json
import subprocess
from pathlib import Path
from langchain_core.tools import tool



def _ejecutar(comando: str, cwd: str, timeout: int = 120) -> dict:
    """Helper interno para ejecutar comandos de Node/npm."""
    try:
        caracteres_peligrosos = ['&', '|', ';', '>', '<', '$', '`']
        if any(c in comando for c in caracteres_peligrosos):
            return json.dumps({"status": "error", "mensaje": "Violación de seguridad: inyección de comandos detectada."})

        r = subprocess.run(
            comando, shell=True, cwd=cwd,
            capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout[:2000],
            "stderr": r.stderr[:1000],
            "code": r.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Timeout superado (120s).", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


@tool
def web_scaffold_html(nombre_proyecto: str, directorio_destino: str) -> str:
    """
    Crea un proyecto web estático completo con HTML5 + CSS moderno + JavaScript.
    No requiere Node.js ni npm. Listo para abrir en el navegador.
    Genera: index.html, style.css, main.js, README.md

    Args:
        nombre_proyecto: Nombre del proyecto (ej: "landing-empresa", "portfolio")
        directorio_destino: Carpeta padre donde se creará el proyecto (ej: "C:/Users/admin/Documents/Agentes/Zoro/proyectos")
    """
    directorio_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        base = Path(directorio_destino) / nombre_proyecto
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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="header">
    <nav class="nav">
      <span class="nav__logo">{nombre_proyecto}</span>
    </nav>
  </header>

  <main class="main" id="app">
    <section class="hero">
      <h1 class="hero__title">{nombre_proyecto}</h1>
      <p class="hero__subtitle">Construido por la Tripulación Sombrero de Paja</p>
      <a href="#" class="btn btn--primary">Comenzar</a>
    </section>
  </main>

  <footer class="footer">
    <p>&copy; 2026 {nombre_proyecto}. Todos los derechos reservados.</p>
  </footer>

  <script src="main.js"></script>
</body>
</html>
""", encoding="utf-8")

        # style.css
        (base / "style.css").write_text("""/* ═══════════════════════════════
   Reset y Variables
═══════════════════════════════ */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --color-bg:        #0f0f1a;
  --color-surface:   #1a1a2e;
  --color-primary:   #6c63ff;
  --color-secondary: #ff6b9d;
  --color-text:      #e8e8f0;
  --color-muted:     #8888aa;
  --font-main:       'Inter', system-ui, sans-serif;
  --radius:          12px;
  --shadow:          0 4px 24px rgba(108,99,255,0.15);
  --transition:      0.25s ease;
}

/* ═══════════════════════════════
   Base
═══════════════════════════════ */
html { scroll-behavior: smooth; }

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-main);
  min-height: 100vh;
  line-height: 1.6;
}

/* ═══════════════════════════════
   Header / Nav
═══════════════════════════════ */
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(15,15,26,0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255,255,255,0.07);
  padding: 1rem 2rem;
}

.nav {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav__logo {
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--color-primary);
  letter-spacing: -0.5px;
}

/* ═══════════════════════════════
   Hero
═══════════════════════════════ */
.hero {
  min-height: 85vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4rem 2rem;
  gap: 1.5rem;
  background:
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(108,99,255,0.15), transparent);
}

.hero__title {
  font-size: clamp(2.5rem, 7vw, 5rem);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -2px;
  background: linear-gradient(135deg, var(--color-text) 0%, var(--color-primary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero__subtitle {
  font-size: 1.15rem;
  color: var(--color-muted);
  max-width: 480px;
}

/* ═══════════════════════════════
   Botones
═══════════════════════════════ */
.btn {
  display: inline-block;
  padding: 0.85rem 2.25rem;
  border-radius: var(--radius);
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: transform var(--transition), box-shadow var(--transition);
  border: none;
}

.btn:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.btn:active { transform: translateY(0); }

.btn--primary {
  background: var(--color-primary);
  color: #fff;
}

/* ═══════════════════════════════
   Main
═══════════════════════════════ */
.main { max-width: 1100px; margin: 0 auto; }

/* ═══════════════════════════════
   Footer
═══════════════════════════════ */
.footer {
  text-align: center;
  padding: 2rem;
  color: var(--color-muted);
  font-size: 0.875rem;
  border-top: 1px solid rgba(255,255,255,0.07);
}

/* ═══════════════════════════════
   Responsive
═══════════════════════════════ */
@media (max-width: 768px) {
  .header { padding: 1rem; }
}
""", encoding="utf-8")

        # main.js
        (base / "main.js").write_text(f"""'use strict';
// {nombre_proyecto} — main.js

document.addEventListener('DOMContentLoaded', () => {{
  console.log('[{nombre_proyecto}] Aplicación iniciada.');

  // Animación de entrada para elementos hero
  const hero = document.querySelector('.hero');
  if (hero) {{
    hero.style.opacity = '0';
    hero.style.transform = 'translateY(20px)';
    hero.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    requestAnimationFrame(() => {{
      hero.style.opacity = '1';
      hero.style.transform = 'translateY(0)';
    }});
  }}
}});
""", encoding="utf-8")

        # README.md
        (base / "README.md").write_text(f"""# {nombre_proyecto}

Proyecto web generado por **Zoro** (Tripulación Sombrero de Paja).

## Estructura

```
{nombre_proyecto}/
├── index.html   — HTML semántico principal
├── style.css    — Estilos modernos (CSS Variables + responsive)
├── main.js      — Lógica JavaScript
└── README.md    — Este archivo
```

## Cómo usar

**Opción 1 — Abrir directamente:**
Haz doble clic en `index.html`.

**Opción 2 — Servidor local (recomendado):**
```bash
npx serve .
# o
python -m http.server 8080
```

## Personalización

- Colores: edita las variables CSS en `:root` dentro de `style.css`
- Contenido: modifica `index.html`
- Lógica: añade funciones en `main.js`
""", encoding="utf-8")

        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "ruta": str(base),
            "archivos_creados": ["index.html", "style.css", "main.js", "README.md"],
            "siguiente_paso": f"Abre {base / 'index.html'} en el navegador o usa: npx serve {base}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def web_scaffold_react(nombre_proyecto: str, directorio_destino: str) -> str:
    """
    Crea un proyecto React moderno usando Vite como bundler.
    Requiere Node.js y npm instalados en el sistema.
    Comando: npm create vite@latest <nombre> -- --template react

    Args:
        nombre_proyecto: Nombre del proyecto React (ej: "mi-app", "dashboard")
        directorio_destino: Carpeta padre donde se creará el proyecto (ej: "C:/Users/admin/Documents/Agentes/Zoro/proyectos")
    """
    directorio_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        dest = Path(directorio_destino)
        dest.mkdir(parents=True, exist_ok=True)
        proyecto_path = dest / nombre_proyecto

        # Crear proyecto Vite + React (no interactivo)
        cmd = f"npm create vite@latest {nombre_proyecto} -- --template react"
        r = _ejecutar(cmd, str(dest), timeout=120)

        if not r["ok"]:
            return json.dumps({
                "status": "error",
                "mensaje": "Error creando proyecto Vite. Verifica que Node.js esté instalado.",
                "stderr": r["stderr"],
                "alternativa": "Usa web_scaffold_html() si no tienes Node.js."
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
            "stdout": r["stdout"][:600]
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


# Lista de herramientas de este skill
HERRAMIENTAS_WEB = [web_scaffold_html, web_scaffold_react]
