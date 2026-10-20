"""
puente_manos_ojos.py — Puente de Automatización Visual y Control de PC / Web (Host Windows)
=============================================================================================
Provee 'Manos y Ojos' para la flota de agentes:
  1. OJOS (Visión & Inspección):
     - Captura de pantalla en tiempo real de la PC Windows (.NET CopyFromScreen).
     - Captura de pantalla de páginas web (Playwright).
     - Análisis visual multimodal por IA (VLM NVIDIA Llama 3.2 Vision).
     - Extracción de contenido, tablas y accesibilidad web.
  2. MANOS (Acción & Control):
     - Navegación web en Chromium visible o silencioso (Headful / Headless).
     - Rellenado inteligente de formularios web (por label, placeholder, name, id o CSS).
     - Clics en botones, enlaces y tabs web.
     - Control del ratón en la PC (mover, clic, doble clic, scroll con PyAutoGUI).
     - Control del teclado en la PC (escribir texto, atajos de teclado, hotkeys).
     - Lanzamiento de aplicaciones del sistema.
"""

import os
import sys
import time
import json
import base64
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

_DASHBOARD_DIR = Path(__file__).resolve().parent
_APP_ROOT = _DASHBOARD_DIR.parent
_ENV_PATH = _APP_ROOT / ".env"
load_dotenv(_ENV_PATH)

# Directorios de salida
ARCHIVOS_TEMPORALES = _APP_ROOT / "Archivos_temporales"
ARCHIVOS_TEMPORALES.mkdir(parents=True, exist_ok=True)
STATIC_CAPTURAS = _DASHBOARD_DIR / "static" / "capturas"
STATIC_CAPTURAS.mkdir(parents=True, exist_ok=True)


def purgar_capturas_antiguas(max_antiguedad_horas: float = 12.0, max_archivos: int = 25) -> Dict[str, Any]:
    """
    Higienizador de espacio en disco: purga capturas temporales web y de escritorio
    en Archivos_temporales y dashboard/static/capturas para evitar saturación de almacenamiento.
    Mantiene únicamente las últimas `max_archivos` capturas más recientes.
    """
    carpetas = [STATIC_CAPTURAS, ARCHIVOS_TEMPORALES]
    ahora = time.time()
    segundos_limite = max_antiguedad_horas * 3600
    eliminados = 0
    bytes_liberados = 0

    for carpeta in carpetas:
        if not carpeta.exists():
            continue
        archivos = []
        try:
            for f in carpeta.iterdir():
                if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"] and (
                    f.name.startswith("web_") or f.name.startswith("pantalla_") or f.name.startswith("captura_")
                ):
                    try:
                        archivos.append((f.stat().st_mtime, f.stat().st_size, f))
                    except Exception:
                        pass
        except Exception:
            continue

        # Ordenar de más reciente a más antiguo
        archivos.sort(key=lambda x: x[0], reverse=True)

        for idx, (mtime, size, fpath) in enumerate(archivos):
            edad = ahora - mtime
            if idx >= max_archivos or edad > segundos_limite:
                try:
                    fpath.unlink(missing_ok=True)
                    eliminados += 1
                    bytes_liberados += size
                except Exception:
                    pass

    mb_liberados = round(bytes_liberados / (1024 * 1024), 2)
    return {
        "status": "success",
        "archivos_eliminados": eliminados,
        "espacio_liberado_mb": mb_liberados,
        "mensaje": f"Purga de capturas completada: {eliminados} archivos eliminados ({mb_liberados} MB liberados)."
    }



# ══════════════════════════════════════════════════════════════════════════════
# 1. GESTOR DE NAVEGADOR WEB VISIBLE (PLAYWRIGHT)
# ══════════════════════════════════════════════════════════════════════════════

from concurrent.futures import ThreadPoolExecutor

# Hilo dedicado único para Playwright (Greenlet / Thread Safety).
# Garantiza que todas las llamadas de Playwright ocurran estrictamente en el mismo hilo del SO.
_PLAYWRIGHT_WORKER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PlaywrightWorker")


class GestorNavegadorWeb:
    """
    Controlador singleton para mantener la sesión de Chromium abierta de forma visible
    mientras los agentes interactúan, navegan o rellenan formularios.
    Todas las operaciones se delegan a un hilo dedicado para evitar colisiones de hilos en Greenlet.
    """
    _instancia = None

    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._proc = None
        self._visible = True

    @classmethod
    def obtener_instancia(cls):
        if cls._instancia is None:
            cls._instancia = GestorNavegadorWeb()
        return cls._instancia

    def _ejecutar(self, func, *args, **kwargs):
        """
        Ejecuta cualquier llamada a Playwright estrictamente en el hilo dedicado único.
        """
        def _wrapper():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                # Si ocurrió desconexión de CDP o error de hilo, resetear para reconectar en el próximo intento
                if any(k in err_msg.lower() for k in ["closed", "disconnected", "thread", "greenlet"]):
                    try:
                        self._page = None
                        self._context = None
                        if self._browser:
                            try:
                                self._browser.close()
                            except Exception:
                                pass
                        self._browser = None
                        if self._pw:
                            try:
                                self._pw.stop()
                            except Exception:
                                pass
                        self._pw = None
                    except Exception:
                        pass
                return {"status": "error", "mensaje": f"Fallo en navegador: {err_msg}"}

        future = _PLAYWRIGHT_WORKER.submit(_wrapper)
        return future.result(timeout=65)

    def _seleccionar_mejor_pagina(self, pages: List[Any]) -> Optional[Any]:
        """
        Selecciona inteligentemente la pestaña activa de trabajo.
        Prioriza páginas web reales que el usuario desea automatizar (Computrabajo, YouTube, etc.)
        por encima del propio Dashboard (localhost:8000) o páginas en blanco (about:blank).
        """
        if self._page is not None:
            try:
                if not self._page.is_closed():
                    u = (self._page.url or "").lower()
                    # Solo conservar si NO es el propio dashboard de control ni about:blank
                    if u and u != "about:blank" and "localhost:8000" not in u and "127.0.0.1:8000" not in u:
                        return self._page
            except Exception:
                pass

        abiertas = [p for p in pages if not p.is_closed()]
        if not abiertas:
            return None

        # 1. Prioridad máxima: Sitios externos de trabajo (no dashboard ni about:blank)
        for p in reversed(abiertas):
            try:
                u = (p.url or "").lower()
                if u and u != "about:blank" and "localhost:8000" not in u and "127.0.0.1:8000" not in u:
                    return p
            except Exception:
                pass

        # 2. Prioridad secundaria: Cualquier página con contenido
        for p in reversed(abiertas):
            try:
                u = (p.url or "").lower()
                if u and u != "about:blank":
                    return p
            except Exception:
                pass

        return abiertas[0]


    def _asegurar_navegador(self, visible: bool = True):
        from playwright.sync_api import sync_playwright
        if self._pw is None:
            self._pw = sync_playwright().start()

        recrear = False
        if self._browser is None:
            recrear = True
        else:
            try:
                if not self._browser.is_connected():
                    recrear = True
            except Exception:
                recrear = True

        if recrear:
            self._visible = visible
            if visible and sys.platform == "win32":
                edge_paths = [
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                ]
                browser_exe = next((p for p in edge_paths if Path(p).exists()), None)
                user_data = ARCHIVOS_TEMPORALES / "browser_visible_profile"
                user_data.mkdir(parents=True, exist_ok=True)

                conectado = False
                try:
                    self._browser = self._pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=2000)
                    conectado = True
                    print("[Puente Manos y Ojos] Reutilizando sesión CDP de Edge interactiva activa.", flush=True)
                except Exception:
                    pass

                if not conectado:
                    # Cerrar procesos huérfanos solo si no hay conexión
                    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], shell=False, capture_output=True)
                    time.sleep(1.0)

                    batch_path = ARCHIVOS_TEMPORALES / "launch_edge_interactive.bat"
                    # Compatibilidad Python < 3.12: el backslash no puede ir dentro de la f-string
                    _user_data_win = str(user_data).replace("/", "\\")
                    _batch_linea = (
                        '@echo off\r\nstart "" "' + str(browser_exe) + '"'
                        ' --remote-debugging-port=9222'
                        ' --user-data-dir="' + _user_data_win + '"'
                        ' --start-maximized --no-first-run --no-default-browser-check'
                        ' --disable-sync about:blank\r\n'
                    )
                    with open(batch_path, "w", encoding="utf-8") as f:
                        f.write(_batch_linea)

                    task_name = "TripulacionNavegadorInteractivo"
                    # H-04: argumentos como lista, sin interprete de shell
                    subprocess.run(
                        ["schtasks", "/Create", "/TN", task_name,
                         "/TR", 'cmd.exe /c "%s"' % str(batch_path),
                         "/SC", "ONCE", "/ST", "23:59", "/F", "/IT"],
                        shell=False, capture_output=True
                    )
                    subprocess.run(["schtasks", "/Run", "/TN", task_name], shell=False, capture_output=True)
                    print("[Puente Manos y Ojos] Edge lanzado en pantalla interactiva (WinSta0\\Default) vía Programador de Tareas", flush=True)

                    for i in range(20):
                        time.sleep(0.5)
                        try:
                            self._browser = self._pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=2000)
                            conectado = True
                            print(f"[Puente Manos y Ojos] CDP conectado exitosamente en intento {i+1}", flush=True)
                            break
                        except Exception:
                            pass

                if conectado:
                    contexts = self._browser.contexts
                    self._context = contexts[0] if contexts else self._browser.new_context()
                    self._page = self._seleccionar_mejor_pagina(self._context.pages) or (self._context.pages[0] if self._context.pages else self._context.new_page())
                else:
                    raise RuntimeError("No fue posible abrir o conectar con la ventana interactiva de Microsoft Edge en la pantalla del usuario.")
            else:
                self._browser = self._pw.chromium.launch(
                    headless=not visible,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
                )
                self._context = self._browser.new_context(no_viewport=True)
                self._page = self._context.new_page()

        if self._context and self._context.pages:
            reval = False
            if self._page is None or self._page.is_closed():
                reval = True
            else:
                try:
                    curr_u = (self._page.url or "").lower()
                    if curr_u == "about:blank" or "localhost:8000" in curr_u or "127.0.0.1:8000" in curr_u:
                        mejor = self._seleccionar_mejor_pagina(self._context.pages)
                        if mejor and mejor != self._page:
                            self._page = mejor
                except Exception:
                    reval = True
            if reval:
                self._page = self._seleccionar_mejor_pagina(self._context.pages) or (self._context.pages[0] if self._context.pages else self._context.new_page())

        return self._page


    # ── MÉTODOS PRIVADOS (EJECUTADOS EN HILO PLAYWRIGHT DEDICADO) ──────────────

    def _navegar_impl(self, url: str, visible: bool = True) -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=visible)
            # Higiene de ventanas: cerrar pestañas huérfanas en blanco o secundarias redundantes
            if self._context and len(self._context.pages) > 1:
                for p in list(self._context.pages):
                    if p != page and not p.is_closed():
                        u = (p.url or "").lower()
                        if u in ["about:blank", "chrome://newtab/", "edge://newtab/"] or not u:
                            try:
                                p.close()
                            except Exception:
                                pass

            if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("file:///"):
                url = "https://" + url

            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)

            timestamp = int(time.time())
            filename = f"web_nav_{timestamp}.png"
            out_path = ARCHIVOS_TEMPORALES / filename
            static_path = STATIC_CAPTURAS / filename
            try:
                page.screenshot(path=str(out_path))
                page.screenshot(path=str(static_path))
                purgar_capturas_antiguas(max_antiguedad_horas=12.0, max_archivos=25)
            except Exception:
                pass

            return {
                "status": "success",
                "url": page.url,
                "titulo": page.title(),
                "status_http": resp.status if resp else 200,
                "captura": f"/static/capturas/{filename}",
                "captura_local": str(out_path)
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al navegar a {url}: {str(e)}"}

    def _rellenar_formulario_impl(self, campos: Dict[str, Any], selector_envio: Optional[str] = None) -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=self._visible)
            if not page or page.is_closed():
                return {"status": "error", "mensaje": "No hay ninguna página web abierta actualmente."}

            paginas_antes = set(self._context.pages) if self._context else set()
            resultados = []

            for key, valor in campos.items():
                str_val = str(valor)
                exito = False

                # 1. Por selector CSS directo
                if key.startswith("#") or key.startswith(".") or key.startswith("input") or key.startswith("textarea") or "[" in key:
                    try:
                        el = page.locator(key).first
                        if el.count() > 0:
                            el.scroll_into_view_if_needed(timeout=2000)
                            el.click(timeout=3000)
                            el.fill(str_val, timeout=3000)
                            resultados.append({"campo": key, "estado": "rellenado_por_selector"})
                            exito = True
                    except Exception:
                        pass

                # 2. Por Label visible
                if not exito:
                    try:
                        el = page.get_by_label(key, exact=False).first
                        if el.count() > 0:
                            el.scroll_into_view_if_needed(timeout=2000)
                            el.click(timeout=3000)
                            el.fill(str_val, timeout=3000)
                            resultados.append({"campo": key, "estado": "rellenado_por_label"})
                            exito = True
                    except Exception:
                        pass

                # 3. Por Placeholder
                if not exito:
                    try:
                        el = page.get_by_placeholder(key, exact=False).first
                        if el.count() > 0:
                            el.scroll_into_view_if_needed(timeout=2000)
                            el.click(timeout=3000)
                            el.fill(str_val, timeout=3000)
                            resultados.append({"campo": key, "estado": "rellenado_por_placeholder"})
                            exito = True
                    except Exception:
                        pass

                # 4. Por atributos (name, aria-label, id) o tipos comunes (Google / Auth / Computrabajo)
                if not exito:
                    locators = [
                        f"input[name='{key}']",
                        f"textarea[name='{key}']",
                        f"[aria-label*='{key}' i]",
                        f"input[id='{key}']",
                        f"input[type='email']" if any(w in key.lower() for w in ["email", "correo", "usuario"]) else None,
                        f"input[type='password']" if any(w in key.lower() for w in ["pass", "clave", "contra", "seguridad"]) else None,
                        "input#identifierId" if any(w in key.lower() for w in ["email", "correo", "google"]) else None,
                        "input[name='Passwd']" if any(w in key.lower() for w in ["pass", "clave", "contra"]) else None,
                    ]
                    for loc in locators:
                        if not loc:
                            continue
                        try:
                            el = page.locator(loc).first
                            if el.count() > 0 and el.is_visible():
                                el.scroll_into_view_if_needed(timeout=2000)
                                el.click(timeout=3000)
                                el.fill(str_val, timeout=3000)
                                resultados.append({"campo": key, "estado": f"rellenado_por_{loc}"})
                                exito = True
                                break
                        except Exception:
                            pass

                # 5. Fallback con foco activo o evaluación en DOM
                if not exito:
                    try:
                        filled = page.evaluate("""([k, val]) => {
                            const norm = s => (s || '').toLowerCase().trim();
                            const target = norm(k);
                            const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea'));
                            for (const inp of inputs) {
                                const id = norm(inp.id);
                                const name = norm(inp.name);
                                const ph = norm(inp.placeholder);
                                const aria = norm(inp.getAttribute('aria-label'));
                                if (id === target || name === target || ph === target || aria === target ||
                                    id.includes(target) || name.includes(target) || ph.includes(target)) {
                                    inp.focus();
                                    inp.value = val;
                                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                                    return true;
                                }
                            }
                            return false;
                        }""", [key, str_val])
                        if filled:
                            resultados.append({"campo": key, "estado": "rellenado_por_dom"})
                            exito = True
                    except Exception:
                        pass

                if not exito:
                    resultados.append({"campo": key, "estado": "no_encontrado"})

                if self._visible:
                    page.wait_for_timeout(350)

            # Envío de formulario si se especificó botón o selector
            envio_realizado = False
            if selector_envio:
                try:
                    if selector_envio.strip().lower() in ["enter", "intro", "{enter}"]:
                        page.keyboard.press("Enter")
                        envio_realizado = True
                        page.wait_for_timeout(2000)
                    else:
                        res_clic = self._hacer_clic_impl(selector_envio)
                        envio_realizado = (res_clic.get("status") == "success")
                except Exception as e:
                    resultados.append({"envio_error": str(e)})

            # Detectar si se abrió una nueva pestaña o ventana emergente
            if self._context:
                paginas_nuevas = [p for p in self._context.pages if p not in paginas_antes and not p.is_closed()]
                if paginas_nuevas:
                    self._page = paginas_nuevas[-1]
                    page = self._page

            page.wait_for_timeout(1000)
            timestamp = int(time.time())
            filename = f"web_form_{timestamp}.png"
            out_path = ARCHIVOS_TEMPORALES / filename
            static_path = STATIC_CAPTURAS / filename
            try:
                page.screenshot(path=str(out_path))
                page.screenshot(path=str(static_path))
            except Exception:
                pass

            return {
                "status": "success",
                "url_actual": page.url,
                "titulo": page.title(),
                "campos_procesados": resultados,
                "envio_ejecutado": envio_realizado,
                "captura": f"/static/capturas/{filename}",
                "captura_local": str(out_path)
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al rellenar formulario: {str(e)}"}

    def _hacer_clic_impl(self, selector_o_texto: str) -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=self._visible)
            if not page or page.is_closed():
                return {"status": "error", "mensaje": "No hay ninguna página web abierta."}

            paginas_antes = set(self._context.pages) if self._context else set()
            clic_hecho = False
            target_texto = selector_o_texto.strip()

            # Atajo especial para presionar Enter o Escape en la página activa
            if target_texto.lower() in ["enter", "intro", "{enter}"]:
                page.keyboard.press("Enter")
                clic_hecho = True
            elif target_texto.lower() in ["escape", "esc", "{esc}"]:
                page.keyboard.press("Escape")
                clic_hecho = True

            # 1. Intentar por selector CSS directo (#id, .class, tag[attr])
            if not clic_hecho and (target_texto.startswith("#") or target_texto.startswith(".") or "[" in target_texto):
                try:
                    loc = page.locator(target_texto).first
                    if loc.count() > 0:
                        try:
                            loc.scroll_into_view_if_needed(timeout=2000)
                        except Exception:
                            pass
                        try:
                            loc.click(timeout=3000)
                        except Exception:
                            loc.click(force=True, timeout=3000)
                        clic_hecho = True
                except Exception:
                    pass

            # 2. Intentar por rol accesible (button, link, tab, menuitem, checkbox, radio)
            if not clic_hecho:
                for rol in ["button", "link", "tab", "menuitem", "checkbox", "radio"]:
                    try:
                        el = page.get_by_role(rol, name=target_texto, exact=False).first
                        if el.count() > 0:
                            try:
                                el.scroll_into_view_if_needed(timeout=2000)
                            except Exception:
                                pass
                            try:
                                el.click(timeout=3000)
                            except Exception:
                                el.click(force=True, timeout=3000)
                            clic_hecho = True
                            break
                    except Exception:
                        pass

            # 3. Intentar por texto visible en cualquier elemento interactivo
            if not clic_hecho:
                try:
                    el = page.get_by_text(target_texto, exact=False).first
                    if el.count() > 0:
                        try:
                            el.scroll_into_view_if_needed(timeout=2000)
                        except Exception:
                            pass
                        try:
                            el.click(timeout=3000)
                        except Exception:
                            el.click(force=True, timeout=3000)
                        clic_hecho = True
                except Exception:
                    pass

            # 4. Fallback DOM/JavaScript (crucial para SPANs como .b_google, .b_primary_inv, divs y botones personalizados)
            if not clic_hecho:
                try:
                    clicked = page.evaluate("""(txt) => {
                        const norm = s => (s || '').toLowerCase().trim();
                        const target = norm(txt);
                        const candidates = Array.from(document.querySelectorAll('a, button, span, div, p, input[type=\"button\"], input[type=\"submit\"]'));
                        for (const el of candidates) {
                            const content = norm(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '');
                            if (content && (content === target || content.includes(target)) && el.offsetParent !== null) {
                                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }""", target_texto)
                    if clicked:
                        clic_hecho = True
                except Exception:
                    pass

            if not clic_hecho:
                return {"status": "error", "mensaje": f"No se encontró el elemento '{selector_o_texto}' para hacer clic."}

            page.wait_for_timeout(1500)

            # Auto-detectar si se abrió una nueva pestaña o ventana emergente (ej. Popup de Google Login)
            if self._context:
                paginas_nuevas = [p for p in self._context.pages if p not in paginas_antes and not p.is_closed()]
                if paginas_nuevas:
                    self._page = paginas_nuevas[-1]
                    page = self._page

            timestamp = int(time.time())
            filename = f"web_click_{timestamp}.png"
            out_path = ARCHIVOS_TEMPORALES / filename
            static_path = STATIC_CAPTURAS / filename
            try:
                page.screenshot(path=str(out_path))
                page.screenshot(path=str(static_path))
                purgar_capturas_antiguas(max_antiguedad_horas=12.0, max_archivos=25)
            except Exception:
                pass

            return {
                "status": "success",
                "elemento": selector_o_texto,
                "url_actual": page.url,
                "titulo": page.title(),
                "captura_local": str(out_path),
                "captura": f"/static/capturas/{filename}"
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al hacer clic: {str(e)}"}

    def _controlar_media_impl(self, accion: str = "reproducir") -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=True)
            if not page or page.is_closed():
                return {"status": "error", "mensaje": "No hay ninguna página web abierta actualmente."}

            acc = (accion or "reproducir").strip().lower()

            res_info = page.evaluate("""(acc) => {
                const v = document.querySelector('video');
                const fsBtn = document.querySelector('.ytp-fullscreen-button') || document.querySelector('[aria-label*="pantalla completa" i]') || document.querySelector('[title*="pantalla completa" i]');
                const playBtn = document.querySelector('.ytp-play-button') || document.querySelector('[aria-label*="reproducir" i]') || document.querySelector('[aria-label*="pausar" i]');
                const muteBtn = document.querySelector('.ytp-mute-button') || document.querySelector('[aria-label*="silenciar" i]');

                let res = { accion: acc, ok: true, detalle: "" };

                if (acc === 'pantalla_completa' || acc === 'fullscreen') {
                    if (fsBtn) {
                        fsBtn.click();
                        res.detalle = "Clic ejecutado en botón de pantalla completa";
                    } else if (v && v.requestFullscreen) {
                        v.requestFullscreen();
                        res.detalle = "requestFullscreen ejecutado en video";
                    } else {
                        res.ok = false;
                        res.detalle = "No se encontró control de pantalla completa";
                    }
                } else if (acc === 'reproducir' || acc === 'play') {
                    if (v && v.paused) {
                        if (playBtn) playBtn.click();
                        else v.play();
                        res.detalle = "Reproducción iniciada";
                    } else if (v && !v.paused) {
                        res.detalle = "El video ya está reproduciéndose";
                    } else if (playBtn) {
                        playBtn.click();
                        res.detalle = "Clic en botón play";
                    }
                } else if (acc === 'pausar' || acc === 'pause') {
                    if (v && !v.paused) {
                        if (playBtn) playBtn.click();
                        else v.pause();
                        res.detalle = "Video pausado";
                    } else if (v && v.paused) {
                        res.detalle = "El video ya estaba pausado";
                    } else if (playBtn) {
                        playBtn.click();
                        res.detalle = "Clic en botón pausa";
                    }
                } else if (acc === 'alternar' || acc === 'toggle') {
                    if (playBtn) {
                        playBtn.click();
                        res.detalle = "Play/Pausa alternado";
                    } else if (v) {
                        if (v.paused) v.play(); else v.pause();
                        res.detalle = v.paused ? "Pausado" : "Reproduciendo";
                    }
                } else if (acc === 'silenciar' || acc === 'mute') {
                    if (muteBtn) {
                        muteBtn.click();
                        res.detalle = "Silencio alternado";
                    } else if (v) {
                        v.muted = !v.muted;
                        res.detalle = v.muted ? "Silenciado" : "Audio activado";
                    }
                } else if (acc === 'adelantar') {
                    if (v) { v.currentTime += 10; res.detalle = "+10 segundos"; }
                } else if (acc === 'retroceder') {
                    if (v) { v.currentTime -= 10; res.detalle = "-10 segundos"; }
                }

                res.estado_video = {
                    hay_video: !!v,
                    pausado: v ? v.paused : null,
                    tiempo_actual: v ? v.currentTime : null,
                    pantalla_completa: !!document.fullscreenElement
                };
                return res;
            }""", acc)

            if acc in ['pantalla_completa', 'fullscreen'] and not res_info.get("estado_video", {}).get("pantalla_completa"):
                page.keyboard.press("f")
                page.wait_for_timeout(300)
                res_info["tecla_f_enviada"] = True
            elif acc in ['reproducir', 'play'] and res_info.get("estado_video", {}).get("pausado"):
                page.keyboard.press("k")
                page.wait_for_timeout(300)
                res_info["tecla_k_enviada"] = True

            return {"status": "success", "resultado": res_info}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al controlar media: {str(e)}"}

    def _gestionar_pestanas_impl(self, accion: str = "listar", url: str = "", indice: int = 0) -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=True)
            if not self._context:
                return {"status": "error", "mensaje": "No hay contexto de navegador abierto."}

            pages = [p for p in self._context.pages if not p.is_closed()]
            acc = (accion or "listar").strip().lower()

            if acc == "listar":
                lista = []
                for idx, p in enumerate(pages):
                    try:
                        lista.append({
                            "indice": idx,
                            "titulo": p.title(),
                            "url": p.url,
                            "activa": (p == self._page)
                        })
                    except Exception:
                        pass
                return {"status": "success", "pestañas": lista, "total": len(lista)}

            elif acc == "nueva":
                nueva = self._context.new_page()
                self._page = nueva
                if url:
                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = "https://" + url
                    nueva.goto(url, wait_until="domcontentloaded", timeout=30000)
                return {
                    "status": "success", 
                    "mensaje": "Nueva pestaña abierta exitosamente", 
                    "titulo": nueva.title(),
                    "url": nueva.url,
                    "total_pestañas": len(self._context.pages)
                }

            elif acc == "cerrar":
                target = pages[indice] if (0 <= indice < len(pages)) else self._page
                if target:
                    target.close()
                restantes = [p for p in self._context.pages if not p.is_closed()]
                self._page = restantes[-1] if restantes else None
                return {"status": "success", "mensaje": "Pestaña cerrada.", "total_pestañas": len(restantes)}

            elif acc in ["cerrar_otras", "limpiar", "sanear"]:
                cerradas = 0
                for p in pages:
                    if p != self._page and not p.is_closed():
                        try:
                            p.close()
                            cerradas += 1
                        except Exception:
                            pass
                restantes = [p for p in self._context.pages if not p.is_closed()]
                return {
                    "status": "success",
                    "mensaje": f"Higiene de ventanas completada: se cerraron {cerradas} pestañas redundantes.",
                    "total_pestañas": len(restantes)
                }

            elif acc in ["cerrar_todas", "apagar", "salir"]:
                cerradas = 0
                for p in pages:
                    if not p.is_closed():
                        try:
                            p.close()
                            cerradas += 1
                        except Exception:
                            pass
                self._page = None
                return {
                    "status": "success",
                    "mensaje": f"Todas las pestañas han sido cerradas ({cerradas} cerradas).",
                    "total_pestañas": 0
                }
            else:
                return {"status": "error", "mensaje": f"Acción '{accion}' no reconocida. Usa 'listar', 'nueva', 'cerrar', 'cerrar_otras', 'cerrar_todas', 'cambiar'."}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al gestionar pestañas: {str(e)}"}

    def _extraer_contenido_impl(self, selector: Optional[str] = None) -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=self._visible)
            if not page or page.is_closed():
                return {"status": "error", "mensaje": "No hay página web abierta."}

            if selector:
                loc = page.locator(selector).first
                texto = loc.inner_text() if loc.count() > 0 else "Selector no encontrado."
            else:
                texto = page.evaluate("""() => {
                    const clone = document.body.cloneNode(true);
                    const toRemove = clone.querySelectorAll('script, style, noscript, nav, footer, svg');
                    toRemove.forEach(el => el.remove());
                    return clone.innerText.replace(/\\n\\s*\\n/g, '\\n').trim();
                }""")

            formularios = page.evaluate("""() => {
                const forms = [];
                document.querySelectorAll('form').forEach((f, idx) => {
                    const inputs = [];
                    f.querySelectorAll('input, textarea, select').forEach(inp => {
                        inputs.push({
                            tag: inp.tagName.toLowerCase(),
                            type: inp.type || 'text',
                            name: inp.name || '',
                            id: inp.id || '',
                            placeholder: inp.placeholder || '',
                            value: inp.value || '',
                            label: inp.labels && inp.labels[0] ? inp.labels[0].innerText : ''
                        });
                    });
                    forms.push({ form_idx: idx, inputs: inputs });
                });
                return forms;
            }""")

            ofertas = page.evaluate("""() => {
                const cards = Array.from(document.querySelectorAll('article.box_offer, article'));
                return cards.map(c => {
                    const titleEl = c.querySelector('h2 a, h1 a, h2, h1, .title, a');
                    const compEl = c.querySelector('.fc_base, .company, [data-gtm-name]');
                    const locEl = c.querySelector('.fs14, .location, .fc_sub');
                    return {
                        titulo: titleEl ? titleEl.innerText.trim() : '',
                        empresa: compEl ? compEl.innerText.trim() : '',
                        ubicacion: locEl ? locEl.innerText.trim() : '',
                        texto: c.innerText.replace(/\\n+/g, ' | ').trim().slice(0, 300)
                    };
                }).filter(o => o.titulo.length > 2);
            }""")

            return {
                "status": "success",
                "titulo": page.title(),
                "url": page.url,
                "contenido_texto": texto[:4000],
                "formularios_detectados": formularios,
                "ofertas_laborales": ofertas
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al extraer contenido: {str(e)}"}

    def _capturar_pantalla_impl(self) -> Dict[str, Any]:
        try:
            page = self._asegurar_navegador(visible=self._visible)
            if not page or page.is_closed():
                return {"status": "error", "mensaje": "No hay página web abierta."}
            timestamp = int(time.time())
            filename = f"web_captura_{timestamp}.png"
            out_path = ARCHIVOS_TEMPORALES / filename
            static_path = STATIC_CAPTURAS / filename
            page.screenshot(path=str(out_path), full_page=False)
            try:
                page.screenshot(path=str(static_path), full_page=False)
                purgar_capturas_antiguas(max_antiguedad_horas=12.0, max_archivos=25)
            except Exception:
                pass
            return {
                "status": "success",
                "captura_local": str(out_path),
                "captura_dashboard": f"/static/capturas/{filename}"
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al capturar pantalla web: {str(e)}"}

    def _cerrar_impl(self) -> Dict[str, Any]:
        try:
            if self._page and not self._page.is_closed():
                try:
                    self._page.close()
                except Exception:
                    pass
            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
            if self._pw:
                try:
                    self._pw.stop()
                except Exception:
                    pass
            self._pw = None
            self._browser = None
            self._context = None
            self._page = None
            if sys.platform == "win32":
                subprocess.run(["schtasks", "/Delete", "/TN", "TripulacionNavegadorInteractivo", "/F"], shell=False, capture_output=True)
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], shell=False, capture_output=True)
            return {"status": "success", "mensaje": "Navegador cerrado correctamente."}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al cerrar navegador: {str(e)}"}

    # ── MÉTODOS PÚBLICOS SEGUROS (DELEGADOS A HILO DEDICADO) ──────────────────

    def navegar(self, url: str, visible: bool = True) -> Dict[str, Any]:
        return self._ejecutar(self._navegar_impl, url, visible)

    def rellenar_formulario(self, campos: Dict[str, Any], selector_envio: Optional[str] = None) -> Dict[str, Any]:
        return self._ejecutar(self._rellenar_formulario_impl, campos, selector_envio)

    def hacer_clic(self, selector_o_texto: str) -> Dict[str, Any]:
        return self._ejecutar(self._hacer_clic_impl, selector_o_texto)

    def controlar_media(self, accion: str = "reproducir") -> Dict[str, Any]:
        return self._ejecutar(self._controlar_media_impl, accion)

    def gestionar_pestanas(self, accion: str = "listar", url: str = "", indice: int = 0) -> Dict[str, Any]:
        return self._ejecutar(self._gestionar_pestanas_impl, accion, url, indice)

    def extraer_contenido(self, selector: Optional[str] = None) -> Dict[str, Any]:
        return self._ejecutar(self._extraer_contenido_impl, selector)

    def capturar_pantalla(self) -> Dict[str, Any]:
        return self._ejecutar(self._capturar_pantalla_impl)

    def cerrar(self) -> Dict[str, Any]:
        return self._ejecutar(self._cerrar_impl)



# ══════════════════════════════════════════════════════════════════════════════
# 2. GESTOR DE CONTROL DE ESCRITORIO Y PC (WINDOWS)
# ══════════════════════════════════════════════════════════════════════════════

def _asegurar_escritorio_interactivo():
    """Garantiza que el hilo actual tenga acceso al escritorio visible del usuario en Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # 0x01FF = GENERIC_ALL para el Desktop
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


class GestorControlEscritorio:
    """
    Controlador de teclado, ratón y captura de pantalla completa en Windows.
    """
    @staticmethod
    def capturar_pantalla_pc(nombre_archivo: Optional[str] = None) -> Dict[str, Any]:
        """
        Captura la pantalla completa de Windows usando PIL ImageGrab con fijación al escritorio interactivo.
        """
        try:
            _asegurar_escritorio_interactivo()
            timestamp = int(time.time())
            filename = nombre_archivo or f"pc_screen_{timestamp}.png"
            if not filename.endswith(".png"):
                filename += ".png"
            out_path = ARCHIVOS_TEMPORALES / filename
            static_path = STATIC_CAPTURAS / filename

            from PIL import ImageGrab, Image
            img = None
            try:
                img = ImageGrab.grab(all_screens=True)
            except Exception:
                _asegurar_escritorio_interactivo()
                try:
                    img = ImageGrab.grab()
                except Exception:
                    pass

            if img is not None:
                img.save(str(out_path))
                try:
                    img.save(str(static_path))
                except Exception:
                    pass

                # Verificar si es totalmente negra
                extrema = img.getextrema()
                es_negra = False
                if isinstance(extrema, tuple):
                    if all(ch == (0, 0) for ch in extrema):
                        es_negra = True

                if not es_negra and out_path.exists() and out_path.stat().st_size > 0:
                    return {
                        "status": "success",
                        "ruta_archivo": str(out_path),
                        "url_dashboard": f"/static/capturas/{filename}",
                        "peso_bytes": out_path.stat().st_size
                    }

            # Si ImageGrab falló o salió negra, intentar fallback con PowerShell CopyFromScreen
            # Compatibilidad Python < 3.12: backslash fuera de la f-string
            _out_path_ps = str(out_path).replace("\\", "/")
            _static_path_ps = str(static_path).replace("\\", "/")
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save('{_out_path_ps}', [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Save('{_static_path_ps}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bmp.Dispose()
"""
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=10)
            if out_path.exists() and out_path.stat().st_size > 0:
                with Image.open(out_path) as check_bmp:
                    ext = check_bmp.getextrema()
                    if isinstance(ext, tuple) and all(ch == (0, 0) for ch in ext):
                        return {
                            "status": "error",
                            "mensaje": "La pantalla capturada es completamente negra (el monitor o escritorio del usuario no está accesible en este momento)."
                        }

                return {
                    "status": "success",
                    "ruta_archivo": str(out_path),
                    "url_dashboard": f"/static/capturas/{filename}",
                    "peso_bytes": out_path.stat().st_size
                }
            else:
                return {"status": "error", "mensaje": f"No se pudo guardar la captura de pantalla: {res.stderr}"}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al capturar pantalla PC: {str(e)}"}

    @staticmethod
    def clic_pantalla(x: int, y: int, tipo: str = "izquierdo", doble: bool = False) -> Dict[str, Any]:
        """
        Mueve el cursor y hace clic en coordenadas de la pantalla en Windows.
        """
        try:
            _asegurar_escritorio_interactivo()
            import pyautogui
            pyautogui.FAILSAFE = False
            
            # Movimiento suave para que el usuario observe la acción
            pyautogui.moveTo(x, y, duration=0.3)
            btn = "left" if tipo.lower() in ["izquierdo", "left"] else "right"
            
            if doble:
                pyautogui.doubleClick(x, y, button=btn)
            else:
                pyautogui.click(x, y, button=btn)

            return {
                "status": "success",
                "posicion": {"x": x, "y": y},
                "tipo_clic": tipo,
                "doble": doble
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al hacer clic en PC ({x}, {y}): {str(e)}"}

    @staticmethod
    def escribir_texto(texto: str, enter: bool = False) -> Dict[str, Any]:
        """
        Escribe texto en la ventana activa del escritorio.
        """
        try:
            _asegurar_escritorio_interactivo()
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.write(texto, interval=0.03)
            if enter:
                pyautogui.press("enter")
            return {"status": "success", "texto_escrito": texto, "enter": enter}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al escribir en PC: {str(e)}"}

    @staticmethod
    def presionar_tecla(combinacion: str) -> Dict[str, Any]:
        """
        Ejecuta atajos de teclado (ej: 'ctrl+c', 'win+r', 'enter', 'tab', 'alt+tab').
        """
        try:
            _asegurar_escritorio_interactivo()
            import pyautogui
            pyautogui.FAILSAFE = False
            teclas = [t.strip().lower() for t in combinacion.replace("+", " ").split()]
            if len(teclas) == 1:
                pyautogui.press(teclas[0])
            else:
                pyautogui.hotkey(*teclas)
            return {"status": "success", "teclas": combinacion}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al presionar tecla(s): {str(e)}"}

    @staticmethod
    def abrir_aplicacion(comando: str) -> Dict[str, Any]:
        """
        Abre una aplicación de Windows en la pantalla interactiva del usuario (ej: 'notepad', 'calc', 'chrome', 'explorer').
        """
        try:
            # H-04: validacion estricta del comando de aplicacion (sin shell)
            if not isinstance(comando, str) or not comando.strip():
                return {"status": "error", "mensaje": "Comando de aplicacion vacio o invalido."}
            if any(m in comando for m in ("&", "|", ";", ">", "<", "$", "`", "\n", "\r")):
                return {"status": "error", "mensaje": "Comando rechazado: contiene metacaracteres de shell."}
            try:
                argv = shlex.split(comando, posix=(os.name != "nt"))
            except ValueError as e:
                return {"status": "error", "mensaje": "Comando malformado: %s" % e}
            if not argv:
                return {"status": "error", "mensaje": "Comando vacio tras el parseo."}

            if sys.platform == "win32":
                task_name = "TripulacionApp_%d" % int(time.time())
                subprocess.run(
                    ["schtasks", "/Create", "/TN", task_name, "/TR", comando,
                     "/SC", "ONCE", "/ST", "23:59", "/F", "/IT"],
                    shell=False, capture_output=True
                )
                subprocess.run(["schtasks", "/Run", "/TN", task_name], shell=False, capture_output=True)
                time.sleep(1.0)
                subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], shell=False, capture_output=True)
                return {"status": "success", "comando": comando, "mensaje": "Aplicación lanzada en la pantalla del usuario."}
            else:
                subprocess.Popen(argv, shell=False)
                time.sleep(1.0)
                return {"status": "success", "comando": comando, "mensaje": "Aplicación lanzada."}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al abrir app: {str(e)}"}

    @staticmethod
    def gestionar_ventanas(accion: str = "listar", titulo_o_proceso: str = "") -> Dict[str, Any]:
        """
        Gestiona las ventanas de Windows (los 3 botones de control y cambio de apps):
        - 'listar': Muestra las ventanas visibles en pantalla.
        - 'maximizar': Maximiza la ventana indicada (o Edge/la activa).
        - 'minimizar': Minimiza la ventana a la barra de tareas.
        - 'restaurar': Restaura al tamaño original normal.
        - 'cerrar': Cierra la ventana.
        - 'enfocar': Trae la ventana al frente.
        """
        try:
            _asegurar_escritorio_interactivo()
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)

            ventanas = []
            def enum_cb(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        t = buff.value.strip()
                        if t and t != "Program Manager":
                            ventanas.append({"hwnd": hwnd, "pid": pid.value, "titulo": t})
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_cb), 0)

            acc = (accion or "listar").strip().lower()
            if acc == "listar":
                return {"status": "success", "ventanas": ventanas, "total": len(ventanas)}

            target = None
            if titulo_o_proceso:
                term = titulo_o_proceso.lower()
                for v in ventanas:
                    if term in v["titulo"].lower():
                        target = v
                        break
            elif ventanas:
                # Si no se pasó término, preferir Edge / navegador activo si existe
                for v in ventanas:
                    if any(k in v["titulo"].lower() for k in ["edge", "youtube", "chrome"]):
                        target = v
                        break
                if not target:
                    target = ventanas[0]

            if not target:
                return {"status": "error", "mensaje": f"No se encontró ninguna ventana con el término '{titulo_o_proceso}'."}

            hwnd = target["hwnd"]
            
            # SW_MAXIMIZE = 3, SW_MINIMIZE = 6, SW_RESTORE = 9, WM_CLOSE = 0x0010
            if acc in ["maximizar", "maximize"]:
                user32.ShowWindow(hwnd, 3)
                user32.SetForegroundWindow(hwnd)
                msg = f"Ventana '{target['titulo']}' maximizada."
            elif acc in ["minimizar", "minimize"]:
                user32.ShowWindow(hwnd, 6)
                msg = f"Ventana '{target['titulo']}' minimizada."
            elif acc in ["restaurar", "restore"]:
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
                msg = f"Ventana '{target['titulo']}' restaurada."
            elif acc in ["cerrar", "close"]:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)
                msg = f"Ventana '{target['titulo']}' cerrada."
            elif acc in ["enfocar", "activar", "focus"]:
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                msg = f"Ventana '{target['titulo']}' traída al frente."
            else:
                return {"status": "error", "mensaje": f"Acción '{accion}' no reconocida. Usa 'maximizar', 'minimizar', 'restaurar', 'cerrar', 'enfocar' o 'listar'."}

            return {
                "status": "success",
                "accion": acc,
                "ventana": target,
                "mensaje": msg
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al gestionar ventanas: {str(e)}"}


# ══════════════════════════════════════════════════════════════════════════════
# 3. GESTOR DE VISIÓN POR IA (MULTIMODAL VLM)
# ══════════════════════════════════════════════════════════════════════════════

class GestorVisionIA:
    """
    Analizador visual de pantallas y formularios usando modelos VLM de NVIDIA NIM
    (meta/llama-3.2-11b-vision-instruct o meta/llama-3.2-90b-vision-instruct).
    """
    @staticmethod
    def analizar_pantalla(instruccion: str = "¿Qué elementos, ventanas o formularios se ven en la pantalla?", ruta_imagen: Optional[str] = None) -> Dict[str, Any]:
        try:
            from openai import OpenAI
            from PIL import Image
            
            # Si no se pasó ruta de imagen, primero verificar si hay una página web abierta en el gestor web
            if not ruta_imagen or not Path(ruta_imagen).exists():
                gestor_web = GestorNavegadorWeb.obtener_instancia()
                if gestor_web._page and not gestor_web._page.is_closed():
                    cap_web = gestor_web.capturar_pantalla()
                    if cap_web.get("status") == "success" and Path(cap_web.get("captura_local", "")).exists():
                        ruta_imagen = cap_web["captura_local"]

                # Si no hay navegador activo, capturar el escritorio completo de la PC
                if not ruta_imagen or not Path(ruta_imagen).exists():
                    cap = GestorControlEscritorio.capturar_pantalla_pc()
                    if cap.get("status") != "success":
                        return {"status": "error", "mensaje": f"Fallo al capturar pantalla para visión: {cap.get('mensaje')}"}
                    ruta_imagen = cap["ruta_archivo"]

            p_img = Path(ruta_imagen)
            if not p_img.exists() or p_img.stat().st_size < 500:
                return {"status": "error", "mensaje": "La captura obtenida está vacía o dañada."}

            # Proteger contra alucinaciones por pantallas negras
            try:
                with Image.open(p_img) as img_check:
                    ext = img_check.getextrema()
                    if isinstance(ext, tuple) and all(ch == (0, 0) for ch in ext):
                        return {
                            "status": "error",
                            "mensaje": "La captura es una pantalla totalmente negra. No hay contenido visual visible para analizar."
                        }
            except Exception:
                pass

            # Optimizar y comprimir imagen a JPEG equilibrado para acelerar la subida al VLM
            import io
            buf = io.BytesIO()
            with Image.open(p_img) as img_in:
                rgb_img = img_in.convert("RGB")
                rgb_img.thumbnail((960, 540))
                rgb_img.save(buf, format="JPEG", quality=80)
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

            # Prioridad: Claves de NVIDIA NIM de la tripulación
            api_key = (
                os.getenv("NVIDIA_API_KEY_LUFFY")
                or os.getenv("NVIDIA_API_KEY_ZORO")
                or os.getenv("NVIDIA_API_KEY_SANJI")
                or os.getenv("NVIDIA_API_KEY")
            )
            if not api_key:
                return {"status": "error", "mensaje": "No se encontró clave API de NVIDIA NIM configurada en el .env"}

            client = OpenAI(
                api_key=api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                timeout=60
            )

            prompt_sistema = """Eres los OJOS de una flota de agentes de IA autónomos con acceso a la pantalla de la computadora.
Tu misión es observar la captura de pantalla provista y responder con precisión quirúrgica:
1. Qué aplicaciones, ventanas o páginas web están abiertas.
2. Si hay formularios, botones, inputs de texto o menús visibles, indica qué dicen y dónde están ubicados (arriba, centro, izquierda, derecha, etc.).
3. Si hay errores, popups de confirmación o mensajes del sistema, identifícalos claramente.
4. Responde de forma concisa, estructurada y en español."""

            response = client.chat.completions.create(
                model="meta/llama-3.2-11b-vision-instruct",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instruccion},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }
                ],
                max_tokens=350,
                temperature=0.2
            )

            analisis = response.choices[0].message.content

            return {
                "status": "success",
                "analisis_visual": analisis,
                "imagen_analizada": str(p_img),
                "modelo_usado": "meta/llama-3.2-11b-vision-instruct"
            }
        except Exception as e:
            return {"status": "error", "mensaje": f"Error en análisis visual VLM: {str(e)}"}
