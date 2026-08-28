import os
import json
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

_APP_ROOT = Path(__file__).resolve().parents[2]
CONTEXTO_DIR = _APP_ROOT / "contexto"
LUFFY_DIR = _APP_ROOT / "Luffy"
ESTADO_ENTREVISTA = LUFFY_DIR / "estado_entrevista.json"

def asegurar_directorios():
    CONTEXTO_DIR.mkdir(exist_ok=True, parents=True)

@tool
def tool_gestionar_entrevista(accion: str, dimensiones_faltantes: str = "", contenido: str = "") -> str:
    """
    Herramienta OBLIGATORIA para gestionar el modo Entrevistador cuando el Capitán pide planear o descubrir una tarea.
    Acciones permitidas:
    - 'iniciar': Crea un nuevo archivo CTX y activa el estado de entrevista.
    - 'actualizar': Agrega la información recolectada del Capitán al archivo CTX actual. DEBES incluir un resumen detallado en `contenido`. Las `dimensiones_faltantes` son los números de las dimensiones que AÚN faltan por preguntar.
    - 'cerrar': Finaliza el modo entrevista, borra el candado y permite continuar con la orquestación normal.
    - 'abortar': Cancela la entrevista y borra el candado.
    """
    asegurar_directorios()
    
    try:
        if accion == "iniciar":
            if ESTADO_ENTREVISTA.exists():
                return "Error: ¡Ya hay una entrevista iniciada! TIENES PROHIBIDO usar 'iniciar'. Usa accion='actualizar' para guardar las respuestas del usuario."
            
            id_ctx = datetime.now().strftime("%Y%m%d%H%M%S")
            ctx_path = CONTEXTO_DIR / f"CTX-{id_ctx}.md"
            
            plantilla = """# CTX-{}: Documento de Descubrimiento

## Checklist de Suficiencia (10 Dimensiones)
- [ ] 1. Identidad Visual y Diseño (UI)
- [ ] 2. Experiencia de Usuario (UX / Animaciones)
- [ ] 3. Objetivo y Propósito de Negocio
- [ ] 4. Entregables Físicos
- [ ] 5. Pila Tecnológica
- [ ] 6. Comportamiento y Casos Borde
- [ ] 7. Restricciones
- [ ] 8. Notificaciones
- [ ] 9. Pruebas y Auditoría
- [ ] 10. Criterios de Aceptación

## Información Recolectada
""".format(id_ctx)
            ctx_path.write_text(plantilla, encoding="utf-8")
            
            estado = {
                "activa": True,
                "ctx_path": str(ctx_path),
                "fecha_inicio": datetime.now().isoformat()
            }
            ESTADO_ENTREVISTA.write_text(json.dumps(estado), encoding="utf-8")
            
            return f"Entrevista iniciada. Archivo de contexto creado en {ctx_path.name}. El sistema ahora está en MODO ENTREVISTADOR."
            
        elif accion == "actualizar":
            if not ESTADO_ENTREVISTA.exists():
                return "Error: No hay una entrevista activa."
            estado = json.loads(ESTADO_ENTREVISTA.read_text(encoding="utf-8"))
            ctx_path = Path(estado["ctx_path"])
            
            if not ctx_path.exists():
                return "Error: El archivo de contexto no existe."
                
            texto_actual = ctx_path.read_text(encoding="utf-8")
            texto_actual += f"\n\n### Actualización {datetime.now().strftime('%H:%M:%S')}\n{contenido}"
            
            # Actualizar checklist rudimentariamente
            import re
            numeros_faltantes = [n.strip() for n in re.split(r'[, ]+', dimensiones_faltantes) if n.strip()]
            for i in range(1, 11):
                if str(i) not in numeros_faltantes:
                    texto_actual = texto_actual.replace(f"- [ ] {i}.", f"- [x] {i}.")
                    
            ctx_path.write_text(texto_actual, encoding="utf-8")
            return f"Contexto actualizado correctamente en {ctx_path.name}."
            
        elif accion == "cerrar":
            if not ESTADO_ENTREVISTA.exists():
                return "Error: No hay una entrevista activa."
            estado = json.loads(ESTADO_ENTREVISTA.read_text(encoding="utf-8"))
            ctx_path = Path(estado["ctx_path"])
            
            if ctx_path.exists():
                texto_actual = ctx_path.read_text(encoding="utf-8")
                texto_actual = texto_actual.replace("# CTX-", "# [FINALIZADO] CTX-")
                ctx_path.write_text(texto_actual, encoding="utf-8")
            
            ESTADO_ENTREVISTA.unlink()
            return f"Entrevista cerrada exitosamente. El contexto reside en {ctx_path.name}. Usa esta información para delegar o crear tickets."
            
        elif accion == "abortar":
            if ESTADO_ENTREVISTA.exists():
                ESTADO_ENTREVISTA.unlink()
            return "Entrevista abortada. Modo orquestador normal restaurado."
            
        else:
            return "Acción no reconocida."
            
    except Exception as e:
        return f"Error gestionando la entrevista: {e}"
