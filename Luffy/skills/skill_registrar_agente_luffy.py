import os
import sys
from pathlib import Path
import json

_APP_ROOT = Path("C:/Users/admin/Documents/Agentes")

def registrar_nuevo_agente_luffy(nombre_agente: str, descripcion_rol: str = "") -> dict:
    """
    Registra un nuevo agente en la tripulacion de forma estructurada para V3.
    - Crea la carpeta del agente y su carpeta .agents
    - Crea el AGENTS.md, el {agente}_perfil.json y el {AGENTE}.md dentro de .agents
    - Crea el Perfil_{Agente}.md en la carpeta raiz del agente.
    - Agrega los placeholders al archivo .env.
    """
    nombre_capitalizado = nombre_agente.capitalize()
    nombre_minuscula = nombre_agente.lower()
    
    raiz_sistema = _APP_ROOT
    
    reporte = {
        "carpeta_creada": False,
        "perfil_json_creado": False,
        "nodos_md_creados": 0,
        "env_actualizado": False,
        "errores": []
    }
    
    try:
        # 1. Crear Espacio Local
        carpeta_agente = raiz_sistema / nombre_capitalizado
        carpeta_agente.mkdir(parents=True, exist_ok=True)
        
        carpeta_agents = carpeta_agente / ".agents"
        carpeta_agents.mkdir(parents=True, exist_ok=True)
        
        agents_md = carpeta_agents / "AGENTS.md"
        if not agents_md.exists():
            agents_md.write_text(f"# Reglas de Comportamiento - {nombre_capitalizado}\\n\\nEste agente es {descripcion_rol}.\\nConsulta las reglas globales en `Reglas de la Tripulacion.md`.\\n", encoding="utf-8")
        reporte["carpeta_creada"] = True
        
        # 2. Crear ADN (Perfil) en .agents
        perfil_json = carpeta_agents / f"{nombre_minuscula}_perfil.json"
        if not perfil_json.exists():
            plantilla_perfil = {
                "nombre_completo": nombre_capitalizado,
                "titulo": descripcion_rol or "Agente Estandar",
                "presentacion": f"Soy {nombre_capitalizado}, {descripcion_rol}.",
                "capacidades": {
                    "habilidad_base": {
                        "nivel": "basico",
                        "descripcion": "Descripcion pendiente de definir."
                    }
                }
            }
            perfil_json.write_text(json.dumps(plantilla_perfil, indent=4, ensure_ascii=False), encoding="utf-8")
        reporte["perfil_json_creado"] = True
        
        # Nodo en mayuscula dentro de .agents
        perfil_md_interno = carpeta_agents / f"{nombre_capitalizado.upper()}.md"
        if not perfil_md_interno.exists():
            perfil_md_interno.write_text(f"# {nombre_capitalizado}\\n\\nRol: {descripcion_rol}\\n", encoding="utf-8")
            reporte["nodos_md_creados"] += 1
            
        # Nodo principal Perfil_Agente.md en la raiz de la carpeta del agente
        perfil_md = carpeta_agente / f"Perfil_{nombre_capitalizado}.md"
        if not perfil_md.exists():
            perfil_md.write_text(f"# Perfil de {nombre_capitalizado}\\n\\n{descripcion_rol}\\n\\n---\\n**Conexiones:** [[Reglas de la Tripulacion]] [[Bitacora]] [[Cerebro]]", encoding="utf-8")
            reporte["nodos_md_creados"] += 1
            
        # 3. Actualizar .env
        env_file = raiz_sistema / ".env"
        if env_file.exists():
            env_content = env_file.read_text(encoding="utf-8")
            if f"NVIDIA_API_KEY_{nombre_capitalizado.upper()}" not in env_content:
                nuevas_vars = f"\\n# Credenciales para {nombre_capitalizado}\\nNVIDIA_API_KEY_{nombre_capitalizado.upper()}=\\nMODEL_{nombre_capitalizado.upper()}_1=meta/llama-3.1-70b-instruct\\n"
                env_file.write_text(env_content + nuevas_vars, encoding="utf-8")
                reporte["env_actualizado"] = True
                
    except Exception as e:
        reporte["errores"].append(str(e))
        
    return reporte

# Alias
registrar_nuevo_agente = registrar_nuevo_agente_luffy

if __name__ == "__main__":
    print(registrar_nuevo_agente_luffy("TestAgente", "Agente de prueba"))
