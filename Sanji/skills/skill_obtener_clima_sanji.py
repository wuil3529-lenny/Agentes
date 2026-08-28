"""
skill_obtener_clima_sanji.py — Habilidad de Consulta del Clima (Sanji)
========================================================================
Herramienta para consultar el clima actual de una ciudad usando la API
pública de Open-Meteo (sin necesidad de API key).

Utilidades disponibles:
  - tool_obtener_clima : Obtiene el clima actual de una ciudad (temperatura,
                         humedad, velocidad del viento, descripción, etc.)

Patrón de uso:
    from skill_obtener_clima_sanji import tool_obtener_clima

    clima = tool_obtener_clima("Madrid")
    print(clima)
"""

import json
import urllib.request
import urllib.parse
from langchain_core.tools import tool

# Mensajes de error genéricos y seguros
_MSG_ERROR_GENERICO = (
    "No se pudo obtener el clima. Ocurrió un error inesperado. "
    "Inténtalo de nuevo o contacta al administrador del sistema."
)
_MSG_CIUDAD_NO_ENCONTRADA = (
    "No se pudo obtener el clima: la ciudad indicada no fue encontrada "
    "o no se pudo geolocalizar."
)

# Endpoints de la API pública de Open-Meteo (sin API key)
_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Parámetros por defecto de la consulta meteorológica
_PARAMS_CLIMA = {
    "current_weather": "true",
    "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m",
    "timezone": "auto",
    "forecast_days": "1",
}


def _geocodificar_ciudad(ciudad: str) -> tuple[float, float, str]:
    """
    Convierte el nombre de una ciudad en coordenadas (lat, lon) y su nombre oficial.
    Retorna (latitud, longitud, nombre_ciudad). Lanza ValueError si no se encuentra.
    """
    params = urllib.parse.urlencode({"name": ciudad, "count": 1, "language": "es", "format": "json"})
    url = f"{_GEOCODING_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
    except Exception:
        raise ValueError(_MSG_ERROR_GENERICO)

    resultados = datos.get("results") or []
    if not resultados:
        raise ValueError(_MSG_CIUDAD_NO_ENCONTRADA)

    primero = resultados[0]
    lat = primero.get("latitude")
    lon = primero.get("longitude")
    nombre = primero.get("name", ciudad)
    if lat is None or lon is None:
        raise ValueError(_MSG_CIUDAD_NO_ENCONTRADA)
    return float(lat), float(lon), nombre


def _consultar_clima(lat: float, lon: float) -> dict:
    """Consulta el clima actual en las coordenadas dadas. Retorna un dict con los datos."""
    params = urllib.parse.urlencode({**_PARAMS_CLIMA, "latitude": lat, "longitude": lon})
    url = f"{_WEATHER_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        raise ValueError(_MSG_ERROR_GENERICO)


def _formatear_clima(ciudad: str, datos: dict) -> str:
    """Formatea los datos meteorológicos en un resumen legible."""
    actual = datos.get("current_weather") or {}
    temp = actual.get("temperature")
    viento = actual.get("windspeed")
    codigo = actual.get("weathercode")
    hora = actual.get("time", "desconocida")

    # Mapa de códigos WMO a descripciones en español
    descripciones = {
        0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado",
        3: "Nublado", 45: "Niebla", 48: "Niebla con escarcha",
        51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna densa",
        61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa",
        71: "Nevada ligera", 73: "Nevada moderada", 75: "Nevada intensa",
        80: "Chubascos ligeros", 81: "Chubascos moderados", 82: "Chubascos violentos",
        95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta con granizo fuerte",
    }
    descripcion = descripciones.get(codigo, "Condiciones desconocidas")

    lineas = [
        f"🌤️ Clima actual en {ciudad} (actualizado: {hora}):",
        f"  - Temperatura: {temp} °C",
        f"  - Condición: {descripcion}",
        f"  - Viento: {viento} km/h",
    ]
    return "\n".join(lineas)


@tool
def tool_obtener_clima(ciudad: str) -> str:
    """
    Obtiene el clima actual de una ciudad.

    Args:
        ciudad: Nombre de la ciudad a consultar (ej. "Madrid", "Buenos Aires").

    Returns:
        Un resumen con la temperatura, condición y velocidad del viento actuales,
        o un mensaje de error si la ciudad no se encuentra.
    """
    try:
        lat, lon, nombre = _geocodificar_ciudad(ciudad)
        datos = _consultar_clima(lat, lon)
        return _formatear_clima(nombre, datos)
    except ValueError as e:
        return str(e)
    except Exception:
        return _MSG_ERROR_GENERICO
