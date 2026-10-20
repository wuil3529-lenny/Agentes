"""
identidad_agentes.py — Cargador Dinámico de Identidades de Agentes
==================================================================
Lee en tiempo real los archivos Markdown (_agents/agente.md) de cada habitación
para extraer:
  - Identidad Canónica del Sistema (ej: Subagente_Diseno)
  - Identidad Asignada por el Usuario (ej: Nami, Pedro Pérez, etc.)
  - Rol / Título profesional
  - Aliases para enrutamiento en Pizarra y Consola
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, Optional

_APP_ROOT = Path(__file__).resolve().parents[1]

SLOTS_DEFECTO = [
    {
        "slot": "luffy",
        "carpeta": "Agente_Orquestador",
        "canonico": "Agente_Orquestador",
        "nombre_defecto": "Luffy",
        "rol_defecto": "Director de Operaciones y Supervisor Supremo",
        "sublabel_defecto": "DeepSeek V3 • Líder",
        "aliases_base": ["luffy", "agente_orquestador", "orquestador", "director", "capitan", "lider"]
    },
    {
        "slot": "zoro",
        "carpeta": "Subagente_Desarrollo",
        "canonico": "Subagente_Desarrollo",
        "nombre_defecto": "Zoro",
        "rol_defecto": "Ingeniero de Software Full-Stack y Orquestación",
        "sublabel_defecto": "DeepSeek V3 • Código",
        "aliases_base": ["zoro", "subagente_desarrollo", "desarrollo", "dev", "programador", "software"]
    },
    {
        "slot": "nami",
        "carpeta": "Subagente_Diseno",
        "canonico": "Subagente_Diseno",
        "nombre_defecto": "Nami",
        "rol_defecto": "Directora Creativa, Navegante de Interfaces y Estratega Visual",
        "sublabel_defecto": "DeepSeek V3 • Diseño",
        "aliases_base": ["nami", "subagente_diseno", "diseno", "diseño", "creativo", "ux", "ui"]
    },
    {
        "slot": "robin",
        "carpeta": "Subagente_Ciberseguridad",
        "canonico": "Subagente_Ciberseguridad",
        "nombre_defecto": "Robin",
        "rol_defecto": "Oficial de Seguridad Defensiva y Auditoría",
        "sublabel_defecto": "DeepSeek V3 • Auditoría",
        "aliases_base": ["robin", "subagente_ciberseguridad", "ciberseguridad", "seguridad", "auditor", "security"]
    },
    {
        "slot": "sanji",
        "carpeta": "Subagente_Asistencia",
        "canonico": "Subagente_Asistencia",
        "nombre_defecto": "Sanji",
        "rol_defecto": "Gestor Ejecutivo y Automatización de Workspace",
        "sublabel_defecto": "DeepSeek V3 • Asistencia",
        "aliases_base": ["sanji", "subagente_asistencia", "asistencia", "asistente", "workspace", "ejecutivo"]
    }
]

def normalizar_texto(texto: str) -> str:
    """Elimina tildes y caracteres especiales para comparaciones insensibles."""
    if not texto:
        return ""
    texto_nfkd = unicodedata.normalize('NFKD', str(texto).lower().strip())
    return "".join(c for c in texto_nfkd if not unicodedata.combining(c))

def obtener_identidades_agentes(directorio_raiz: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Lee dinámicamente _agents/agente.md para cada agente y extrae su identidad asignada.
    Retorna un diccionario indexado por slot ('luffy', 'zoro', 'nami', 'robin', 'sanji').
    """
    raiz = directorio_raiz or _APP_ROOT
    resultado = {}

    for info in SLOTS_DEFECTO:
        slot = info["slot"]
        carpeta = info["carpeta"]
        canonico = info["canonico"]
        dir_agente = raiz / carpeta
        
        md_path = dir_agente / "_agents" / "agente.md"
        if not md_path.exists():
            md_path = dir_agente / ".agents" / "agente.md"
            
        nombre_asignado = info["nombre_defecto"]
        rol = info["rol_defecto"]
        sublabel = info["sublabel_defecto"]
        archivo_encontrado = str(md_path) if md_path.exists() else ""
        
        if md_path.exists():
            try:
                content = md_path.read_text(encoding="utf-8")
                
                # Extraer Identidad Canónica si está definida
                m_canon = re.search(r"\*\*Identidad Can[óo]nica del Sistema:\*\*\s*[`'\"]?([A-Za-z0-9_]+)[`'\"]?", content)
                if m_canon:
                    canonico = m_canon.group(1).strip()
                    
                # Extraer Identidad Asignada por el Usuario
                m_asig = re.search(r"\*\*Identidad Asignada por el Usuario:\*\*\s*[`'\"]?([^`'\"\*\n\r\(]+)[`'\"]?", content)
                if m_asig:
                    val = m_asig.group(1).strip()
                    if val:
                        nombre_asignado = val
                        
                # Extraer Rol / Título de la línea 1
                m_title = re.search(r"^#\s*([^—\n\r]+?)(?:\s*—\s*([^\n\r]+))?$", content, re.MULTILINE)
                if m_title and m_title.group(2):
                    rol = m_title.group(2).strip()
                elif m_title and m_title.group(1):
                    rol = m_title.group(1).strip()
                    
            except Exception as e:
                print(f"[Identidad] Error leyendo {md_path}: {e}")
                
        # Construir lista dinámica de aliases
        aliases = list(info["aliases_base"])
        if nombre_asignado:
            nombre_clean = nombre_asignado.strip()
            norm_asig = normalizar_texto(nombre_clean)
            if norm_asig and norm_asig not in aliases:
                aliases.append(norm_asig)
            # Agregar palabras individuales si es un nombre compuesto (ej. "Pedro Pérez" -> "pedro", "perez")
            for parte in norm_asig.split():
                if len(parte) >= 3 and parte not in aliases:
                    aliases.append(parte)

        if canonico.lower() not in aliases:
            aliases.append(canonico.lower())
            
        resultado[slot] = {
            "slot": slot,
            "carpeta": carpeta,
            "canonico": canonico,
            "nombre_asignado": nombre_asignado,
            "nombre_display": nombre_asignado if nombre_asignado else canonico,
            "rol": rol,
            "sublabel": sublabel,
            "archivo_md": archivo_encontrado,
            "aliases": aliases
        }

    return resultado

def mapear_responsable_a_canonico(texto_responsable: str, identidades: Optional[dict] = None) -> str:
    """
    Recibe el campo 'responsable' de un ticket o mensaje (ej: 'Pedro Pérez', 'Pedro', 'Nami', 'Zoro', 'Subagente_Diseno')
    y retorna el nombre canónico correspondiente (ej: 'Subagente_Diseno').
    Si no encuentra coincidencia, devuelve 'Subagente_Desarrollo' por defecto seguro.
    """
    if not texto_responsable:
        return "Subagente_Desarrollo"
        
    ids = identidades or obtener_identidades_agentes()
    texto_norm = normalizar_texto(texto_responsable)
    
    # 1. Comprobación exacta por nombre asignado o canónico
    for slot, data in ids.items():
        if normalizar_texto(data["nombre_asignado"]) == texto_norm:
            return data["canonico"]
        if normalizar_texto(data["canonico"]) == texto_norm:
            return data["canonico"]
            
    # 2. Comprobación por coincidencia en aliases
    for slot, data in ids.items():
        for al in data["aliases"]:
            # Verificar si el alias está como palabra completa en el texto
            patron = rf"\b{re.escape(al)}\b"
            if re.search(patron, texto_norm):
                return data["canonico"]
                
    # 3. Fallback de contingencia
    return "Subagente_Desarrollo"

def obtener_nombre_display(identificador: str, identidades: Optional[dict] = None) -> str:
    """
    Devuelve el nombre visible asignado (ej: 'Pedro Pérez') a partir del nombre canónico o slot.
    """
    ids = identidades or obtener_identidades_agentes()
    id_norm = normalizar_texto(identificador)
    
    for slot, data in ids.items():
        if slot == id_norm or normalizar_texto(data["canonico"]) == id_norm or normalizar_texto(data["nombre_asignado"]) == id_norm:
            return data["nombre_display"]
            
    return identificador

def actualizar_nombre_asignado_en_md(slot_o_canonico: str, nuevo_nombre: str, directorio_raiz: Optional[Path] = None) -> bool:
    """
    Actualiza el archivo _agents/agente.md del agente indicado con el nuevo nombre asignado.
    """
    raiz = directorio_raiz or _APP_ROOT
    ids = obtener_identidades_agentes(raiz)
    
    target_data = None
    id_norm = normalizar_texto(slot_o_canonico)
    for slot, data in ids.items():
        if slot == id_norm or normalizar_texto(data["canonico"]) == id_norm:
            target_data = data
            break
            
    if not target_data or not target_data["archivo_md"]:
        return False
        
    md_file = Path(target_data["archivo_md"])
    if not md_file.exists():
        return False
        
    try:
        content = md_file.read_text(encoding="utf-8")
        patron = r"(\*\*Identidad Asignada por el Usuario:\*\*\s*[`'\"]?)([^`'\"\*\n\r\(]+)([`'\"]?)"
        
        def _reemplazo(m):
            return f"**Identidad Asignada por el Usuario:** `{nuevo_nombre.strip()}`"
            
        if re.search(patron, content):
            nuevo_content = re.sub(patron, _reemplazo, content, count=1)
        else:
            # Si no existía la clave, insertarla bajo la sección 1
            seccion_1 = "## 1. Identidad Dual y Regla de Interacción con el Usuario"
            if seccion_1 in content:
                bloque_nuevo = f"{seccion_1}\n- **Identidad Canónica del Sistema:** `{target_data['canonico']}`\n- **Identidad Asignada por el Usuario:** `{nuevo_nombre.strip()}`\n"
                nuevo_content = content.replace(seccion_1, bloque_nuevo)
            else:
                nuevo_content = content
                
        md_file.write_text(nuevo_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[Identidad] Error actualizando nombre en {md_file}: {e}")
        return False
