"""
skill_frontend_design.py — Habilidad: Arquitectura y Diseño Frontend Avanzado
==============================================================================
Herramientas para generar componentes visuales, interfaces pulidas y arquitectura
frontend bajo 5 metodologías de diseño de clase mundial:
  1. Anthropic Clean Design: Baja carga cognitiva, espacios generosos y colores neutros.
  2. UI/UX Pro Max: Glassmorphism, degradados vibrantes, microinteracciones y tarjetas elevadas.
  3. Emil Design Engineering: Precisión matemática en espaciados (múltiplos de 4/8px), pixel-perfect y a11y.
  4. Huashu Oriental Minimalist: Monocromático, asimetría elegante y equilibrio espacial.
  5. Vercel Guidelines: Brutalismo corporativo, tipografía monoespaciada/sans limpia y enfoque Edge/SSR.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_frontend_design() -> str:
    """
    System Prompt especializado y encapsulado para la arquitectura y diseño
    de interfaces de usuario avanzadas del Subagente de Desarrollo.
    """
    return """[🛑 HARD-STOP: MODO DISEÑO FRONTEND Y ARQUITECTURA UI/UX ACTIVO 🛑]
Eres el Diseñador de Sistemas de Diseño y Arquitecto Frontend del Subagente de Desarrollo.
Tu misión es construir interfaces y componentes visuales que combinen belleza estética con rigor ingenieril, accesibilidad (WCAG 2.1 AA) y experiencia de usuario fluida.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. SELECCIÓN DE ENFOQUE DE DISEÑO:
   - `aplicar_frontend_design_anthropic`: Para herramientas analíticas, paneles de control corporativos y lectores de contenido donde la legibilidad y la neutralidad visual son prioritarias.
   - `aplicar_ui_ux_pro_max`: Para landings de alto impacto comercial, aplicaciones Web3 o productos modernos con estética glassmorphism, sombras volumétricas y efectos visuales ricos.
   - `aplicar_emil_design_eng`: Para refactorizaciones donde se requiere exactitud milimétrica en padding/margin (escala de 4px/8px), navegación por teclado y contraste cromático estricto.
   - `aplicar_huashu_design`: Para productos de autor, blogs conceptuales o experiencias minimalistas con contraste blanco/negro y tipografía editorial refinada.
   - `aplicar_vercel_guidelines`: Para portales de infraestructura técnica, herramientas para desarrolladores y documentación técnica con estética oscura tipo Vercel/Next.js.
2. CALIDAD DE CÓDIGO GENERADO:
   - Todo componente debe auto-contener su estructura semántica, estilos CSS modulares y accesibilidad nativa.
   - Rutas de almacenamiento siempre dentro de `/app/Subagente_Desarrollo/proyectos/`.
"""


def _resolver_ruta_archivo(ruta_destino: str, nombre_defecto: str) -> Path:
    """Resuelve la ruta final asegurando que sea un archivo dentro de proyectos."""
    if not ruta_destino:
        carpeta = _PROYECTOS
        return carpeta / nombre_defecto

    p = Path(ruta_destino)
    if p.is_dir() or not p.suffix:
        p.mkdir(parents=True, exist_ok=True)
        return p / nombre_defecto

    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@tool
def aplicar_frontend_design_anthropic(nombre_componente: str, ruta_destino: str = "") -> str:
    """
    Genera un componente visual con enfoque utilitario, baja carga cognitiva y espacios limpios (Estilo Anthropic).
    Ideal para paneles de control, tablas de datos y herramientas de productividad.

    Args:
        nombre_componente: Nombre del componente o módulo (ej: 'PanelAnalitica', 'TablaUsuarios').
        ruta_destino: Ruta de archivo o directorio donde se guardará.
    """
    try:
        archivo = _resolver_ruta_archivo(ruta_destino, f"{nombre_componente.lower()}_anthropic.html")
        contenido = f"""<!-- [Anthropic Design System] Componente: {nombre_componente} -->
<div class="anthropic-card" role="region" aria-label="{nombre_componente}">
  <div class="anthropic-header">
    <h2 class="anthropic-title">{nombre_componente}</h2>
    <span class="anthropic-badge">Estable</span>
  </div>
  <div class="anthropic-body">
    <p class="anthropic-desc">Componente estructurado con enfoque utilitario, contraste moderado y espaciados simétricos para reducir la fatiga cognitiva.</p>
    <div class="anthropic-action-bar">
      <button type="button" class="anthropic-btn-primary">Ejecutar Acción</button>
      <button type="button" class="anthropic-btn-secondary">Opciones</button>
    </div>
  </div>
</div>

<style>
.anthropic-card {{
  background: #ffffff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 1.5rem;
  max-width: 640px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #1f1f1f;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}}
.anthropic-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 0.75rem;
  margin-bottom: 1rem;
}}
.anthropic-title {{
  font-size: 1.15rem;
  font-weight: 600;
  margin: 0;
}}
.anthropic-badge {{
  font-size: 0.75rem;
  background: #f4f4f4;
  color: #666;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}}
.anthropic-desc {{
  font-size: 0.95rem;
  line-height: 1.5;
  color: #4b4b4b;
  margin-bottom: 1.25rem;
}}
.anthropic-action-bar {{
  display: flex;
  gap: 0.75rem;
}}
.anthropic-btn-primary {{
  background: #202020;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}}
.anthropic-btn-secondary {{
  background: transparent;
  color: #333;
  border: 1px solid #ccc;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}}
</style>
"""
        archivo.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "componente": nombre_componente,
            "estilo": "Anthropic Clean Design",
            "archivo": str(archivo),
            "mensaje": f"Componente {nombre_componente} generado con éxito en {archivo}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def aplicar_ui_ux_pro_max(descripcion_interfaz: str, ruta_destino: str = "") -> str:
    """
    Genera interfaces visualmente impactantes con glassmorphism, sombras volumétricas y animaciones fluidas (UI/UX Pro Max).

    Args:
        descripcion_interfaz: Descripción del propósito visual (ej: 'Dashboard Financiero Glassmorphism').
        ruta_destino: Ruta de archivo o directorio donde se guardará.
    """
    try:
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', descripcion_interfaz.lower())[:30].strip('_')
        archivo = _resolver_ruta_archivo(ruta_destino, f"{slug}_promax.html")
        contenido = f"""<!-- [UI/UX Pro Max] Interfaz: {descripcion_interfaz} -->
<div class="promax-container">
  <div class="promax-glass-card">
    <div class="promax-glow"></div>
    <div class="promax-content">
      <span class="promax-tag">PREMIUM EXPERIENCE</span>
      <h2 class="promax-heading">{descripcion_interfaz}</h2>
      <p class="promax-sub">Diseño de alta fidelidad con efectos de refracción óptica, gradientes dinámicos y bordes translúcidos.</p>
      <div class="promax-grid">
        <div class="promax-stat">
          <span class="promax-stat-val">+148%</span>
          <span class="promax-stat-label">Rendimiento</span>
        </div>
        <div class="promax-stat">
          <span class="promax-stat-val">99.9%</span>
          <span class="promax-stat-label">Confiabilidad</span>
        </div>
      </div>
      <button class="promax-btn">Desbloquear Funciones</button>
    </div>
  </div>
</div>

<style>
.promax-container {{
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: radial-gradient(circle at 10% 20%, #1e1035 0%, #080612 90%);
  padding: 2rem;
  font-family: 'Inter', system-ui, sans-serif;
}}
.promax-glass-card {{
  position: relative;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 2.5rem;
  max-width: 500px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  overflow: hidden;
  color: #ffffff;
}}
.promax-glow {{
  position: absolute;
  top: -50px;
  right: -50px;
  width: 150px;
  height: 150px;
  background: #9d4edd;
  filter: blur(80px);
  opacity: 0.6;
  border-radius: 50%;
}}
.promax-tag {{
  display: inline-block;
  font-size: 0.75rem;
  letter-spacing: 1.5px;
  font-weight: 700;
  color: #c77dff;
  margin-bottom: 0.5rem;
}}
.promax-heading {{
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 0.75rem;
}}
.promax-sub {{
  color: #adb5bd;
  font-size: 0.95rem;
  line-height: 1.5;
  margin-bottom: 1.5rem;
}}
.promax-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
}}
.promax-stat {{
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 1rem;
}}
.promax-stat-val {{
  display: block;
  font-size: 1.4rem;
  font-weight: 700;
  color: #7b2cbf;
}}
.promax-stat-label {{
  font-size: 0.8rem;
  color: #8a8a9e;
}}
.promax-btn {{
  width: 100%;
  padding: 0.85rem;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #7b2cbf, #9d4edd);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.promax-btn:hover {{
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(157, 78, 221, 0.4);
}}
</style>
"""
        archivo.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "interfaz": descripcion_interfaz,
            "estilo": "UI/UX Pro Max Glassmorphism",
            "archivo": str(archivo),
            "mensaje": f"Interfaz visualmente avanzada generada en {archivo}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def aplicar_emil_design_eng(componente_a_refactorizar: str, ruta_destino: str = "") -> str:
    """
    Aplica disciplina matemática de ingeniería de diseño: accesibilidad AA, pixel-perfect y escala de 8px (Estilo Emil).

    Args:
        componente_a_refactorizar: Nombre del componente a pulir (ej: 'BotonAccion', 'FormularioRegistro').
        ruta_destino: Ruta de archivo o directorio donde se guardará.
    """
    try:
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', componente_a_refactorizar.lower())[:30].strip('_')
        archivo = _resolver_ruta_archivo(ruta_destino, f"{slug}_emil.html")
        contenido = f"""<!-- [Emil Design Engineering] Componente: {componente_a_refactorizar} -->
<form class="emil-form" role="form" aria-labelledby="form-title">
  <h3 id="form-title" class="emil-title">{componente_a_refactorizar}</h3>
  <div class="emil-field">
    <label for="emil-input" class="emil-label">Parámetro Principal</label>
    <input id="emil-input" type="text" class="emil-input" placeholder="Valor requerido" required aria-required="true" />
    <span class="emil-hint">Espaciado estricto en múltiplos de 8px (Grid System).</span>
  </div>
  <button type="submit" class="emil-submit-btn">Confirmar Operación</button>
</form>

<style>
.emil-form {{
  max-width: 480px;
  background: #ffffff;
  border: 1px solid #111111;
  padding: 32px;
  box-shadow: 4px 4px 0px #111111;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.emil-title {{
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 24px;
  color: #111111;
  letter-spacing: -0.5px;
}}
.emil-field {{
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
}}
.emil-label {{
  font-size: 14px;
  font-weight: 600;
  color: #222222;
}}
.emil-input {{
  height: 48px;
  padding: 0 16px;
  border: 1px solid #767676;
  border-radius: 0px;
  font-size: 16px;
  color: #111111;
  outline-offset: 2px;
}}
.emil-input:focus {{
  outline: 2px solid #005fcc;
  border-color: #005fcc;
}}
.emil-hint {{
  font-size: 12px;
  color: #666666;
}}
.emil-submit-btn {{
  height: 48px;
  width: 100%;
  background: #111111;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  outline-offset: 2px;
}}
.emil-submit-btn:focus-visible {{
  outline: 3px solid #005fcc;
}}
</style>
"""
        archivo.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "componente": componente_a_refactorizar,
            "estilo": "Emil Design Engineering",
            "archivo": str(archivo),
            "mensaje": f"Componente refactorizado con rigor matemático y a11y en {archivo}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def aplicar_huashu_design(concepto_oriental: str, ruta_destino: str = "") -> str:
    """
    Genera interfaces minimalistas asimétricas, de alto contraste monocromático y equilibrio espacial (Estilo Huashu).

    Args:
        concepto_oriental: Concepto estético o temático (ej: 'Silencio Espacial', 'Caligrafia Digital').
        ruta_destino: Ruta de archivo o directorio donde se guardará.
    """
    try:
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', concepto_oriental.lower())[:30].strip('_')
        archivo = _resolver_ruta_archivo(ruta_destino, f"{slug}_huashu.html")
        contenido = f"""<!-- [Huashu Minimalist Design] Concepto: {concepto_oriental} -->
<section class="huashu-container">
  <div class="huashu-asymmetric-layout">
    <div class="huashu-accent-column">
      <span class="huashu-vertical-text">華術・MINIMAL</span>
    </div>
    <div class="huashu-main-column">
      <h1 class="huashu-headline">{concepto_oriental}</h1>
      <p class="huashu-prose">El vacío no es ausencia, sino el espacio donde la función adquiere significado. Tipografía sobria, bordes afilados y contraste puro.</p>
      <div class="huashu-divider"></div>
      <span class="huashu-index">01 / ARCHITECTURE</span>
    </div>
  </div>
</section>

<style>
.huashu-container {{
  background: #000000;
  color: #ffffff;
  padding: 80px 40px;
  font-family: 'Cinzel', 'Georgia', serif;
  min-height: 450px;
  display: flex;
  align-items: center;
}}
.huashu-asymmetric-layout {{
  display: flex;
  gap: 40px;
  max-width: 700px;
  margin: 0 auto;
}}
.huashu-accent-column {{
  border-right: 1px solid #333333;
  padding-right: 20px;
}}
.huashu-vertical-text {{
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 11px;
  letter-spacing: 4px;
  color: #666666;
}}
.huashu-main-column {{
  padding-left: 20px;
}}
.huashu-headline {{
  font-size: 38px;
  font-weight: 400;
  letter-spacing: 2px;
  line-height: 1.1;
  margin-bottom: 24px;
  color: #f5f5f5;
}}
.huashu-prose {{
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #999999;
  max-width: 440px;
}}
.huashu-divider {{
  width: 40px;
  height: 1px;
  background: #ffffff;
  margin: 30px 0 15px;
}}
.huashu-index {{
  font-family: monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #555555;
}}
</style>
"""
        archivo.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "concepto": concepto_oriental,
            "estilo": "Huashu Oriental Minimalist",
            "archivo": str(archivo),
            "mensaje": f"Diseño Huashu minimalista generado en {archivo}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


@tool
def aplicar_vercel_guidelines(nombre_proyecto: str, ruta_destino: str = "") -> str:
    """
    Genera arquitectura y componentes con estética brutalista corporativa, optimizados para Edge, SSR y rendimiento (Estilo Vercel).

    Args:
        nombre_proyecto: Nombre del proyecto o interfaz técnica (ej: 'ConsolaEdge', 'MonitorServicios').
        ruta_destino: Ruta de archivo o directorio donde se guardará.
    """
    try:
        archivo = _resolver_ruta_archivo(ruta_destino, f"{nombre_proyecto.lower()}_vercel.html")
        contenido = f"""<!-- [Vercel Design System Guidelines] Proyecto: {nombre_proyecto} -->
<div class="vercel-root">
  <div class="vercel-nav">
    <div class="vercel-brand">
      <svg width="20" height="17" viewBox="0 0 76 65" fill="#fff"><path d="M37.5274 0L75.0548 65H0L37.5274 0Z"/></svg>
      <span>{nombre_proyecto}</span>
    </div>
    <span class="vercel-status-pill"><span class="vercel-dot"></span> Ready</span>
  </div>
  <div class="vercel-card-grid">
    <div class="vercel-card">
      <div class="vercel-card-header">Edge Deployment</div>
      <div class="vercel-card-body">
        <code>iad1::iad1-p6m8q</code>
        <p>Latencia media &lt; 15ms. Servido directamente desde la caché perimetral global.</p>
      </div>
    </div>
    <div class="vercel-card">
      <div class="vercel-card-header">Core Web Vitals</div>
      <div class="vercel-card-body">
        <span class="vercel-metric">100 / 100</span>
        <p>LCP 0.4s • FID 2ms • CLS 0.00</p>
      </div>
    </div>
  </div>
</div>

<style>
.vercel-root {{
  background: #000000;
  color: #ededed;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  padding: 32px;
  border: 1px solid #333333;
  border-radius: 8px;
  max-width: 720px;
}}
.vercel-nav {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #222222;
  padding-bottom: 16px;
  margin-bottom: 24px;
}}
.vercel-brand {{
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  font-size: 16px;
}}
.vercel-status-pill {{
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #888888;
  border: 1px solid #333333;
  padding: 4px 10px;
  border-radius: 999px;
}}
.vercel-dot {{
  width: 8px;
  height: 8px;
  background: #0070f3;
  border-radius: 50%;
}}
.vercel-card-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}}
.vercel-card {{
  border: 1px solid #333333;
  border-radius: 6px;
  padding: 20px;
  background: #0a0a0a;
  transition: border-color 0.15s ease;
}}
.vercel-card:hover {{
  border-color: #666666;
}}
.vercel-card-header {{
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 12px;
}}
.vercel-card-body code {{
  font-family: monospace;
  background: #1a1a1a;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #0070f3;
}}
.vercel-card-body p {{
  font-size: 13px;
  color: #888888;
  line-height: 1.5;
  margin-top: 8px;
}}
.vercel-metric {{
  font-size: 24px;
  font-weight: 700;
  color: #50e3c2;
}}
</style>
"""
        archivo.write_text(contenido, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "proyecto": nombre_proyecto,
            "estilo": "Vercel Guidelines (SSR / Edge)",
            "archivo": str(archivo),
            "mensaje": f"Proyecto Vercel Guidelines generado en {archivo}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


HERRAMIENTAS_FRONTEND_DESIGN = [
    aplicar_frontend_design_anthropic,
    aplicar_ui_ux_pro_max,
    aplicar_emil_design_eng,
    aplicar_huashu_design,
    aplicar_vercel_guidelines
]
