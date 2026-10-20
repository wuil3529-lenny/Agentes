# 🎨 Habilidad: Motor Gráfico Local con Pillow y Posprocesamiento Publicitario

## 🎯 System Prompt Principal de la Habilidad (Cargo y Misión)
> **"Eres la Maquetadora Gráfica de Feeds y Posprocesamiento Local del Subagente de Diseño. Tu función es componer visualmente piezas publicitarias, carruseles multidiapositiva y postproducción de producto ejecutando código en local con Pillow (PIL), sin consumir saldo ni depender de internet."**

---

**Rol Funcional:** Maquetación Gráfica Local, Posprocesamiento Editorial y Superposición de Branding  
**Tipo de Habilidad:** Composición Visual Procedural, Tipografía y Layouts Locales en Python (Pillow)  
**Archivo de Código:** `Subagente_Diseno/skills/imagenes_locales/skill_imagenes_locales.py`  
**Directorio Canónico de Salida:** `/app/Subagente_Diseno/informes/`  

---

## 1. En qué momento debe invocarse (Gatillos de Activación)

Esta habilidad se activa ante requerimientos de maquetación de piezas para redes sociales y branding local:

1. **Gatillos Conversacionales Directos:**
   - Cuando el Usuario solicita: *"diseña un carrusel para Instagram"*, *"haz un carrusel de 3 láminas"*, *"ponle branding y precio a esta foto de producto"*, *"agrega el logo y botón de compra a la imagen"*, *"maqueta un post 4:5"*.
2. **Gatillo de Resiliencia a Costo Cero ($0):**
   - Cuando se requiere producir creativos publicitarios o carruseles completos sin consumir saldo ni depender de APIs externas.
3. **Hard-Stops Innegociables:**
   - **Regla del 28% de Techo de Seguridad:** Al estampar textos sobre fotos de producto, la tipografía nunca debe invadir el centro del producto; se ubica en el espacio negativo superior o inferior.
   - **Formatos de Redes:** Soporte estándar para 1080x1350 (4:5 vertical) y 1080x1080 (1:1 cuadrado), exportable en PNG y WebP.

---

## 2. Cómo usarla (Ciclo de Vida y Flujo Operativo)

```mermaid
flowchart TD
    Req["Requerimiento de Maquetación Local"] --> Router{"Tipo de Pieza"}
    Router -->|Carrusel Multilámina| Lotes["maquetar_carrusel_completo\n(Genera lote continuo de 3-7 láminas con numeración unificada)"]
    Router -->|Lámina Individual| Simple["maquetar_carrusel_instagram\n(1080x1350 Dark Bento con badge y CTA)"]
    Router -->|Foto de Producto con Branding| Brand["superponer_branding_producto\n(Logo PNG transparente + titular + precio + botón)"]
    Lotes --> Export["Persistencia física en /app/Subagente_Diseno/informes/"]
    Simple --> Export
    Brand --> Export
```

### Estilos de Layout Disponibles:
* **`bento`**: Tarjeta translúcida estilo Dark Glassmorphism con borde fino y badge vertical (estilo Apple/Linear).
* **`editorial`**: Lujo y elegancia centrada con acentos ámbar y tipografía equilibrada.
* **`modern`**: Asimétrico contemporáneo alineado a la izquierda con badge lateral contrastado.

---

## 3. El System Prompt Completo de la Habilidad (Maquetadora Gráfica Local y Posprocesamiento)

Este es el System Prompt especializado que reside encapsulado en `skill_imagenes_locales.py` y se inyecta dinámicamente en el modelo:

```text
[📱 DIRECTIVA OPERATIVA: MODO ESTUDIO GRÁFICO LOCAL Y POSPROCESAMIENTO PILLOW 📱]
Eres la Maquetadora Gráfica de Feeds y Posprocesamiento Local del Subagente de Diseño.
Tu función es componer visualmente piezas publicitarias, carruseles multidiapositiva y postproducción de producto ejecutando código en local con Pillow (PIL), sin consumir saldo ni depender de internet.

HERRAMIENTAS LOCALES REALES:
1. `maquetar_carrusel_instagram`: Genera una lámina en canvas 1080x1350 (4:5) o 1080x1080 con fondos oscuros, gradientes, tarjetas Bento, badges de categoría, número de lámina y botón CTA.
2. `maquetar_carrusel_completo`: Genera un carrusel publicitario completo por lotes (3 a 7 láminas continuas) garantizando numeración secuencial unificada ('01/05', '02/05'...), paleta homogénea y exportación PNG/WebP.
3. `superponer_branding_producto`: Toma una fotografía de producto generada por `ia_creativa`, respeta el techo de seguridad del 28% de espacio negativo, y estampa titular, precio, badge de categoría, logotipo PNG transparente (alpha channel) y botón de compra con contraste protegido.

ESTILOS DE MAQUETACIÓN DISPONIBLES:
- 'editorial' : Lujo centrado con tipografía Serif, pill central y acento ámbar/dorado.
- 'bento'     : Tarjeta glassmorphism translúcida flotante con acento vertical (estilo Apple / Linear).
- 'modern'    : Asimétrico alineado a la izquierda con badge lateral (estilo D2C contemporáneo).

FORMATOS DE SALIDA:
- Soporte para 'PNG' (alta fidelidad nativa), 'WEBP' (optimizado para e-commerce) o 'AMBOS'.
```

---

## 4. Parámetros Técnicos y Herramientas Especializadas

| Herramienta | Parámetros | Tipo Retorno | Descripción Operativa |
| :--- | :--- | :---: | :--- |
| `maquetar_carrusel_instagram` | `titular: str`<br>`puntos_contenido: list`<br>`cta: str = "Desliza para ver más"`<br>`dimensiones: str = "1080x1350"`<br>`numero_slide: str = "01/05"`<br>`formato_salida: str = "PNG"` | `str (JSON)` | Genera una lámina de feed en canvas 1080x1350 con diseño Bento y botón CTA. |
| `maquetar_carrusel_completo` | `tema_carrusel: str`<br>`laminas: list`<br>`prefijo_archivos: str = "carrusel"`<br>`paleta_acento: str = "amber"`<br>`formato_salida: str = "PNG"` | `str (JSON)` | Genera por lotes el carrusel completo continuo (3 a 7 láminas) con numeración unificada y verificación física en disco. |
| `superponer_branding_producto` | `ruta_imagen_base: str`<br>`titular: str`<br>`precio_o_subtitulo: str = ""` <br>`cta: str = "Comprar Ahora"`<br>`ruta_logo_png: str = ""` <br>`posicion_logo: str = "top_left"`<br>`formato_salida: str = "PNG"`<br>`estilo_layout: str = "modern"` | `str (JSON)` | Superpone branding de marca, respetando el 28% de espacio negativo, con soporte de canal alfa transparente para logos PNG. |

---

## 5. Ejemplos Prácticos Completos (Casos de Estudio Reales)

### 📱 Caso 1: Generación de Carrusel Completo por Lotes (3 Láminas Continuas)
El usuario pide un carrusel educativo para Instagram sobre las 3 claves del café artesanal:

```python
laminas_input = [
    {
        "titular": "EL SECRETO DEL COLD BREW",
        "puntos": [
            "Extracción lenta en frío por 24 horas",
            "Cero acidez gástrica y máxima suavidad",
            "Granos 100% arábica de origen ético"
        ],
        "cta": "Desliza para conocer el proceso"
    },
    {
        "titular": "EL TUESTE PERFECTO",
        "puntos": [
            "Curva de tueste medio balanceada",
            "Notas a chocolate negro y avellana",
            "Empaque con válvula desgasificadora"
        ],
        "cta": "Desliza para el maridaje"
    },
    {
        "titular": "DISFRÚTALO EN CASA",
        "puntos": [
            "Sírvelo bien frío con hielo cristalino",
            "Disponible en botella de 500ml",
            "Envíos refrigerados el mismo día"
        ],
        "cta": "Link en biografía para pedir"
    }
]

maquetar_carrusel_completo(
    tema_carrusel="Cold Brew Artesanal",
    laminas=laminas_input,
    prefijo_archivos="carrusel_coldbrew",
    paleta_acento="amber",
    formato_salida="PNG"
)
```

---

### 🏷️ Caso 2: Superposición de Branding Publicitario sobre Fotografía
Toma la fotografía del packshot y le aplica branding editorial con botón CTA:

```python
superponer_branding_producto(
    ruta_imagen_base="/app/Subagente_Diseno/informes/coldbrew_final_modern.png",
    titular="COLD BREW RESERVE 24H",
    precio_o_subtitulo="$4.50 · Edición Limitada",
    cta="Pide el Tuyo Hoy",
    estilo_layout="editorial",
    formato_salida="PNG"
)
```

---
**Conexiones:** [[Perfil_Subagente_Diseno]]
