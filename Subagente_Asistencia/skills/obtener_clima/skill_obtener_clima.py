"""
skill_obtener_clima.py — Habilidad de Consulta Meteorológica y Clima en Tiempo Real
===================================================================================
Herramienta de asistencia para consultar las condiciones meteorológicas y el pronóstico
actual de cualquier ciudad del mundo utilizando la API pública y determinística de Open-Meteo
(sin necesidad de claves de API ni dependencias externas propietarias).

Utilidades disponibles:
  - tool_obtener_clima : Obtiene temperatura, condición climática WMO, viento y hora de reporte.
  - obtener_prompt_obtener_clima : System Prompt especializado para inyección bajo demanda.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, Tuple
from langchain_core.tools import tool

# Mensajes controlados y seguros
_MSG_ERROR_GENERICO = (
    "No se pudo obtener el clima debido a un error de conexión con el servicio meteorológico. "
    "Por favor, verifica la conexión a Internet o intenta nuevamente."
)
_MSG_CIUDAD_NO_ENCONTRADA = (
    "No se pudo obtener el clima: la ciudad indicada no fue encontrada "
    "o no pudo ser geolocalizada en el servicio global."
)

# Endpoints oficiales de Open-Meteo
_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Parámetros meteorológicos
_PARAMS_CLIMA = {
    "current_weather": "true",
    "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m",
    "timezone": "auto",
    "forecast_days": "1",
}

# Mapa estándar WMO (World Meteorological Organization) a español
_DESCRIPCIONES_WMO = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna densa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    71: "Nevada ligera",
    73: "Nevada moderada",
    75: "Nevada intensa",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos violentos",
    95: "Tormenta eléctrica",
    96: "Tormenta eléctrica con granizo leve",
    99: "Tormenta eléctrica con granizo severo",
}


def obtener_prompt_obtener_clima() -> str:
    """
    System Prompt especializado y encapsulado para el Asistente Meteorológico y Ambiental.
    """
    return """[🛑 HARD-STOP: MODO ASISTENCIA METEOROLÓGICA Y CONTEXTO AMBIENTAL ACTIVO 🛑]
Eres el Asistente de Información Meteorológica del Subagente de Asistencia.
Tu misión es consultar, sintetizar y contextualizar las condiciones climáticas de cualquier ubicación solicitada con precisión técnica y tono ejecutivo.

DIRECTIVAS OPERATIVAS:
1. PRECISIÓN GEOGRÁFICA:
   - Al recibir una consulta de clima, normaliza el nombre de la ciudad y utiliza `tool_obtener_clima`.
   - Si el usuario menciona un país o estado junto con la ciudad, incluye la ciudad principal como insumo inicial.
2. CONTEXTO AMBIENTAL PARA LA AGENDA:
   - Cuando la consulta provenga de la planificación de una reunión, viaje o evento de calendario, destaca si las condiciones climáticas (lluvias, tormentas o temperaturas extremas) ameritan recomendaciones preventivas o ajustes de horario.
3. FORMATO DE RESPUESTA:
   - Reporta siempre la temperatura en °C, el estado del cielo y la velocidad del viento en km/h de manera concisa y clara.
"""


def _geocodificar_ciudad(ciudad: str) -> Tuple[float, float, str]:
    """
    Convierte el nombre de una ciudad en coordenadas geográficas (latitud, longitud) y su nombre canónico.
    """
    params = urllib.parse.urlencode({
        "name": ciudad.strip(),
        "count": 1,
        "language": "es",
        "format": "json"
    })
    url = f"{_GEOCODING_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Antigravity-Asistencia/3.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
    except Exception:
        raise ValueError(_MSG_ERROR_GENERICO)

    resultados = datos.get("results") or []
    if not resultados:
        raise ValueError(_MSG_CIUDAD_NO_ENCONTRADA)

    primero = resultados[0]
    lat = primero.get("latitude")
    lon = primero.get("longitude")
    nombre_oficial = primero.get("name", ciudad)
    pais = primero.get("country", "")
    ubicacion_completa = f"{nombre_oficial}, {pais}" if pais else nombre_oficial

    if lat is None or lon is None:
        raise ValueError(_MSG_CIUDAD_NO_ENCONTRADA)

    return float(lat), float(lon), ubicacion_completa


def _consultar_clima(lat: float, lon: float) -> Dict[str, Any]:
    """
    Consulta las condiciones meteorológicas en tiempo real en las coordenadas dadas.
    """
    params = urllib.parse.urlencode({**_PARAMS_CLIMA, "latitude": lat, "longitude": lon})
    url = f"{_WEATHER_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Antigravity-Asistencia/3.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        raise ValueError(_MSG_ERROR_GENERICO)


def _formatear_clima(ubicacion: str, datos: Dict[str, Any]) -> str:
    """
    Formatea el reporte meteorológico en texto ejecutivo claro y estructurado.
    """
    actual = datos.get("current_weather") or {}
    temp = actual.get("temperature", "N/D")
    viento = actual.get("windspeed", "N/D")
    codigo = actual.get("weathercode", -1)
    hora = actual.get("time", "Reciente")

    descripcion = _DESCRIPCIONES_WMO.get(codigo, "Condiciones variables")

    lineas = [
        f"🌤️ **Reporte Meteorológico — {ubicacion}**",
        f"- **Temperatura:** {temp} °C",
        f"- **Condición Actual:** {descripcion}",
        f"- **Velocidad del Viento:** {viento} km/h",
        f"- **Hora de Observación:** {hora}",
    ]
    return "\n".join(lineas)


@tool
def tool_obtener_clima(ciudad: str) -> str:
    """
    Obtiene el reporte del clima actual para una ciudad o región específica.

    Args:
        ciudad: Nombre de la ciudad a consultar (ej: 'Madrid', 'Caracas', 'Buenos Aires', 'Tokyo').

    Returns:
        Resumen estructurado con temperatura actual (°C), condición del cielo,
        velocidad del viento y hora de reporte.
    """
    if not ciudad or not ciudad.strip():
        return "Error: Se debe proporcionar el nombre de una ciudad válida para consultar el clima."

    try:
        lat, lon, ubicacion = _geocodificar_ciudad(ciudad)
        datos = _consultar_clima(lat, lon)
        return _formatear_clima(ubicacion, datos)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"{_MSG_ERROR_GENERICO} Detalle: {str(e)}"


# Alias de compatibilidad histórica
tool_obtener_clima_sanji = tool_obtener_clima

__all__ = [
    "tool_obtener_clima",
    "tool_obtener_clima_sanji",
    "obtener_prompt_obtener_clima",
]
