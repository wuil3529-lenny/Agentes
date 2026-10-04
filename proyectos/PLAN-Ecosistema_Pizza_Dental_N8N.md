# PLAN: Ecosistema_Pizza_Dental_N8N

**Proyecto:** Ecosistema_Pizza_Dental_N8N  
**Fecha de Creación:** 2026-10-03 21:19:10  
**Arquitecto / Lead:** Agente Orquestador (Modo Plan - COO & Arquitecto de Soluciones)  
**Contexto de Origen:** CTX-Ecosistema_Pizza_Dental_N8N.md  
**Estado:** Listo para Aprobación del Usuario  

---

# PLAN MAESTRO — Ecosistema_Pizza_Dental_N8N

**Proyecto:** Ecosistema_Pizza_Dental_N8N
**Origen:** CTX-Ecosistema_Pizza_Dental_N8N.md (consolidado)
**Estratega:** Agente_Orquestador
**Fecha:** 2026-10-03
**Modalidad:** OPCIÓN A — Prototipos de demostración de alto impacto visual (datos mock ultra-realistas)
**Stack:** HTML5 + Tailwind CSS (CDN) + Three.js (CDN) + GSAP / spring physics. Sin build step.
**Delegación:** EXCLUSIVA a Subagente_Desarrollo (Zoro) — habilidades: desarrollo web, animaciones, taste, 3D WebGL, n8n.

---

## 🎯 Objetivo General
Entregar un ecosistema de demostración compuesto por 4 artefactos web de alto impacto visual (2 dashboards de pizzería + 2 páginas odontológicas con 3D) y 1 workflow unificado de automatización n8n, con calidad de diseño de clase mundial (cero AI-slop) y evidencia física verificable en disco.

---

## 📐 Arquitectura de Entregables

```
Subagente_Desarrollo/proyectos/
├── napoletana_dashboard_dark_bento/index.html      (Frente 1 - Diseño 1)
├── napoletana_dashboard_warm_gourmet/index.html    (Frente 1 - Diseño 2)
├── odontovanguard_clinical_trust/index.html        (Frente 2 - Página 1)
├── odontovanguard_3d_immersive/index.html          (Frente 2 - Página 2)
└── flujo_ecosistema_pizza_dental.json              (Frente 3 - n8n)
```

---

## 🗺️ FASES DEL PLAN

### FASE 0 — Preparación y Andamiaje (Dependencia: ninguna)
- **F0.1** Verificar/crear estructura de carpetas oficiales en `Subagente_Desarrollo/proyectos/`.
- **F0.2** Confirmar disponibilidad de CDNs (Tailwind, Three.js, GSAP) y definir tokens de diseño compartidos (paletas, tipografías, escalas de espaciado).
- **F0.3** Definir el JSON mock maestro de la pizzería (pedidos por hora, masa madre, ingredientes top, clientes recurrentes, canales Dine-in/Delivery).

### FASE 1 — Frente 1: Dashboard Pizzería (Dependencia: FASE 0)
- **F1.1** Construir **Diseño 1 — Dark Neo-Bento** (`napoletana_dashboard_dark_bento/index.html`):
  - Modo oscuro `#0a0a0c`, Bento Grid, pastilla morfológica (Hoy/Semana/Mes), badges con pulso.
  - KPIs: Ventas $1,850 (+18.4%), pedidos en tiempo real (6 horno / 4 reparto / 12 entregados), ticket $24.50, Top 4 pizzas.
  - Gráfico temporal por franja horaria (pico 20:00–22:00) + desglose de canales.
  - Microinteracciones de resorte físico + `prefers-reduced-motion`.
- **F1.2** Construir **Diseño 2 — Artisanal Warm Gourmet** (`napoletana_dashboard_warm_gourmet/index.html`):
  - Modo cálido `#fbf9f5`, terracota `#c2410c`, verde albahaca `#15803d`.
  - Tarjetas estilo comanda de cocina + animación de progreso de cocción.
  - Mismos KPIs y datos, estética editorial distinta.

### FASE 2 — Frente 2: Web Odontológica (Dependencia: FASE 0)
- **F2.1** Construir **Página 1 — Clinical Trust & Clear Services** (`odontovanguard_clinical_trust/index.html`):
  - Paleta blanco puro / cian quirúrgico / azul pizarra.
  - Hero empática + catálogo de tratamientos con acordeones interactivos + formulario de reserva.
- **F2.2** Construir **Página 2 — Experiencia Espacial 3D Inmersiva** (`odontovanguard_3d_immersive/index.html`):
  - Hero WebGL Three.js a pantalla completa, modelo 3D interactivo con amortiguación al cursor (60 FPS).
  - Partículas flotantes + tarjeta holográfica CSS 3D `preserve-3d` con giroscopio físico.
  - Controles de modo: sólido / alambre / escaneo.

### FASE 3 — Frente 3: Automatización n8n (Dependencia: FASE 0)
- **F3.1** Construir workflow unificado `flujo_ecosistema_pizza_dental.json`:
  - Nodo Webhook de disparo con bifurcación por `tipo`.
  - Rama `pedido_pizza` → filtro por monto + comanda de cocina.
  - Rama `cita_odontologica` → clasificación por especialidad + confirmación.
- **F3.2** Persistir y validar el workflow mediante `skill_n8n` en la carpeta oficial de proyectos.

### FASE 4 — Auditoría de Calidad y Ciberseguridad (Dependencia: FASES 1, 2, 3)
- **F4.1** Auditoría anti-slop (`tool_taste_auditar_anti_defaults`) sobre los 4 artefactos web.
- **F4.2** Auditoría de diseño (`tool_impeccable_auditar_diseno`) — calificación IMPECABLE.
- **F4.3** Verificación responsive (`tool_playwright_verificar_responsive`) en Desktop (1440×900) y Mobile (390×844).
- **F4.4** Auditoría de ciberseguridad (`tool_solicitar_auditoria_ciberseguridad`) sobre el workflow n8n y los HTML (secretos, fugas, permisos).

### FASE 5 — Cierre y Notificación (Dependencia: FASE 4)
- **F5.1** Generar informe ejecutivo consolidado en `Subagente_Desarrollo/documentos_desarrollo/`.
- **F5.2** Notificar creación exitosa + resumen de nodos n8n en el canal de la tripulación y en `Bitacora.md`.
- **F5.3** Auditoría SSOT del Orquestador: verificar evidencia física en disco y cerrar tickets.

---

## 🎫 BORRADOR DE TICKETS (a aperturar en Bitacora.md)

| Ticket | Fase | Responsable | Acción única verificable | Evidencia esperada |
|--------|------|-------------|--------------------------|--------------------|
| TKT-DEV-20261003002 | F0 | Subagente_Desarrollo | Andamiaje de carpetas + tokens de diseño + JSON mock maestro | `proyectos/_design_tokens.md` + `proyectos/mock_data_pizzeria.json` |
| TKT-DEV-20261003003 | F1.1 | Subagente_Desarrollo | Dashboard Dark Neo-Bento | `napoletana_dashboard_dark_bento/index.html` |
| TKT-DEV-20261003004 | F1.2 | Subagente_Desarrollo | Dashboard Artisanal Warm Gourmet | `napoletana_dashboard_warm_gourmet/index.html` |
| TKT-DEV-20261003005 | F2.1 | Subagente_Desarrollo | Página Clinical Trust & Clear Services | `odontovanguard_clinical_trust/index.html` |
| TKT-DEV-20261003006 | F2.2 | Subagente_Desarrollo | Página 3D Inmersiva Three.js | `odontovanguard_3d_immersive/index.html` |
| TKT-DEV-20261003007 | F3 | Subagente_Desarrollo | Workflow unificado n8n | `proyectos/flujo_ecosistema_pizza_dental.json` |
| TKT-DEV-20261003008 | F4 | Subagente_Desarrollo | Auditorías de calidad, responsive y ciberseguridad | Informe de auditoría |
| TKT-DEV-20261003009 | F5 | Subagente_Desarrollo | Informe ejecutivo consolidado + notificación | `documentos_desarrollo/informe_ecosistema_pizza_dental.md` |

---

## 🔒 HARD-STOPS DEL PROYECTO
- **[HS-01] ZERO-LOSS:** Evidencia preservada en disco; nada se elimina destructivamente.
- **[HS-02] ZERO-TRUST:** Ningún ticket se cierra sin evidencia física verificable.
- **[HS-03] ANTI-LOOPING:** Máx. 3 reintentos idénticos por herramienta.
- **[HS-04] HIGIENE:** Sin carpetas `temp/` internas; solo `Archivos_temporales/` en raíz.
- **[HS-05] CERO BYPASS:** Toda comunicación vía `Bitacora.md`.
- **[HS-06] DELEGACIÓN GRANULAR:** Un ticket = una acción verificable = un responsable.

---

## ✅ CRITERIOS DE ÉXITO
1. 4 artefactos web funcionales, responsivos y con animaciones fluidas (60 FPS).
2. Cero defaults de IA detectados en auditoría de taste (10/10).
3. Calificación IMPECABLE en auditoría de diseño.
4. Workflow n8n unificado creado, validado y persistido.
5. Evidencia física verificable de cada entregable en disco.
6. Notificación ejecutiva enviada al usuario.

---
**Pertenece a:** [[Perfil_Agente_Orquestador]]
