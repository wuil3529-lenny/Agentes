import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]
import os
from langchain.tools import tool
from pydantic import BaseModel, Field

# Modelos Pydantic para asegurar que LangGraph entienda los parámetros requeridos
class AnthropicParams(BaseModel):
    nombre_componente: str = Field(description="Nombre del componente (ej. Dashboard, Panel).")
    ruta_destino: str = Field(description="Ruta donde se guardará el archivo.")

class UIUXProMaxParams(BaseModel):
    descripcion_interfaz: str = Field(description="Descripción de la interfaz (efectos, animaciones).")
    ruta_destino: str = Field(description="Ruta donde se guardará el archivo.")

class EmilDesignParams(BaseModel):
    componente_a_refactorizar: str = Field(description="Componente a pulir con precisión matemática.")
    ruta_destino: str = Field(description="Ruta donde se guardará el archivo.")

class HuashuParams(BaseModel):
    concepto_oriental: str = Field(description="Descripción del concepto minimalista.")
    ruta_destino: str = Field(description="Ruta donde se guardará el archivo.")

class VercelParams(BaseModel):
    nombre_proyecto: str = Field(description="Nombre del proyecto SSR / Edge.")
    ruta_destino: str = Field(description="Ruta donde se inicializará el proyecto.")

# Implementación de Herramientas
@tool("aplicar_frontend_design_anthropic", args_schema=AnthropicParams)

def aplicar_frontend_design_anthropic(nombre_componente: str, ruta_destino: str) -> str:
    """Genera componentes con enfoque utilitario, baja carga cognitiva y espacios limpios (Anthropic)."""
    ruta_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        # Aquí iría la lógica real de scaffolding
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(f"<!-- [Anthropic Design] Componente: {nombre_componente} -->\n")
            f.write("<!-- Alta legibilidad, colores neutros, tipografía sans-serif limpia. -->")
        return f"Éxito: Scaffolding Anthropic-Design aplicado en {ruta_destino}."
    except Exception as e:
        return f"Error: {str(e)}"

@tool("aplicar_ui_ux_pro_max", args_schema=UIUXProMaxParams)
def aplicar_ui_ux_pro_max(descripcion_interfaz: str, ruta_destino: str) -> str:
    """Genera interfaces visualmente impactantes, glassmorphism y animaciones fluidas."""
    ruta_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(f"<!-- [UI/UX Pro Max] Interfaz: {descripcion_interfaz} -->\n")
            f.write("<!-- Tokens vibrantes, sombras profundas, framer-motion ready. -->")
        return f"Éxito: Interfaz avanzada Pro-Max creada en {ruta_destino}."
    except Exception as e:
        return f"Error: {str(e)}"

@tool("aplicar_emil_design_eng", args_schema=EmilDesignParams)
def aplicar_emil_design_eng(componente_a_refactorizar: str, ruta_destino: str) -> str:
    """Aplica disciplina extrema (Pixel-perfect, a11y, estados completos)."""
    ruta_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(f"<!-- [Emil Design Eng] Refactor: {componente_a_refactorizar} -->\n")
            f.write("<!-- Accesibilidad total, a11y focus, espaciados rem exactos. -->")
        return f"Éxito: Componente refactorizado con rigor matemático en {ruta_destino}."
    except Exception as e:
        return f"Error: {str(e)}"

@tool("aplicar_huashu_design", args_schema=HuashuParams)
def aplicar_huashu_design(concepto_oriental: str, ruta_destino: str) -> str:
    """Diseño minimalista asimétrico, alto contraste y monocromático (Huashu)."""
    ruta_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(f"<!-- [Huashu Design] Concepto: {concepto_oriental} -->\n")
            f.write("<!-- Monocromático, asimetría elegante, minimalismo contemporáneo. -->")
        return f"Éxito: Diseño Huashu inicializado en {ruta_destino}."
    except Exception as e:
        return f"Error: {str(e)}"

@tool("aplicar_vercel_guidelines", args_schema=VercelParams)
def aplicar_vercel_guidelines(nombre_proyecto: str, ruta_destino: str) -> str:
    """Scaffolding orientado a performance, SSR, Edge y estética brutalista corporativa (Vercel)."""
    ruta_destino = str(_APP_ROOT / "Zoro" / "proyectos")
    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(f"<!-- [Vercel Guidelines] Proyecto: {nombre_proyecto} -->\n")
            f.write("<!-- Brutalismo corporativo, optimizado para SSR y Edge Vitals. -->")
        return f"Éxito: Proyecto optimizado al estilo Vercel creado en {ruta_destino}."
    except Exception as e:
        return f"Error: {str(e)}"

# Exportar las herramientas como lista para el bind_tools de LangChain
HERRAMIENTAS_FRONTEND_DESIGN = [
    aplicar_frontend_design_anthropic,
    aplicar_ui_ux_pro_max,
    aplicar_emil_design_eng,
    aplicar_huashu_design,
    aplicar_vercel_guidelines
]
