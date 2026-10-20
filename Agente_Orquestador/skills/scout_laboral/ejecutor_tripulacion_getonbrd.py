"""
ejecutor_postulaciones_gob.py — Módulo Autónomo de la Tripulación para Postulaciones en Get on Board
==================================================================================================
Ejecuta el protocolo procedural definido en memoria/Playbook_Postulacion_GetOnBrd.md
bajo supervisión en Modo Centinela (Zero-Noise, Zero-Trust, captura obligatoria).
"""

import sys
import time
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[3]
INFORMES_DIR = ROOT_DIR / "Agente_Orquestador" / "informes"
INFORMES_DIR.mkdir(parents=True, exist_ok=True)
PLAYBOOK_FILE = ROOT_DIR / "memoria" / "Playbook_Postulacion_GetOnBrd.md"
API_BASE = "http://127.0.0.1:8000/api/manos_ojos/web"


def _api_call(endpoint: str, data: Optional[Dict[str, Any]] = None, timeout: int = 40) -> Dict[str, Any]:
    url = f"{API_BASE}/{endpoint}"
    payload = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "error", "mensaje": f"Fallo al invocar {endpoint}: {str(e)}"}


def log_centinela(nivel: str, mensaje: str, data: Optional[Dict[str, Any]] = None):
    ev = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "nivel": nivel,
        "mensaje": mensaje,
        "datos": data or {}
    }
    print(f"[CENTINELA-EVENT] {json.dumps(ev, ensure_ascii=False)}", flush=True)


def responder_killer_question(pregunta: str, salario_def: str = "3000") -> str:
    p = (pregunta or "").lower()
    
    if any(k in p for k in ["sueldo", "pretensi", "expectativa salarial", "cuanto aspiras", "remuneraci"]):
        return f"Mi expectativa salarial es de ${salario_def} USD brutos mensuales, acorde con el rango propuesto para la posición y sujeta a evaluación del paquete global."
        
    if any(k in p for k in ["freelance", "contractor", "prestador", "independiente", "honorarios"]):
        return "Sí, estoy totalmente dispuesto a trabajar bajo modalidad freelance / contractor remoto a tiempo completo con disponibilidad inmediata y flexibilidad horaria."
        
    if any(k in p for k in ["react", "frontend", "front-end", "javascript", "typescript", "ui"]):
        return "Tengo sólida experiencia integrando interfaces dinámicas con React y TypeScript conectadas a APIs asíncronas en FastAPI y WebSockets, construyendo dashboards modulares, optimizados y reactivos."
        
    if any(k in p for k in ["python", "fastapi", "django", "flask", "anos de experiencia", "años de experiencia"]):
        return "Cuento con más de 3 años de experiencia sólida desarrollando arquitecturas backend, microservicios asíncronos y APIs de alto rendimiento con Python y FastAPI bajo estándares de calidad industrial."
        
    if any(k in p for k in ["api", "rest", "restful", "endpoints", "graphql", "swagger", "openapi"]):
        return "Sí, ampliamente. He diseñado, documentado con OpenAPI/Swagger e implementado APIs REST asíncronas seguras con autenticación JWT/OAuth2, validación Pydantic y comunicación en tiempo real con WebSockets."
        
    if any(k in p for k in ["base de datos", "postgresql", "mysql", "sql", "sqlalchemy", "pydantic", "docker", "git"]):
        return "Experiencia avanzada con bases de datos PostgreSQL y MySQL, ORMs como SQLAlchemy, serialización y validación estricta con Pydantic, dockerización multicontenedor con Docker Compose y control de versiones con Git."
        
    if any(k in p for k in ["microservicio", "microservices", "cloud", "aws", "gcp", "azure", "ci/cd", "ci-cd"]):
        return "Sí. He diseñado e implementado microservicios desacoplados en contenedores Docker, pipelines CI/CD automatizados y despliegue en entornos cloud y servidores Linux con monitoreo y alta disponibilidad."
        
    if any(k in p for k in ["ia", "ai", "agente", "agents", "llm", "langchain", "langgraph", "rag", "machine learning"]):
        return "Especialista en sistemas multi-agente autónomos, flujos en LangGraph, arquitecturas RAG con bases de datos vectoriales (ChromaDB), Transformers y optimización de inferencia en modelos de lenguaje."
        
    return "Cuento con sólida experiencia práctica en ingeniería de software, arquitectura backend en Python, microservicios y despliegue de soluciones robustas enfocadas en escalabilidad, calidad y valor al negocio."


def generar_pitch_empresa(empresa: str, cargo: str) -> str:
    return (
        f"Me entusiasma enormemente integrarme al equipo de {empresa} en el rol de {cargo}. "
        "Aporto una sólida trayectoria en desarrollo backend con Python, microservicios asíncronos en FastAPI y arquitecturas escalables. "
        "Además, mi especialización en automatización, sistemas multi-agente e inteligencia artificial aplicada me permite resolver "
        "desafíos técnicos complejos con rigor metodológico, alta velocidad de iteración y enfoque absoluto en resultados de impacto."
    )


def procesar_oferta(idx: int, cargo: str, empresa: str, url_empleo: str, salario_ref: str) -> Dict[str, Any]:
    log_centinela("INFO", f"Iniciando evaluación y postulación para Oferta #{idx}: {cargo} en {empresa}", {"url": url_empleo})
    
    # Extraer valor salarial sugerido
    salario_num = "3000"
    m_sal = re.findall(r"\d[\d,\.]*", salario_ref.replace(",", ""))
    if m_sal:
        nums = [int(re.sub(r"[^\d]", "", n)) for n in m_sal if re.sub(r"[^\d]", "", n)]
        if nums:
            salario_num = str(max(nums) if len(nums) == 1 else (sum(nums) // len(nums)))
    
    # 1. Navegar a la página del empleo
    nav_res = _api_call("navegar", {"url": url_empleo, "visible": True})
    if nav_res.get("status") != "success":
        log_centinela("ERROR", f"Fallo al navegar a {url_empleo}", nav_res)
        return {"exito": False, "razon": "Error de navegación"}
    
    time.sleep(2)
    
    # 2. Extraer contenido de la página para detectar si ya se postuló o si está abierta
    ext_res = _api_call("extraer")
    texto_pagina = (ext_res.get("contenido_texto") or "").lower()
    
    if any(k in texto_pagina for k in ["ya postulaste", "postulación enviada", "postulaste a este empleo"]):
        log_centinela("ALERTA", f"Ya existía postulación previa para {cargo} en {empresa}", {"idx": idx})
        return {"exito": True, "estado": "YA_POSTULADO", "razon": "Postulación previa detectada"}
        
    if any(k in texto_pagina for k in ["este empleo ya no está disponible", "convocatoria cerrada", "empleo cerrado"]):
        log_centinela("ALERTA", f"El empleo {cargo} en {empresa} ha cerrado", {"idx": idx})
        return {"exito": False, "estado": "CERRADA", "razon": "Convocatoria cerrada en Get on Board"}
    
    # 3. Detectar botón de postular
    # En Get on Board el enlace a postulación suele ser a[href*='/applications/new'] o botón 'Postularme'
    clic_post = _api_call("clic", {"selector_o_texto": "Postularme"})
    if clic_post.get("status") != "success":
        clic_post = _api_call("clic", {"selector_o_texto": "Apply now"})
    if clic_post.get("status") != "success":
        clic_post = _api_call("clic", {"selector_o_texto": "a[href*='/applications/new']"})
    if clic_post.get("status") != "success":
        # Intentar navegar directo a /applications/new
        url_app = url_empleo.rstrip("/") + "/applications/new"
        log_centinela("INFO", f"Navegando directamente a URL de postulación: {url_app}")
        clic_post = _api_call("navegar", {"url": url_app, "visible": True})
        
    time.sleep(2)
    
    # 4. Flujo a través de los pasos del Wizard de Get on Board
    intentos_paso = 0
    max_pasos = 6
    while intentos_paso < max_pasos:
        intentos_paso += 1
        ext_actual = _api_call("extraer")
        url_actual = (ext_actual.get("url") or "").lower()
        texto_actual = (ext_actual.get("contenido_texto") or "").lower()
        forms = ext_actual.get("formularios_detectados", [])
        inputs = forms[0].get("inputs", []) if forms else []
        
        log_centinela("DEBUG", f"Iteración de paso {intentos_paso}: {url_actual}")
        
        # Paso 4 / Vista Previa:
        if "job_application_preview=true" in url_actual or "ésta es una vista previa" in texto_actual or "vista previa de tu postulación" in texto_actual:
            log_centinela("INFO", "Detectada Vista Previa. Enviando postulación definitiva...")
            env_res = _api_call("clic", {"selector_o_texto": "Enviar postulación ahora"})
            time.sleep(3)
            break
            
        # Detectar si ya se envió con éxito
        if "fue enviada exitosamente" in texto_actual or "tus postulaciones" in texto_actual and "enviada" in texto_actual:
            log_centinela("INFO", "Confirmación de postulación exitosa detectada.")
            break
            
        # Paso 1: Experiencia
        if "step=experience" in url_actual or "cuéntanos sobre tu experiencia y perfil profesional" in texto_actual:
            log_centinela("INFO", "Procesando Paso 1: Experiencia Profesional...")
            # Los campos suelen venir precargados del perfil de Wuil. Clic en Siguiente.
            sig_res = _api_call("clic", {"selector_o_texto": "Siguiente"})
            time.sleep(2)
            continue
            
        # Paso 2: Información básica
        if "step=basic" in url_actual or "expectativa de sueldo bruto" in texto_actual:
            log_centinela("INFO", f"Procesando Paso 2: Info Básica (Salario: ${salario_num} USD)...")
            pitch = generar_pitch_empresa(empresa, cargo)
            campos = {
                "#job_application_expected_salary": salario_num,
                "#reason-to-apply": pitch
            }
            rellenar_res = _api_call("rellenar", {"campos": campos, "selector_envio": "Siguiente"})
            time.sleep(2)
            continue
            
        # Paso 3: Preguntas (Killer Questions)
        if "step=questions" in url_actual or "preguntas" in url_actual:
            log_centinela("INFO", "Procesando Paso 3: Killer Questions...")
            # Extraer las preguntas
            textareas = [inp for inp in inputs if inp.get("tag") == "textarea" and inp.get("id")]
            campos_respuestas = {}
            for t in textareas:
                tid = t.get("id")
                # Obtener texto del bloque padre
                det_q = _api_call("extraer", {"selector": f"div:has(> #{tid})"})
                texto_q = det_q.get("contenido_texto", "")
                ans = responder_killer_question(texto_q, salario_num)
                campos_respuestas[f"#{tid}"] = ans
                log_centinela("DEBUG", f"Pregunta: {texto_q[:60]}... -> Respuesta ({len(ans)} chars)")
                
            if campos_respuestas:
                _api_call("rellenar", {"campos": campos_respuestas})
                time.sleep(1)
            
            # Clic en Revisar y enviar
            _api_call("clic", {"selector_o_texto": "Siguiente: Revisar y enviar"})
            time.sleep(2)
            continue
            
        # Si no encaja en ninguno específico, intentar hacer clic en 'Siguiente'
        sig_btn = _api_call("clic", {"selector_o_texto": "Siguiente"})
        if sig_btn.get("status") != "success":
            break
        time.sleep(2)

    # 5. Captura Física de Evidencia Zero-Trust
    timestamp = int(time.time())
    img_name = f"captura_postulacion_gob_{idx:03d}.png"
    destino_img = INFORMES_DIR / img_name
    
    cap_res = _api_call("capturar")
    if cap_res.get("status") == "success" and cap_res.get("captura_local"):
        try:
            import shutil
            shutil.copy(cap_res.get("captura_local"), str(destino_img))
            log_centinela("INFO", f"Evidencia física Zero-Trust resguardada en {destino_img}")
        except Exception as e:
            log_centinela("WARNING", f"No se pudo copiar captura: {e}")
            
    # Verificar estado final
    verif = _api_call("extraer")
    txt_final = (verif.get("contenido_texto") or "").lower()
    exito = "enviada exitosamente" in txt_final or "enviada" in txt_final or "tus postulaciones" in txt_final
    
    return {
        "exito": exito,
        "idx": idx,
        "cargo": cargo,
        "empresa": empresa,
        "evidencia": str(destino_img),
        "estado": "ENVIADA" if exito else "REVISAR"
    }


def main():
    log_centinela("INFO", "ORDEN RECIBIDA: La tripulación inicia la ejecución de postulaciones en Get on Board")
    
    # Procesar Oferta #2 (Zaelot)
    oferta_2 = {
        "idx": 2,
        "cargo": "Back-end Software Engineer",
        "empresa": "Zaelot",
        "url": "https://www.getonbrd.com/empleos/programacion/backend-software-engineer-zaelot-remote-fbc2",
        "salario": "$4,000 – $6,500 USD"
    }
    
    resultado = procesar_oferta(
        oferta_2["idx"],
        oferta_2["cargo"],
        oferta_2["empresa"],
        oferta_2["url"],
        oferta_2["salario"]
    )
    
    log_centinela("RESULTADO", f"Postulación Oferta #{oferta_2['idx']} finalizada", resultado)


if __name__ == "__main__":
    main()
