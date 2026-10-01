import os
import sys
import json
import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
LUFFY_DIR = APP_ROOT / "Agente_Orquestador"
SKILLS_DIR = LUFFY_DIR / "skills"

if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

try:
    from memoria_vectorial.skill_memoria_vectorial import _get_collection
except Exception:
    _get_collection = None

def asegurar_nota_obsidian(ruta_md: Path, titulo: str, contenido: str, enlaces: list, sobreescribir: bool = False):
    ruta_md.parent.mkdir(parents=True, exist_ok=True)
    links_str = " ".join([f"[[{link}]]" for link in enlaces])
    texto_final = f"# {titulo}\n\n{contenido}\n\n---\n**Conexiones:** {links_str}\n"
    
    if not ruta_md.exists() or sobreescribir:
        ruta_md.write_text(texto_final, encoding="utf-8")
        print(f"[Obsidian] Nodo escrito: {ruta_md.name}")
    return ruta_md

def sanear_enlace_exclusivo(md_file: Path, link_destino: str):
    """
    Garantiza que el archivo tenga ÚNICAMENTE la conexión hacia link_destino.
    Elimina cualquier otra conexión (Nexo, Conexiones Core, Conexiones, Pertenece a anteriores).
    """
    try:
        cont = md_file.read_text(encoding="utf-8")
        
        # Eliminar cualquier bloque o línea de Nexo, Conexiones Core, Conexiones o Pertenece a
        cont_limpio = re.sub(r"(?im)^\s*>\s*🔗?\s*\*\*Nexo:\*\*.*$", "", cont)
        cont_limpio = re.sub(r"(?im)^\s*>\s*\*\*Conexiones Core:\*\*.*$", "", cont_limpio)
        cont_limpio = re.sub(r"(?im)^\s*\*\*Conexiones:\*\*.*$", "", cont_limpio)
        cont_limpio = re.sub(r"(?im)^\s*\*\*Pertenece a:\*\*.*$", "", cont_limpio)
        
        # Limpiar separadores --- residuales al final del archivo
        cont_limpio = cont_limpio.strip()
        while cont_limpio.endswith("---"):
            cont_limpio = cont_limpio[:-3].strip()
            
        cont_final = cont_limpio + f"\n\n---\n**Pertenece a:** {link_destino}\n"
        
        if cont_final != cont:
            md_file.write_text(cont_final, encoding="utf-8")
            print(f"[Obsidian] Conexión exclusiva asegurada: {md_file.name} -> {link_destino}")
    except Exception as e:
        print(f"[Sync] Error saneando enlace exclusivo en {md_file.name}: {e}")

def sincronizar_conocimiento():
    print("Iniciando Limpieza y Sincronización del Cerebro...")
    
    # Limpieza preventiva de carpetas obsoletas (anti-duplicados)
    mc_dir = APP_ROOT / "memoria_compartida"
    if mc_dir.exists():
        import shutil
        shutil.rmtree(mc_dir, ignore_errors=True)
        print("[Sync] Carpeta obsoleta memoria_compartida eliminada.")

    collection = None
    if os.getenv("ENABLE_RAG_SYNC", "0") in ("1", "true") and _get_collection:
        try:
            collection = _get_collection()
        except Exception as e_col:
            print(f"[Sync] Aviso: Colección vectorial no disponible ({e_col}). Continuando con sincronización de Obsidian...")
            collection = None
    documentos_rag = []
    metadatos_rag = []
    ids_rag = []

    def agregar_al_rag(doc_id, texto, metadata):
        documentos_rag.append(texto)
        metadatos_rag.append(metadata)
        ids_rag.append(doc_id)

    agentes_conocidos = [
        "Agente_Orquestador",
        "Subagente_Desarrollo",
        "Subagente_Diseno",
        "Subagente_Ciberseguridad",
        "Subagente_Asistencia"
    ]
    for agente in agentes_conocidos:
        agente_dir = APP_ROOT / agente
        
        # Soportar tanto _agents como .agents y nombres de perfiles
        candidatos_perfil = [
            agente_dir / "_agents" / f"{agente.lower()}_perfil.json",
            agente_dir / ".agents" / f"{agente.lower()}_perfil.json"
        ]
        # Búsqueda por comodín en subcarpetas de agentes
        for subc in ["_agents", ".agents"]:
            d = agente_dir / subc
            if d.exists():
                for f_p in d.glob("*_perfil.json"):
                    if f_p not in candidatos_perfil:
                        candidatos_perfil.append(f_p)
                        
        perfil_json = next((p for p in candidatos_perfil if p.exists()), None)
        carpeta_skills_agy = (agente_dir / "_agents" / "skills") if (agente_dir / "_agents" / "skills").exists() else (agente_dir / ".agents" / "skills")
        
        if perfil_json and perfil_json.exists():
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
                    "Agente_Orquestador": "memoria",
                    "Subagente_Desarrollo": "proyectos",
                    "Subagente_Diseno": "informes",
                    "Subagente_Ciberseguridad": "reportes",
                    "Subagente_Asistencia": "documentos_sanji",
                    # Compatibilidad
                    "Luffy": "memoria",
                    "Zoro": "proyectos",
                    "Nami": "informes",
                    "Robin": "reportes",
                    "Sanji": "documentos_sanji"
                }
                carpeta_trabajo = mapa_carpetas.get(agente, "proyectos")
                
                # Si el agente es el Orquestador (Director), hereda la responsabilidad de las carpetas globales
                if agente in ["Agente_Orquestador", "Luffy"]:
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
                                link_destino = f"[[Perfil_{agente}]]"
                                if link_destino not in contenido_md:
                                    contenido_md += f"\n\n---\n**Pertenece a:** {link_destino}\n"
                                    archivo_raiz.write_text(contenido_md, encoding="utf-8")
                                    print(f"[Obsidian] Nodo global atado a perfil de {agente}: {archivo_raiz.name}")
                            except Exception:
                                pass

                for directorio in directorios_a_barrer:
                    if not directorio.exists(): continue
                    for md_file in directorio.rglob("*.md"):
                        if md_file.name == ruta_md.name: continue
                        if md_file.name in ["Hub_Central.md", "Bitacora.md", "Reglas de la Tripulacion.md", "Cerebro.md"]: continue
                        if md_file.name.startswith("Skill_") and md_file.parent.name in ["skills", agente]: continue
                        
                        try:
                            # 1. Archivos HUB de cada carpeta de trabajo (conectan directamente a su agente o pilares)
                            if md_file.name == "memoria.md":
                                cont = md_file.read_text(encoding="utf-8")
                                cont_limpio = re.sub(r"(?im)^\s*(\*\*Conexiones:\*\*|\*\*Pertenece a:\*\*|> 🔗 \*\*Nexo:\*\*).*$", "", cont).strip()
                                while cont_limpio.endswith("---"):
                                    cont_limpio = cont_limpio[:-3].strip()
                                cont_final = cont_limpio + "\n\n---\n**Conexiones:** [[Reglas de la Tripulacion]] [[Bitacora]] [[Cerebro]]\n"
                                if cont_final != cont:
                                    md_file.write_text(cont_final, encoding="utf-8")
                                    print(f"[Obsidian] Nodo memoria conectado a los 3 pilares: {md_file.name}")
                                continue
                            elif md_file.name == "reportes.md":
                                link_destino = "[[Perfil_Subagente_Ciberseguridad]]"
                            elif md_file.name == "proyectos.md":
                                link_destino = "[[Perfil_Subagente_Desarrollo]]"
                            elif md_file.name == "informes.md":
                                link_destino = "[[Perfil_Subagente_Diseno]]"
                            elif md_file.name in ["documentos_sanji.md", "documentos_asistencia.md"]:
                                link_destino = "[[Perfil_Subagente_Asistencia]]"
                            # 2. Archivos contenidos dentro de cada carpeta (conectan a su nodo carpeta)
                            elif "reportes" in md_file.parts:
                                link_destino = "[[reportes]]"
                            elif "memoria" in md_file.parts:
                                link_destino = "[[memoria]]"
                            elif md_file.name == "SKILL.md":
                                link_destino = f"[[Perfil_{agente}]]"
                            elif agente in ["Agente_Orquestador", "Luffy"]:
                                if "Archivos_temporales" in md_file.parts:
                                    link_destino = "[[archivos_temporales]]"
                                elif "contexto" in md_file.parts:
                                    link_destino = "[[contexto]]"
                                else:
                                    link_destino = "[[Perfil_Agente_Orquestador]]"
                            else:
                                link_destino = f"[[{carpeta_trabajo}]]"
                                
                            sanear_enlace_exclusivo(md_file, link_destino)
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
    if not agents_md.exists():
        agents_md = LUFFY_DIR / "_agents" / "AGENTS.md"
    if agents_md.exists():
        agregar_al_rag("PROTOCOLO-ORQUESTADOR", agents_md.read_text(encoding="utf-8"), {"tipo": "regla_orquestador", "ruta": str(agents_md)})

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
    if collection and documentos_rag:
        try:
            collection.upsert(documents=documentos_rag, metadatas=metadatos_rag, ids=ids_rag)
            print(f"[RAG] Sincronización exitosa: {len(documentos_rag)} nodos.")
        except Exception as e:
            pass

    print("[Obsidian] Estructura orgánica completada con éxito.")

if __name__ == "__main__":
    sincronizar_conocimiento()
