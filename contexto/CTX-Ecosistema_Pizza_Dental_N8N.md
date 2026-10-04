# CTX: Ecosistema_Pizza_Dental_N8N

**Proyecto:** Ecosistema_Pizza_Dental_N8N  
**Fecha de Inicio:** 2026-10-03 21:18:20  
**Estratega / Lead:** Agente Orquestador (Modo Entrevista - CEO & CTO)  
**Estado:** [CONSOLIDADO] Listo para Modo Plan  

---

## 1. Visión General y Propósito del Proyecto
Definición inicial en proceso de refinamiento estratégico.

## 2. Caminos Evaluados, Opciones y Decisiones Clave
Registro de alternativas analizadas, trade-offs y elecciones del Usuario.

## 3. Requerimientos Técnicos y de Negocio
Especificaciones técnicas, dependencias, estándares de calidad y restricciones.

## 4. Participación y Roles de la Tripulación
- **Agente Orquestador:** Supervisión general, orquestación y control de calidad.
- **Subagente de Desarrollo:** Implementación técnica, código, APIs y testing.
- **Subagente de Diseño y Arte:** UI/UX, estilos visuales, arte conceptual y maquetación.
- **Subagente de Ciberseguridad:** Auditoría de vulnerabilidades, control de accesos y secretos.
- **Subagente de Asistencia e Integraciones:** Notificaciones, documentación y servicios conectados.

## 5. Entregables Concretos y Criterios de Éxito
Definición de qué resultado exacto considerará el Usuario como misión cumplida.

## 6. Historial de Diálogo y Refinamiento Continuo
Registro acumulativo de las rondas de intercambio estratégico.


### Ronda de Descubrimiento #1 — 21:18:24
# CTX — Ecosistema_Pizza_Dental_n8n (Ronda 1: Apertura)

## 1. Visión del Proyecto
Proyecto de alta prioridad que combina **desarrollo web de alto impacto visual** + **automatización de procesos de negocio (n8n)** para DOS clientes distintos:
- **Cliente A:** Pizzería (dashboard de ventas).
- **Cliente B:** Centro odontológico (sitio web profesional con experiencia 3D).

## 2. Alcance Declarado por el Usuario (3 frentes)
### Frente 1 — Dashboard de Ventas (Pizzería)
- DOS diseños profesionales (dos propuestas visuales distintas).
- Animaciones fluidas de alta calidad: microinteracciones + físicas de resorte (spring physics).
- Naturaleza: dashboard de datos/ventas.

### Frente 2 — Web Centro Odontológico
- DOS páginas web profesionales.
- Obligatorio: UN diseño interactivo en 3D (Three.js WebGL / CSS 3D).

### Frente 3 — Automatización n8n
- Acceder a la instancia n8n.
- Crear workflow para: (a) recepción y procesamiento de pedidos de pizza, (b) citas odontológicas.
- Notificar la creación del workflow.

## 3. Restricción de Proceso (Regla Obligatoria del Usuario)
- Entrar en MODO ENTREVISTADOR antes de crear plan o tickets.
- Preguntas estratégicas iterativas hasta cerrar alcance.
- Consolidar ficha de contexto ANTES del plan.

## 4. Estado Actual
- Entrevista INICIADA. Documento vivo creado.
- Pendiente: cerrar dimensiones de negocio, diseño, stack y automatización.

## 5. Dimensiones a Cerrar (Checklist Estratégico)
- [ ] Negocio: KPIs del dashboard, métricas de ventas, datos de origen.
- [ ] Diseño: estilo visual de cada propuesta, paleta, tipografía, referencias.
- [ ] Stack: framework frontend, backend, hosting.
- [ ] 3D: alcance exacto de la escena Three.js (qué se modela, interactividad).
- [ ] n8n: instancia/URL, credenciales, disparadores, integraciones (WhatsApp, email, Sheets, etc.).
- [ ] Entregables y criterios de aceptación por frente.
- [ ] Seguridad: manejo de secretos, auditoría de ciberseguridad.

## 6. Decisiones Tomadas
- (Ninguna aún — ronda de apertura.)


### Ronda de Descubrimiento #2 — 21:19:00
## Ronda de Descubrimiento #2 — 2026-10-03 (CIERRE DE ALCANCE)

### DECISIÓN ESTRATÉGICA GLOBAL
- **Opción elegida:** OPCIÓN A — Prototipos de demostración de alto impacto visual con datos mock ultra-realistas.
- **Stack confirmado:** HTML5 + Tailwind CSS (CDN) + Three.js (CDN) + GSAP/spring physics. SIN dependencias pesadas, SIN build step.
- **Filosofía de diseño:** Microinteracciones de resorte físico (Emil Kowalski), soporte `prefers-reduced-motion`, hover acelerado por GPU, cero "AI slop".

---

## 🍕 FRENTE 1 — Dashboard de Ventas (Pizzería 'Napoletana Crust & Co.')

### 1. Datos
- Mock enriquecido en **JSON embebido**: pedidos por hora, distribución de masa madre, ingredientes top, clientes recurrentes.

### 2. KPIs Clave (obligatorios)
- **Ventas del día:** $1,850 USD (+18.4%).
- **Pedidos en tiempo real:** 6 en Horno de Leña, 4 en Reparto, 12 Entregados.
- **Ticket Promedio:** $24.50.
- **Top Pizzas:** Margherita D.O.P., Diavola Trufada, Quattro Formaggi, Prosciutto & Funghi.
- **Gráfico temporal:** ventas por franja horaria (pico 20:00–22:00).
- **Desglose de canales:** Dine-in vs Delivery.

### 3. Los DOS Diseños (propuestas visuales alternativas del mismo dashboard)
- **Diseño 1 — Dark Neo-Bento:**
  - Modo oscuro profundo `#0a0a0c`.
  - Tarjetas Bento Grid con microinteracciones de resorte físico.
  - Pastilla deslizante morfológica para filtrar periodos (Hoy / Semana / Mes).
  - Badges de estado con pulso.
- **Diseño 2 — Artisanal Warm Gourmet:**
  - Modo cálido/craft `#fbf9f5`, terracota `#c2410c`, verde albahaca `#15803d`.
  - Estética editorial con tarjetas de pedidos estilo comanda de cocina.
  - Animación de progreso de cocción.

### 4. Interactividad
- Tabs morfológicas, toggles con feedback de resorte, hover suave GPU, `prefers-reduced-motion`.

---

## 🦷 FRENTE 2 — Web Centro Odontológico ('Clínica OdontoVanguard')

### 5. Las DOS Páginas
- **Página 1 — Clinical Trust & Clear Services:**
  - Landing orientada a conversión y confianza médica.
  - Paleta: blanco puro, cian quirúrgico, azul pizarra.
  - Hero empática + catálogo de tratamientos (Implantología Digital, Ortodoncia Invisible, Blanqueamiento Láser) con acordeones interactivos + formulario de reserva de citas.
- **Página 2 — Experiencia Espacial 3D Inmersiva (Three.js):**
  - Showcase de tecnología médica avanzada.
  - Hero interactivo con lienzo WebGL Three.js a pantalla completa.
  - Modelo 3D interactivo que rota y reacciona al cursor con amortiguación suave.
  - Partículas flotantes + tarjeta holográfica CSS 3D con efecto giroscópico físico.

### 6. El 3D
- Three.js WebGL nativo vía CDN, geometría interactiva al mouse (60 FPS).
- Controles de modo: sólido / alambre / escaneo.
- Tarjeta holográfica con CSS 3D `preserve-3d` y reflejo especular.

### 7. Contenido
- OdontoVanguard Clinic, dirección ficticia premium (Av. Las Mercedes, Torre Médica Piso 4).
- Doctores especialistas certificados y precios transparentes.

---

## ⚙️ FRENTE 3 — Automatización n8n

### 8. Instancia
- Acceso local/contenedor: `http://localhost:5678` o `http://tripulacion_n8n:5678`.

### 9. Flujo Unificado
- Archivo: `flujo_ecosistema_pizza_dental.json`.
- Nodo Webhook de disparo que detecta el tipo de evento:
  - Si `tipo == 'pedido_pizza'` → filtra por monto y comanda de cocina.
  - Si `tipo == 'cita_odontologica'` → clasifica por especialidad y emite confirmación.

### 10. Edición y Persistencia
- Guardar y validar mediante `skill_n8n` en la carpeta oficial de proyectos.

### 11. Notificación
- Notificar creación exitosa + resumen de nodos en el canal de la tripulación y en `Bitacora.md`.

---

## 🚀 REGLA DE ORO DE DELEGACIÓN (definida por el Usuario)
1. Actualizar y cerrar la ficha de contexto `CTX-Ecosistema_Pizza_Dental_N8N.md`.
2. Pasar de inmediato a MODO PLAN (`tool_crear_plan`) para generar el plan maestro paso a paso.
3. **Todos los tickets de construcción se asignan EXCLUSIVAMENTE al Subagente_Desarrollo (Zoro)**, inyectando sus habilidades de: desarrollo web, animaciones, taste, 3D WebGL y n8n.

---

## ✅ DIMENSIONES CERRADAS (Checklist)
- [x] Negocio: KPIs, métricas y datos de origen definidos.
- [x] Diseño: estilo visual, paleta y referencias de cada propuesta.
- [x] Stack: HTML5 + Tailwind CDN + Three.js CDN + GSAP.
- [x] 3D: alcance exacto de la escena Three.js definido.
- [x] n8n: instancia, disparadores y flujo unificado definidos.
- [x] Entregables y criterios de aceptación por frente.
- [x] Delegación: exclusiva a Subagente_Desarrollo.

---
**Pertenece a:** [[contexto]]
