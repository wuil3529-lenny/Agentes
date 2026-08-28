import os
import time
from openai import OpenAI

def call_nim_with_fallback(api_key, model_1, model_2, prompt, system_prompt=""):
    """
    Llama a la API de NVIDIA NIM utilizando un modelo principal con reintentos.
    Si falla, salta automáticamente al modelo de respaldo.
    """
    if not api_key or api_key == "YOUR_NVIDIA_API_KEY_HERE":
        print("[NIM Client] ERROR: API Key no configurada o inválida.")
        return None

    base_url = "https://api.deepseek.com/v1" if "deepseek" in model_1 else "https://integrate.api.nvidia.com/v1"
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Intentos con Modelo 1 (Retry Logic)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[NIM Client] Solicitando a {model_1} (Intento {attempt+1})...")
            response = client.chat.completions.create(
                model=model_1,
                messages=messages,
                temperature=0.2,
                max_tokens=2048,
                timeout=30
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[NIM Client] Error con modelo 1 ({model_1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[NIM Client] Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            
    # Fallback a Modelo 2
    print(f"\n[NIM Client] ALERTA: Modelo 1 fallo. Iniciando Fallback a {model_2}...\n")
    try:
        response = client.chat.completions.create(
            model=model_2,
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
            timeout=30
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[NIM Client] Error fatal con modelo 2 ({model_2}): {e}")
        return None
