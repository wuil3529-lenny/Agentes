"""
skill_memoria_vectorial.py — Memoria a Largo Plazo con Base de Datos Vectorial
============================================================================
Permite a Luffy indexar y buscar historial y soluciones previas usando ChromaDB.
"""

import os
import json
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DB_PATH = str(_APP_ROOT / "Luffy" / "data" / "chroma_db")

def _get_collection():
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        # Usaremos el modelo por defecto de Chroma (all-MiniLM-L6-v2) que se descarga automáticamente
        # si se instalan las dependencias (sentence-transformers).
        sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        collection = client.get_or_create_collection(
            name="historial_tripulacion",
            embedding_function=sentence_transformer_ef
        )
        return collection
    except ImportError:
        raise ImportError("ChromaDB o sentence-transformers no están instalados. Asegúrate de ejecutar 'pip install chromadb sentence-transformers'.")

@tool
def tool_guardar_solucion(ticket_id: str, descripcion: str, contenido: str) -> str:
    """
    Guarda la resolución de un ticket en la memoria vectorial a largo plazo.
    
    Args:
        ticket_id: ID único del ticket (ej: TKT-ZORO-1234)
        descripcion: Resumen breve de qué trata el problema y solución.
        contenido: El bloque del ticket completo, código o lección aprendida.
    """
    try:
        import sys
        from pathlib import Path
        import json
        
        # Encontrar directorio Luffy
        _ROOT = Path(__file__).resolve().parents[2]
        luffy_dir = str(_ROOT / "Luffy")
        if luffy_dir not in sys.path:
            sys.path.insert(0, luffy_dir)
            
        from memory import guardar_cerebro
        
        # Derivar agente
        agente = "Luffy"
        up_t = ticket_id.upper()
        if "ZOR" in up_t: agente = "Zoro"
        elif "NAM" in up_t: agente = "Nami"
        elif "ROB" in up_t: agente = "Robin"
        elif "SAN" in up_t: agente = "Sanji"
        
        # Ejecutar el flujo maestro (Cerebro.md + archivo en memoria/ + ChromaDB)
        guardar_cerebro(agente, f"[{ticket_id}] {descripcion}", contenido)
        
        return json.dumps({"status": "success", "mensaje": f"Solución {ticket_id} vectorizada en ChromaDB, registrada en Cerebro.md y exportada a memoria/ exitosamente."})
    except Exception as e:
        import traceback
        return json.dumps({"status": "error", "mensaje": f"Error al guardar memoria: {str(e)} | {traceback.format_exc()}"})

@tool
def tool_buscar_soluciones(query_semantica: str, n_resultados: int = 2) -> str:
    """
    Busca soluciones previas en la memoria a largo plazo basándose en el significado.
    
    Usa esta herramienta cuando un usuario te pida resolver un problema que la tripulación 
    podría haber enfrentado antes, para no reinventar la rueda.
    
    Args:
        query_semantica: Tu búsqueda en lenguaje natural (ej: "cómo solucionar el error de rutas en Docker")
        n_resultados: Cantidad de resultados similares a devolver (por defecto 2).
    """
    try:
        collection = _get_collection()
        results = collection.query(
            query_texts=[query_semantica],
            n_results=n_resultados
        )
        
        if not results['documents'] or not results['documents'][0]:
            return json.dumps({"status": "success", "resultados": [], "mensaje": "No se encontraron soluciones previas."})
            
        soluciones = []
        for i in range(len(results['documents'][0])):
            soluciones.append({
                "ticket_id": results['metadatas'][0][i].get('ticket_id'),
                "descripcion": results['metadatas'][0][i].get('descripcion'),
                "contenido": results['documents'][0][i],
                "distancia": results['distances'][0][i]
            })
            
        return json.dumps({"status": "success", "resultados": soluciones})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})

@tool
def consultar_estado_ticket(ticket_id: str) -> str:
    """
    Consulta en la base de datos vectorial (Cerebro) si un ticket especifico (ej. TKT-ZORO-123) ya fue cerrado/completado.
    Usalo cuando estes validando si los agentes hijos terminaron su trabajo y sus tickets ya no estan en Bitacora.md.
    """
    try:
        collection = _get_collection()
        results = collection.get(
            ids=[ticket_id]
        )
        if results and results.get('ids') and len(results['ids']) > 0:
            return json.dumps({
                "status": "success",
                "estado": "CERRADO_Y_ARCHIVADO",
                "mensaje": f"El ticket {ticket_id} ya fue completado, cerrado y vectorizado exitosamente en el historial."
            })
        else:
            return json.dumps({
                "status": "not_found",
                "mensaje": f"El ticket {ticket_id} no se encuentra en el archivo historico."
            })
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})
