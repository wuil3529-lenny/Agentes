"""
costos_tracker.py — Rastreador y Registro Real de Consumo de Tokens y Costos
=============================================================================
Intercepta las llamadas de los agentes hacia los modelos de lenguaje (DeepSeek,
OpenAI, Gemini, NVIDIA NIM, Ollama) y acumula en tiempo real los tokens y el
gasto financiero en dashboard/costos.json.
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime

_LOCK = threading.Lock()

# Rutas base dinámicas (compatible con Windows y Linux/Docker)
_CURRENT_DIR = Path(__file__).resolve().parent
_APP_ROOT = _CURRENT_DIR.parent
if str(_APP_ROOT).endswith("app") or not (_APP_ROOT / "dashboard").exists():
    if Path("/app/dashboard").exists():
        _DASHBOARD_DIR = Path("/app/dashboard")
    else:
        _DASHBOARD_DIR = _APP_ROOT / "dashboard"
else:
    _DASHBOARD_DIR = _APP_ROOT / "dashboard"

COSTOS_JSON_PATH = _DASHBOARD_DIR / "costos.json"

# Tarifas por 1,000 tokens (USD)
# Formato: clave_modelo -> (tarifa_prompt_1k, tarifa_completion_1k)
TARIFAS_POR_1K = {
    "deepseek": (0.00014, 0.00028),
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o": (0.00250, 0.01000),
    "gemini": (0.000075, 0.00030),
    "llama": (0.0, 0.0),
    "ollama": (0.0, 0.0),
    "nim": (0.00020, 0.00040),
    "default": (0.00020, 0.00040)
}

def calcular_costo_llamada(tokens_prompt: int, tokens_completion: int, modelo: str = "") -> float:
    """Calcula el costo estimado en USD de una llamada según el modelo."""
    m_lower = (modelo or "").lower()
    tarifa_in, tarifa_out = TARIFAS_POR_1K["default"]
    
    for k, v in TARIFAS_POR_1K.items():
        if k in m_lower:
            tarifa_in, tarifa_out = v
            break
            
    costo_in = (max(0, tokens_prompt) / 1000.0) * tarifa_in
    costo_out = (max(0, tokens_completion) / 1000.0) * tarifa_out
    return round(costo_in + costo_out, 6)

def registrar_consumo_tokens(agente: str, tokens_prompt: int, tokens_completion: int, modelo: str = "") -> dict:
    """
    Registra de forma segura y acumulativa el consumo de tokens y costo en dashboard/costos.json.
    """
    ag_key = (agente or "luffy").strip().lower()
    total_llamada = max(0, tokens_prompt) + max(0, tokens_completion)
    costo_llamada = calcular_costo_llamada(tokens_prompt, tokens_completion, modelo)
    
    if total_llamada <= 0 and costo_llamada <= 0:
        return {}
        
    mes_actual = datetime.now().strftime("%Y-%m")
    
    with _LOCK:
        # Asegurar directorio
        COSTOS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Leer datos actuales
        data = {
            "mes_activo": mes_actual,
            "tokens": 0,
            "costo": 0.0,
            "bloqueado_por_presupuesto": False,
            "presupuesto_maximo": 100.0,
            "agentes": {
                "luffy": {"tokens": 0, "costo": 0.0},
                "zoro": {"tokens": 0, "costo": 0.0},
                "sanji": {"tokens": 0, "costo": 0.0},
                "robin": {"tokens": 0, "costo": 0.0},
                "nami": {"tokens": 0, "costo": 0.0}
            },
            "historial_meses": {}
        }
        
        if COSTOS_JSON_PATH.exists():
            for _ in range(5):
                try:
                    raw = json.loads(COSTOS_JSON_PATH.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        data = raw
                    break
                except Exception:
                    time.sleep(0.05)
                    
        # Inicializar claves requeridas
        data.setdefault("mes_activo", mes_actual)
        data.setdefault("tokens", 0)
        data.setdefault("costo", 0.0)
        data.setdefault("bloqueado_por_presupuesto", False)
        data.setdefault("presupuesto_maximo", 100.0)
        if "agentes" not in data or not isinstance(data["agentes"], dict):
            data["agentes"] = {}
            
        for ag in ["luffy", "zoro", "sanji", "robin", "nami"]:
            if ag not in data["agentes"]:
                data["agentes"][ag] = {"tokens": 0, "costo": 0.0}
                
        if ag_key not in data["agentes"]:
            data["agentes"][ag_key] = {"tokens": 0, "costo": 0.0}
            
        # Acumular
        data["tokens"] = int(data.get("tokens", 0)) + total_llamada
        data["costo"] = round(float(data.get("costo", 0.0)) + costo_llamada, 6)
        
        data["agentes"][ag_key]["tokens"] = int(data["agentes"][ag_key].get("tokens", 0)) + total_llamada
        data["agentes"][ag_key]["costo"] = round(float(data["agentes"][ag_key].get("costo", 0.0)) + costo_llamada, 6)
        
        presupuesto = float(data.get("presupuesto_maximo", 100.0))
        if data["costo"] >= presupuesto:
            data["bloqueado_por_presupuesto"] = True
            
        # Guardar atómicamente
        temp_file = COSTOS_JSON_PATH.parent / f"costos_tmp_{os.getpid()}_{int(time.time()*1000)}.json"
        try:
            temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            temp_file.replace(COSTOS_JSON_PATH)
        except Exception as e_write:
            # Fallback a escritura directa si replace falla
            try:
                COSTOS_JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            if temp_file.exists():
                try: temp_file.unlink()
                except Exception: pass
                
        print(f"[{ag_key.title()}] [TokenTracker] +{total_llamada} tokens (${costo_llamada:.4f}) registrados. Total: {data['tokens']} (${data['costo']:.2f})")
        return {
            "tokens_llamada": total_llamada,
            "costo_llamada": costo_llamada,
            "tokens_total": data["tokens"],
            "costo_total": data["costo"]
        }


# ─── Callback Handler para LangChain ──────────────────────────────────────────
try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult

    class TokenTrackerCallbackHandler(BaseCallbackHandler):
        """
        Callback handler que captura los tokens de uso en llamadas de LangChain / ChatOpenAI.
        """
        def __init__(self, agente: str = "luffy"):
            super().__init__()
            self.agente = agente.lower()

        def on_llm_end(self, response: LLMResult, **kwargs):
            try:
                tokens_in = 0
                tokens_out = 0
                model_name = ""
                
                # A. Buscar en llm_output
                if response.llm_output:
                    model_name = response.llm_output.get("model_name", "")
                    usage = response.llm_output.get("token_usage", {})
                    if usage:
                        tokens_in = usage.get("prompt_tokens", 0) or 0
                        tokens_out = usage.get("completion_tokens", 0) or 0
                    elif "estimated_tokens" in response.llm_output:
                        tokens_in = response.llm_output.get("estimated_tokens", 0) or 0
                        
                # B. Buscar en response_metadata de los mensajes generados
                if (tokens_in == 0 and tokens_out == 0) and response.generations:
                    for gen_list in response.generations:
                        for gen in gen_list:
                            msg = getattr(gen, "message", None)
                            if msg and hasattr(msg, "response_metadata"):
                                meta = msg.response_metadata or {}
                                usage = meta.get("token_usage") or meta.get("usage") or {}
                                if usage:
                                    tokens_in = usage.get("prompt_tokens", 0) or 0
                                    tokens_out = usage.get("completion_tokens", 0) or 0
                                    if not model_name:
                                        model_name = meta.get("model_name", "")

                total = tokens_in + tokens_out
                if total > 0:
                    registrar_consumo_tokens(self.agente, tokens_in, tokens_out, model_name)
            except Exception as e:
                print(f"[{self.agente.title()}] [TokenTracker] Error procesando tokens del LLM: {e}")

except ImportError:
    class TokenTrackerCallbackHandler:
        def __init__(self, agente: str = "luffy"):
            self.agente = agente
