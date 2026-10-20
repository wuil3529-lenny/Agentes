"""
Habilidad: Grafo Canónico y Arquitectura Visual de Obsidian (Fase 6: Entregables por Agente)
Agente: Agente_Orquestador
Propósito: Mantener la salud perfecta (100/100) del grafo de Obsidian conforme al Estándar de Oro.

Topología de Fase 6:
1. Gobernanza Central: 3 Pilares Maestros interconectados (Bitacora <-> Cerebro <-> Reglas).
2. Perfiles de Agentes (5) + Memoria Central (memoria.md) conectados a los 3 Pilares.
3. Bóveda de Memoria: Todos los archivos en memoria/ conectados a [[memoria]].
4. Jerarquía de Entregables por Agente (Pétalos Fractales):
   - Cada agente posee su propio Hub de Entregables conectado a su Perfil:
     * Agente_Orquestador/informes/informes_orquestador.md -> [[Perfil_Agente_Orquestador]]
     * Subagente_Desarrollo/proyectos/proyectos_desarrollo.md -> [[Perfil_Subagente_Desarrollo]]
     * Subagente_Diseno/proyectos/proyectos_diseno.md -> [[Perfil_Subagente_Diseno]]
     * Subagente_Ciberseguridad/reportes/reportes_ciberseguridad.md -> [[Perfil_Subagente_Ciberseguridad]]
     * Subagente_Asistencia/informes/informes_asistencia.md -> [[Perfil_Subagente_Asistencia]]
   - Todo archivo de tareas, reportes o proyectos dentro de esa carpeta se conecta a su respectivo Hub de Entregables.
   - Las habilidades (skills/) y archivos base del agente se conectan directamente a su Perfil.
5. Tres Satélites Independientes (Hubs Sueltos sin enlaces al centro):
   - sistema/sistema.md <- agrupa 34 documentos de arquitectura, utilidades, .agents/, protocolo/ y README.md.
   - contexto/contexto.md <- agrupa archivos de contexto/ y proyectos generales.
   - Archivos_temporales/archivos_temporales.md <- agrupa archivos efímeros en Archivos_temporales/.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set
from langchain_core.tools import tool

APP_ROOT = Path(r"C:\Users\admin\Documents\Agentes")
OBSIDIAN_GRAPH_CONFIG = APP_ROOT / ".obsidian" / "graph.json"

CARPETAS_EXCLUIDAS: Set[str] = {
    ".git",
    ".gemini",
    ".vscode",
    ".idea",
    ".obsidian",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "env",
    "scratch",
    "data",
    "canales",
    "static",
}

MAPA_AGENTES_PERFILES = {
    "agente_orquestador": "Perfil_Agente_Orquestador",
    "subagente_desarrollo": "Perfil_Subagente_Desarrollo",
    "subagente_diseno": "Perfil_Subagente_Diseno",
    "subagente_ciberseguridad": "Perfil_Subagente_Ciberseguridad",
    "subagente_asistencia": "Perfil_Subagente_Asistencia",
}

MAPA_ENTREGABLES_AGENTES = {
    "agente_orquestador": {
        "carpeta": "informes",
        "hub_file": "informes_orquestador.md",
        "hub_tag": "informes_orquestador",
        "titulo": "📋 Hub de Informes Ejecutivos — Agente Orquestador",
        "desc": "Hub oficial de informes de gobernanza, diagnósticos de arquitectura y auditorías ejecutivas del Agente Orquestador.",
    },
    "subagente_desarrollo": {
        "carpeta": "proyectos",
        "hub_file": "proyectos_desarrollo.md",
        "hub_tag": "proyectos_desarrollo",
        "titulo": "💻 Hub de Proyectos y Entregables — Subagente de Desarrollo",
        "desc": "Hub oficial de proyectos, remediaciones de software y código técnico de Zoro.",
    },
    "subagente_diseno": {
        "carpeta": "proyectos",
        "hub_file": "proyectos_diseno.md",
        "hub_tag": "proyectos_diseno",
        "titulo": "🎨 Hub de Proyectos y Diseños — Subagente de Diseño",
        "desc": "Hub oficial de entregables visuales, prototipos de marca, animaciones y producciones creativas de Nami.",
    },
    "subagente_ciberseguridad": {
        "carpeta": "reportes",
        "hub_file": "reportes_ciberseguridad.md",
        "hub_tag": "reportes_ciberseguridad",
        "titulo": "📑 Hub de Reportes de Seguridad — Subagente de Ciberseguridad",
        "desc": "Hub oficial de auditorías estáticas SAST, escaneos dinámicos y reportes de seguridad de Robin.",
    },
    "subagente_asistencia": {
        "carpeta": "informes",
        "hub_file": "informes_asistencia.md",
        "hub_tag": "informes_asistencia",
        "titulo": "✉️ Hub de Informes y Correos — Subagente de Asistencia",
        "desc": "Hub oficial de gestión ofimática, catalogación de correos e informes de asistencia de Sanji.",
    },
}

# Conexiones oficiales del Núcleo Central
ENLACES_PILAR_BITACORA = "[[Cerebro]] [[Reglas de la Tripulacion]] [[Perfil_Agente_Orquestador]] [[Perfil_Subagente_Desarrollo]] [[Perfil_Subagente_Diseno]] [[Perfil_Subagente_Ciberseguridad]] [[Perfil_Subagente_Asistencia]] [[memoria]]"
ENLACES_PILAR_CEREBRO = "[[Bitacora]] [[Reglas de la Tripulacion]] [[Perfil_Agente_Orquestador]] [[Perfil_Subagente_Desarrollo]] [[Perfil_Subagente_Diseno]] [[Perfil_Subagente_Ciberseguridad]] [[Perfil_Subagente_Asistencia]] [[memoria]]"
ENLACES_PILAR_REGLAS = "[[Bitacora]] [[Cerebro]] [[Perfil_Agente_Orquestador]] [[Perfil_Subagente_Desarrollo]] [[Perfil_Subagente_Diseno]] [[Perfil_Subagente_Ciberseguridad]] [[Perfil_Subagente_Asistencia]] [[memoria]]"
ENLACES_SATELITES_A_PILARES = "[[Bitacora]] [[Cerebro]] [[Reglas de la Tripulacion]]"

NODOS_GOBERNANZA = {
    "bitacora.md": ENLACES_PILAR_BITACORA,
    "cerebro.md": ENLACES_PILAR_CEREBRO,
    "reglas de la tripulacion.md": ENLACES_PILAR_REGLAS,
    "memoria.md": ENLACES_SATELITES_A_PILARES,
    "perfil_agente_orquestador.md": ENLACES_SATELITES_A_PILARES,
    "perfil_subagente_desarrollo.md": ENLACES_SATELITES_A_PILARES,
    "perfil_subagente_diseno.md": ENLACES_SATELITES_A_PILARES,
    "perfil_subagente_ciberseguridad.md": ENLACES_SATELITES_A_PILARES,
    "perfil_subagente_asistencia.md": ENLACES_SATELITES_A_PILARES,
}

# Hubs sueltos que agrupan documentación sin conectar a los pilares
HUBS_SUELTOS = {"sistema.md", "contexto.md", "archivos_temporales.md"}

PLANTILLA_MEMORIA_ESPEJO = """# 🏛️ Memoria Central del Ecosistema (Espejo de Directorio)

Nodo central de memoria persistente de la tripulación y espejo estructurado de la carpeta `memoria/`.

## 📂 Directorio y Estructura de `memoria/`

### 1. Gobernanza y Perfiles Humanos
- `Perfil de wuil.md` — Perfil de identidad, preferencias operativas y requerimientos del Capitán Wuil.
- `Perfil_Laboral_Wuil.md` — Trayectoria profesional, certificaciones y requisitos para postulaciones.

### 2. Bóvedas de Incidencias e Inmunización
- `Memoria_Viva_Errores.md` — Bóveda centralizada de diagnóstico, códigos de error y recetas de inmunización.
- `Tickets_Archivados.md` — Registro histórico consolidado de misiones y tickets resueltos por la tripulación.

### 3. Procedimientos y Aprendizaje Continuo
- `playbooks_memoria.md` — Índice temático y catálogo de playbooks operacionales.
- `procedimientos_aprendidos.json` — Bóveda de procedimientos aprendidos estructurados en JSON.
- `sesion_aprendizaje_activa.json` — Registro de estado de sesiones de aprendizaje guiado.
- `36_Agente_Orquestador_Playbook_Arquitectura_Jerarquica_Grafo_Obsidian.md` — Playbook maestro de arquitectura del grafo.

### 4. Bóveda de Playbooks Operativos (01 al 28)
- Playbooks de ingeniería, despliegue y automatización (`Subagente_Desarrollo`).
- Playbooks de atención al cliente y gestión de correos (`Subagente_Asistencia`).
- Playbooks de auditoría, SAST y hardening defensivo (`Subagente_Ciberseguridad`).
- Playbooks de supervisión, diseño de flujos y orquestación (`Agente_Orquestador`).

---
**Conexiones:** [[Bitacora]] [[Cerebro]] [[Reglas de la Tripulacion]]
"""

PLANTILLA_SISTEMA_SUELTO = """# ⚙️ Hub de Sistema, Arquitectura y Protocolos

Nodo concentrador independiente y biblioteca técnica del sistema. Agrupa toda la infraestructura, arquitectura, utilidades de scripts y protocolos técnicos de la tripulación.

## 📂 Componentes Agrupados

### 1. Arquitectura y Configuración
- `Arquitectura.md` — Arquitectura general de la tripulación autónoma V3.
- `Configuracion.md` — Parámetros, variables de entorno y puertos.
- `Documentacion de Seguridad.md` — Políticas de seguridad, aislamiento y firewall.
- `Inicio Rapido.md` — Guía de arranque rápido del sistema.
- `Cambios_Arquitectura_2026-10-01.md` — Historial de cambios arquitectónicos.
- `Nuevas_Funcionalidades_2026-09-29.md` — Registro de funcionalidades.

### 2. Documentación Técnica de Agentes
- Documentación técnica especializada de Orquestador, Desarrollo, Diseño, Ciberseguridad y Asistencia.

### 3. Documentación de Scripts del Sistema
- Scripts de listeners, memoria, cliente NIM, QA Gherkin, bucle de autocorrección y puentes.

### 4. Protocolos Técnicos y Habilidades Globales
- `protocolo/Protocolo de Herramientas.md` y `protocolo/Protocolo Inter-Agente.md`.
- Habilidades globales en `.agents/skills/`.
- `README.md` del repositorio maestro.
"""

PLANTILLA_CONTEXTO_SUELTO = """# 📋 Hub de Contexto y Proyectos Generales

Nodo independiente (suelto) del sistema que agrupa todos los documentos de contexto de negocio, entrevistas con usuarios (`contexto/`) y planes maestros de proyectos a nivel ecosistema (`proyectos/`).

## 📂 Propósito
Conforme a las Reglas de la Tripulación (Regla 18.4), este hub consolida los requerimientos, especificaciones y alcances de proyectos de la tripulación sin interferir en los núcleos de código de los agentes.
"""

PLANTILLA_TEMPORALES_SUELTO = """# 🗂️ Hub de Archivos Temporales

Nodo independiente (suelto) del sistema que agrupa todos los documentos transitorios, minutas efímeras y scratchpads en Markdown generados en la carpeta `Archivos_temporales/`.

## 📂 Propósito
Conforme a las Reglas de la Tripulación (Regla 18.4), los archivos efímeros creados durante misiones se enlazan exclusivamente a este hub temporal para mantener el resto del grafo libre de contaminación.
"""


def _purgar_wikilinks_texto(texto: str) -> str:
    """Elimina conexiones residuales [[...]] y las convierte en texto plano."""
    texto = re.sub(
        r"(?ims)^##\s*\d*\.?\s*(?:Conexiones y Referencias|Referencias y Conexiones|Referencias en el Grafo)[^\n]*\n.*?(?=^##\s|\Z)",
        "",
        texto,
    )
    texto = re.sub(r"(?im)^\s*>\s*🔗?\s*\*\*Nexo:\*\*.*$", "", texto)
    texto = re.sub(r"(?im)^\s*>\s*\*\*Conexiones Core:\*\*.*$", "", texto)
    texto = re.sub(r"(?im)^\s*\*\*Conexiones:\*\*.*$", "", texto)
    texto = re.sub(r"(?im)^\s*\*\*Pertenece a:\*\*.*$", "", texto)
    texto = re.sub(r'\["\[([^\]]+)\]"\]', r'["(\1)"]', texto)
    texto = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", texto)
    texto = re.sub(r"\[\[([^\]]+)\]\]", r"\1", texto)
    texto = texto.strip()
    while texto.endswith("---"):
        texto = texto[:-3].strip()
    return texto + "\n"


@tool
def tool_auditar_grafo_obsidian() -> Dict[str, Any]:
    """
    Audita la topología de Fase 6 del Grafo de Obsidian en disco.
    Verifica:
    1. Gobernanza: 3 Pilares interconectados entre sí y con los 5 perfiles + memoria.md.
    2. Hubs de Entregables: Cada agente tiene su Hub de entregables conectado a su Perfil.
    3. Tareas y Proyectos: Archivos en carpetas de entregables conectados al Hub de Entregables.
    4. Habilidades y Base: Skills de agentes conectados directamente a su Perfil.
    5. Memoria: Archivos en memoria/ conectados al nodo [[memoria]].
    6. Contexto: Archivos en contexto/ y proyectos/ conectados a [[contexto]].
    7. Temporales: Archivos en Archivos_temporales/ conectados a [[archivos_temporales]].
    8. Sistema: Archivos restantes conectados a [[sistema]].
    """
    print("\n[Agente_Orquestador] Ejecutando: tool_auditar_grafo_obsidian() [Fase 6: Jerarquía de Entregables]...")
    hallazgos: List[str] = []
    desalineaciones: List[str] = []
    archivos_evaluados = 0
    archivos_con_enlaces = set()

    conteo_gobernanza_ok = 0
    conteo_entregables_hubs_ok = 0
    conteo_entregables_hojas_ok = 0
    conteo_skills_ok = 0
    conteo_memoria_ok = 0
    conteo_contexto_ok = 0
    conteo_temporales_ok = 0
    conteo_sistema_ok = 0

    hub_filenames = {info["hub_file"].lower() for info in MAPA_ENTREGABLES_AGENTES.values()}

    for root, dirs, files in os.walk(APP_ROOT):
        dirs[:] = [d for d in dirs if d not in CARPETAS_EXCLUIDAS and d.lower() not in CARPETAS_EXCLUIDAS]
        rel_root = os.path.relpath(root, APP_ROOT)
        parts = Path(rel_root).parts if rel_root != "." else ()
        top_folder = parts[0].lower() if parts else ""

        for f in files:
            if not f.endswith(".md"):
                continue
            archivos_evaluados += 1
            md_path = Path(root) / f
            f_lower = f.lower()

            try:
                content = md_path.read_text(encoding="utf-8")
                wikilinks = set(re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content))
                if wikilinks:
                    archivos_con_enlaces.add(md_path)

                # Caso 1: Nodos de gobernanza central
                if f_lower in NODOS_GOBERNANZA:
                    esperados = set(re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", NODOS_GOBERNANZA[f_lower]))
                    if esperados.issubset(wikilinks):
                        conteo_gobernanza_ok += 1
                    else:
                        desalineaciones.append(f"{f} (faltan enlaces de gobernanza: {esperados - wikilinks})")

                # Caso 2: Hubs sueltos independientes
                elif f_lower in HUBS_SUELTOS:
                    if len(wikilinks) == 0:
                        pass
                    else:
                        desalineaciones.append(f"Hub suelto {f} tiene enlaces salientes inesperados: {wikilinks}")

                # Caso 3: Archivos dentro de las 5 carpetas de agentes
                elif top_folder in MAPA_AGENTES_PERFILES:
                    perfil_esperado = MAPA_AGENTES_PERFILES[top_folder]
                    info_entregable = MAPA_ENTREGABLES_AGENTES.get(top_folder)

                    # Subcaso 3A: Es el archivo Hub de Entregables del agente
                    if info_entregable and f_lower == info_entregable["hub_file"].lower():
                        if perfil_esperado in wikilinks and len(wikilinks) == 1:
                            conteo_entregables_hubs_ok += 1
                        else:
                            desalineaciones.append(f"Hub {f} (esperaba enlace exclusivo a [[{perfil_esperado}]])")

                    # Subcaso 3B: Es un archivo dentro de la carpeta oficial de entregables
                    elif info_entregable and (
                        (len(parts) > 1 and parts[1].lower() == info_entregable["carpeta"])
                        or (top_folder == "subagente_asistencia" and len(parts) > 1 and parts[1].lower() == "documentos_asistencia")
                    ):
                        hub_tag = info_entregable["hub_tag"]
                        if hub_tag in wikilinks and len(wikilinks) == 1:
                            conteo_entregables_hojas_ok += 1
                        else:
                            desalineaciones.append(f"Entregable {rel_root}/{f} (esperaba enlace a [[{hub_tag}]])")

                    # Subcaso 3C: Demás archivos del agente (skills, agente.md) conectan a su Perfil
                    else:
                        if perfil_esperado in wikilinks and len(wikilinks) == 1:
                            conteo_skills_ok += 1
                        else:
                            desalineaciones.append(f"{rel_root}/{f} (esperaba enlace a [[{perfil_esperado}]])")

                # Caso 4: Archivos dentro de memoria/
                elif top_folder == "memoria":
                    if "memoria" in wikilinks and len(wikilinks) == 1:
                        conteo_memoria_ok += 1
                    else:
                        desalineaciones.append(f"{rel_root}/{f} (esperaba enlace a [[memoria]])")

                # Caso 5: Archivos dentro de contexto/ o proyectos/ generales
                elif top_folder in ("contexto", "proyectos"):
                    if "contexto" in wikilinks and len(wikilinks) == 1:
                        conteo_contexto_ok += 1
                    else:
                        desalineaciones.append(f"{rel_root}/{f} (esperaba enlace a [[contexto]])")

                # Caso 6: Archivos dentro de Archivos_temporales/
                elif top_folder == "archivos_temporales":
                    if "archivos_temporales" in wikilinks and len(wikilinks) == 1:
                        conteo_temporales_ok += 1
                    else:
                        desalineaciones.append(f"{rel_root}/{f} (esperaba enlace a [[archivos_temporales]])")

                # Caso 7: Archivos restantes conectan a [[sistema]]
                else:
                    if "sistema" in wikilinks and len(wikilinks) == 1:
                        conteo_sistema_ok += 1
                    else:
                        desalineaciones.append(f"{rel_root}/{f} (esperaba enlace a [[sistema]])")

            except Exception as e:
                desalineaciones.append(f"Error leyendo {rel_root}/{f}: {e}")

    if len(desalineaciones) > 0:
        hallazgos.append(
            f"Desalineaciones topológicas en Fase 6: {len(desalineaciones)} archivos con conexiones no canónicas."
        )

    # Auditar graph.json
    config_ok = False
    show_orphans = False
    color_groups_count = 0
    if OBSIDIAN_GRAPH_CONFIG.exists():
        try:
            cfg = json.loads(OBSIDIAN_GRAPH_CONFIG.read_text(encoding="utf-8"))
            config_ok = True
            show_orphans = cfg.get("showOrphans", False)
            color_groups_count = len(cfg.get("colorGroups", []))
            if not show_orphans:
                hallazgos.append("showOrphans es False: los hubs sueltos no se mostrarán en Obsidian.")
        except Exception as e:
            hallazgos.append(f"Error al leer graph.json: {e}")

    penalizaciones = len(hallazgos) * 20
    puntuacion = max(10, 100 - penalizaciones)
    if len(desalineaciones) == 0 and show_orphans and color_groups_count >= 5:
        puntuacion = 100

    return {
        "status": "success",
        "puntuacion_salud": puntuacion,
        "fase_activa": "Fase 6 — Arquitectura Jerárquica de Entregables por Agente",
        "total_archivos_md": archivos_evaluados,
        "total_archivos_conectados": len(archivos_con_enlaces),
        "nodos_gobernanza": len(NODOS_GOBERNANZA),
        "hubs_entregables_agentes": conteo_entregables_hubs_ok,
        "entregables_conectados": conteo_entregables_hojas_ok,
        "skills_y_base_agentes": conteo_skills_ok,
        "nodos_memoria_conectados": conteo_memoria_ok,
        "nodos_contexto_conectados": conteo_contexto_ok,
        "nodos_temporales_conectados": conteo_temporales_ok,
        "nodos_sistema_conectados": conteo_sistema_ok,
        "hubs_sueltos_independientes": len(HUBS_SUELTOS),
        "desalineaciones": desalineaciones,
        "config_obsidian": {
            "existe": config_ok,
            "showOrphans": show_orphans,
            "grupos_color_definidos": color_groups_count,
        },
        "hallazgos": hallazgos,
        "recomendacion": "Fase 6 perfecta: Gobernanza, Agentes, Entregables departamentales, Memoria, Contexto, Temporales y Sistema al 100%." if puntuacion == 100 else "Ejecutar tool_sincronizar_grafo_canonico para reparar conexiones.",
    }


@tool
def tool_sincronizar_grafo_canonico(purgar_residuos: bool = True, calibrar_obsidian: bool = True) -> Dict[str, Any]:
    """
    Sincroniza el Grafo de Obsidian bajo la directiva de Fase 6:
    - 3 Pilares Maestros interconectados entre sí (Bitacora, Cerebro, Reglas de la Tripulacion).
    - 5 Perfiles de Agentes conectados a los 3 Pilares.
    - 1 Memoria Central (memoria/memoria.md) conectada a los 3 Pilares.
    - Todos los archivos en memoria/ conectados a [[memoria]].
    - 5 Hubs de Entregables Departamentales:
      * Agente_Orquestador/informes/informes_orquestador.md -> [[Perfil_Agente_Orquestador]]
      * Subagente_Desarrollo/proyectos/proyectos_desarrollo.md -> [[Perfil_Subagente_Desarrollo]]
      * Subagente_Diseno/proyectos/proyectos_diseno.md -> [[Perfil_Subagente_Diseno]]
      * Subagente_Ciberseguridad/reportes/reportes_ciberseguridad.md -> [[Perfil_Subagente_Ciberseguridad]]
      * Subagente_Asistencia/informes/informes_asistencia.md -> [[Perfil_Subagente_Asistencia]]
    - Todos los archivos dentro de la carpeta de entregables de cada agente conectados a su Hub respectivo.
    - Habilidades y archivos base de agentes conectados a su Perfil de Agente.
    - 3 Hubs Sueltos Independientes:
      * sistema/sistema.md (suelto) <- todos los archivos restantes conectan a [[sistema]].
      * contexto/contexto.md (suelto) <- todos los archivos en contexto/ y proyectos/ conectan a [[contexto]].
      * Archivos_temporales/archivos_temporales.md (suelto) <- todos los archivos en Archivos_temporales/ conectan a [[archivos_temporales]].
    - Configura .obsidian/graph.json con showOrphans=True, grupos de color distintivos y física balanceada.
    """
    print("\n[Agente_Orquestador] Ejecutando: tool_sincronizar_grafo_canonico() [Fase 6: Jerarquía de Entregables]...")
    archivos_modificados = 0
    nodos_conectados = 0

    # 1. Asegurar memoria.md
    memoria_md = APP_ROOT / "memoria" / "memoria.md"
    try:
        memoria_md.parent.mkdir(parents=True, exist_ok=True)
        memoria_md.write_text(PLANTILLA_MEMORIA_ESPEJO, encoding="utf-8")
        archivos_modificados += 1
        nodos_conectados += 1
    except Exception as e:
        print(f"[Grafo_Obsidian] Error escribiendo memoria.md: {e}")

    # 2. Asegurar sistema/sistema.md (hub suelto)
    sistema_md = APP_ROOT / "sistema" / "sistema.md"
    try:
        sistema_md.parent.mkdir(parents=True, exist_ok=True)
        sistema_md.write_text(PLANTILLA_SISTEMA_SUELTO, encoding="utf-8")
        archivos_modificados += 1
    except Exception as e:
        print(f"[Grafo_Obsidian] Error escribiendo sistema.md: {e}")

    # 3. Asegurar contexto/contexto.md (hub suelto)
    contexto_md = APP_ROOT / "contexto" / "contexto.md"
    try:
        contexto_md.parent.mkdir(parents=True, exist_ok=True)
        contexto_md.write_text(PLANTILLA_CONTEXTO_SUELTO, encoding="utf-8")
        archivos_modificados += 1
    except Exception as e:
        print(f"[Grafo_Obsidian] Error escribiendo contexto.md: {e}")

    # 4. Asegurar Archivos_temporales/archivos_temporales.md (hub suelto)
    temporales_md = APP_ROOT / "Archivos_temporales" / "archivos_temporales.md"
    try:
        temporales_md.parent.mkdir(parents=True, exist_ok=True)
        temporales_md.write_text(PLANTILLA_TEMPORALES_SUELTO, encoding="utf-8")
        archivos_modificados += 1
    except Exception as e:
        print(f"[Grafo_Obsidian] Error escribiendo archivos_temporales.md: {e}")

    # 5. Asegurar los 5 Hubs de Entregables Departamentales
    for ag_key, ag_info in MAPA_ENTREGABLES_AGENTES.items():
        ag_folder = ag_key
        entregable_dir = APP_ROOT / ag_folder / ag_info["carpeta"]
        entregable_dir.mkdir(parents=True, exist_ok=True)
        hub_path = entregable_dir / ag_info["hub_file"]
        perfil_agente = MAPA_AGENTES_PERFILES[ag_key]
        plantilla_hub = f"""# {ag_info["titulo"]}

{ag_info["desc"]}

---
**Conexiones:** [[{perfil_agente}]]
"""
        try:
            hub_path.write_text(plantilla_hub, encoding="utf-8")
            archivos_modificados += 1
            nodos_conectados += 1
        except Exception as e:
            print(f"[Grafo_Obsidian] Error escribiendo {hub_path.name}: {e}")

    # 6. Recorrer todos los archivos Markdown y aplicar la topología de Fase 6
    hub_filenames = {info["hub_file"].lower() for info in MAPA_ENTREGABLES_AGENTES.values()}

    for root, dirs, files in os.walk(APP_ROOT):
        dirs[:] = [d for d in dirs if d not in CARPETAS_EXCLUIDAS and d.lower() not in CARPETAS_EXCLUIDAS]
        rel_root = os.path.relpath(root, APP_ROOT)
        parts = Path(rel_root).parts if rel_root != "." else ()
        top_folder = parts[0].lower() if parts else ""

        for f in files:
            if not f.endswith(".md"):
                continue
            md_path = Path(root) / f
            f_lower = f.lower()

            # Hubs ya formateados y gestionados explícitamente
            if f_lower in ("memoria.md", "sistema.md", "contexto.md", "archivos_temporales.md") or f_lower in hub_filenames:
                continue

            try:
                orig = md_path.read_text(encoding="utf-8")
                limpio = _purgar_wikilinks_texto(orig).strip()

                # Caso 1: Nodos de gobernanza central o perfiles
                if f_lower in NODOS_GOBERNANZA:
                    enlace = NODOS_GOBERNANZA[f_lower]
                    nuevo = f"{limpio}\n\n---\n**Conexiones:** {enlace}\n"
                    nodos_conectados += 1

                # Caso 2: Archivos internos dentro de las carpetas de agentes
                elif top_folder in MAPA_AGENTES_PERFILES:
                    perfil_agente = MAPA_AGENTES_PERFILES[top_folder]
                    info_entregable = MAPA_ENTREGABLES_AGENTES.get(top_folder)

                    # Subcaso 2A: Está dentro de la carpeta oficial de entregables del agente
                    if info_entregable and (
                        (len(parts) > 1 and parts[1].lower() == info_entregable["carpeta"])
                        or (top_folder == "subagente_asistencia" and len(parts) > 1 and parts[1].lower() == "documentos_asistencia")
                    ):
                        hub_tag = info_entregable["hub_tag"]
                        nuevo = f"{limpio}\n\n---\n**Conexiones:** [[{hub_tag}]]\n"
                        nodos_conectados += 1

                    # Subcaso 2B: Demás archivos del agente (skills/, agente.md) conectan a su Perfil
                    else:
                        nuevo = f"{limpio}\n\n---\n**Conexiones:** [[{perfil_agente}]]\n"
                        nodos_conectados += 1

                # Caso 3: Archivos internos dentro de la carpeta memoria/
                elif top_folder == "memoria":
                    nuevo = f"{limpio}\n\n---\n**Conexiones:** [[memoria]]\n"
                    nodos_conectados += 1

                # Caso 4: Archivos dentro de contexto/ o proyectos/ generales de raíz
                elif top_folder in ("contexto", "proyectos"):
                    nuevo = f"{limpio}\n\n---\n**Conexiones:** [[contexto]]\n"
                    nodos_conectados += 1

                # Caso 5: Archivos dentro de Archivos_temporales/
                elif top_folder == "archivos_temporales":
                    nuevo = f"{limpio}\n\n---\n**Conexiones:** [[archivos_temporales]]\n"
                    nodos_conectados += 1

                # Caso 6: Todos los demás archivos conectan al nodo suelto [[sistema]]
                else:
                    nuevo = f"{limpio}\n\n---\n**Conexiones:** [[sistema]]\n"
                    nodos_conectados += 1

                if nuevo != orig:
                    md_path.write_text(nuevo, encoding="utf-8")
                    archivos_modificados += 1
            except Exception as e:
                print(f"[Grafo_Obsidian] Error procesando {md_path.name}: {e}")

    # 7. Calibrar .obsidian/graph.json
    config_ok = False
    if calibrar_obsidian:
        try:
            OBSIDIAN_GRAPH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            nueva_config = {
                "collapse-filter": False,
                "search": "",
                "showTags": False,
                "showAttachments": False,
                "hideUnresolved": True,
                "showOrphans": True,  # Permite ver los hubs sueltos independientes
                "collapse-color-groups": False,
                "colorGroups": [
                    {
                        "query": 'file:Cerebro OR file:Bitacora OR file:"Reglas de la Tripulacion"',
                        "color": {"a": 1, "rgb": 16096779},  # Oro Gobernanza Central (#F59E0B)
                    },
                    {
                        "query": "path:Agente_Orquestador OR file:Agente_Orquestador",
                        "color": {"a": 1, "rgb": 15680580},  # Rojo Carmesí Orquestador (#EF4444)
                    },
                    {
                        "query": "path:Subagente_Desarrollo OR file:Subagente_Desarrollo",
                        "color": {"a": 1, "rgb": 1096065},   # Verde Esmeralda Desarrollo (#10B981)
                    },
                    {
                        "query": "path:Subagente_Diseno OR file:Subagente_Diseno",
                        "color": {"a": 1, "rgb": 16347926},  # Naranja Mandarina Diseño (#F97316)
                    },
                    {
                        "query": "path:Subagente_Ciberseguridad OR file:Subagente_Ciberseguridad",
                        "color": {"a": 1, "rgb": 9133302},   # Púrpura Amatista Ciberseguridad (#8B5CF6)
                    },
                    {
                        "query": "path:Subagente_Asistencia OR file:Subagente_Asistencia",
                        "color": {"a": 1, "rgb": 440020},    # Cian Eléctrico Asistencia (#06B6D4)
                    },
                    {
                        "query": "path:memoria OR file:memoria",
                        "color": {"a": 1, "rgb": 1357990},   # Turquesa Menta Memoria (#14B8A6)
                    },
                    {
                        "query": "path:sistema OR path:protocolo OR file:sistema",
                        "color": {"a": 1, "rgb": 6583435},   # Gris Pizarra Sistema y Protocolos (#64748B)
                    },
                    {
                        "query": "path:contexto OR file:contexto OR (path:proyectos -path:Subagente)",
                        "color": {"a": 1, "rgb": 15485081},  # Rosa Fucsia Contexto y Proyectos Generales (#EC4899)
                    },
                    {
                        "query": "path:Archivos_temporales OR file:archivos_temporales",
                        "color": {"a": 1, "rgb": 7434618},   # Zinc Ceniza Temporales (#71717A)
                    },
                ],
                "collapse-display": True,
                "showArrow": True,
                "textFadeMultiplier": 0,
                "nodeSizeMultiplier": 1.25,
                "lineSizeMultiplier": 1.1,
                "collapse-forces": False,
                "centerStrength": 0.35,
                "repelStrength": 14,
                "linkStrength": 1.0,
                "linkDistance": 115,
                "scale": 0.30,
                "close": True,
            }
            OBSIDIAN_GRAPH_CONFIG.write_text(json.dumps(nueva_config, indent=2), encoding="utf-8")
            config_ok = True
        except Exception as e:
            print(f"[Grafo_Obsidian] Error configurando graph.json: {e}")

    return {
        "status": "success",
        "mensaje": "Fase 6 completada: Hubs de entregables departamentales creados y conectados por agente, habilidades preservadas y satélites independientes calibrados.",
        "archivos_modificados": archivos_modificados,
        "nodos_conectados": nodos_conectados,
        "configuracion_obsidian_calibrada": config_ok,
        "showOrphans": True,
        "reglas_aplicadas": [
            "3 Pilares Maestros interconectados entre sí (Bitacora, Cerebro, Reglas de la Tripulacion).",
            "5 Perfiles de Agentes conectados a los 3 Pilares Maestros.",
            "memoria.md como espejo estructurado y conectado a los 3 Pilares.",
            "Todos los archivos de memoria/ conectados al nodo [[memoria]].",
            "5 Hubs departamentales de entregables conectados a sus respectivos perfiles de agentes.",
            "Todos los archivos de tareas, proyectos y reportes conectados a su respectivo hub departamental.",
            "Habilidades conectadas directamente al Perfil de su agente.",
            "Hub suelto [[sistema]] agrupando documentación técnica, .agents/, protocolo/ y README.",
            "Hub suelto [[contexto]] agrupando todos los archivos de contexto/ y proyectos/ generales.",
            "Hub suelto [[archivos_temporales]] agrupando archivos efímeros en Archivos_temporales/.",
            "showOrphans=True activo en Obsidian con 8 grupos de color distintivos.",
        ],
    }


@tool
def tool_capturar_verificar_grafo_obsidian() -> Dict[str, Any]:
    """
    Ejecuta una captura de pantalla visual de Obsidian usando el puente motriz de Windows
    para auditoría visual multimodal por el equipo de agentes.
    """
    print("\n[Agente_Orquestador] Ejecutando: tool_capturar_verificar_grafo_obsidian()...")
    try:
        import urllib.request
        base_url = os.getenv("CONSOLE_HOST_URL", "http://host.docker.internal:8000").rstrip("/")
        req = urllib.request.Request(
            f"{base_url}/api/manos_ojos/pc/capturar",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            return {
                "status": "success",
                "mensaje": "Captura de pantalla de Obsidian obtenida.",
                "datos_captura": data,
            }
    except Exception as e:
        return {"status": "error", "mensaje": f"Error capturando pantalla de Obsidian: {str(e)}"}


def obtener_prompt_grafo_obsidian() -> str:
    """Retorna el System Prompt especializado para la habilidad de Grafo de Obsidian."""
    return """
[HABILIDAD ACTIVA: GESTIÓN Y AUDITORÍA DEL GRAFO DE OBSIDIAN — FASE 6]
Eres el custodio de la arquitectura del conocimiento de la tripulación en Obsidian.
Tus reglas operativas obligatorias:
1. GOBERNANZA CENTRAL: Bitacora.md <--> Cerebro.md <--> Reglas de la Tripulacion.md, con los 5 perfiles y memoria.md conectados a ellos.
2. HUBS DE ENTREGABLES POR AGENTE:
   - Agente_Orquestador/informes/informes_orquestador.md -> [[Perfil_Agente_Orquestador]]
   - Subagente_Desarrollo/proyectos/proyectos_desarrollo.md -> [[Perfil_Subagente_Desarrollo]]
   - Subagente_Diseno/proyectos/proyectos_diseno.md -> [[Perfil_Subagente_Diseno]]
   - Subagente_Ciberseguridad/reportes/reportes_ciberseguridad.md -> [[Perfil_Subagente_Ciberseguridad]]
   - Subagente_Asistencia/informes/informes_asistencia.md -> [[Perfil_Subagente_Asistencia]]
   Todo archivo de tareas, reportes o proyectos generado por el agente se conecta exclusivamente a su Hub de Entregables.
3. HABILIDADES DE AGENTES:
   - Todo archivo de habilidades (skills/) se conecta directamente a su [[Perfil_...]].
4. BÓVEDA DE MEMORIA:
   - Todo archivo .md dentro de memoria/ (excepto memoria.md) se conecta a [[memoria]].
5. HUBS SUELTOS INDEPENDIENTES:
   - sistema/sistema.md (suelto) <- agrupa archivos de sistema/, .agents/, protocolo/ y README.md.
   - contexto/contexto.md (suelto) <- agrupa archivos de contexto/ y proyectos/ generales.
   - Archivos_temporales/archivos_temporales.md (suelto) <- agrupa archivos de Archivos_temporales/.
6. AUDITORÍA PERIÓDICA: Usa tool_auditar_grafo_obsidian para medir la salud del grafo y tool_sincronizar_grafo_canonico para reparar desalineaciones.
"""

HERRAMIENTAS_GRAFO_OBSIDIAN = [
    tool_auditar_grafo_obsidian,
    tool_sincronizar_grafo_canonico,
    tool_capturar_verificar_grafo_obsidian,
]
