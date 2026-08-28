import os
import sys
import json
from pathlib import Path

APP_ROOT = Path(r"C:\Users\admin\Documents\Agentes")
LUFFY_DIR = APP_ROOT / "Luffy"
SKILLS_DIR = LUFFY_DIR / "skills"

if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

try:
    from skill_memoria_vectorial import _get_collection
except ImportError:
    print("[Sync] Error: No se pudo importar skill_memoria_vectorial.")
    _get_collection = None

def asegurar_nota_obsidian(ruta_md: Path, titulo: str, contenido: str, enlaces: list, sobreescribir: bool = False):
    ruta_md.parent.mkdir(parents=True, exist_ok=True)
    links_str = " ".join([f"[[{link}]]" for link in enlaces])
    texto_final = f"# {titulo}\n\n{contenido}\n\n---\n**Conexiones:** {links_str}\n"
    
    if not ruta_md.exists() or sobreescribir:
        ruta_md.write_text(texto_final, encoding="utf-8")
        print(f"[Obsidian] Nodo escrito: {ruta_md.name}")
    return ruta_md

def sincronizar_conocimiento():
    print("Iniciando Limpieza y Sincronización del Cerebro...")
    
    # LIMPIEZA PREVIA: (Eliminado para no destruir el contenido generado por los LLMs)

    if not _get_collection:
        return

    collection = _get_collection()
    documentos_rag = []
    metadatos_rag = []
    ids_rag = []

    def agregar_al_rag(doc_id, texto, metadata):
        documentos_rag.append(texto)
        metadatos_rag.append(metadata)
        ids_rag.append(doc_id)

    agentes_conocidos = ["Luffy", "Zoro", "Nami", "Robin", "Sanji", "Chopper", "Franky", "Brook", "Jinbe"]
    for agente in agentes_conocidos:
        agente_dir = APP_ROOT / agente
        
        # Soportar tanto _agents como .agents
        perfil_json = agente_dir / "_agents" / f"{agente.lower()}_perfil.json"
        carpeta_skills_agy = agente_dir / "_agents" / "skills"
        
        if not perfil_json.exists():
            perfil_json = agente_dir / ".agents" / f"{agente.lower()}_perfil.json"
            carpeta_skills_agy = agente_dir / ".agents" / "skills"
            
        if perfil_json.exists():
            try:
                datos = json.loads(perfil_json.read_text(encoding="utf-8"))
                desc = datos.get("presentacion", f"Perfil base de {agente}")
                
                ruta_md = agente_dir / f"Perfil_{agente}.md"
                # Conexiones centrales: Atraen a los agentes al medio
                enlaces = ["Reglas de la Tripulacion", "Bitacora", "Cerebro"]
                
                # 1. Skills clásicas
                carpeta_skills_py = agente_dir / "skills"
                if carpeta_skills_py.exists():
                    for py_file in carpeta_skills_py.glob("skill_*.py"):
                        nombre_skill = py_file.stem
                        
                        nombre_nodo_skill = nombre_skill.title()
                        if not nombre_nodo_skill.endswith(f"_{agente}") and not nombre_nodo_skill.endswith(agente.title()):
                            nombre_nodo_skill += f"_{agente}"
                            
                        enlaces.append(nombre_nodo_skill)
                        
                        skill_md = carpeta_skills_py / f"{nombre_nodo_skill}.md"
                        
                        # Solo crear el archivo si no existe, si ya existe, el barrido de huérfanos le agregará las conexiones
                        if not skill_md.exists():
                            desc_skill = f"Herramienta/Habilidad: {nombre_skill}. Implementada en Python por {agente}."
                            asegurar_nota_obsidian(skill_md, f"Habilidad: {nombre_skill}", desc_skill, [f"Perfil_{agente}"], sobreescribir=False)
                        
                        try:
                            # Leer el contenido real del archivo para el RAG en lugar de usar una descripción genérica
                            contenido_real = skill_md.read_text(encoding="utf-8")
                        except Exception:
                            contenido_real = f"Habilidad {nombre_skill} de {agente}"
                            
                        agregar_al_rag(
                            f"SKILL-{agente.upper()}-{nombre_skill.upper()}",
                            contenido_real,
                            {"tipo": "habilidad", "agente": agente, "ruta": str(skill_md)}
                        )
                        
                # 2. Skills de Antigravity
                if carpeta_skills_agy.exists():
                    for agy_skill in carpeta_skills_agy.iterdir():
                        if agy_skill.is_dir():
                            nombre_nodo_skill = f"Skill_{agy_skill.name.title()}"
                            if not nombre_nodo_skill.endswith(f"_{agente}") and not nombre_nodo_skill.endswith(agente.title()):
                                nombre_nodo_skill += f"_{agente}"
                                
                            enlaces.append(nombre_nodo_skill)
                            
                            skill_md = carpeta_skills_agy / agy_skill.name / f"{nombre_nodo_skill}.md"
                            
                            if not skill_md.exists():
                                desc_skill_agy = f"Habilidad del sistema Antigravity: {agy_skill.name} para {agente}."
                                asegurar_nota_obsidian(skill_md, f"Habilidad: {agy_skill.name}", desc_skill_agy, [f"Perfil_{agente}"], sobreescribir=False)
                            
                            try:
                                contenido_real = skill_md.read_text(encoding="utf-8")
                            except Exception:
                                contenido_real = f"Habilidad Antigravity {agy_skill.name} de {agente}"
                                
                            agregar_al_rag(
                                f"SKILL-AGY-{agente.upper()}-{agy_skill.name.upper()}",
                                contenido_real,
                                {"tipo": "habilidad", "agente": agente, "ruta": str(skill_md)}
                            )
                
                asegurar_nota_obsidian(ruta_md, f"Perfil de {agente}", desc, enlaces, sobreescribir=True)
                agregar_al_rag(
                    f"AGENTE-{agente.upper()}",
                    f"Identidad de {agente}:\n{desc}",
                    {"tipo": "perfil", "agente": agente, "ruta": str(ruta_md)}
                )

                # 3. BARRIDO DE ARCHIVOS HUÉRFANOS DEL AGENTE
                directorios_a_barrer = [agente_dir]
                
                # Mapeo de carpetas de trabajo por agente
                mapa_carpetas = {
                    "Luffy": "memoria",
                    "Zoro": "proyectos",
                    "Nami": "informes",
                    "Robin": "reportes",
                    "Sanji": "documentos_sanji"
                }
                carpeta_trabajo = mapa_carpetas.get(agente, "proyectos")
                
                # Si el agente es Luffy (Capitán), él hereda la responsabilidad de las carpetas globales del sistema
                if agente == "Luffy":
                    directorios_a_barrer.extend([
                        APP_ROOT / "protocolo",
                        APP_ROOT / "sistema",
                        APP_ROOT / "memoria",
                        APP_ROOT / "Archivos_temporales",
                        APP_ROOT / "contexto"
                    ])
                    # También los archivos sueltos en la raíz (Bitacora, Cerebro, etc.) excluyendo los centrales absolutos
                    for archivo_raiz in APP_ROOT.glob("*.md"):
                        if archivo_raiz.name in ["Hub_Central.md", "Bitacora.md", "Reglas de la Tripulacion.md", "Cerebro.md"]: continue
                        if archivo_raiz.is_file():
                            try:
                                contenido_md = archivo_raiz.read_text(encoding="utf-8")
                                # El usuario instruyó: "todo lo que tenga que ver con el sistema va anexado al perfil de luffy"
                                link_destino = f"[[Perfil_{agente}]]"
                                if link_destino not in contenido_md:
                                    contenido_md += f"\n\n---\n**Pertenece a:** {link_destino}\n"
                                    archivo_raiz.write_text(contenido_md, encoding="utf-8")
                                    print(f"[Obsidian] Nodo global atado a carpeta de Luffy: {archivo_raiz.name}")
                            except Exception:
                                pass

                for directorio in directorios_a_barrer:
                    if not directorio.exists(): continue
                    for md_file in directorio.rglob("*.md"):
                        if md_file.name == ruta_md.name: continue
                        if md_file.name in ["Hub_Central.md", "Bitacora.md", "Reglas de la Tripulacion.md", "Cerebro.md"]: continue
                        if md_file.name.startswith("Skill_") and md_file.parent.name in ["skills", agente]: continue
                        
                        try:
                            contenido_md = md_file.read_text(encoding="utf-8")
                            
                            # Si es un SKILL.md de Antigravity, sí va al perfil. 
                            if md_file.name == "SKILL.md":
                                link_destino = f"[[Perfil_{agente}]]"
                            elif agente == "Luffy":
                                if "memoria" in md_file.parts:
                                    link_destino = "[[memoria]]"
                                elif "Archivos_temporales" in md_file.parts:
                                    link_destino = "[[archivos_temporales]]"
                                elif "contexto" in md_file.parts:
                                    link_destino = "[[contexto]]"
                                else:
                                    link_destino = "[[Perfil_Luffy]]"
                            else:
                                link_destino = f"[[{carpeta_trabajo}]]"
                                
                            if link_destino not in contenido_md:
                                contenido_md += f"\n\n---\n**Pertenece a:** {link_destino}\n"
                                md_file.write_text(contenido_md, encoding="utf-8")
                                print(f"[Obsidian] Nodo atado: {md_file.name} -> {link_destino}")
                        except Exception as e:
                            pass

            except Exception as e:
                print(f"[Sync] Error procesando a {agente}: {e}")

    # Reglas
    reglas_dir = APP_ROOT / "protocolo"
    reglas_md = reglas_dir / "Reglas de la Tripulacion.md"
    if reglas_md.exists():
        agregar_al_rag("PROTOCOLO-REGLAS", reglas_md.read_text(encoding="utf-8"), {"tipo": "regla_global", "ruta": str(reglas_md)})

    agents_md = LUFFY_DIR / ".agents" / "AGENTS.md"
    if agents_md.exists():
        agregar_al_rag("PROTOCOLO-LUFFY", agents_md.read_text(encoding="utf-8"), {"tipo": "regla_luffy", "ruta": str(agents_md)})

    # Interconectar nodos centrales (Trinidad: Bitacora, Cerebro, Reglas)
    nodos_centrales = ["Bitacora.md", "Cerebro.md", "protocolo/Reglas de la Tripulacion.md"]
    for nodo_str in nodos_centrales:
        nodo_path = APP_ROOT / nodo_str
        if nodo_path.exists():
            try:
                cont = nodo_path.read_text(encoding="utf-8")
                links_inyectar = []
                for otro in ["Bitacora", "Cerebro", "Reglas de la Tripulacion"]:
                    if otro not in nodo_path.name and f"[[{otro}]]" not in cont:
                        links_inyectar.append(f"[[{otro}]]")
                
                if links_inyectar:
                    str_links = " ".join(links_inyectar)
                    cont += f"\n\n---\n**Conexiones:** {str_links}\n"
                    nodo_path.write_text(cont, encoding="utf-8")
            except Exception:
                pass

    # RAG Upsert
    if documentos_rag:
        try:
            collection.upsert(documents=documentos_rag, metadatas=metadatos_rag, ids=ids_rag)
            print(f"[RAG] Sincronización exitosa: {len(documentos_rag)} nodos.")
        except Exception as e:
            pass

    print("[Obsidian] Estructura orgánica completada con éxito.")

if __name__ == "__main__":
    sincronizar_conocimiento()
