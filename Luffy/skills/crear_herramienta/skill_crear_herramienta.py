import os
from pathlib import Path
import traceback

def iniciar_creacion_skill(agente: str, nombre_skill: str, objetivo: str, entradas_salidas: str, hard_stops: str, codigo_python: str) -> str:
    """
    Crea los archivos iniciales (.md y .py) para una nueva habilidad en la carpeta del agente especificado,
    y formatea un mensaje para que el agente levante un ticket de auditoría a Robin.
    """
    try:
        agentes_root = Path(__file__).resolve().parents[2]
        agente_path = agentes_root / agente.capitalize()
        
        if not agente_path.exists() or not agente_path.is_dir():
            return f"ERROR_CONTROLADO: El agente '{agente}' no existe en {agentes_root}."
        
        skills_path = agente_path / "skills"
        skills_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Crear el archivo Markdown (Drafting)
        md_file_path = skills_path / f"skill_{nombre_skill}.md"
        md_content = f"# {nombre_skill.replace('_', ' ').title()}\n\n"
        md_content += f"## Objetivo\n{objetivo}\n\n"
        md_content += f"## Entradas / Salidas Esperadas\n{entradas_salidas}\n\n"
        md_content += f"## Límites de Seguridad (Hard-Stops)\n{hard_stops}\n\n"
        md_content += f"---\n**Conexiones:** [[Perfil_{agente.capitalize()}]]\n"
        
        md_file_path.write_text(md_content, encoding="utf-8")
        
        # 2. Crear el archivo Python (Script)
        py_file_path = skills_path / f"skill_{nombre_skill}.py"
        
        # Inyectar estructura si el LLM no la incluyó bien
        if "def " not in codigo_python:
            py_content = '"""\nScript autogenerado para habilidad.\n"""\nfrom typing import Any, Dict, Optional\n\n'
            py_content += f"def ejecutar_{nombre_skill}(input_data: str, config: Optional[Dict[str, Any]] = None) -> str:\n"
            py_content += "    try:\n"
            py_content += "        # Logica inyectada:\n"
            for line in codigo_python.split('\n'):
                py_content += f"        {line}\n"
            py_content += '        return "Operación completada"\n'
            py_content += '    except Exception as e:\n'
            py_content += '        return f"ERROR_CRITICO: {str(e)}"\n'
        else:
            py_content = codigo_python

        py_file_path.write_text(py_content, encoding="utf-8")
        
        mensaje = (
            f"EXCELENTE. Los archivos para la habilidad '{nombre_skill}' han sido creados físicamente en la carpeta de {agente.capitalize()}.\n"
            f"- Markdown: {md_file_path}\n"
            f"- Python: {py_file_path}\n\n"
            "⚠️ ATENCIÓN LUFFY: TU TAREA AÚN NO TERMINA. DEBES GENERAR AHORA MISMO UN TICKET EN LA PIZARRA (Bitacora.md) ASIGNADO A 'Robin' "
            f"PARA QUE AUDITE EL CÓDIGO DE '{nombre_skill}.py'. NO CIERRES EL FLUJO SIN GENERAR ESE TICKET."
        )
        return mensaje
        
    except Exception as e:
        return f"ERROR_CRITICO al crear la habilidad: {str(e)}\n{traceback.format_exc()}"
