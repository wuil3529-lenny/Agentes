import os
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[2]
PROYECTOS_DIR = _APP_ROOT / "proyectos"

def asegurar_directorios():
    PROYECTOS_DIR.mkdir(exist_ok=True, parents=True)

@tool
def tool_crear_plan(origen_contexto: str, nombre_proyecto: str, plan_estructurado: str) -> str:
    """
    Crea un archivo maestro de planificación estratégico (PLAN-[ID]-[nombre_proyecto].md).
    Úsalo cuando el usuario te pida explícitamente estructurar un plan a partir de un contexto (CTX).
    El plan debe contener fases, delegaciones claras (Zoro, Nami, Robin, Sanji) y dependencias.
    """
    asegurar_directorios()
    
    try:
        # Sanitizar nombre del proyecto
        nombre_seguro = "".join(c if c.isalnum() else "_" for c in nombre_proyecto).strip("_")
        
        # Un solo archivo por proyecto
        nombre_archivo = f"PLAN-{nombre_seguro}.md"
        plan_path = PROYECTOS_DIR / nombre_archivo
            
        contenido_final = f"""# {nombre_proyecto.replace('_', ' ').title()}
**Última Actualización:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Contexto Origen:** {origen_contexto}

---

{plan_estructurado}
"""
        
        plan_path.write_text(contenido_final, encoding="utf-8")
        
        return f"Plan guardado/actualizado exitosamente en: {plan_path}. Ahora puedes leerlo para crear los tickets correspondientes en la Pizarra."
        
    except Exception as e:
        return f"Error al generar el plan: {str(e)}"
