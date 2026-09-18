"""
Plantilla de Habilidad / Herramienta para Agentes de la Tripulación.
Regla Estricta: Código tipado y cero excepciones no controladas.
"""
from typing import Any, Dict, Optional

def ejecutar_herramienta(parametro_principal: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    [Descripción breve de lo que hace la función según el drafting]
    
    Args:
        parametro_principal (str): [Descripción de la entrada]
        config (Dict, opcional): Configuraciones adicionales permitidas.
        
    Returns:
        str: El resultado de la operación o un mensaje de error estrictamente controlado.
    """
    try:
        # 1. Validación de Límites de Seguridad (Hard-Stops)
        if not parametro_principal:
            return "ERROR_CONTROLADO: El parámetro de entrada no puede estar vacío."
        
        # 2. Lógica principal de la herramienta
        # [AQUÍ VA EL CÓDIGO IMPLEMENTADO POR LUFFY]
        resultado = f"Operación ejecutada exitosamente sobre: {parametro_principal}"
        
        # 3. Retornar el resultado estructurado
        return resultado
        
    except Exception as e:
        # CAPTURA FINAL (Cero excepciones arrojadas al sistema)
        return f"ERROR_CRITICO: Fallo interno en la herramienta. Detalle: {str(e)}"
