import os
import sys
from pathlib import Path
_APP_ROOT = Path(__file__).resolve().parents[2]
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Asegurar importaciones relativas
sys.path.insert(0, str(_APP_ROOT / "Luffy"))
from memory import _cargar_canal, publicar_mensaje, _cargar_bitacora, _cargar_cerebro, registrar_bitacora
from nim_client import call_nim_with_fallback

# --- Configuraciones ---
MAX_MENSAJES_BUCLE = 15
TIEMPO_BUCLE_MINUTOS = 10


def auditar_consistencia_ssot():
    """
    Verifica que las tareas marcadas como completadas existan tanto en el Canal como en la Bitácora.
    """
    bitacora = _cargar_bitacora()
    canal = _cargar_canal("interno")
    mensajes = canal.get("mensajes", [])

    # Obtener eventos de los últimos 10 minutos
    ahora = datetime.now()
    hace_poco = ahora - timedelta(minutes=10)

    # 1. Completados en Bitácora sin mensaje en el Canal
    completados_bitacora = [b for b in bitacora if b.get("estado") == "COMPLETADO"]
    for b in completados_bitacora[-5:]:
        try:
            t_bit = datetime.fromisoformat(b["timestamp"])
            if t_bit >= hace_poco:
                agente = b["agente"]
                # Buscar si hay un mensaje completado de este agente en los ultimos 10 min
                tiene_canal = any(m for m in mensajes if m.get("tipo") == "completado" and m.get("de") == agente and datetime.fromisoformat(m["timestamp"]) >= hace_poco)
                
                if not tiene_canal:
                    print(f"[Supervisor] Inconsistencia SSOT detectada: {agente} marcó completado en Bitácora pero no reportó en Canal.")
                    notificar_agente_inconsistencia(agente, "Marcaste una tarea como COMPLETADA en la Bitácora, pero olvidaste enviar el reporte oficial por el Canal de Comunicación.")
        except:
            pass

    # 2. Completados en Canal sin mensaje en la Bitácora
    completados_canal = [m for m in mensajes if m.get("tipo") == "completado"]
    for m in completados_canal[-5:]:
        try:
            t_msg = datetime.fromisoformat(m["timestamp"])
            if t_msg >= hace_poco:
                agente = m["de"]
                # Buscar si hay entrada en bitacora
                tiene_bitacora = any(b for b in completados_bitacora if b["agente"] == agente and datetime.fromisoformat(b["timestamp"]) >= hace_poco)
                
                if not tiene_bitacora:
                    print(f"[Supervisor] Inconsistencia SSOT detectada: {agente} reportó completado en Canal pero no actualizó la Bitácora.")
                    notificar_agente_inconsistencia(agente, "Enviaste un reporte de 'completado' por el Canal, pero olvidaste actualizar el estado de tu tarea a COMPLETADO en la Bitácora.")
        except:
            pass

def notificar_agente_inconsistencia(agente, razon):
    contenido_msg = {
        "texto": f"SUPERVISOR ALERTA: {razon} Recuerda que la arquitectura SSOT exige que actualices todos los pilares. Por favor, corrige esto inmediatamente."
    }
    publicar_mensaje(de="Luffy (Supervisor)", para=agente, tipo="delegacion", contenido=contenido_msg)
    registrar_bitacora(agente, "Corregir inconsistencia en los pilares SSOT reportada por el Supervisor.", "PENDIENTE")

def detectar_bucles_y_desvios(api_key, model_1, model_2):
    """
    Frena bucles si superan el límite.
    Bloquea tareas inventadas (desvíos) usando LLM.
    """
    canal = _cargar_canal("interno")
    mensajes = canal.get("mensajes", [])
    
    if not mensajes: return

    # --- 1. Detectar Bucles ---
    ahora = datetime.now()
    hace_bucle = ahora - timedelta(minutes=TIEMPO_BUCLE_MINUTOS)
    mensajes_recientes = [m for m in mensajes if m.get("tipo") != "silencio"]
    
    # Contar mensajes en el marco de tiempo
    recientes_tiempo = []
    for m in mensajes_recientes:
        try:
            if datetime.fromisoformat(m["timestamp"]) >= hace_bucle:
                recientes_tiempo.append(m)
        except:
            pass
            
    if len(recientes_tiempo) > MAX_MENSAJES_BUCLE:
        print("[Supervisor] Bucle masivo detectado. Forzando silencio.")
        enviar_alerta_telegram(f"⚠️ Alerta: Posible bucle infinito o saturación en el canal. {len(recientes_tiempo)} mensajes en {TIEMPO_BUCLE_MINUTOS} minutos. Se forzará una pausa.")
        publicar_mensaje(de="Luffy (Supervisor)", para="Tripulación", tipo="error", contenido={"texto": "SISTEMA: Demasiados mensajes en poco tiempo. TODOS LOS AGENTES DEBEN HACER SILENCIO Y ESPERAR ÓRDENES DEL CAPITÁN."})
        return

    # --- 2. Detectar Desvíos en Delegaciones ---
    # Revisamos el último mensaje si es de delegación
    ultimo = mensajes[-1]
    if ultimo.get("tipo") == "delegacion" and ultimo.get("de") not in ["Usuario", "Luffy (Supervisor)", "Luffy", "Luffy (Capitán)", "Sistema"]:
        # Vamos a preguntarle al LLM si esta delegación está justificada por la Bitácora/Canal del Usuario
        # Obtener el último objetivo del usuario
        canal_user = _cargar_canal("usuario")
        user_msgs = [m for m in canal_user.get("mensajes", []) if m.get("de") == "Usuario"]
        ultimo_objetivo = user_msgs[-1]["contenido"]["texto"] if user_msgs else "Ningún objetivo definido."
        
        prompt = f"""
Objetivo actual del usuario: "{ultimo_objetivo}"

El agente {ultimo['de']} acaba de delegar la siguiente tarea a {ultimo['para']}:
{json.dumps(ultimo['contenido'])}

Teniendo en cuenta que los agentes SÓLO pueden delegar tareas si están directamente relacionadas con cumplir el objetivo del usuario (ej. dividir el trabajo en pasos técnicos para lograrlo), pero NO pueden inventar tareas nuevas post-objetivo.

¿Esta delegación es válida y necesaria para cumplir el objetivo del usuario? 
Responde ÚNICAMENTE con un JSON: {{"valida": true, "razon": "..."}} o {{"valida": false, "razon": "..."}}
"""
        try:
            respuesta = call_nim_with_fallback(api_key, model_1, model_2, prompt, "Eres un supervisor estricto.")
            if "```json" in respuesta:
                respuesta = respuesta.split("```json")[1].split("```")[0].strip()
            evaluacion = json.loads(respuesta)
            
            if not evaluacion.get("valida"):
                print(f"[Supervisor] Delegación no autorizada de {ultimo['de']}. Bloqueando.")
                enviar_alerta_telegram(f"⛔ Supervisor bloqueó una delegación de {ultimo['de']} hacia {ultimo['para']} por desvío de objetivo.\nRazón: {evaluacion.get('razon')}")
                publicar_mensaje(de="Luffy (Supervisor)", para=ultimo["de"], tipo="error", contenido={"texto": f"SISTEMA: Delegación rechazada. Tarea inventada o no alineada con el objetivo del usuario. Razón: {evaluacion.get('razon')}"})
        except Exception as e:
            print(f"[Supervisor] Error evaluando desvío: {e}")


def enviar_alerta_telegram(texto):
    """
    Envía una alerta al telegram del usuario.
    """
    try:
        from telegram_bridge import send_message
        send_message(texto)
        print(f"[Supervisor] Alerta enviada a Telegram: {texto}")
    except Exception as e:
        print(f"[Supervisor] Fallo enviando a Telegram: {e}")

def ejecutar_supervision(api_key, model_1, model_2):
    print("[Supervisor] Ejecutando rutinas de supervisión...")
    auditar_consistencia_ssot()
    detectar_bucles_y_desvios(api_key, model_1, model_2)
    
    print("[Supervisor] Sincronizando el cerebro y el orden de los archivos...")
    try:
        import subprocess
        import sys
        subprocess.run([sys.executable, str(_APP_ROOT / "Luffy" / "sync_cerebro.py")], check=True)
        print("[Supervisor] ✅ Sincronización del cerebro completada con éxito.")
    except Exception as e:
        print(f"[Supervisor] ❌ Error durante la sincronización: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv((_APP_ROOT / ".env"))
    ak = os.getenv("NVIDIA_API_KEY_LUFFY")
    m1 = os.getenv("MODEL_LUFFY_1")
    m2 = os.getenv("MODEL_LUFFY_2")
    ejecutar_supervision(ak, m1, m2)
