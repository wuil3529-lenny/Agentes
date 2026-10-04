"""
Subagente_Desarrollo/skills/__init__.py
======================================
Punto de agregación centralizado para las 13 habilidades modulares
y sus respectivas herramientas especializadas.
"""

from typing import Dict, Any, List, Set, Callable
import re

# 1. Base (Infraestructura y archivos)
from .base.skill_base import (
    crear_archivo,
    leer_archivo,
    listar_directorio,
    ejecutar_comando,
    obtener_prompt_base,
    HERRAMIENTAS_BASE,
)

# 2. Control de Versiones Git
from .git.skill_git import (
    git_init,
    git_status,
    git_add,
    git_commit,
    git_log,
    git_branch,
    git_checkout,
    git_clone,
    git_pull,
    git_push,
    git_diff,
    obtener_prompt_git,
    HERRAMIENTAS_GIT,
)

# 3. Software Python y Entornos
from .software.skill_software import (
    python_ejecutar_script,
    python_pip_instalar,
    python_crear_venv,
    obtener_prompt_software,
    HERRAMIENTAS_SOFTWARE,
)

# 4. Desarrollo Web
from .web.skill_web import (
    web_scaffold_html,
    web_scaffold_react,
    obtener_prompt_web,
    HERRAMIENTAS_WEB,
)

# 5. Aplicaciones Móviles
from .mobile.skill_mobile import (
    mobile_scaffold_expo,
    mobile_scaffold_rn,
    obtener_prompt_mobile,
    HERRAMIENTAS_MOBILE,
)

# 6. Arquitectura y Diseño Frontend
from .frontend_design.skill_frontend_design import (
    aplicar_frontend_design_anthropic,
    aplicar_ui_ux_pro_max,
    aplicar_emil_design_eng,
    aplicar_huashu_design,
    aplicar_vercel_guidelines,
    obtener_prompt_frontend_design,
    HERRAMIENTAS_FRONTEND_DESIGN,
)

# 7. Automatización de Flujos n8n
from .n8n.skill_n8n import (
    n8n_guardar_workflow,
    n8n_api_call,
    n8n_activar_workflow,
    n8n_iniciar,
    obtener_prompt_n8n,
    HERRAMIENTAS_N8N,
)

# 8. Documentación de Nodos n8n
from .n8n_docs.skill_n8n_docs import (
    n8n_buscar_nodos,
    n8n_leer_parametros_nodo,
    obtener_prompt_n8n_docs,
    HERRAMIENTAS_N8N_DOCS,
)

# 9. Plantillas de la Comunidad n8n
from .n8n_templates.skill_n8n_templates import (
    n8n_buscar_plantillas,
    n8n_obtener_plantilla,
    obtener_prompt_n8n_templates,
    HERRAMIENTAS_N8N_TEMPLATES,
)

# 10. Monitor de Actualizaciones n8n
from .n8n_updater.skill_n8n_updater import (
    n8n_obtener_ultimas_novedades,
    obtener_prompt_n8n_updater,
    HERRAMIENTAS_N8N_UPDATER,
)

# 11. Conectividad y Túneles Ngrok
from .ngrok.skill_ngrok import (
    ngrok_iniciar_tunel,
    ngrok_obtener_url,
    obtener_prompt_ngrok,
    HERRAMIENTAS_NGROK,
)

# 12. Monitoreo, Diagnóstico y Resiliencia Sentry
from .sentry.skill_sentry import (
    tool_consultar_sentry_errores,
    tool_registrar_solucion_error,
    tool_reportar_fallo_critico,
    consultar_sentry_errores,
    registrar_solucion_error,
    obtener_prompt_sentry,
    HERRAMIENTAS_SENTRY,
)

# 13. Higiene y Mantenimiento del Workspace
from .limpiar_workspace.skill_limpiar_workspace import (
    tool_limpiar_workspace,
    tool_limpiar_habitacion,
    obtener_prompt_limpiar_workspace,
    HERRAMIENTAS_LIMPIAR_WORKSPACE,
)

# 14. Ingeniería de Animaciones y Motion UI (Filosofía Emil Kowalski)
from .animaciones.skill_animaciones import (
    tool_generar_animacion_css,
    tool_generar_animacion_motion,
    tool_auditar_animaciones,
    tool_catalogo_recetas_animacion,
    obtener_prompt_animaciones,
    HERRAMIENTAS_ANIMACIONES,
)

# 15. Criterio de Diseño Frontend y Anti-Slop (Taste Skill)
from .taste.skill_taste import (
    tool_taste_inferir_brief,
    tool_taste_generar_tokens,
    tool_taste_auditar_anti_defaults,
    tool_taste_catalogo_estilos,
    obtener_prompt_taste,
    HERRAMIENTAS_TASTE,
)

# 16. Dirección de Diseño y Arquitectura UI/UX Impeccable (Paul Bakaus)
from .impeccable.skill_impeccable import (
    tool_impeccable_definir_superficie,
    tool_impeccable_auditar_diseno,
    tool_impeccable_harden_componente,
    tool_impeccable_distill_ui,
    obtener_prompt_impeccable,
    HERRAMIENTAS_IMPECCABLE,
)

# 17. Verificación en Navegador y Pruebas con Playwright (Playwright MCP)
from .playwright.skill_playwright import (
    tool_playwright_generar_test,
    tool_playwright_verificar_responsive,
    tool_playwright_inspeccionar_accesibilidad,
    tool_playwright_configurar_mcp,
    obtener_prompt_playwright,
    HERRAMIENTAS_PLAYWRIGHT,
)

# 18. Conectores Universales MCP y APIs con Ciberseguridad
from .conectores_mcp_api.skill_conectores_mcp_api import (
    tool_solicitar_auditoria_ciberseguridad,
    tool_conectar_api_rest,
    tool_conectar_servidor_mcp,
    tool_probar_conexion_segura,
    obtener_prompt_conectores_mcp_api,
    HERRAMIENTAS_CONECTORES_MCP_API,
)

# 19. Gestión de Bases de Datos, SQL y Big Data
from .bases_de_datos_sql.skill_bases_de_datos_sql import (
    tool_sql_ejecutar_consulta,
    tool_sql_procesar_grandes_datos,
    tool_sql_analizar_rendimiento,
    tool_sql_migracion_y_esquema,
    obtener_prompt_bases_de_datos_sql,
    HERRAMIENTAS_BASES_DE_DATOS_SQL,
)

# 20. Auto-Aprendizaje Continuo y Memoria Procedural de Playbooks
from .auto_aprendizaje.skill_auto_aprendizaje import (
    tool_consultar_playbook_memoria,
    tool_registrar_playbook_memoria,
    obtener_prompt_auto_aprendizaje,
    HERRAMIENTAS_AUTO_APRENDIZAJE,
)

# 21. Solicitud de Soporte, Pausa y Delegación en Pizarra
from .solicitar_soporte_pizarra.skill_solicitar_soporte_pizarra import (
    tool_solicitar_ayuda_pizarra,
    tool_consultar_estado_ticket_pizarra,
    obtener_prompt_solicitar_soporte_pizarra,
    HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA,
)

# Catálogo completo de herramientas de desarrollo (sin duplicados)
HERRAMIENTAS_DESARROLLO = (
    HERRAMIENTAS_BASE
    + HERRAMIENTAS_GIT
    + HERRAMIENTAS_SOFTWARE
    + HERRAMIENTAS_WEB
    + HERRAMIENTAS_MOBILE
    + HERRAMIENTAS_FRONTEND_DESIGN
    + HERRAMIENTAS_N8N
    + HERRAMIENTAS_N8N_DOCS
    + HERRAMIENTAS_N8N_TEMPLATES
    + HERRAMIENTAS_N8N_UPDATER
    + HERRAMIENTAS_NGROK
    + HERRAMIENTAS_SENTRY
    + HERRAMIENTAS_LIMPIAR_WORKSPACE
    + HERRAMIENTAS_ANIMACIONES
    + HERRAMIENTAS_TASTE
    + HERRAMIENTAS_IMPECCABLE
    + HERRAMIENTAS_PLAYWRIGHT
    + HERRAMIENTAS_CONECTORES_MCP_API
    + HERRAMIENTAS_BASES_DE_DATOS_SQL
    + HERRAMIENTAS_AUTO_APRENDIZAJE
    + HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA
)

# Mapa consolidado de habilidades y sus metadatos
MAPA_HABILIDADES: Dict[str, Dict[str, Any]] = {
    "base": {
        "nombre": "Infraestructura Base y Archivos",
        "prompt": obtener_prompt_base,
        "herramientas": HERRAMIENTAS_BASE,
        "keywords": ["archivo", "escribir", "leer", "comando", "bash", "directorio", "listar", "touch", "cat"]
    },
    "git": {
        "nombre": "Control de Versiones Git",
        "prompt": obtener_prompt_git,
        "herramientas": HERRAMIENTAS_GIT,
        "keywords": ["git", "commit", "rama", "branch", "repositorio", "diff", "staging", "checkout"]
    },
    "software": {
        "nombre": "Software Python y Entornos",
        "prompt": obtener_prompt_software,
        "herramientas": HERRAMIENTAS_SOFTWARE,
        "keywords": ["python", "venv", "virtualenv", "pip", "script", "test", "pytest", "librería", "modulo"]
    },
    "web": {
        "nombre": "Desarrollo Web Full-Stack",
        "prompt": obtener_prompt_web,
        "herramientas": HERRAMIENTAS_WEB,
        "keywords": ["web", "html", "react", "vite", "landing", "spa", "css", "javascript"]
    },
    "mobile": {
        "nombre": "Desarrollo de Aplicaciones Móviles",
        "prompt": obtener_prompt_mobile,
        "herramientas": HERRAMIENTAS_MOBILE,
        "keywords": ["movil", "móvil", "mobile", "expo", "react native", "android", "ios", "app"]
    },
    "frontend_design": {
        "nombre": "Arquitectura y Diseño Frontend",
        "prompt": obtener_prompt_frontend_design,
        "herramientas": HERRAMIENTAS_FRONTEND_DESIGN,
        "keywords": ["ui", "ux", "diseño", "design", "componente", "tailwind", "vercel", "emil", "huashu", "glassmorphism"]
    },
    "n8n": {
        "nombre": "Automatización n8n",
        "prompt": obtener_prompt_n8n,
        "herramientas": HERRAMIENTAS_N8N,
        "keywords": ["n8n", "workflow", "flujo", "automatización", "webhook", "nodo"]
    },
    "n8n_docs": {
        "nombre": "Documentación de Nodos n8n",
        "prompt": obtener_prompt_n8n_docs,
        "herramientas": HERRAMIENTAS_N8N_DOCS,
        "keywords": ["esquema nodo", "documentacion n8n", "propiedades nodo", "buscar nodo"]
    },
    "n8n_templates": {
        "nombre": "Plantillas Comunitarias n8n",
        "prompt": obtener_prompt_n8n_templates,
        "herramientas": HERRAMIENTAS_N8N_TEMPLATES,
        "keywords": ["plantilla n8n", "template n8n", "galeria n8n", "reutilizar flujo"]
    },
    "n8n_updater": {
        "nombre": "Monitor de Actualizaciones n8n",
        "prompt": obtener_prompt_n8n_updater,
        "herramientas": HERRAMIENTAS_N8N_UPDATER,
        "keywords": ["actualizacion n8n", "release n8n", "version n8n", "changelog n8n"]
    },
    "ngrok": {
        "nombre": "Túneles y Conectividad Ngrok",
        "prompt": obtener_prompt_ngrok,
        "herramientas": HERRAMIENTAS_NGROK,
        "keywords": ["ngrok", "tunel", "túnel", "exponer puerto", "url publica", "webhook publico"]
    },
    "sentry": {
        "nombre": "Monitoreo y Diagnóstico Sentry",
        "prompt": obtener_prompt_sentry,
        "herramientas": HERRAMIENTAS_SENTRY,
        "keywords": ["error", "fallo", "excepcion", "excepción", "sentry", "diagnostico", "diagnóstico", "bug", "resiliencia"]
    },
    "limpiar_workspace": {
        "nombre": "Higienización del Workspace",
        "prompt": obtener_prompt_limpiar_workspace,
        "herramientas": HERRAMIENTAS_LIMPIAR_WORKSPACE,
        "keywords": ["limpiar", "workspace", "pycache", "ordenar habitacion", "higiene", "basura", "cache"]
    },
    "animaciones": {
        "nombre": "Ingeniería de Animaciones y Motion UI",
        "prompt": obtener_prompt_animaciones,
        "herramientas": HERRAMIENTAS_ANIMACIONES,
        "keywords": [
            "animacion", "animaciones", "animar", "motion", "framer motion", "transicion",
            "transiciones", "spring", "resorte", "microinteraccion", "microinteracciones",
            "interactivo", "stagger", "gesto", "drawer", "modal animado", "dashboard animado"
        ]
    },
    "taste": {
        "nombre": "Criterio de Diseño Frontend y Anti-Slop",
        "prompt": obtener_prompt_taste,
        "herramientas": HERRAMIENTAS_TASTE,
        "keywords": [
            "taste", "criterio", "anti-slop", "slop", "brief", "read the room", "estetica",
            "tipografia", "paleta", "linear style", "bento grid", "diseño de autor", "tokens diseño"
        ]
    },
    "impeccable": {
        "nombre": "Dirección de Diseño y Arquitectura Impeccable",
        "prompt": obtener_prompt_impeccable,
        "herramientas": HERRAMIENTAS_IMPECCABLE,
        "keywords": [
            "impeccable", "paul bakaus", "operate", "persuade", "craft", "critique", "polish",
            "distill", "harden", "superficie", "anti-patrones", "empty state", "overflow"
        ]
    },
    "playwright": {
        "nombre": "Verificación en Navegador y Pruebas Playwright (Playwright MCP)",
        "prompt": obtener_prompt_playwright,
        "herramientas": HERRAMIENTAS_PLAYWRIGHT,
        "keywords": [
            "playwright", "mcp playwright", "navegador", "test e2e", "prueba e2e", "responsive",
            "overflow-x", "screenshot", "captura de pantalla", "arbol de accesibilidad", "inspeccionar ui"
        ]
    },
    "conectores_mcp_api": {
        "nombre": "Conectores Universales MCP y APIs con Ciberseguridad",
        "prompt": obtener_prompt_conectores_mcp_api,
        "herramientas": HERRAMIENTAS_CONECTORES_MCP_API,
        "keywords": [
            "mcp", "api", "rest", "graphql", "webhook", "servidor mcp", "conector",
            "conectar api", "ciberseguridad conector", "auditoria conector", "ssrf"
        ]
    },
    "bases_de_datos_sql": {
        "nombre": "Gestión de Bases de Datos, SQL y Big Data",
        "prompt": obtener_prompt_bases_de_datos_sql,
        "herramientas": HERRAMIENTAS_BASES_DE_DATOS_SQL,
        "keywords": [
            "sql", "base de datos", "sqlite", "postgres", "postgresql", "mysql",
            "big data", "grandes datos", "polars sql", "consulta sql", "explain", "migracion sql", "tabla", "indice"
        ]
    },
    "auto_aprendizaje": {
        "nombre": "Auto-Aprendizaje Continuo y Memoria Procedural",
        "prompt": obtener_prompt_auto_aprendizaje,
        "herramientas": HERRAMIENTAS_AUTO_APRENDIZAJE,
        "keywords": [
            "playbook", "aprender", "aprendizaje", "auto-aprendizaje", "memoria procedural",
            "receta", "blueprint", "one-shot", "un solo prompt", "recordar", "consultar memoria",
            "primera vez", "plantilla", "reutilizar"
        ]
    },
    "solicitar_soporte_pizarra": {
        "nombre": "Solicitud de Soporte y Pausa en Pizarra",
        "prompt": obtener_prompt_solicitar_soporte_pizarra,
        "herramientas": HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA,
        "keywords": [
            "ayuda", "soporte", "pausa", "pausar", "bloqueo", "bloqueado", "ticket pizarra",
            "insumo", "delegar", "pedir ayuda", "auxilio", "orquestador", "asistencia orquestador",
            "ayuda usuario", "necesito ayuda", "otro subagente"
        ]
    },
}

# Mapa de herramienta -> (nombre_habilidad, prompt_específico) (Inyección Nivel 2)
MAPA_HERRAMIENTA_PROMPTS: Dict[str, tuple] = {}
for _hab_key, _hab_data in MAPA_HABILIDADES.items():
    for _tool in _hab_data["herramientas"]:
        _tool_name = getattr(_tool, "name", getattr(_tool, "__name__", str(_tool)))
        MAPA_HERRAMIENTA_PROMPTS[_tool_name] = (_hab_data["nombre"], _hab_data["prompt"])


def detectar_prompts_habilidad(texto: str) -> List[str]:
    """
    Inyección Dinámica Nivel 1 (Quirúrgica):
    Escanea el texto de la tarea o ticket y retorna los prompts especializados
    de las habilidades cuyas palabras clave coincidan con el requerimiento.
    """
    texto_norm = texto.lower()
    prompts_activados = []
    
    for _hab_key, _hab_data in MAPA_HABILIDADES.items():
        for kw in _hab_data["keywords"]:
            patron = rf"\b{re.escape(kw.lower())}\b"
            if re.search(patron, texto_norm):
                prompts_activados.append(_hab_data["prompt"]())
                break
                
    return prompts_activados


__all__ = [
    # Herramientas por categoría
    "HERRAMIENTAS_BASE",
    "HERRAMIENTAS_GIT",
    "HERRAMIENTAS_SOFTWARE",
    "HERRAMIENTAS_WEB",
    "HERRAMIENTAS_MOBILE",
    "HERRAMIENTAS_FRONTEND_DESIGN",
    "HERRAMIENTAS_N8N",
    "HERRAMIENTAS_N8N_DOCS",
    "HERRAMIENTAS_N8N_TEMPLATES",
    "HERRAMIENTAS_N8N_UPDATER",
    "HERRAMIENTAS_NGROK",
    "HERRAMIENTAS_SENTRY",
    "HERRAMIENTAS_LIMPIAR_WORKSPACE",
    "HERRAMIENTAS_ANIMACIONES",
    "HERRAMIENTAS_TASTE",
    "HERRAMIENTAS_IMPECCABLE",
    "HERRAMIENTAS_PLAYWRIGHT",
    "HERRAMIENTAS_CONECTORES_MCP_API",
    "HERRAMIENTAS_BASES_DE_DATOS_SQL",
    "HERRAMIENTAS_AUTO_APRENDIZAJE",
    "HERRAMIENTAS_SOLICITAR_SOPORTE_PIZARRA",
    "HERRAMIENTAS_DESARROLLO",
    # Mapeos e inyección dinámica
    "MAPA_HABILIDADES",
    "MAPA_HERRAMIENTA_PROMPTS",
    "detectar_prompts_habilidad",
]
