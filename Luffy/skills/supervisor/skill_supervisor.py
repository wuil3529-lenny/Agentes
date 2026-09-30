import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime, timedelta

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() == "luffy" else _CURRENT.parents[2]

# Asegurar importaciones relativas
sys.path.insert(0, str(_APP_ROOT / "Luffy"))
try:
    from memory import _cargar_canal, publicar_mensaje, _cargar_bitacora, _cargar_cerebro, registrar_bitacora
except ImportError:
    _cargar_canal = None
    publicar_mensaje = None
    _cargar_bitacora = None
    _cargar_cerebro = None
    registrar_bitacora = None

try:
    from nim_client import call_nim_with_fallback
except ImportError:
    call_nim_with_fallback = None

# --- Configuraciones ---
MAX_MENSAJES_BUCLE = 15
TIEMPO_BUCLE_MINUTOS = 10


def auditar_tickets_pizarra():
    """
    Lee Bitacora.md e informa si la pizarra tiene tickets abiertos o si está limpia.
    """
    bitacora_path = _APP_ROOT / "Bitacora.md"
    if not bitacora_path.exists():
        print("[Supervisor] ℹ️ Bitacora.md no existe.")
        return []

    try:
        texto = bitacora_path.read_text(encoding="utf-8")
        bloques = re.split(r"(?=## TKT-[A-Z0-9\-]+(?:[^\n]*)\n)", texto)
        tickets_abiertos = []
        
        for bloque in bloques:
            bloque = bloque.strip()
            if not bloque.startswith("## TKT-"):
                continue
            
            m_id = re.search(r"(## TKT-[A-Z0-9\-]+)", bloque)
            m_tarea = re.search(r"\n(?:-?\s*\*\*|###\s*)Tarea[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            m_resp = re.search(r"\n(?:-?\s*\*\*|###\s*)Responsable[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            m_estado = re.search(r"\n(?:-?\s*\*\*|###\s*)Estado[:\*\*]*\s*(.*?)(?=\n(?:-?\s*\*\*|###)|$)", "\n" + bloque, re.DOTALL | re.IGNORECASE)
            
            t_id = m_id.group(1).replace("## ", "").strip() if m_id else "DESCONOCIDO"
            tarea = m_tarea.group(1).strip() if m_tarea else "N/A"
            resp = m_resp.group(1).strip() if m_resp else "N/A"
            estado = m_estado.group(1).split("\n")[0].strip() if m_estado else "DESCONOCIDO"
            
            if estado.upper() not in ["CERRADO", "ARCHIVADO"]:
                tickets_abiertos.append({
                    "id": t_id,
                    "tarea": tarea,
                    "responsable": resp,
                    "estado": estado
                })
        
        if tickets_abiertos:
            print(f"[Supervisor] 📋 Auditoría de Pizarra: {len(tickets_abiertos)} ticket(s) abierto(s):")
            for t in tickets_abiertos:
                print(f"  - [{t['id']}] ({t['responsable']}) [{t['estado']}]: {t['tarea'][:80]}")
        else:
            print("[Supervisor] 🟢 Auditoría de Pizarra: Tablero limpio. No hay tickets abiertos ni pendientes.")
            
        return tickets_abiertos
    except Exception as e:
        print(f"[Supervisor] ⚠️ Error auditando tickets de la pizarra: {e}")
        return []


def auditar_consistencia_ssot():
    """
    Verifica que las tareas marcadas como completadas existan tanto en el Canal como en la Bitácora.
    """
    if not _cargar_bitacora or not _cargar_canal:
        return
        
    try:
        bitacora = _cargar_bitacora()
        canal = _cargar_canal("interno")
        mensajes = canal.get("mensajes", [])

        ahora = datetime.now()
        hace_poco = ahora - timedelta(minutes=10)

        completados_bitacora = [b for b in bitacora if b.get("estado") == "COMPLETADO"]
        for b in completados_bitacora[-5:]:
            try:
                t_bit = datetime.fromisoformat(b["timestamp"])
                if t_bit >= hace_poco:
                    agente = b["agente"]
                    tiene_canal = any(m for m in mensajes if m.get("tipo") == "completado" and m.get("de") == agente and datetime.fromisoformat(m["timestamp"]) >= hace_poco)
                    
                    if not tiene_canal:
                        print(f"[Supervisor] Inconsistencia SSOT detectada: {agente} marcó completado en Bitácora pero no reportó en Canal.")
                        notificar_agente_inconsistencia(agente, "Marcaste una tarea como COMPLETADA en la Bitácora, pero olvidaste enviar el reporte oficial por el Canal de Comunicación.")
            except:
                pass

        completados_canal = [m for m in mensajes if m.get("tipo") == "completado"]
        for m in completados_canal[-5:]:
            try:
                t_msg = datetime.fromisoformat(m["timestamp"])
                if t_msg >= hace_poco:
                    agente = m["de"]
                    tiene_bitacora = any(b for b in completados_bitacora if b["agente"] == agente and datetime.fromisoformat(b["timestamp"]) >= hace_poco)
                    
                    if not tiene_bitacora:
                        print(f"[Supervisor] Inconsistencia SSOT detectada: {agente} reportó completado en Canal pero no actualizó la Bitácora.")
                        notificar_agente_inconsistencia(agente, "Enviaste un reporte de 'completado' por el Canal, pero olvidaste actualizar el estado de tu tarea a COMPLETADO en la Bitácora.")
            except:
                pass
    except Exception:
        pass


def notificar_agente_inconsistencia(agente, razon):
    if not publicar_mensaje or not registrar_bitacora:
        return
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
    if not _cargar_canal or not call_nim_with_fallback:
        return
        
    try:
        canal = _cargar_canal("interno")
        mensajes = canal.get("mensajes", [])
        
        if not mensajes: return

        ahora = datetime.now()
        hace_bucle = ahora - timedelta(minutes=TIEMPO_BUCLE_MINUTOS)
        mensajes_recientes = [m for m in mensajes if m.get("tipo") != "silencio"]
        
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
            if publicar_mensaje:
                publicar_mensaje(de="Luffy (Supervisor)", para="Tripulación", tipo="error", contenido={"texto": "SISTEMA: Demasiados mensajes en poco tiempo. TODOS LOS AGENTES DEBEN HACER SILENCIO Y ESPERAR ÓRDENES DEL CAPITÁN."})
            return

        ultimo = mensajes[-1]
        if ultimo.get("tipo") == "delegacion" and ultimo.get("de") not in ["Usuario", "Luffy (Supervisor)", "Luffy", "Luffy (Capitán)", "Sistema"]:
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
                    if publicar_mensaje:
                        publicar_mensaje(de="Luffy (Supervisor)", para=ultimo["de"], tipo="error", contenido={"texto": f"SISTEMA: Delegación rechazada. Tarea inventada o no alineada con el objetivo del usuario. Razón: {evaluacion.get('razon')}"})
            except Exception as e:
                print(f"[Supervisor] Error evaluando desvío: {e}")
    except Exception:
        pass


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


def sincronizar_grafo_obsidian():
    """
    Ejecuta sync_cerebro.py para organizar el grafo y notas de Obsidian.
    """
    print("[Supervisor] 🌐 Sincronizando el cerebro y organizando el grafo de Obsidian...")
    try:
        import subprocess
        script_sync = str(_APP_ROOT / "Luffy" / "sync_cerebro.py")
        res = subprocess.run([sys.executable, script_sync], capture_output=True, text=True, check=True)
        for line in res.stdout.strip().split("\n"):
            if line.strip():
                print(f"  [Obsidian Sync] {line.strip()}")
        print("[Supervisor] ✅ Grafo y notas de Obsidian organizados con éxito.")
    except Exception as e:
        print(f"[Supervisor] ❌ Error durante la sincronización de Obsidian: {e}")


def ejecutar_supervision(api_key=None, model_1="deepseek-chat", model_2="deepseek-chat"):
    """
    Rutina completa del modo supervisor ejecutada al final del turno de Luffy.
    """
    print("\n[Supervisor] 👁️  Iniciando modo supervisor de la tripulación...")
    auditar_tickets_pizarra()
    auditar_consistencia_ssot()
    if api_key:
        detectar_bucles_y_desvios(api_key, model_1, model_2)
    sincronizar_grafo_obsidian()
    print("[Supervisor] ✅ Modo supervisor completado.\n")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv((_APP_ROOT / ".env"))
    ak = os.getenv("NVIDIA_API_KEY_LUFFY")
    m1 = os.getenv("MODEL_LUFFY_1", "deepseek-chat")
    m2 = os.getenv("MODEL_LUFFY_2", "deepseek-chat")
    ejecutar_supervision(ak, m1, m2)
