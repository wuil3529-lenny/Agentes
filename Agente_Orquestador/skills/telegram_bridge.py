import os
import sys
import time
import requests

def enviar_mensaje_telegram(mensaje: str, remitente: str = "Luffy") -> str:
    """
    Envía un mensaje a través de Telegram usando el bot y asegura el espejo en la consola.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    res = "Telegram no configurado."
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensaje}
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            res = "Mensaje enviado con éxito."
        except Exception as e:
            res = f"Error enviando mensaje por Telegram: {e}"

    # Espejo automático hacia la consola del Dashboard
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from memory import publicar_mensaje, _cargar_canal
        canal = _cargar_canal("usuario")
        mensajes = canal.get("mensajes", [])
        ya_existe = False
        if mensajes:
            ult = mensajes[-1]
            if ult.get("de") == remitente and ult.get("contenido", {}).get("texto") == mensaje:
                ya_existe = True
        if not ya_existe:
            publicar_mensaje(
                de=remitente,
                para="usuario",
                tipo="mensaje_dashboard",
                contenido={"texto": mensaje},
                canal_tipo="usuario"
            )
    except Exception as e_pub:
        print(f"[telegram_bridge] Error espejeando mensaje a consola: {e_pub}")

    return res

def daemon_mode():
    """
    Bucle principal para leer mensajes de Telegram y pasarlos a la memoria del sistema.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[telegram_bridge] TELEGRAM_BOT_TOKEN no definido. Saliendo gracefully...")
        sys.exit(0)
    
    print("[telegram_bridge] Iniciando puente de Telegram en background...")
    
    # Importar publicar_mensaje para inyectar al canal del usuario
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from memory import publicar_mensaje
    except ImportError:
        print("[telegram_bridge] ⚠️ Advertencia: No se pudo importar 'publicar_mensaje'.")
        publicar_mensaje = None

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0

    while True:
        try:
            r = requests.get(url, params={"timeout": 30, "offset": offset}, timeout=40)
            if r.status_code == 200:
                data = r.json()
                for item in data.get("result", []):
                    offset = item["update_id"] + 1
                    msg = item.get("message", {})
                    texto = msg.get("text", "")
                    if texto:
                        print(f"[telegram_bridge] Comando de usuario recibido: {texto}")
                        if publicar_mensaje:
                            publicar_mensaje("usuario", "Luffy", "mensaje_telegram", {"texto": texto}, "usuario")
            
            time.sleep(1)
        except Exception as e:
            print(f"[telegram_bridge] Error en polling de Telegram: {e}")
            time.sleep(5)

if __name__ == "__main__":
    daemon_mode()
