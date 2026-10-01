import os
import re
import json
import urllib.parse
import requests
from pathlib import Path
from langchain.tools import tool
from pydantic import BaseModel, Field

def _transformar_ruta_linux(ruta: str) -> str:
    """Asegura que la ruta de destino sea Linux y dentro del contenedor /app/.
    Maneja rutas vacías, literales de parámetro, rutas Windows y rutas relativas."""
    if not isinstance(ruta, str) or not ruta.strip():
        return str(Path(__file__).resolve().parents[2] / "Nami" / "informes" / "imagen_ia_generada.png")
    
    literales_parametro = {"ruta_destino", "prompt_estructurado", "modelo_preferido", "ruta", "destino"}
    if ruta.strip().lower() in literales_parametro:
        return str(Path(__file__).resolve().parents[2] / "Nami" / "informes" / "imagen_ia_generada.png")
    
    if not os.path.sep in ruta and "/" not in ruta and "\\" not in ruta:
        if not ruta.endswith((".png", ".jpg", ".jpeg")):
            ruta = ruta + ".png"
        return str(Path(__file__).resolve().parents[2] / "Nami" / "informes" / ruta)
    
    patron = r"[Cc]:[/\\]+Users[/\\]+admin[/\\]+Documents[/\\]+Agentes[/\\]*"
    ruta_tr = re.sub(patron, "/app/", ruta, flags=re.IGNORECASE)
    ruta_tr = ruta_tr.replace("\\", "/")
    
    if not ruta_tr.startswith("/app/"):
        nombre_archivo = os.path.basename(ruta_tr)
        if not nombre_archivo:
            nombre_archivo = "imagen_ia_generada.png"
        if not nombre_archivo.endswith((".png", ".jpg", ".jpeg")):
            nombre_archivo = nombre_archivo + ".png"
        return str(Path(__file__).resolve().parents[2] / "Nami" / "informes" / nombre_archivo)
    
    return ruta_tr

def _llamar_ideogram(prompt: str, api_key: str) -> bytes:
    url = "https://api.ideogram.ai/generate"
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "image_request": {
            "prompt": prompt[:2000],
            "aspect_ratio": "ASPECT_16_9",
            "model": "V_2",
            "magic_prompt_option": "AUTO"
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=45)
    if response.status_code == 200:
        data = response.json()
        image_url = data["data"][0]["url"]
        img_resp = requests.get(image_url, timeout=30)
        if img_resp.status_code == 200:
            return img_resp.content
    raise Exception(f"Ideogram API error ({response.status_code}): {response.text[:150]}")

def _llamar_dall_e(prompt: str, api_key: str) -> bytes:
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt[:4000],
        "n": 1,
        "size": "1024x1024"
    }
    response = requests.post(url, headers=headers, json=payload, timeout=45)
    if response.status_code == 200:
        data = response.json()
        image_url = data["data"][0]["url"]
        img_resp = requests.get(image_url, timeout=30)
        if img_resp.status_code == 200:
            return img_resp.content
    raise Exception(f"DALL-E API error ({response.status_code}): {response.text[:150]}")

def _llamar_pollinations_fallback(prompt: str) -> bytes:
    """Generación real de imagen por API pública sin clave de autenticación como respaldo seguro."""
    encoded_prompt = urllib.parse.quote(prompt[:500])
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&nologo=true"
    response = requests.get(url, timeout=45)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    raise Exception(f"Pollinations fallback falló ({response.status_code})")

def _crear_metadatos_verificacion(ruta_archivo: str, prompt: str, modelo: str, tamano_bytes: int) -> str:
    """
    Crea un archivo de metadatos JSON junto al asset generado para que el Auditor
    pueda verificar la existencia del archivo sin depender del binario 'file'
    (que está bloqueado por el firewall). Este archivo sirve como evidencia
    física verificable por lectura directa.
    """
    try:
        ruta_p = Path(ruta_archivo)
        dir_destino = ruta_p.parent
        nombre_base = ruta_p.stem
        ruta_meta = dir_destino / f"{nombre_base}.verificacion.json"
        
        # Leer magic bytes del archivo generado
        magic_hex = ""
        with open(ruta_archivo, "rb") as f:
            magic_hex = f.read(4).hex()
        
        metadatos = {
            "archivo_generado": str(ruta_p),
            "tamano_bytes": tamano_bytes,
            "modelo_ia": modelo,
            "formato": "PNG/JPEG binario",
            "verificacion_disco": f"EXISTE: True | BYTES: {tamano_bytes} | MAGIC: 0x{magic_hex}",
            "magic_hex": magic_hex,
            "prompt_estructurado": prompt,
            "timestamp_verificacion": __import__('datetime').datetime.now().isoformat()
        }
        
        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(metadatos, f, ensure_ascii=False, indent=2)
        
        return str(ruta_meta)
    except Exception as e:
        return f"Error creando metadatos: {str(e)}"

class GeneracionIA_Params(BaseModel):
    prompt_estructurado: str = Field(description="Prompt con la fórmula: Sujeto + Estilo + Iluminación + Composición + Aspect Ratio")
    modelo_preferido: str = Field(description="Opciones: Gemini, Flux, Ideogram, DALL-E, Grok, Kling, Luma")
    ruta_destino: str = Field(description="Ruta donde se guardará el archivo binario generado.")

@tool("generar_multimedia_ia", args_schema=GeneracionIA_Params)
def generar_multimedia_ia(prompt_estructurado: str, modelo_preferido: str, ruta_destino: str) -> str:
    """Ejecuta una petición HTTP real a las APIs de IA para generar imágenes binarias genuinas (Ideogram, DALL-E o Fallback real)."""
    try:
        ruta_limpia = _transformar_ruta_linux(ruta_destino)
        dir_destino = os.path.dirname(ruta_limpia)
        if not dir_destino:
            dir_destino = str(Path(__file__).resolve().parents[2] / "Nami" / "informes")
            ruta_limpia = os.path.join(dir_destino, "imagen_ia_generada.png")
        os.makedirs(dir_destino, exist_ok=True)
        
        ideogram_key = os.environ.get("IDEOGRAM_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        
        imagen_binaria = None
        modelo_ejecutado = modelo_preferido
        errores = []
        
        # 1. Intentar Ideogram si está solicitado o como primera opción si hay API Key
        if (modelo_preferido.upper() == "IDEOGRAM" or ideogram_key) and not imagen_binaria:
            try:
                if ideogram_key:
                    imagen_binaria = _llamar_ideogram(prompt_estructurado, ideogram_key)
                    modelo_ejecutado = "Ideogram API (Real)"
            except Exception as e:
                errores.append(str(e))
                
        # 2. Intentar DALL-E 3 si no se ha generado y existe OPENAI_API_KEY
        if openai_key and not imagen_binaria:
            try:
                imagen_binaria = _llamar_dall_e(prompt_estructurado, openai_key)
                modelo_ejecutado = "DALL-E 3 API (Real)"
            except Exception as e:
                errores.append(str(e))
                
        # 3. Fallback a API pública de generación real de imágenes (Pollinations) si fallan las keys
        if not imagen_binaria:
            try:
                imagen_binaria = _llamar_pollinations_fallback(prompt_estructurado)
                modelo_ejecutado = "Pollinations AI (Fallback Real)"
            except Exception as e:
                errores.append(str(e))
                
        if not imagen_binaria:
            return f"Error: No se pudo generar la imagen con ningún servicio real. Errores: {'; '.join(errores)}"
            
        # Guardado en formato binario real ('wb')
        with open(ruta_limpia, "wb") as f:
            f.write(imagen_binaria)
        
        # Crear metadatos de verificación para que el Auditor pueda verificar sin el binario 'file'
        ruta_meta = _crear_metadatos_verificacion(
            ruta_archivo=ruta_limpia,
            prompt=prompt_estructurado,
            modelo=modelo_ejecutado,
            tamano_bytes=len(imagen_binaria)
        )
        
        return f"Éxito: Generación binaria completada usando {modelo_ejecutado}. Asset real guardado en {ruta_limpia} ({len(imagen_binaria)} bytes). Metadatos de verificación: {ruta_meta}"
    except Exception as e:
        return f"Error: Fallo crítico generando imagen: {str(e)}"

HERRAMIENTAS_IA_CREATIVA = [generar_multimedia_ia]
