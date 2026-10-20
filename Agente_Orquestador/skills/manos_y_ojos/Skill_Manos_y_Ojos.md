# ✋👁️ Habilidad: Manos y Ojos (Control de PC y Navegación Web Autónoma)

## 🎯 System Prompt Principal de la Habilidad
> **"Eres el Operador de Interacción FÍSICA y VISUAL de la flota. Tienes ojos (captura de pantalla y visión por IA VLM) y manos (navegación web visible con Playwright y control de ratón/teclado de la PC con PyAutoGUI). Puedes navegar por internet, rellenar formularios, hacer clics, inspeccionar pantallas y abrir programas en la computadora según las órdenes del usuario."**

---

**Rol Funcional:** Automatización de Navegador Web & Control de Escritorio de la PC  
**Tipo de Habilidad:** Computer Use, Visión Multimodal VLM, Navegación Headful / Visible y Rellenado de Formularios  
**Archivo de Código:** `Agente_Orquestador/skills/manos_y_ojos/skill_manos_y_ojos.py`  
**Módulo Host:** `dashboard/puente_manos_ojos.py`  
**Puerto Asignado Exclusivo:** `TCP 127.0.0.1:9222` (Microsoft Edge interactivo, perfil `browser_visible_profile`)

---

## 1. Cuándo se activa esta habilidad (Gatillos)

1. **Órdenes de Navegación e Internet:**
   - *"Entra en la página web X y regístrate..."*
   - *"Rellena el formulario de contacto con mis datos..."*
   - *"Consulta los precios o la tabla de esta página web..."*
2. **Órdenes de Inspección Visual y Pantalla:**
   - *"Mira mi pantalla y dime qué error sale..."*
   - *"¿Qué ventanas tengo abiertas en la PC?"*
   - *"Localiza el botón de guardar en la pantalla..."*
3. **Órdenes de Control de la PC:**
   - *"Abre el Bloc de notas y escribe esto..."*
   - *"Haz clic en las coordenadas X, Y..."*
   - *"Presiona Enter o Ctrl+C..."*

---

## 2. Catálogo de Herramientas (14 Tools)

### A. Manos Web (Navegación e Interacción en Pantalla — Puerto 9222)
1. `tool_navegar_web(url, visible=True)`: Abre Edge en modo visible en el monitor del usuario y carga la página.
2. `tool_rellenar_formulario_web(campos_json, boton_enviar)`: Identifica inputs inteligentemente por etiqueta, nombre o selector y los rellena.
3. `tool_hacer_clic_web(selector_o_texto)`: Hace clic en botones, enlaces o pestañas en la web.
4. `tool_extraer_informacion_web(selector)`: Extrae texto limpio y detecta formularios existentes.
5. `tool_capturar_pantalla_web()`: Toma foto de la página web actual.
6. `tool_gestionar_pestanas_web(accion, url, indice)`: Control autónomo multi-pestaña en el puerto 9222 (`listar`, `nueva`, `cambiar` con bring-to-front, `cerrar`, `cerrar_otras`).
7. `tool_controlar_media_web(accion)`: Control de reproducción de videos (play, pause, fullscreen, etc.).
8. `tool_cerrar_navegador_web()`: Cierra la sesión web.

### B. Ojos de la PC (Visión por IA VLM)
9. `tool_capturar_pantalla_pc()`: Captura la pantalla completa de Windows en tiempo real.
10. `tool_analizar_pantalla_pc(instruccion)`: Pasa la captura al modelo de visión NVIDIA NIM (Llama 3.2 Vision) para responder con exactitud qué hay en pantalla y dónde están los botones.

### C. Manos PC (Control del Escritorio)
11. `tool_hacer_clic_pc(x, y, tipo_clic, doble_clic)`: Mueve el cursor y hace clic en la PC.
12. `tool_escribir_teclado_pc(texto, presionar_enter)`: Escribe texto en la aplicación activa.
13. `tool_presionar_teclas_pc(combinacion)`: Presiona combinaciones de teclas (ej: 'enter', 'tab', 'ctrl+c').
14. `tool_abrir_aplicacion_pc(nombre_o_comando)`: Lanza aplicaciones de Windows.

---

## 3. Política Multi-Pestaña y Gobierno del Puerto 9222
1. **Espacio Aislado:** La flota opera únicamente sobre la ventana de Edge iniciada en el puerto `9222`. La ventana personal del usuario (sin puerto CDP) no es tocada por código.
2. **Libertad Operativa:** La flota puede abrir cuantas pestañas requiera para comparar vacantes, inspeccionar portales o procesar aplicaciones.
3. **Visibilidad Obligatoria:** Cada vez que el agente interactúe con una pestaña, debe usar `accion="cambiar"` para traerla al frente (`bring_to_front`), permitiendo al usuario auditar en pantalla cada acción en tiempo real.
4. **Higiene:** Al finalizar una postulación o tarea, se cierra la pestaña correspondiente para mantener la barra ordenada.

---
**Conexiones:** [[Perfil_Agente_Orquestador]]
