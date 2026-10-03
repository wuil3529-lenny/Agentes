"""
skill_memoria_vectorial.py — Memoria a Largo Plazo con Base de Datos Vectorial (RAG)
==================================================================================
Permite al Agente Orquestador y a la tripulación indexar y buscar historial de soluciones,
lecciones aprendidas y recibos de misión usando ChromaDB y la tríada de conocimiento.
"""

import os
import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[3]
_CHROMA_DOCKER = Path("/app/Agente_Orquestador/data/chroma_db")
CHROMA_DB_PATH = str(_CHROMA_DOCKER if _CHROMA_DOCKER.exists() else _APP_ROOT / "Agente_Orquestador" / "data" / "chroma_db")


def obtener_prompt_memoria_vectorial() -> str:
    """
    System Prompt especializado y encapsulado para la gestión de Memoria Vectorial
    a Largo Plazo (ChromaDB + RAG + Recibos de Misión).
    """
    return """[🛑 HARD-STOP: MODO MEMORIA VECTORIAL Y RAG DE SOLUCIONES ACTIVO 🛑]
Eres el Archivero Maestro y Gestor de Memoria Vectorial de la tripulación de agentes.
Tu misión es salvaguardar, indexar y recuperar el conocimiento técnico acumulado en ChromaDB, Cerebro.md y los recibos de misión, garantizando que ninguna lección aprendida se pierda y que la tripulación nunca repita errores del pasado.

DIRECTIVAS OPERATIVAS FUNDAMENTALES:
1. CONSULTA SEMÁNTICA PREVIA (NO REINVENTAR LA RUEDA):
   - Ante cualquier tarea compleja, investiga previamente con `tool_buscar_soluciones` si existe un antecedente o patrón técnico resuelto en el historial.
2. REGISTRO RIGUROSO DE RESOLUCIONES:
   - Al concluir un ticket, invoca obligatoriamente `tool_guardar_solucion` detallando el ID del ticket, la descripción, las herramientas usadas, las decisiones clave y la ruta exacta de la Evidencia Física en disco.
3. INTEGRIDAD DE LA MEMORIA DE TRES CAPAS:
   - Todo registro se almacena en: (1) La base de conocimiento central en Cerebro.md, (2) Un archivo físico persistente en memoria/, y (3) La colección vectorial de ChromaDB para similitud semántica.
4. VERIFICACIÓN DE ESTADO DE TICKETS:
   - Utiliza `consultar_estado_ticket` para confirmar si un ticket específico ya fue cerrado y archivado formalmente antes de declararlo concluido.
"""


def _get_collection():
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        collection = client.get_or_create_collection(
            name="historial_tripulacion",
            embedding_function=sentence_transformer_ef
        )
        return collection
    except ImportError:
        raise ImportError("ChromaDB o sentence-transformers no están instalados. Asegúrate de ejecutar 'pip install chromadb sentence-transformers'.")


@tool
def tool_guardar_solucion(
    ticket_id: str,
    descripcion: str,
    contenido: str,
    herramientas_usadas: str = "N/A",
    decisiones_clave: str = "N/A",
    evidencia_fisica: str = "N/A",
    agentes_involucrados: str = "N/A"
) -> str:
    """
    Guarda la resolución de un ticket en la memoria vectorial a largo plazo (Cerebro.md, memoria/ y ChromaDB).
    Genera automáticamente el Recibo Ejecutivo de Misión detallando herramientas y decisiones tomadas.
    
    Args:
        ticket_id: ID único del ticket (ej: TKT-001 o TKT-DEV-20261001001)
        descripcion: Resumen breve del problema y solución aplicada.
        contenido: Bloque completo del ticket, código relevante o lección aprendida.
        herramientas_usadas: Lista de herramientas ejecutadas (ej: listar_directorio, leer_archivo, crear_archivo).
        decisiones_clave: Decisiones técnicas tomadas para resolver la tarea o mitigar riesgos.
        evidencia_fisica: Ruta exacta del archivo generado o verificado en disco.
        agentes_involucrados: Subagentes que participaron en la misión.
    """
    try:
        # Resolución agnóstica del módulo memory (Docker / Host)
        rutas_orquestador = [
            _APP_ROOT / "Agente_Orquestador",
            _APP_ROOT / "Luffy",
            Path("/app/Agente_Orquestador"),
            Path("/app/Luffy")
        ]
        for r in rutas_orquestador:
            if r.exists() and str(r) not in sys.path:
                sys.path.insert(0, str(r))
                break
                
        try:
            from memory import guardar_cerebro
        except ImportError:
            from Agente_Orquestador.memory import guardar_cerebro
        
        # Mapeo canónico agnóstico del agente responsable
        agente = "Agente_Orquestador"
        up_t = ticket_id.upper()
        if any(k in up_t for k in ["ZOR", "DESARROLLO", "SOFTWARE", "BACKEND", "TECNICO"]):
            agente = "Subagente_Desarrollo"
        elif any(k in up_t for k in ["NAM", "DISENO", "DISEÑO", "ARTE", "UI", "UX"]):
            agente = "Subagente_Diseno"
        elif any(k in up_t for k in ["ROB", "SEGURIDAD", "CIBER", "AUDIT"]):
            agente = "Subagente_Ciberseguridad"
        elif any(k in up_t for k in ["SAN", "ASISTENCIA", "INTEGRA", "DOCS"]):
            agente = "Subagente_Asistencia"
        
        # Ejecutar flujo maestro de tres capas (Cerebro.md + memoria/ + ChromaDB)
        guardar_cerebro(
            agente=agente,
            tema=f"[{ticket_id}] {descripcion}",
            contenido=contenido,
            herramientas_usadas=herramientas_usadas,
            decisiones=decisiones_clave,
            evidencia_fisica=evidencia_fisica,
            agentes_involucrados=agentes_involucrados
        )
        
        return json.dumps({
            "status": "success",
            "mensaje": f"Solución {ticket_id} vectorizada en ChromaDB con Recibo de Misión, registrada en Cerebro.md y exportada a memoria/ exitosamente."
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error al guardar memoria: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


@tool
def tool_buscar_soluciones(query_semantica: str, n_resultados: int = 2) -> str:
    """
    Busca soluciones previas en la memoria a largo plazo basándose en el significado semántico.
    
    Usa esta herramienta cuando necesites resolver un problema que la tripulación 
    podría haber enfrentado antes, para reutilizar lecciones aprendidas y no reinventar la rueda.
    
    Args:
        query_semantica: Búsqueda en lenguaje natural (ej: "cómo solucionar error de rutas en Docker")
        n_resultados: Cantidad de resultados más similares a devolver (por defecto 2).
    """
    try:
        collection = _get_collection()
        results = collection.query(
            query_texts=[query_semantica],
            n_results=n_resultados
        )
        
        if not results['documents'] or not results['documents'][0]:
            return json.dumps({
                "status": "success",
                "resultados": [],
                "mensaje": "No se encontraron soluciones previas relacionadas con la consulta."
            }, ensure_ascii=False)
            
        soluciones = []
        for i in range(len(results['documents'][0])):
            soluciones.append({
                "ticket_id": results['metadatas'][0][i].get('ticket_id'),
                "descripcion": results['metadatas'][0][i].get('descripcion'),
                "contenido": results['documents'][0][i],
                "distancia": results['distances'][0][i]
            })
            
        return json.dumps({
            "status": "success",
            "resultados": soluciones
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error en búsqueda semántica: {str(e)}"
        }, ensure_ascii=False)


@tool
def consultar_estado_ticket(ticket_id: str) -> str:
    """
    Consulta en la base de datos vectorial (Cerebro) si un ticket específico ya fue cerrado,
    completado y archivado en el historial.
    
    Args:
        ticket_id: ID exacto del ticket a consultar (ej: TKT-001 o TKT-DEV-20261001001)
    """
    try:
        collection = _get_collection()
        results = collection.get(ids=[ticket_id])
        if results and results.get('ids') and len(results['ids']) > 0:
            return json.dumps({
                "status": "success",
                "estado": "CERRADO_Y_ARCHIVADO",
                "mensaje": f"El ticket {ticket_id} ya fue completado, cerrado y vectorizado exitosamente en el historial."
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "not_found",
                "mensaje": f"El ticket {ticket_id} no se encuentra en el archivo histórico."
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "mensaje": f"Error al consultar estado de ticket: {str(e)}"
        }, ensure_ascii=False)
