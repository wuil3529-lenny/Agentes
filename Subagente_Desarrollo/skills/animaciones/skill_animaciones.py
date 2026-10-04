"""
skill_animaciones.py — Habilidad: Ingeniería de Animaciones y Microinteracciones UI
====================================================================================
Basada en la filosofía de Emil Kowalski (autor de Sonner, Vaul, animations.dev).
Proporciona herramientas para diseñar, generar y auditar animaciones de alta gama
en aplicaciones web, dashboards, SPAs en React y apps móviles con rigor técnico:
  1. No alucina curvas: utiliza curvas canónicas y configuraciones de resortes (springs).
  2. Aceleración por hardware: opera exclusivamente en 'transform' y 'opacity' (salta layout y repaint).
  3. Evita 'scale(0)': arranca desde 'scale(0.95)' con opacidad cero.
  4. Duración óptima: microinteracciones < 300ms (150-250ms estándar UI).
  5. Accesibilidad obligatoria: integra 'prefers-reduced-motion' y gating para punteros/táctil.
  6. Variedad y recetas: modales, dropdowns, cajones (drawers), toasts, accordions,
     staggered grids, tabs morphing, botones hápticos/reactivos y scroll reveals.
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and _CURRENT.parents[2].name.lower() in ["subagente_desarrollo"] else _CURRENT.parents[2]
_AGENTE = "Subagente_Desarrollo"
_PROYECTOS = _APP_ROOT / _AGENTE / "proyectos"


def obtener_prompt_animaciones() -> str:
    """
    System Prompt especializado y encapsulado para el modo de animación y microinteracciones
    del Subagente de Desarrollo, basado en los estándares de Emil Kowalski.
    """
    return """[🛑 HARD-STOP: MODO INGENIERÍA DE ANIMACIONES Y MOTION UI ACTIVO 🛑]
Eres el Especialista en Ingeniería de Animación y Craft UI del Subagente de Desarrollo.
Tu misión es dotar a páginas web, dashboards y aplicaciones de transiciones y microinteracciones fluidas, elegantes, accesibles y optimizadas por GPU, siguiendo la filosofía de Emil Kowalski.

SECUENCIA DE DECISIÓN OBLIGATORIA (ÁRBOL DE EMIL KOWALSKI):
1. ¿DEBE ANIMARSE?:
   - Acciones de alta frecuencia (atajos de teclado, switches rápidos, 100+ veces/día): CERO ANIMACIÓN. Cambio instantáneo.
   - Navegación frecuente (hover, tabs, listas): Animación casi imperceptible (< 150ms).
   - Acciones ocasionales (modales, cajones/drawers, toasts, dropdowns): Animación estándar (150-250ms).
   - Eventos raros o celebraciones (onboarding, checkout, badge): Permitido mayor lucimiento.
2. PROPIEDADES PERMITIDAS (GPU ONLY):
   - Usa EXCLUSIVAMENTE `transform` y `opacity`.
   - NUNCA animes `width`, `height`, `top`, `left`, `margin` ni `padding` (salvo altura en accordions con truco grid o WAAPI).
   - NUNCA uses `scale(0)` en entradas: nada en el mundo real surge de la nada. Usa `scale(0.95)` + `opacity: 0`.
3. CURVAS CANÓNICAS Y RESORTES (SPRINGS):
   - Entradas y salidas: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`. NUNCA uses `ease-in` en UI.
   - Movimiento/morphing en pantalla: `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)`.
   - Cajones/Drawers tipo iOS: `--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1)`.
   - Resortes (Springs): `{ type: "spring", duration: 0.5, bounce: 0.2 }` (Apple style para gestos interactivos).
4. ACCESIBILIDAD Y DISPOSITIVOS:
   - Toda animación debe incluir soporte para `@media (prefers-reduced-motion: reduce)` (reducir a un fundido suave de opacidad).
   - El hover debe condicionarse a `@media (hover: hover) and (pointer: fine)` para no disparar hovers falsos en pantallas táctiles.
5. CERO SLOP Y NUNCA USAR:
   - NUNCA `transition: all`. Especifica las propiedades exactas.
   - NUNCA duraciones mayores a 300ms en componentes interactivos de UI.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# RECETAS DE ANIMACIÓN Y TOKENS CANÓNICOS
# ═══════════════════════════════════════════════════════════════════════════════

TOKENS_CSS_BASE = """/* Tokens Canónicos de Animación (Filosofía Emil Kowalski) */
:root {
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
  --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
  --duration-press: 120ms;
  --duration-tooltip: 150ms;
  --duration-dropdown: 180ms;
  --duration-modal: 220ms;
  --duration-drawer: 300ms;
}
"""

RECETAS_CATALOGO = {
    "boton_press": {
        "nombre": "Botón Táctil / Press Feedback",
        "descripcion": "Efecto de compresión y escala elástica al hacer click o tap, con feedback instantáneo.",
        "css": """/* Botón con microinteracción de presión */
.btn-motion {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--duration-press, 120ms) var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)),
              box-shadow var(--duration-press, 120ms) var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
  will-change: transform;
}

@media (hover: hover) and (pointer: fine) {
  .btn-motion:hover {
    transform: translateY(-1px);
  }
}

.btn-motion:active {
  transform: scale(0.97) translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .btn-motion {
    transition: opacity 120ms ease;
  }
  .btn-motion:active {
    transform: none;
    opacity: 0.85;
  }
}""",
        "motion": """// Botón en React / Motion
import { motion } from "motion/react"; // o framer-motion

export function MotionButton({ children, onClick }) {
  return (
    <motion.button
      whileHover={{ transform: "translateY(-1px)" }}
      whileTap={{ transform: "scale(0.97)" }}
      transition={{ duration: 0.12, ease: [0.23, 1, 0.32, 1] }}
      onClick={onClick}
      className="btn-motion"
    >
      {children}
    </motion.button>
  );
}"""
    },
    "dropdown_popover": {
        "nombre": "Dropdown / Popover / Menú Contextual",
        "descripcion": "Apertura desde el trigger con transform-origin dinámico, arrancando desde scale(0.95) y fade-in acelerado por GPU.",
        "css": """/* Dropdown / Menú flotante */
.dropdown-menu {
  transform-origin: var(--transform-origin, top center);
  transition: transform 180ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)),
              opacity 180ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
}

.dropdown-menu[data-state="closed"] {
  transform: scale(0.95);
  opacity: 0;
  pointer-events: none;
}

.dropdown-menu[data-state="open"] {
  transform: scale(1);
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .dropdown-menu {
    transform: none !important;
    transition: opacity 150ms ease;
  }
}""",
        "motion": """// Popover animado con Motion
import { motion, AnimatePresence } from "motion/react";

export function MotionDropdown({ isOpen, children }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, transform: "scale(0.95) translateY(-4px)" }}
          animate={{ opacity: 1, transform: "scale(1) translateY(0)" }}
          exit={{ opacity: 0, transform: "scale(0.95) translateY(-4px)" }}
          transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
          className="dropdown-menu"
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}"""
    },
    "modal_dialog": {
        "nombre": "Modal / Dialog Centrado",
        "descripcion": "Entrada centrada con backdrop blur y escala sutil de 0.96 a 1, salida rápida y sincronizada.",
        "css": """/* Modal y Overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  transition: opacity 220ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
}

.modal-content {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(1);
  transition: transform 220ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)),
              opacity 220ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
  will-change: transform, opacity;
}

.modal-overlay[data-state="closed"],
.modal-content[data-state="closed"] {
  opacity: 0;
  pointer-events: none;
}

.modal-content[data-state="closed"] {
  transform: translate(-50%, -48%) scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .modal-content {
    transform: translate(-50%, -50%) !important;
    transition: opacity 180ms ease;
  }
}""",
        "motion": """// Modal centrado con Motion
import { motion, AnimatePresence } from "motion/react";

export function MotionModal({ isOpen, onClose, children }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, transform: "scale(0.96) translateY(8px)" }}
            animate={{ opacity: 1, transform: "scale(1) translateY(0)" }}
            exit={{ opacity: 0, transform: "scale(0.96) translateY(8px)" }}
            transition={{ duration: 0.22, ease: [0.23, 1, 0.32, 1] }}
            className="relative z-10 w-full max-w-lg rounded-2xl bg-white dark:bg-zinc-900 p-6 shadow-2xl"
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}"""
    },
    "cajon_drawer": {
        "nombre": "Cajón Inferior / Sheet Drawer (Estilo iOS Vaul)",
        "descripcion": "Cajón deslizable inferior con física de arrastre, spring suave y curva de desaceleración nativa.",
        "css": """/* Sheet Drawer con curva nativa iOS */
.drawer-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  transform: translateY(0);
  transition: transform 320ms cubic-bezier(0.32, 0.72, 0, 1);
  will-change: transform;
}

.drawer-sheet[data-state="closed"] {
  transform: translateY(100%);
}

@media (prefers-reduced-motion: reduce) {
  .drawer-sheet {
    transition: opacity 200ms ease;
  }
  .drawer-sheet[data-state="closed"] {
    transform: translateY(0);
    opacity: 0;
  }
}""",
        "motion": """// Drawer deslizable con gesture drag y spring
import { motion, AnimatePresence } from "motion/react";

export function MotionDrawer({ isOpen, onClose, children }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 z-40 backdrop-blur-xs"
          />
          <motion.div
            initial={{ transform: "translateY(100%)" }}
            animate={{ transform: "translateY(0%)" }}
            exit={{ transform: "translateY(100%)" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            drag="y"
            dragConstraints={{ top: 0 }}
            dragElastic={0.2}
            onDragEnd={(_, info) => {
              if (info.offset.y > 100 || info.velocity.y > 500) {
                onClose();
              }
            }}
            className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-zinc-900 rounded-t-3xl p-6 shadow-xl max-h-[85vh] touch-none"
          >
            <div className="w-12 h-1.5 bg-zinc-300 dark:bg-zinc-700 rounded-full mx-auto mb-4" />
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}"""
    },
    "toast_stack": {
        "nombre": "Toast Notificación / Sistema de Alertas (Estilo Sonner)",
        "descripcion": "Notificaciones apiladas que no usan keyframes, salen simétricamente y escalan en cascada.",
        "css": """/* Toast con transiciones elásticas sin reiniciar keyframes */
.toast-item {
  transform: translateY(0) scale(1);
  opacity: 1;
  transition: transform 260ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)),
              opacity 260ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
}

.toast-item[data-state="entering"] {
  transform: translateY(16px) scale(0.94);
  opacity: 0;
}

.toast-item[data-state="exiting"] {
  transform: translateY(100%);
  opacity: 0;
}""",
        "motion": """// Toast con Motion & Layout stacking
import { motion, AnimatePresence } from "motion/react";

export function MotionToastContainer({ toasts, onDismiss }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, transform: "translateY(20px) scale(0.95)" }}
            animate={{ opacity: 1, transform: "translateY(0) scale(1)" }}
            exit={{ opacity: 0, transform: "translateY(16px) scale(0.95)" }}
            transition={{ type: "spring", duration: 0.45, bounce: 0.15 }}
            className="pointer-events-auto bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 px-4 py-3 rounded-xl shadow-lg flex items-center justify-between min-w-[280px]"
          >
            <span>{toast.message}</span>
            <button onClick={() => onDismiss(toast.id)} className="ml-3 text-xs opacity-70 hover:opacity-100">✕</button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}"""
    },
    "stagger_grid": {
        "nombre": "Entrada Escalonada (Staggered Group / Dashboard Cards)",
        "descripcion": "Aparición progresiva de tarjetas, filas de tablas o métricas de dashboard con retardo escalonado de 35-50ms.",
        "css": """/* Stagger en CSS Puro con variables de índice */
.stagger-item {
  opacity: 0;
  transform: translateY(12px);
  animation: staggerFadeIn 320ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)) forwards;
  animation-delay: calc(var(--index, 0) * 40ms);
}

@keyframes staggerFadeIn {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .stagger-item {
    animation: none;
    opacity: 1;
    transform: none;
  }
}""",
        "motion": """// Stagger en React con variants de Motion
import { motion } from "motion/react";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.045, // 45ms entre cada tarjeta del dashboard
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, transform: "translateY(12px) scale(0.98)" },
  visible: {
    opacity: 1,
    transform: "translateY(0) scale(1)",
    transition: { duration: 0.28, ease: [0.23, 1, 0.32, 1] },
  },
};

export function MotionDashboardGrid({ cards }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 md:grid-cols-3 gap-6"
    >
      {cards.map((c, i) => (
        <motion.div key={i} variants={cardVariants} className="p-6 rounded-2xl bg-white shadow-sm border border-zinc-100">
          <h4 className="text-zinc-500 text-sm font-medium">{c.titulo}</h4>
          <p className="text-2xl font-semibold mt-2">{c.valor}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}"""
    },
    "tabs_morphing": {
        "nombre": "Indicador de Pestañas Morphing / Sliding Indicator",
        "descripcion": "Píldora o indicador deslizante que se mueve fluidamente entre pestañas usando layoutId sin saltos.",
        "css": """/* Indicador deslizante en CSS */
.tab-nav {
  position: relative;
  display: flex;
  background: rgba(0, 0, 0, 0.05);
  padding: 4px;
  border-radius: 9999px;
}

.tab-indicator {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 0;
  width: var(--tab-width, 80px);
  transform: translateX(var(--tab-offset, 0px));
  background: #ffffff;
  border-radius: 9999px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  transition: transform 220ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)),
              width 220ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
}""",
        "motion": """// Tabs morphing con layoutId en Motion
import { useState } from "react";
import { motion } from "motion/react";

export function MotionTabs({ tabs }) {
  const [activeTab, setActiveTab] = useState(tabs[0]);

  return (
    <div className="flex gap-1 p-1 bg-zinc-100 dark:bg-zinc-800 rounded-full w-fit">
      {tabs.map((tab) => {
        const isActive = activeTab === tab;
        return (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`relative px-4 py-1.5 text-sm font-medium rounded-full transition-colors ${
              isActive ? "text-zinc-900 dark:text-white" : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400"
            }`}
          >
            {isActive && (
              <motion.div
                layoutId="activeTabPill"
                className="absolute inset-0 bg-white dark:bg-zinc-700 rounded-full shadow-sm"
                transition={{ type: "spring", duration: 0.38, bounce: 0.15 }}
              />
            )}
            <span className="relative z-10">{tab}</span>
          </button>
        );
      })}
    </div>
  );
}"""
    },
    "scroll_reveal": {
        "nombre": "Scroll Reveal / Vista al Desplazar",
        "descripcion": "Revelación elegante cuando los elementos entran en el viewport con CSS animation-timeline o Motion whileInView.",
        "css": """/* Scroll Reveal moderno */
.reveal-on-scroll {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 300ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1)),
              transform 300ms var(--ease-out, cubic-bezier(0.23, 1, 0.32, 1));
}

.reveal-on-scroll.is-visible {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .reveal-on-scroll {
    transform: none !important;
    transition: opacity 150ms ease;
  }
}""",
        "motion": """// Scroll reveal en Motion
import { motion } from "motion/react";

export function MotionScrollSection({ children }) {
  return (
    <motion.section
      initial={{ opacity: 0, transform: "translateY(24px)" }}
      whileInView={{ opacity: 1, transform: "translateY(0)" }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.45, ease: [0.23, 1, 0.32, 1] }}
    >
      {children}
    </motion.section>
  );
}"""
    },
    "skeleton_shimmer": {
        "nombre": "Skeleton Shimmer / Carga Fluida",
        "descripcion": "Efecto de resplandor sutil para estados de carga sin saltos de layout.",
        "css": """/* Skeleton Shimmer sin saltos */
.skeleton-shimmer {
  background: linear-gradient(
    90deg,
    rgba(228, 228, 231, 0.8) 0%,
    rgba(244, 244, 245, 0.9) 50%,
    rgba(228, 228, 231, 0.8) 100%
  );
  background-size: 200% 100%;
  animation: shimmerWave 1.4s infinite ease-in-out;
  border-radius: 8px;
}

@keyframes shimmerWave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-shimmer {
    animation: none;
    opacity: 0.6;
  }
}""",
        "motion": """// Skeleton Shimmer reutilizable
export function Skeleton({ className = "h-4 w-full" }) {
  return <div className={`skeleton-shimmer ${className}`} />;
}"""
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS TÉCNICAS DE LA HABILIDAD
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tool_generar_animacion_css(
    tipo_componente: str,
    selector_css: str = ".elemento",
    duracion_ms: int = 200,
    incluir_reduced_motion: bool = True
) -> str:
    """
    Genera código CSS listo para producción con animaciones fluidas aceleradas por GPU,
    siguiendo los estándares de Emil Kowalski.

    Args:
        tipo_componente: Tipo de componente o efecto ('boton_press', 'dropdown_popover', 'modal_dialog',
                         'cajon_drawer', 'toast_stack', 'stagger_grid', 'tabs_morphing', 'scroll_reveal', 'skeleton_shimmer').
        selector_css: Selector CSS al que se le aplicará la regla (ej: '.mi-boton', '.card-dashboard').
        duracion_ms: Duración en milisegundos (recomendado entre 120ms y 250ms).
        incluir_reduced_motion: Si True, inyecta la consulta de medios para accesibilidad.
    """
    try:
        clave = tipo_componente.lower().replace("-", "_").replace(" ", "_")
        receta = RECETAS_CATALOGO.get(clave)

        if not receta:
            claves_validas = list(RECETAS_CATALOGO.keys())
            return json.dumps({
                "status": "error",
                "mensaje": f"Tipo de componente '{tipo_componente}' no reconocido.",
                "opciones_validas": claves_validas
            }, ensure_ascii=False)

        codigo_css = receta["css"]
        if selector_css != ".elemento" and selector_css:
            codigo_css = re.sub(r"\.(btn-motion|dropdown-menu|modal-content|modal-overlay|drawer-sheet|toast-item|stagger-item|tab-indicator|reveal-on-scroll|skeleton-shimmer)", selector_css, codigo_css)

        # Ajuste de duración si difiere del valor por defecto
        if duracion_ms and duracion_ms != 200:
            codigo_css = re.sub(r"\b(120|180|220|260|300|320)ms\b", f"{duracion_ms}ms", codigo_css)

        return json.dumps({
            "status": "success",
            "componente": receta["nombre"],
            "descripcion": receta["descripcion"],
            "tokens_base": TOKENS_CSS_BASE,
            "codigo_css": codigo_css
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al generar animación CSS: {str(e)}"})


@tool
def tool_generar_animacion_motion(
    tipo_componente: str,
    tipo_resorte: str = "apple",
    soporte_gestos: bool = True
) -> str:
    """
    Genera componentes React utilizando Motion (framer-motion o motion/react) con configuraciones
    de resortes (springs) naturales, transform strings acelerados por hardware y transiciones fluidas.

    Args:
        tipo_componente: Componente a generar ('boton_press', 'dropdown_popover', 'modal_dialog',
                         'cajon_drawer', 'toast_stack', 'stagger_grid', 'tabs_morphing', 'scroll_reveal').
        tipo_resorte: Estilo de física ('apple' con duration+bounce o 'fisica' con mass+stiffness+damping).
        soporte_gestos: Si True, incluye soporte para arrastre (drag), gestos táctiles y microinteracciones.
    """
    try:
        clave = tipo_componente.lower().replace("-", "_").replace(" ", "_")
        receta = RECETAS_CATALOGO.get(clave)

        if not receta:
            claves_validas = list(RECETAS_CATALOGO.keys())
            return json.dumps({
                "status": "error",
                "mensaje": f"Tipo de componente '{tipo_componente}' no reconocido.",
                "opciones_validas": claves_validas
            }, ensure_ascii=False)

        codigo_motion = receta["motion"]

        # Ajuste según tipo de física
        config_spring = (
            '{ type: "spring", duration: 0.45, bounce: 0.18 }'
            if tipo_resorte.lower() == "apple"
            else '{ type: "spring", mass: 1, stiffness: 120, damping: 14 }'
        )

        return json.dumps({
            "status": "success",
            "componente": receta["nombre"],
            "libreria_recomendada": "motion/react o framer-motion",
            "configuracion_resorte": config_spring,
            "codigo_jsx": codigo_motion
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al generar código Motion: {str(e)}"})


@tool
def tool_auditar_animaciones(codigo_css_o_js: str) -> str:
    """
    Auditor riguroso de animaciones basado en el evaluador 'review-animations' de Emil Kowalski.
    Escanea código CSS o JSX en busca de malas prácticas de rendimiento, curvas incorrectas y falta de accesibilidad.

    Args:
        codigo_css_o_js: Cadena con el código CSS, SCSS, Tailwind o JSX a auditar.
    """
    hallazgos = []
    bloqueos_criticos = []

    # 1. Regla: Nunca 'transition: all'
    if re.search(r"transition:\s*all\b", codigo_css_o_js, re.IGNORECASE):
        bloqueos_criticos.append("Uso de 'transition: all' detectado. Debe reemplazarse especificando las propiedades exactas (ej: 'transform', 'opacity', 'background-color') para no forzar recálculos masivos de layout.")

    # 2. Regla: Nunca scale(0)
    if re.search(r"scale\(\s*0\s*\)", codigo_css_o_js):
        bloqueos_criticos.append("Uso de 'scale(0)' detectado en animación de entrada. En el mundo real ningún objeto aparece desde un punto nulo. Usa 'scale(0.95)' o 'scale(0.96)' combinado con 'opacity: 0'.")

    # 3. Regla: Prohibido ease-in en entradas de UI
    if re.search(r"\b(ease-in)\b", codigo_css_o_js) and not re.search(r"\b(ease-in-out)\b", codigo_css_o_js):
        hallazgos.append("Uso de 'ease-in' en interfaz de usuario. 'ease-in' inicia lento y produce sensación de lentitud o 'lag'. Usa 'ease-out' o 'cubic-bezier(0.23, 1, 0.32, 1)' para entradas de elementos.")

    # 4. Regla: Propiedades que disparan Layout (width, height, top, left, margin, padding)
    layout_props = ["width", "height", "top", "left", "right", "bottom", "margin", "padding"]
    for prop in layout_props:
        if re.search(rf"transition:\s*[^;]*\b{prop}\b", codigo_css_o_js, re.IGNORECASE):
            hallazgos.append(f"Animación de propiedad de layout '{prop}'. Dispara Reflow y Repaint en CPU. Conviértelo a 'transform: translate(...)' o 'transform: scale(...)' para correr en GPU.")

    # 5. Regla: Duraciones excesivas en UI (> 300ms)
    duraciones = re.findall(r"(\d+)(ms|s)", codigo_css_o_js)
    for valor, unidad in duraciones:
        ms = int(valor) if unidad == "ms" else float(valor) * 1000
        if ms > 350:
            hallazgos.append(f"Duración de {valor}{unidad} detectada. En interfaces de usuario (botones, dropdowns, modales) las animaciones deben mantenerse bajo 300ms (150-250ms) para sentirse reactivas.")
            break

    # 6. Regla: Falta de prefers-reduced-motion
    if "prefers-reduced-motion" not in codigo_css_o_js and "useReducedMotion" not in codigo_css_o_js:
        hallazgos.append("Falta soporte de accesibilidad: no se detectó '@media (prefers-reduced-motion: reduce)' ni el hook 'useReducedMotion()'. Es obligatorio incluirlo.")

    # 7. Regla: Hover táctil no filtrado
    if ":hover" in codigo_css_o_js and "(hover: hover)" not in codigo_css_o_js:
        hallazgos.append("Reglas ':hover' sin filtrar con '@media (hover: hover) and (pointer: fine)'. En dispositivos móviles táctiles disparará hovers pegajosos falsos al pulsar.")

    es_aprobado = len(bloqueos_criticos) == 0

    return json.dumps({
        "status": "success",
        "calificacion": "APROBADO" if es_aprobado and len(hallazgos) == 0 else ("CON OBSERVACIONES" if es_aprobado else "RECHAZADO"),
        "bloqueos_criticos": bloqueos_criticos,
        "advertencias_optimizacion": hallazgos,
        "conclusiones": "El código cumple los estándares de Emil Kowalski." if es_aprobado and len(hallazgos) == 0 else "Aplica las correcciones indicadas antes de pasar a producción."
    }, ensure_ascii=False)


@tool
def tool_catalogo_recetas_animacion(filtro_categoria: str = "todas") -> str:
    """
    Devuelve el catálogo completo de recetas de animación de Emil Kowalski para componentes UI
    (botones, modales, cajones, dropdowns, dashboards, tabs, scroll reveals, skeletons).

    Args:
        filtro_categoria: Categoría a filtrar ('todas' o nombres como 'modal', 'boton', 'drawer', 'dashboard', 'toast').
    """
    try:
        resultado = []
        filtro = filtro_categoria.lower()

        for clave, item in RECETAS_CATALOGO.items():
            if filtro == "todas" or filtro in clave or filtro in item["nombre"].lower():
                resultado.append({
                    "id": clave,
                    "nombre": item["nombre"],
                    "descripcion": item["descripcion"]
                })

        return json.dumps({
            "status": "success",
            "total_recetas": len(resultado),
            "tokens_css_canónicos": TOKENS_CSS_BASE,
            "recetas_disponibles": resultado
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Error al consultar catálogo: {str(e)}"})


# Catálogo oficial exportado
HERRAMIENTAS_ANIMACIONES = [
    tool_generar_animacion_css,
    tool_generar_animacion_motion,
    tool_auditar_animaciones,
    tool_catalogo_recetas_animacion,
]
