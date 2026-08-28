"""
memory.py — Motor de Memoria (3 Pilares Rediseñados)
======================================================
Gestiona la memoria persistente que todos los agentes comparten.

NUEVO FLUJO ARQUITECTÓNICO:
  1. Canal JSON  → Comunicación LIBRE entre agentes (preguntas, coordinación, info).
                   NO se usa para delegar tareas operativas.
  2. Bitácora.md → TABLERO DE TAREAS. Luffy (o Robin) crean tickets aquí.
                   Los agentes leen SUS tickets PENDIENTES y los actualizan.
  3. Cerebro.md  → Memoria a largo plazo. Solo se escribe cuando una tarea
                   está COMPLETADA. Genera automáticamente el archivo en /memoria.
"""
import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[1]

import os
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

_CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))

# ─── Cargar variables de entorno ──────────────
ROOT_ENV_PATH = _APP_ROOT / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)

SHARED_MEMORY_PATH = Path(
    os.getenv("SHARED_MEMORY_PATH", str(_APP_ROOT / "memoria_compartida"))
)
SHARED_MEMORY_PATH.mkdir(parents=True, exist_ok=True)

# ─── Archivos de memoria (JSON - Solo Canal) ──────────────────────────────────
CANAL_FILE    = _APP_ROOT / "canal_comunicacion.json"
CANAL_USUARIO_FILE = _APP_ROOT / "canal_usuario.json"

# ─── Archivos Obsidian (Living Vault .md) ──────────────────────────────────────
MEMORIA_MD_PATH = _APP_ROOT / "memoria"
MEMORIA_MD_PATH.mkdir(parents=True, exist_ok=True)

CANAL_USUARIO_MD = _APP_ROOT / "CanalUsuario.md"
BITACORA_MD = _APP_ROOT / "Bitacora.md"
CEREBRO_MD  = _APP_ROOT / "Cerebro.md"
ARCHIVOS_TEMPORALES_PATH = _APP_ROOT / "Archivos_temporales"
LUFFY_PERFIL_FILE = _APP_ROOT / "Luffy" / ".agents" / "luffy_perfil.json"

# ══════════════════════════════════════════════════════════════════════════════
# 1. PILAR CANAL (Comunicación y Errores - JSON)
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_canal(canal_tipo: str = "interno") -> dict:
    if canal_tipo == "interno":
        return {"mensajes": []}  # Canal interno deshabilitado por el usuario
    archivo = CANAL_USUARIO_FILE
    if archivo.exists():
        try:
            return json.loads(archivo.read_text(encoding="utf-8"))
        except:
            pass
    return {"mensajes": []}

def _guardar_canal(canal: dict, canal_tipo: str = "interno") -> None:
    if canal_tipo == "interno":
        return  # No escribir nada en el canal interno
    archivo = CANAL_USUARIO_FILE
    archivo.write_text(json.dumps(canal, ensure_ascii=False, indent=2), encoding="utf-8")

def publicar_mensaje(de: str, para: str, tipo: str, contenido: dict, canal_tipo: str = "interno") -> str:
    canal = _cargar_canal(canal_tipo)
    mensajes = canal.get("mensajes", [])
    
    msg_id = f"msg-{len(mensajes) + 1:03d}"
    
    nuevo_mensaje = {
        "id": msg_id,
        "timestamp": datetime.now().isoformat(),
        "de": de,
        "para": para,
        "tipo": tipo,
        "estado": "enviado",
        "leido_por": [de],
        "contenido": contenido,
    }
    mensajes.append(nuevo_mensaje)
    canal["mensajes"] = mensajes
    _guardar_canal(canal, canal_tipo)

    return msg_id

def leer_mensajes(agente: str) -> list[dict]:
    def leer_de_canal(tipo_c):
        canal = _cargar_canal(tipo_c)
        mensajes = canal.get("mensajes", [])
        resultado = []
        for msg in mensajes:
            para_str = str(msg.get("para", "")).lower()
            if para_str in (agente.lower(), "todos", "tripulación", "tripulacion") and agente not in msg.get("leido_por", []):
                msg["leido_por"].append(agente)
                resultado.append(msg)
                
        if resultado:
            canal["mensajes"] = mensajes
            _guardar_canal(canal, tipo_c)
        return resultado

    mensajes_finales = leer_de_canal("interno")
    if agente == "Luffy":
        mensajes_finales.extend(leer_de_canal("usuario"))
        
    return mensajes_finales

# ══════════════════════════════════════════════════════════════════════════════
# 2. PILAR BITÁCORA (Corto Plazo / Tareas - MD Only)
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_bitacora() -> list:
    if not BITACORA_MD.exists():
        return []
    try:
        texto_md = BITACORA_MD.read_text(encoding="utf-8")
        # Regex multiline para extraer entradas que pueden abarcar varios párrafos
        # Patrón: - **[TIMESTAMP] [ESTADO] AGENTE:** ENTRADA
        matches = re.finditer(r"^- \*\*\[(.*?)\] \[(.*?)\] (.*?):\*\* (.*?)(?=\n- \*\*\[|$)", texto_md, re.MULTILINE | re.DOTALL)
        bitacora = []
        for match in matches:
            bitacora.append({
                "timestamp": match.group(1).strip(),
                "estado": match.group(2).strip(),
                "agente": match.group(3).strip(),
                "entrada": match.group(4).strip()
            })
        return bitacora
    except Exception:
        return []

def registrar_bitacora(agente: str, entrada: str, estado: str = "INFO") -> None:
    timestamp = datetime.now().isoformat()
    
    if not BITACORA_MD.exists():
        # Inicializar con mapa
        mapa_rutas = """# 📓 Bitácora (Tablero de Tareas)

> [!NOTE] 🗺️ Mapa de Rutas del Ecosistema
> - **Raíz del Sistema:** `C:\\Users\\admin\\Documents\\Agentes\\`
>   - **Agentes (Espacios Locales):** Aquí vive cada agente. Dentro de sus carpetas van sus skills (habilidades) locales y los códigos o proyectos que realice cada uno.
>     - **Luffy:** `C:\\Users\\admin\\Documents\\Agentes\\Luffy\\`
>       - `skills\\`: Scripts y herramientas de Luffy (ej. `skill_limpiar_habitacion.py`).
>       - `data\\`: Archivos de estado y reportes (`.txt`, `.csv`).
>       - `[raíz]`: Scripts principales de Luffy y credenciales.
>     - **Zoro:** `C:\\Users\\admin\\Documents\\Agentes\\Zoro\\`
>     - **Robin:** `C:\\Users\\admin\\Documents\\Agentes\\Robin\\`
>     - **Nami:** `C:\\Users\\admin\\Documents\\Agentes\\Nami\\`
>     - **Sanji:** `C:\\Users\\admin\\Documents\\Agentes\\Sanji\\`
>   - **Archivos Temporales:** `C:\\Users\\admin\\Documents\\Agentes\\Archivos_temporales\\` (Cualquier archivo temporal que pueda ser borrado y no forme parte ni de skins, ni habilidades, ni funciones de Luffy, Zoro, Nami, Robin y Sanji, debe guardarse aquí).
>   - **Carpetas de Configuración y Documentación en Raíz:**
>     - `protocolo\\`: Protocolos de comportamiento y estructura de la tripulación (`Reglas de la Tripulacion.md`).
>     - `sistema\\`: Documentación arquitectónica de Antigravity.
>     - `perfiles\\`: Perfiles detallados de cada agente y el del usuario (Wuilfredo).
>     - `recursos_externos\\`: Recursos, exports y plantillas externas.
>   - **Memoria Compartida:** `C:\\Users\\admin\\Documents\\Agentes\\memoria_compartida\\`
>     - `memoria\\`: Archivos detallados del Cerebro a largo plazo (bóveda).
>   - **Archivos Base en Raíz:**
>     - `Bitacora.md`: Tablero de tareas. Luffy y Robin crean tickets aquí. Los agentes buscan sus tickets PENDIENTES.
>     - `Cerebro.md`: Registro de conocimiento a largo plazo (solo tareas COMPLETADAS).
>     - `canal_comunicacion.json`: Canal libre de comunicación entre agentes.
"""
        BITACORA_MD.write_text(mapa_rutas + "\n", encoding="utf-8")
        
    with open(BITACORA_MD, "a", encoding="utf-8") as f:
        f.write(f"\n- **[{timestamp[:19]}] [{estado}] {agente}:** {entrada}\n")


# ──────────────────────────────────────────────────────────────────────────────
# SISTEMA DE TICKETS (Bitácora como Tablero de Tareas)
# ──────────────────────────────────────────────────────────────────────────────
# Formato de ticket en Bitácora:
# - **[TIMESTAMP] [TICKET|PENDIENTE] Agente_Asignado:** ID_TICKET :: DESCRIPCION
# Al actualizarse:
# - **[TIMESTAMP] [COMPLETADO|EN_PROGRESO|CANCELADO] Agente_Asignado:** ID_TICKET :: DESCRIPCION
# ──────────────────────────────────────────────────────────────────────────────

import uuid as _uuid

def crear_ticket_bitacora(asignado_a: str, descripcion: str, creado_por: str = "Luffy") -> str:
    """
    Crea un ticket de tarea en la Bitácora con el nuevo formato Pizarra (Blackboard).
    """
    ticket_id = f"TKT-{str(_uuid.uuid4())[:8].upper()}"
    timestamp  = datetime.now().isoformat()[:19]
    
    # Construir el bloque multilínea exacto
    bloque_ticket = f"""
## {ticket_id}
- **Tarea:** {descripcion}
- **Responsable:** {asignado_a}
- **Estado:** PENDIENTE
- **Evidencia_Fisica:** N/A
- **Contexto:** Ticket creado inicialmente por {creado_por}.
- **Historial:**
  - [{creado_por} - {timestamp}]: Ticket generado y asignado a {asignado_a}.
"""
    if not BITACORA_MD.exists():
        # Escribir cabecera básica si no existe
        BITACORA_MD.write_text("# 📓 Bitácora (Tablero de Tareas)\n\n", encoding="utf-8")
        
    with open(BITACORA_MD, "a", encoding="utf-8") as f:
        f.write(bloque_ticket)
        
    return ticket_id


def leer_tickets_pendientes(agente: str) -> list:
    """
    [DEPRECADO EN FASE 3]
    La lectura de tickets ahora la realiza directamente base_listener.py (Orquestador).
    """
    print("[memory] advertencia: leer_tickets_pendientes() está deprecado en Fase 3.")
    return []


def actualizar_ticket_bitacora(ticket_id: str, agente: str, nuevo_estado: str, nota: str = "") -> bool:
    """
    [DEPRECADO EN FASE 3]
    La actualización la hacen los propios LLMs reescribiendo el bloque Markdown.
    """
    print("[memory] advertencia: actualizar_ticket_bitacora() está deprecado en Fase 3.")
    return False

# ══════════════════════════════════════════════════════════════════════════════
# 3. PILAR CEREBRO (Largo Plazo / Conocimiento - MD Only)
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_cerebro() -> list:
    if not CEREBRO_MD.exists():
        return []
    try:
        texto_md = CEREBRO_MD.read_text(encoding="utf-8")
        # Regex multiline: ### [ID] TEMA (por AGENTE)\nCONTENIDO\n*Archivo Detallado:* RUTA\n*Ruta Local:* RUTA\n---
        matches = re.finditer(r"^### (?:\[(\d+)\] )?(.*?) \(por (.*?)\)\n(.*?)(?:\n\*Archivo Detallado:\* `?(.*?)`?)?(?:\n\*Ruta Local:\* `?(.*?)`?)?(?=\n---|###|$)", texto_md, re.MULTILINE | re.DOTALL)
        cerebro = []
        for match in matches:
            cerebro.append({
                "id": match.group(1).strip() if match.group(1) else None,
                "tema": match.group(2).strip(),
                "agente": match.group(3).strip(),
                "contenido": match.group(4).strip(),
                "archivo_detallado": match.group(5).strip() if match.group(5) else None,
                "ruta_local": match.group(6).strip() if match.group(6) else None
            })
        return cerebro
    except Exception:
        return []

def guardar_cerebro(agente: str, tema: str, contenido: str, ruta_local: str = None) -> None:
    # --- 🛡️ FILTRO ANTI-BASURA ---
    tema_limpio = tema.strip()
    if not tema_limpio or tema_limpio in ["N/A", "Informar tarea completada al usuario", "Procesar mensajes entrantes Te"] or "N/A" in contenido:
        print(f"[Memoria] Se omitió guardar en el cerebro (contenido irrelevante): {tema_limpio}")
        return

    timestamp = datetime.now().isoformat()
    
    if not CEREBRO_MD.exists():
        CEREBRO_MD.write_text("# 🧠 Cerebro (Largo Plazo)\n\n", encoding="utf-8")
        
    # Identificar el ID
    max_id = -1
    for f_path in MEMORIA_MD_PATH.glob("*.md"):
        match = re.match(r"^(\d{2,})_", f_path.name)
        if match:
            max_id = max(max_id, int(match.group(1)))
    new_id = max_id + 1
    
    safe_tema = "".join([c if c.isalnum() else "_" for c in tema]).strip("_")
    md_filename = f"{new_id:02d}_{agente}_{safe_tema}.md"
    md_filepath = MEMORIA_MD_PATH / md_filename
    
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(CEREBRO_MD, "a", encoding="utf-8") as f:
        linea_indice = f"- **[{new_id:02d}]** | **Fecha:** {fecha_hora} | **Agente:** {agente} | **Descripción:** {tema} | **Ruta:** `C:\\Users\\admin\\Documents\\Agentes\\memoria\\{md_filename}`\n"
        f.write(linea_indice)
        
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(f"# Registro de Cerebro: {tema}\n\n")
        f.write(f"**Agente:** {agente}\n")
        f.write(f"**Fecha:** {timestamp}\n\n")
        f.write(f"## Contenido / Aprendizaje\n\n")
        f.write(f"{contenido}\n")
        if ruta_local:
            f.write(f"\n**Ruta Local Asociada:** `{ruta_local}`\n")
            
        # Conexiones Obsidian
        f.write("\n---\n")
        f.write("**Conexiones:** [[memoria]]\n")

    # --- 🧠 INTEGRACIÓN AUTOMÁTICA CON RAG (ChromaDB) ---
    try:
        import sys
        skills_path = _APP_ROOT / "Luffy" / "skills"
        if str(skills_path) not in sys.path:
            sys.path.insert(0, str(skills_path))
        from skill_memoria_vectorial import _get_collection
        
        collection = _get_collection()
        ticket_id_virt = f"TKT-MEM-{new_id:02d}"
        collection.add(
            documents=[contenido],
            metadatas=[{"ticket_id": ticket_id_virt, "descripcion": tema, "agente": agente}],
            ids=[ticket_id_virt]
        )
        print(f"[Memoria RAG] Solución guardada automáticamente en ChromaDB: {ticket_id_virt}")
    except Exception as e:
        print(f"[Memoria RAG] Error al sincronizar con ChromaDB: {e}")
        
    # Si tiene ruta_local, es una habilidad. Lo guardamos en el .md local del agente
    if ruta_local:
        ruta_raiz = _APP_ROOT / agente
        ruta_raiz.mkdir(parents=True, exist_ok=True)
        md_file = ruta_raiz / f"Perfil_{agente}.md"
        
        if not md_file.exists():
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(f"# Perfil de {agente}\n\n")
                
        with open(md_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Habilidad: {tema}\n")
            f.write(f"* **Descripción:** {contenido}\n")
            f.write(f"* **Ruta:** `{ruta_local}`\n")
            
        # Sincronizar automáticamente la tarjeta de presentación global
        import shutil
        global_agentes_dir = SHARED_MEMORY_PATH / "agentes"
        global_agentes_dir.mkdir(parents=True, exist_ok=True)
        global_md_file = global_agentes_dir / f"{agente}.md"
        shutil.copy2(md_file, global_agentes_dir / f"Perfil_{agente}.md")

# ══════════════════════════════════════════════════════════════════════════════
# Perfiles y Utilidades
# ══════════════════════════════════════════════════════════════════════════════

def cargar_perfil_agente(nombre: str) -> dict:
    # 1. Buscar en la subcarpeta .agents del propio agente
    archivo_local = _APP_ROOT / nombre.capitalize() / ".agents" / f"{nombre.lower()}_perfil.json"
    if archivo_local.exists():
        try:
            return json.loads(archivo_local.read_text(encoding="utf-8"))
        except:
            pass
    # 2. Fallback a carpeta general perfiles/ en la raíz
    archivo_general = (_APP_ROOT / "perfiles") / f"{nombre.lower()}_perfil.json"
    if archivo_general.exists():
        try:
            return json.loads(archivo_general.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def leer_nodo_obsidian(ruta_relativa: str) -> str:
    if not ruta_relativa.endswith(".md"):
        ruta_relativa += ".md"
    ruta_completa = SHARED_MEMORY_PATH / ruta_relativa
    if ruta_completa.exists():
        return ruta_completa.read_text(encoding="utf-8")
    return f"[Nodo {ruta_relativa} no encontrado]"

# ══════════════════════════════════════════════════════════════════════════════
# 4. SISTEMA DE TURNOS (Token Ring con Timestamp)
# ══════════════════════════════════════════════════════════════════════════════

# Ruta del archivo de turno (en la raíz de Agentes, compartida por todos)
_TURNO_FILE = (_APP_ROOT / "turno.json")


def leer_turno() -> dict:
    """[DEPRECADO] El sistema de turnos ha sido reemplazado por Orquestación On-Demand."""
    return {
        "turno_actual": "Luffy",
        "orden": ["Luffy"],
        "hora_inicio": None,
    }


def reclamar_turno(agente: str) -> None:
    """[DEPRECADO] Orquestación On-Demand activa."""
    pass


def avanzar_turno(agente_actual: str) -> None:
    """[DEPRECADO] Orquestación On-Demand activa."""
    pass

    # Inyectar el turno actual en el canal de comunicación para visibilidad
    try:
        canal = _cargar_canal("interno")
        canal["turno_actual"] = siguiente
        _guardar_canal(canal, "interno")
    except Exception:
        pass


def guardar_en_historial(objetivo: str, resultado: str, agentes: list[str]) -> None:
    """
    Guarda una entrada en historial.json dentro de memoria compartida.
    """
    historial_file = SHARED_MEMORY_PATH / "historial.json"
    historial = cargar_historial()
    entrada = {
        "fecha": datetime.now().isoformat(),
        "objetivo": objetivo,
        "resultado": resultado,
        "agentes_involucrados": agentes
    }
    historial.append(entrada)
    try:
        historial_file.write_text(json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[memoria] Error guardando historial: {e}")


def cargar_historial() -> list[dict]:
    """
    Carga y retorna la lista del historial de misiones.
    """
    historial_file = SHARED_MEMORY_PATH / "historial.json"
    if historial_file.exists():
        try:
            return json.loads(historial_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def listar_perfiles_disponibles() -> list[str]:
    """
    Lista los nombres de agentes con perfil JSON disponible en sus carpetas .agents.
    """
    nombres = set()
    root_agentes = _APP_ROOT
    for f in root_agentes.glob("*/.agents/*_perfil.json"):
        nombres.add(f.stem.replace("_perfil", ""))
    perfiles_dir = root_agentes / "perfiles"
    if perfiles_dir.exists():
        for f in perfiles_dir.glob("*_perfil.json"):
            nombres.add(f.stem.replace("_perfil", ""))
    return sorted(list(nombres))


def construir_contexto_para_agente(nombre_agente: str = "Luffy", limite: int = 5) -> str:
    """
    Construye un string de contexto con las últimas misiones en historial.json
    para inyectar en el prompt o memoria de sesión del agente.
    """
    historial = cargar_historial()
    if not historial:
        return ""
    recientes = historial[-limite:]
    lineas = []
    for h in recientes:
        obj = h.get("objetivo", "")
        res = str(h.get("resultado", ""))[:150]
        lineas.append(f"- Objetivo: {obj} | Resultado: {res}")
    return "\n".join(lineas)
