import re
from pathlib import Path

def limpiar_pizarra_luffy(id_ticket: str) -> str:
    ruta_bitacora = Path("/app/Bitacora.md")
    if not ruta_bitacora.exists():
        return "Error: Bitacora.md no existe."
        
    try:
        texto = ruta_bitacora.read_text(encoding="utf-8")
        
        bloques = re.split(r'(?m)^##\s+', texto)
        if len(bloques) <= 1:
            return f"No se encontraron tickets en la pizarra."
            
        header = bloques[0]
        tickets = bloques[1:]
        
        nuevos_tickets = []
        encontrado = False
        ticket_borrado_contenido = ""
        
        for bloque in tickets:
            if bloque.strip().startswith(id_ticket):
                encontrado = True
                ticket_borrado_contenido = "## " + bloque
            else:
                nuevos_tickets.append("## " + bloque)
                
        if encontrado:
            # 1. Actualizar pizarra primero
            nuevo_texto = header + "".join(nuevos_tickets)
            nuevo_texto = re.sub(r'\n{3,}', '\n\n', nuevo_texto)
            ruta_bitacora.write_text(nuevo_texto, encoding="utf-8")
            
            # 2. Archivar en Tickets_Archivados.md (SIEMPRE, no en try opcional)
            ruta_archivados = Path("/app/memoria/Tickets_Archivados.md")
            ruta_archivados.parent.mkdir(parents=True, exist_ok=True)
            contenido_sin_links = re.sub(r'\[\[(.*?)\]\]', r'[\1]', ticket_borrado_contenido)
            with open(ruta_archivados, "a", encoding="utf-8") as f:
                f.write("\n\n" + contenido_sin_links.strip())
            
            # 3. Vectorizar en ChromaDB (intento, no bloquea si falla)
            try:
                import sys
                import os
                skills_path = Path(__file__).parent
                if str(skills_path) not in sys.path:
                    sys.path.insert(0, str(skills_path))
                from skill_memoria_vectorial import tool_guardar_solucion
                
                desc = "Ticket archivado: " + id_ticket
                match_obj = re.search(r'\*\*Objetivo:\*\*\s*(.+)', ticket_borrado_contenido)
                if match_obj:
                    desc = match_obj.group(1).strip()
                    
                tool_guardar_solucion(id_ticket, desc, ticket_borrado_contenido)
                rag_msg = "vectorizado en ChromaDB"
            except Exception as e_rag:
                print(f"[Warning] Error vectorizando ticket {id_ticket}: {e_rag}")
                rag_msg = "ChromaDB no disponible (vectorizacion omitida)"
                
            return f"Ticket {id_ticket} eliminado de la pizarra, archivado en Tickets_Archivados.md y {rag_msg} exitosamente."
        else:
            return f"No se encontro el ticket {id_ticket} en la pizarra."
            
    except Exception as e:
        return f"Error al limpiar la pizarra: {e}"
