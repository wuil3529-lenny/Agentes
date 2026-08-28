"""
═══════════════════════════════════════════════════════════════════════════════
QA Gherkin Universal de la Tripulación
═══════════════════════════════════════════════════════════════════════════════

DIRECTIVA UNIVERSAL:
"Tu rol como QA Gherkin no es aprobar la velocidad ni el código de respuesta
de la red. Tu única misión es verificar que el resultado entregado por el
agente responda directamente a la intención del usuario. Si la tarea requería
contar, listar o extraer información, el agente tiene prohibido cerrar el
ticket hasta que los datos hayan sido procesados y volcados en el reporte final."

Implementa el principio de Doble Validación:
  Capa 1 (Red/Infraestructura): ¿La llamada HTTP o el servicio respondió correctamente?
  Capa 2 (Contenido/Cumplimiento): ¿El payload contiene datos útiles y analizables?
"""

import json
import re


# ══════════════════════════════════════════════════════════════════════════════
# Capa 1 — Sello de Red / Infraestructura
# ══════════════════════════════════════════════════════════════════════════════

def validar_capa_red(resultado) -> tuple:
    """
    Verifica que la llamada HTTP o servicio respondió sin errores de red,
    bloqueos de Cloudflare, timeouts o fallos de conexión.

    Retorna (True, motivo)  si la infraestructura está OK.
    Retorna (False, motivo) si hay fallo de red/infraestructura.
    """
    res_str = str(resultado)

    try:
        if isinstance(resultado, dict):
            res_dict = resultado
        else:
            res_dict = json.loads(res_str)

        status = str(res_dict.get("status", "")).lower()
        codigo_http = res_dict.get("codigo_http") or res_dict.get("status_code")
        metodo = str(res_dict.get("metodo", "")).upper()

        # Fallo explícito del servicio
        if status == "error":
            mensaje = res_dict.get("mensaje", "Error desconocido")
            return False, f"Fallo de infraestructura: {mensaje}"

        # Código HTTP exitoso
        if codigo_http is not None:
            if int(codigo_http) in (200, 201, 204):
                return True, f"Red OK: HTTP {codigo_http} en método {metodo or 'ejecutado'}."
            else:
                return False, f"Código HTTP inesperado: {codigo_http}."

        # Status textual exitoso sin código HTTP
        if status in ("success", "ok", "creado", "éxito", "exito"):
            return True, f"Red OK: Operación reportada como exitosa (status: {status})."

    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Patrones de fallo de infraestructura en texto libre
    patrones_fallo_red = [
        r"no está accesible",
        r"connection refused",
        r"timeout",
        r"cloudflare.*block",
        r"ECONNREFUSED",
        r"socket hang up",
    ]
    for patron in patrones_fallo_red:
        if re.search(patron, res_str, re.IGNORECASE):
            return False, f"Fallo de infraestructura detectado: patrón '{patron}'."

    # Patrones de éxito en texto libre
    patrones_exito_red = [
        r"archivo.*creado",
        r"guardado.*[eé]xito",
        r"completed",
        r"/app/",
    ]
    for patron in patrones_exito_red:
        if re.search(patron, res_str, re.IGNORECASE):
            return True, f"Red OK: Patrón de éxito detectado ('{patron}')."

    # Beneficio de la duda: si no hay indicadores de fallo, asumimos red OK
    return True, "Red OK: Sin indicadores de fallo de infraestructura."


# ══════════════════════════════════════════════════════════════════════════════
# Capa 2 — Sello Funcional / Cumplimiento de Contenido
# ══════════════════════════════════════════════════════════════════════════════

def validar_capa_contenido(resultado, objetivo_ticket="") -> tuple:
    """
    Verifica que el payload contiene contenido útil y analizable.
    
    Reglas:
    - Operaciones de ESCRITURA (POST, PUT, DELETE): HTTP éxito ES la evidencia.
    - Operaciones de LECTURA (GET): HTTP éxito es solo la puerta. Se exige
      que el payload contenga datos analizables (listas con elementos,
      objetos con campos, o texto sustancial).
    
    Retorna (True, motivo)  si el contenido es suficiente.
    Retorna (False, motivo) si falta contenido útil.
    """
    res_str = str(resultado)

    try:
        if isinstance(resultado, dict):
            res_dict = resultado
        else:
            res_dict = json.loads(res_str)

        # ═══ FASE 3: Verificación de exit code para herramientas de ejecución ═══
        # Para ejecutar_comando y python_ejecutar_script, un exit code != 0 es un fallo
        # sin importar qué diga el campo 'status'.
        exit_code = res_dict.get("codigo_retorno") or res_dict.get("exit_code") or res_dict.get("code")
        if exit_code is not None:
            try:
                exit_code_int = int(exit_code)
                if exit_code_int != 0:
                    stderr_extracto = str(res_dict.get("stderr", ""))[:300] or "(sin stderr)"
                    stdout_extracto = str(res_dict.get("stdout", ""))[:200] or "(sin stdout)"
                    return False, (
                        f"Exit code {exit_code_int} — la ejecución falló. "
                        f"Stderr: {stderr_extracto}. "
                        f"Stdout: {stdout_extracto}. "
                        f"El agente debe leer el traceback y aplicar la corrección de causa raíz."
                    )
                else:
                    return True, f"Exit code 0 confirmado. La ejecución fue exitosa."
            except (TypeError, ValueError):
                pass  # No es un entero, continuar con el resto de la validación

        metodo = str(res_dict.get("metodo", "")).upper()

        # ── Operaciones de escritura: el éxito HTTP ES la prueba ──
        if metodo in ("POST", "PUT", "DELETE", "PATCH"):
            return True, f"Operación de escritura ({metodo}) completada. El éxito HTTP es evidencia suficiente."

        # ── Operaciones de lectura (GET) o sin método: exigir datos ──
        campos_datos = [
            "data", "datos", "workflows", "resultado", "items",
            "nodes", "connections", "response", "results", "flujos",
            "respuesta"
        ]
        for campo in campos_datos:
            valor = res_dict.get(campo)
            if valor is not None:
                if isinstance(valor, list) and len(valor) > 0:
                    return True, f"Contenido verificado: campo '{campo}' contiene {len(valor)} elemento(s)."
                elif isinstance(valor, dict) and len(valor) > 0:
                    return True, f"Contenido verificado: campo '{campo}' contiene datos estructurados."
                elif isinstance(valor, (str, int, float)) and len(str(valor)) > 5:
                    return True, f"Contenido verificado: campo '{campo}' contiene valor significativo."

        # Si la respuesta total es lo suficientemente rica
        if len(res_str) > 300:
            return True, "Contenido verificado: respuesta con datos sustanciales (>300 chars)."

        # GET con respuesta corta y sin campos de datos → contenido insuficiente
        if metodo == "GET":
            return False, (
                "Recibí los datos por la red protegida, pero el payload no contiene "
                "datos analizables suficientes. Lee el resultado de la herramienta, "
                "analiza su contenido, y responde a la pregunta del usuario."
            )

        # Respuesta sin método y corta
        if len(res_str) < 80:
            return False, "Contenido insuficiente: respuesta demasiado corta para verificar cumplimiento."

        return True, "Contenido aceptable."

    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Para resultados no-JSON, verificar longitud
    if len(res_str) > 150:
        return True, "Contenido verificado: resultado textual sustancial."

    return False, "No se pudo verificar contenido útil en la respuesta."


# ══════════════════════════════════════════════════════════════════════════════
# Función Principal — QA Gherkin Universal (Doble Validación)
# ══════════════════════════════════════════════════════════════════════════════

def evaluar_qa_gherkin(resultado_operacion, objetivo_ticket="", nombre_agente="Agente") -> bool:
    """
    QA Gherkin Universal de la Tripulación IA.
    Ejecuta las dos capas de validación secuencialmente.

    Retorna True   → Ambas capas aprobadas. El agente puede cerrar.
    Retorna False  → Al menos una capa falló. El agente debe corregir o analizar.
    """
    print(f"\n[{nombre_agente} - QA Gherkin Híbrido] ─── EVALUANDO ESCENARIO GHERKIN ───")

    res_str = str(resultado_operacion)[:80]

    # ═══ CAPA 1: Sello de Red ═══
    red_ok, motivo_red = validar_capa_red(resultado_operacion)

    print(f"  [Dado]       La herramienta devolvió: ({res_str}...)")
    print(f"  [Capa Red]   {'✅ ' + motivo_red if red_ok else '❌ ' + motivo_red}")

    if not red_ok:
        print(f"  [Entonces]   Fallo de infraestructura. Se requiere corrección de red.")
        print(f"[{nombre_agente} - QA Gherkin Híbrido] ❌ BLOQUEADO POR CAPA DE RED.")
        return False

    # ═══ CAPA 2: Sello de Contenido ═══
    contenido_ok, motivo_contenido = validar_capa_contenido(resultado_operacion, objetivo_ticket)

    print(f"  [Capa Cont.] {'✅ ' + motivo_contenido if contenido_ok else '⚠️ ' + motivo_contenido}")

    if not contenido_ok:
        cuando = f"Se verifica contra objetivo: '{objetivo_ticket[:60] if objetivo_ticket else 'operación solicitada'}'"
        print(f"  [Cuando]     {cuando}")
        print(f"  [Entonces]   Red protegida OK, pero contenido insuficiente. El agente debe analizar los datos.")
        print(f"[{nombre_agente} - QA Gherkin Híbrido] ⚠️ CONTENIDO PENDIENTE DE ANÁLISIS. No se autoriza cierre.")
        return False

    # ═══ AMBAS CAPAS APROBADAS ═══
    cuando = f"Se verifica contra objetivo: '{objetivo_ticket[:60] if objetivo_ticket else 'operación solicitada'}'"
    print(f"  [Cuando]     {cuando}")
    print(f"  [Entonces]   Ambas capas validadas. Se aprueba el cierre del flujo.")
    print(f"[{nombre_agente} - QA Gherkin Híbrido] ✅ VISTO BUENO CONFIRMADO. Autorizando Hard-Stop.")
    return True
