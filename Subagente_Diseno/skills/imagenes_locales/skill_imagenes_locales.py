"""
skill_imagenes_locales.py — Habilidad: Motor Gráfico Local con Pillow y Posprocesamiento
===========================================================================================
Motor de composición gráfica procedural y maquetación de piezas publicitarias ejecutado
en local con Pillow (PIL). No consume APIs externas ni saldo.

Herramientas disponibles:
  - maquetar_carrusel_instagram    : Maqueta una lámina individual (1080x1350 vertical o 1080x1080)
                                      con jerarquía editorial, tarjetas, badges y CTA.
  - maquetar_carrusel_completo     : Genera un carrusel publicitario completo por lotes (de 2 a 7 láminas)
                                      con numeración secuencial, coherencia de diseño y salida PNG/WebP.
  - superponer_branding_producto   : Toma una fotografía con espacio negativo generado por IA y
                                      le superpone titular, precio, badge, logotipo PNG transparente y botón CTA.
  - obtener_prompt_imagenes_locales: System Prompt Canónico de la habilidad.
"""

import os
import re
import json
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFont

_CURRENT = Path(__file__).resolve()
_APP_ROOT = _CURRENT.parents[3] if len(_CURRENT.parents) > 3 and "subagente" in _CURRENT.parents[2].name.lower() else _CURRENT.parents[2]
_INFORMES = _APP_ROOT / "Subagente_Diseno" / "informes"
_INFORMES.mkdir(parents=True, exist_ok=True)


def obtener_prompt_imagenes_locales() -> str:
    """
    Retorna el System Prompt especializado para la maquetación y diseño de carruseles e imágenes.
    """
    return """[📱 DIRECTIVA OPERATIVA: MODO ESTUDIO GRÁFICO LOCAL Y POSPROCESAMIENTO PILLOW 📱]
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
"""


def _transformar_ruta(ruta: str, nombre_default: str = "carrusel_slide.png") -> Path:
    if not isinstance(ruta, str) or not ruta.strip():
        return _INFORMES / nombre_default

    literales = {"ruta_destino", "texto_overlay", "dimensiones", "ruta", "destino"}
    if ruta.strip().lower() in literales:
        return _INFORMES / nombre_default

    p = Path(ruta)
    nombre = p.name
    if not nombre or nombre in literales:
        nombre = nombre_default
    if not nombre.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        nombre += ".png"

    return _INFORMES / nombre


def _hex_a_rgba(hex_code: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Convierte un color HEX (ej. #D97706) a una tupla RGBA."""
    h = hex_code.strip().lstrip("#")
    if len(h) == 6:
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
        except Exception:
            pass
    return (217, 119, 6, alpha)


def _obtener_fuente_por_tipo(estilo_o_nombre: str, tamano: int) -> ImageFont.ImageFont:
    """Carga fuentes específicas con jerarquía visual (serif para editorial, sans-bold para titulares)."""
    fonts_dir = Path("C:/Windows/Fonts")
    mapa = {
        "serif_bold": ["georgiab.ttf", "timesbd.ttf"],
        "serif": ["georgia.ttf", "times.ttf"],
        "sans_bold": ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"],
        "sans": ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
    }
    candidatas = mapa.get(estilo_o_nombre, [estilo_o_nombre, "segoeuib.ttf", "arial.ttf"])
    for f in candidatas:
        p = fonts_dir / f if not Path(f).is_absolute() else Path(f)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), tamano)
            except Exception:
                pass
        try:
            return ImageFont.truetype(f, tamano)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=tamano)
    except Exception:
        return ImageFont.load_default()


def _obtener_fuente_tamano(tamano: int) -> ImageFont.ImageFont:
    """Intenta cargar fuentes del sistema o recurre a la fuente por defecto de PIL."""
    return _obtener_fuente_por_tipo("sans_bold", tamano)


def _ajustar_lineas_texto(texto: str, draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, max_ancho: int) -> List[str]:
    """Divide un texto largo en múltiples líneas para no desbordar el ancho del canvas."""
    palabras = texto.split()
    lineas = []
    linea_actual = ""

    for palabra in palabras:
        prueba = f"{linea_actual} {palabra}".strip()
        try:
            bbox = draw.textbbox((0, 0), prueba, font=font)
            ancho_prueba = bbox[2] - bbox[0]
        except Exception:
            ancho_prueba = len(prueba) * 10

        if ancho_prueba <= max_ancho:
            linea_actual = prueba
        else:
            if linea_actual:
                lineas.append(linea_actual)
            linea_actual = palabra

    if linea_actual:
        lineas.append(linea_actual)

    return lineas if lineas else [texto]


def _crear_metadatos_verificacion(ruta_archivo: Path, prompt_o_desc: str, tipo_diseno: str, tamano_bytes: int) -> str:
    try:
        ruta_meta = ruta_archivo.parent / f"{ruta_archivo.stem}.verificacion.json"
        magic_hex = ""
        with open(ruta_archivo, "rb") as f:
            magic_hex = f.read(4).hex()

        metadatos = {
            "archivo_generado": str(ruta_archivo).replace("\\", "/"),
            "tamano_bytes": tamano_bytes,
            "tipo_diseno": tipo_diseno,
            "motor": "Pillow (PIL) Local Graphics Engine",
            "formato": f"{ruta_archivo.suffix.upper().lstrip('.')} binario genuino",
            "verificacion_disco": f"EXISTE: True | BYTES: {tamano_bytes} | MAGIC: 0x{magic_hex}",
            "magic_hex": magic_hex,
            "descripcion": prompt_o_desc,
            "timestamp_verificacion": datetime.datetime.now().isoformat()
        }

        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(metadatos, f, ensure_ascii=False, indent=2)

        return str(ruta_meta).replace("\\", "/")
    except Exception as e:
        return f"Error creando metadatos: {str(e)}"


def _guardar_en_formatos(
    imagen_canvas: Image.Image,
    destino_p: Path,
    formato_salida: str,
    descripcion: str,
    tipo_diseno: str
) -> Dict[str, Any]:
    """Guarda la imagen PIL en PNG, WEBP o ambos según formato_salida y crea metadatos."""
    archivos_generados = []
    fmt = formato_salida.upper().strip()
    canvas_rgb = imagen_canvas.convert("RGB")

    # 1. Guardar PNG
    if fmt in ["PNG", "AMBOS"]:
        ruta_png = destino_p.with_suffix(".png")
        canvas_rgb.save(str(ruta_png), "PNG", quality=95)
        bytes_png = ruta_png.stat().st_size
        meta_png = _crear_metadatos_verificacion(ruta_png, descripcion, tipo_diseno, bytes_png)
        archivos_generados.append({
            "formato": "PNG",
            "ruta": str(ruta_png).replace("\\", "/"),
            "bytes": bytes_png,
            "metadatos": meta_png
        })

    # 2. Guardar WebP
    if fmt in ["WEBP", "AMBOS"]:
        ruta_webp = destino_p.with_suffix(".webp")
        canvas_rgb.save(str(ruta_webp), "WEBP", quality=90, method=6)
        bytes_webp = ruta_webp.stat().st_size
        meta_webp = _crear_metadatos_verificacion(ruta_webp, descripcion, tipo_diseno, bytes_webp)
        archivos_generados.append({
            "formato": "WEBP",
            "ruta": str(ruta_webp).replace("\\", "/"),
            "bytes": bytes_webp,
            "metadatos": meta_webp
        })

    return {
        "ruta_principal": archivos_generados[0]["ruta"] if archivos_generados else str(destino_p),
        "archivos": archivos_generados
    }


def _renderizar_slide_carrusel(
    titular: str,
    puntos: List[str],
    cta: str,
    categoria_badge: str,
    numero_slide: str,
    ruta_imagen_fondo: Optional[str],
    ancho: int,
    alto: int,
    paleta_acento: str = "#6366F1"
) -> Image.Image:
    """Función de renderizado interno para una sola diapositiva de carrusel."""
    # 1. Crear Canvas Base
    if ruta_imagen_fondo and Path(ruta_imagen_fondo).exists():
        img_base = Image.open(ruta_imagen_fondo).convert("RGBA")
        img_base = img_base.resize((ancho, alto), Image.Resampling.LANCZOS)
        overlay_oscuro = Image.new("RGBA", (ancho, alto), (2, 6, 23, 215))
        canvas = Image.alpha_composite(img_base, overlay_oscuro)
    else:
        canvas = Image.new("RGBA", (ancho, alto), (15, 23, 42, 255))
        draw_bg = ImageDraw.Draw(canvas)
        for y in range(alto):
            alpha = int((y / alto) * 45)
            draw_bg.line([(0, y), (ancho, y)], fill=(2, 6, 23, 255 - alpha))

    draw = ImageDraw.Draw(canvas)
    rgba_acento = _hex_a_rgba(paleta_acento, 240)

    font_badge = _obtener_fuente_tamano(24)
    font_titulo = _obtener_fuente_tamano(54)
    font_cuerpo = _obtener_fuente_tamano(32)
    font_cta = _obtener_fuente_tamano(30)

    margen_x = 80
    y_cursor = 80

    # 2. Header: Badge de Categoría + Número de Slide
    badge_texto = f"  {categoria_badge.upper()}  "
    try:
        bbox_b = draw.textbbox((0, 0), badge_texto, font=font_badge)
        ancho_b = bbox_b[2] - bbox_b[0]
        alto_b = bbox_b[3] - bbox_b[1]
    except Exception:
        ancho_b, alto_b = 200, 40

    draw.rounded_rectangle(
        [margen_x, y_cursor, margen_x + ancho_b + 20, y_cursor + alto_b + 20],
        radius=12,
        fill=(rgba_acento[0], rgba_acento[1], rgba_acento[2], 55),
        outline=(rgba_acento[0], rgba_acento[1], rgba_acento[2], 200),
        width=2
    )
    draw.text((margen_x + 10, y_cursor + 8), badge_texto, font=font_badge, fill=(224, 231, 255, 255))
    draw.text((ancho - margen_x - 120, y_cursor + 8), numero_slide, font=font_badge, fill=(148, 163, 184, 255))

    y_cursor += 120

    # 3. Titular Principal en Negrita con Auto-Wrap
    lineas_titulo = _ajustar_lineas_texto(titular, draw, font_titulo, max_ancho=ancho - (margen_x * 2))
    for linea in lineas_titulo:
        draw.text((margen_x, y_cursor), linea, font=font_titulo, fill=(255, 255, 255, 255))
        y_cursor += 70

    y_cursor += 35

    # 4. Tarjetas Bento de Puntos de Contenido
    for punto in puntos[:4]:
        tarjeta_y_inicio = y_cursor
        lineas_punto = _ajustar_lineas_texto(punto, draw, font_cuerpo, max_ancho=ancho - (margen_x * 2) - 80)
        alto_tarjeta = (len(lineas_punto) * 48) + 40

        draw.rounded_rectangle(
            [margen_x, tarjeta_y_inicio, ancho - margen_x, tarjeta_y_inicio + alto_tarjeta],
            radius=16,
            fill=(30, 41, 59, 160),
            outline=(51, 65, 85, 200),
            width=1
        )

        draw.ellipse(
            [margen_x + 25, tarjeta_y_inicio + 26, margen_x + 39, tarjeta_y_inicio + 40],
            fill=rgba_acento
        )

        texto_y = tarjeta_y_inicio + 18
        for lp in lineas_punto:
            draw.text((margen_x + 55, texto_y), lp, font=font_cuerpo, fill=(226, 232, 240, 255))
            texto_y += 48

        y_cursor += alto_tarjeta + 22

    # 5. Botón CTA Inferior
    cta_y = alto - 150
    draw.rounded_rectangle(
        [margen_x, cta_y, ancho - margen_x, cta_y + 70],
        radius=18,
        fill=rgba_acento,
        outline=(min(rgba_acento[0] + 30, 255), min(rgba_acento[1] + 30, 255), min(rgba_acento[2] + 30, 255), 255),
        width=2
    )
    try:
        bbox_cta = draw.textbbox((0, 0), cta, font=font_cta)
        ancho_cta = bbox_cta[2] - bbox_cta[0]
        pos_x_cta = margen_x + ((ancho - (margen_x * 2) - ancho_cta) // 2)
    except Exception:
        pos_x_cta = margen_x + 40

    draw.text((pos_x_cta, cta_y + 18), cta, font=font_cta, fill=(255, 255, 255, 255))
    return canvas


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 1: MAQUETAR LÁMINA INDIVIDUAL DE CARRUSEL
# ══════════════════════════════════════════════════════════════════════════════

class CarruselParams(BaseModel):
    titular: str = Field(description="Título impactante del post o de la lámina del carrusel.")
    puntos_contenido: List[str] = Field(default=[], description="Lista de puntos clave o viñetas (máximo 4).")
    cta: str = Field(default="Desliza para más 👉", description="Llamada a la acción inferior o botón.")
    ruta_destino: str = Field(default="carrusel_slide.png", description="Ruta o nombre de guardado en informes/.")
    dimensiones: str = Field(default="1080x1350", description="Dimensiones: '1080x1350' (vertical 4:5) o '1080x1080' (cuadrado).")
    categoria_badge: str = Field(default="ESTRATEGIA & IA", description="Pill badge superior de temática.")
    numero_slide: str = Field(default="01/05", description="Indicador numérico de diapositiva (ej. '01/05').")
    ruta_imagen_fondo: Optional[str] = Field(default=None, description="Ruta a imagen de fondo generada por IA.")
    formato_salida: str = Field(default="PNG", description="Formato: 'PNG', 'WEBP' o 'AMBOS'.")


@tool("maquetar_carrusel_instagram", args_schema=CarruselParams)
def maquetar_carrusel_instagram(
    titular: str,
    puntos_contenido: Optional[List[str]] = None,
    cta: str = "Desliza para más 👉",
    ruta_destino: str = "carrusel_slide.png",
    dimensiones: str = "1080x1350",
    categoria_badge: str = "ESTRATEGIA & IA",
    numero_slide: str = "01/05",
    ruta_imagen_fondo: Optional[str] = None,
    formato_salida: str = "PNG"
) -> str:
    """
    Maqueta y renderiza en local una lámina gráfica individual para feeds/carruseles.
    Aplica diseño profesional Dark Slate, tarjetas Bento, auto-wrap y exportación a PNG o WebP.
    """
    try:
        puntos = puntos_contenido or ["Punto estratégico 1.", "Implementación paso a paso sin rodeos."]
        destino_p = _transformar_ruta(ruta_destino, "carrusel_slide.png")
        destino_p.parent.mkdir(parents=True, exist_ok=True)

        ancho, alto = 1080, 1350
        if "x" in dimensiones.lower():
            try:
                partes = dimensiones.lower().split("x")
                ancho = int(partes[0].strip())
                alto = int(partes[1].strip())
            except Exception:
                pass

        canvas = _renderizar_slide_carrusel(
            titular=titular,
            puntos=puntos,
            cta=cta,
            categoria_badge=categoria_badge,
            numero_slide=numero_slide,
            ruta_imagen_fondo=ruta_imagen_fondo,
            ancho=ancho,
            alto=alto
        )

        res_guardado = _guardar_en_formatos(
            imagen_canvas=canvas,
            destino_p=destino_p,
            formato_salida=formato_salida,
            descripcion=titular,
            tipo_diseno="Lámina de Carrusel Editorial"
        )

        return json.dumps({
            "status": "success",
            "ruta_archivo": res_guardado["ruta_principal"],
            "archivos": res_guardado["archivos"],
            "dimensiones": f"{ancho}x{alto}",
            "slide": numero_slide,
            "mensaje": f"Lámina de carrusel maquetada con éxito en {res_guardado['ruta_principal']}."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al maquetar lámina: {str(e)}"}, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 2: MAQUETAR CARRUSEL COMPLETO POR LOTES (3 A 7 LÁMINAS)
# ══════════════════════════════════════════════════════════════════════════════

class CarruselCompletoParams(BaseModel):
    tema_carrusel: str = Field(description="Tema central o título de la campaña.")
    laminas: List[Dict[str, Any]] = Field(description="Lista de diccionarios para cada lámina con: 'titular', 'puntos_contenido', y opcionales 'cta', 'categoria_badge', 'ruta_imagen_fondo'.")
    prefijo_archivos: str = Field(default="carrusel_campana", description="Prefijo de los archivos generados en informes/.")
    dimensiones: str = Field(default="1080x1350", description="'1080x1350' (vertical) o '1080x1080' (cuadrado).")
    paleta_acento: str = Field(default="#6366F1", description="Color HEX de acento homogéneo (ej. #6366F1, #10B981, #D97706).")
    formato_salida: str = Field(default="PNG", description="Formato: 'PNG', 'WEBP' o 'AMBOS'.")


@tool("maquetar_carrusel_completo", args_schema=CarruselCompletoParams)
def maquetar_carrusel_completo(
    tema_carrusel: str,
    laminas: List[Dict[str, Any]],
    prefijo_archivos: str = "carrusel_campana",
    dimensiones: str = "1080x1350",
    paleta_acento: str = "#6366F1",
    formato_salida: str = "PNG"
) -> str:
    """
    Genera un carrusel publicitario completo de múltiples láminas (por lotes) en una sola ejecución.
    Calcula automáticamente la numeración secuencial unificada ('01/05', '02/05', etc.), mantiene
    coherencia tipográfica y de color, y crea metadatos de verificación individual en disco.
    """
    try:
        if not laminas or not isinstance(laminas, list):
            return json.dumps({"status": "error", "mensaje": "Se requiere una lista de láminas válida."}, ensure_ascii=False)

        total_laminas = len(laminas)
        ancho, alto = 1080, 1350
        if "x" in dimensiones.lower():
            try:
                partes = dimensiones.lower().split("x")
                ancho = int(partes[0].strip())
                alto = int(partes[1].strip())
            except Exception:
                pass

        entregables = []
        for i, item in enumerate(laminas):
            num_str = f"0{i + 1}/0{total_laminas}" if total_laminas < 10 else f"{i + 1}/{total_laminas}"
            nombre_archivo = f"{prefijo_archivos}_slide_{i + 1:02d}.png"
            destino_p = _INFORMES / nombre_archivo

            titular = item.get("titular", f"Lámina {i + 1}")
            puntos = item.get("puntos_contenido", [])
            cta = item.get("cta", "Desliza para continuar 👉" if i < total_laminas - 1 else "Síguenos para más 🚀")
            badge = item.get("categoria_badge", tema_carrusel[:20].upper())
            fondo = item.get("ruta_imagen_fondo")

            canvas = _renderizar_slide_carrusel(
                titular=titular,
                puntos=puntos,
                cta=cta,
                categoria_badge=badge,
                numero_slide=num_str,
                ruta_imagen_fondo=fondo,
                ancho=ancho,
                alto=alto,
                paleta_acento=paleta_acento
            )

            res = _guardar_en_formatos(
                imagen_canvas=canvas,
                destino_p=destino_p,
                formato_salida=formato_salida,
                descripcion=f"{tema_carrusel} - Slide {num_str}: {titular}",
                tipo_diseno=f"Carrusel Multilámina ({num_str})"
            )

            entregables.append({
                "slide": num_str,
                "titular": titular,
                "archivo_principal": res["ruta_principal"],
                "archivos": res["archivos"]
            })

        return json.dumps({
            "status": "success",
            "tema_carrusel": tema_carrusel,
            "total_laminas_generadas": len(entregables),
            "dimensiones": f"{ancho}x{alto}",
            "formato_salida": formato_salida,
            "entregables": entregables,
            "mensaje": f"Carrusel completo de {len(entregables)} láminas generado exitosamente en {_INFORMES.as_posix()}."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al generar carrusel completo: {str(e)}"}, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HERRAMIENTA 3: SUPERPONER BRANDING SOBRE FOTO DE PRODUCTO (ESPACIO NEGATIVO)
# ══════════════════════════════════════════════════════════════════════════════

class BrandingProductoParams(BaseModel):
    ruta_imagen_base: str = Field(description="Ruta de la foto de producto generada con IA (que contiene espacio negativo).")
    titular: str = Field(description="Titular publicitario del producto o beneficio principal.")
    precio_o_subtitulo: str = Field(default="", description="Precio, descuento o subtítulo descriptivo (ej. '$4.50 USD' o 'Notas de cata y origen').")
    cta: str = Field(default="ORDENAR AHORA", description="Texto del botón de compra o llamada a la acción.")
    ruta_destino: str = Field(default="post_producto_final.png", description="Ruta de salida del entregable publicitario.")
    posicion_texto: str = Field(default="top", description="Zona de espacio negativo: 'top' (arriba) o 'bottom' (abajo).")
    estilo_maquetacion: str = Field(default="editorial", description="Estilo: 'editorial' (lujo centrado serif), 'modern' (asimétrico con badges), 'bento' (tarjeta glassmorphism flotante).")
    eyebrow_categoria: str = Field(default="", description="Pill superior de categoría o etiqueta (ej. 'COLD BREW ARTESANAL').")
    badge_lateral: str = Field(default="", description="Badge superior secundario (ej. 'CALIDAD 4.9/5' o '-20% HOY').")
    paleta_acento: str = Field(default="#D97706", description="Color HEX de acento de marca para botones y bordes (default ámbar #D97706).")
    ruta_logo_png: Optional[str] = Field(default=None, description="Ruta opcional a un archivo de logotipo PNG con transparencia (canal alfa).")
    posicion_logo: str = Field(default="top_left", description="Posición del logotipo: 'top_left', 'top_right' o 'top_center'.")
    formato_salida: str = Field(default="PNG", description="Formato de exportación: 'PNG', 'WEBP' o 'AMBOS'.")


@tool("superponer_branding_producto", args_schema=BrandingProductoParams)
def superponer_branding_producto(
    ruta_imagen_base: str,
    titular: str,
    precio_o_subtitulo: str = "",
    cta: str = "ORDENAR AHORA",
    ruta_destino: str = "post_producto_final.png",
    posicion_texto: str = "top",
    estilo_maquetacion: str = "editorial",
    eyebrow_categoria: str = "",
    badge_lateral: str = "",
    paleta_acento: str = "#D97706",
    ruta_logo_png: Optional[str] = None,
    posicion_logo: str = "top_left",
    formato_salida: str = "PNG"
) -> str:
    """
    Fase 4: Posprocesamiento de Branding y Maquetación de Agencia. Toma una fotografía de producto generada por IA,
    respeta rigurosamente el espacio negativo superior (máximo 28% de altura) sin tocar el envase ni tapar el producto,
    superpone logotipo PNG con canal alfa si existe, y compone tipografía editorial, badges, subtítulo y botón CTA.
    Soporta exportación a PNG y WebP.
    """
    try:
        p_base = Path(ruta_imagen_base)
        if not p_base.is_absolute():
            p_base = _INFORMES / p_base.name

        if not p_base.exists():
            return json.dumps({"status": "error", "mensaje": f"No se encontró la imagen base en {ruta_imagen_base}."}, ensure_ascii=False)

        destino_p = _transformar_ruta(ruta_destino, "post_producto_final.png")
        destino_p.parent.mkdir(parents=True, exist_ok=True)

        img = Image.open(p_base).convert("RGBA")
        ancho, alto = img.size

        # Capa de degradado suave para proteger contraste sobre el espacio negativo
        degradado = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
        draw_deg = ImageDraw.Draw(degradado)

        # Techo de seguridad: Máximo 28% de la altura total para NO tocar el producto jamás
        altura_zona = int(alto * 0.28)
        if posicion_texto.lower() == "top":
            for y in range(altura_zona + 40):
                alpha = int(180 * (1 - (y / (altura_zona + 40))))
                draw_deg.line([(0, y), (ancho, y)], fill=(10, 15, 26, alpha))
            y_base_cursor = int(alto * 0.045)
        else:
            y_base_scrim = alto - altura_zona - 40
            for y in range(altura_zona + 40):
                alpha = int(180 * (y / (altura_zona + 40)))
                draw_deg.line([(0, y_base_scrim + y), (ancho, y_base_scrim + y)], fill=(10, 15, 26, alpha))
            y_base_cursor = alto - altura_zona + 20

        img_compuesta = Image.alpha_composite(img, degradado)

        # ----------------------------------------------------------------------
        # SUPERPOSICIÓN DE LOGOTIPO PNG TRANSPARENTE CON CANAL ALFA
        # ----------------------------------------------------------------------
        if ruta_logo_png:
            p_logo = Path(ruta_logo_png)
            if not p_logo.is_absolute():
                p_logo = _INFORMES / p_logo.name
            if p_logo.exists():
                try:
                    logo_img = Image.open(p_logo).convert("RGBA")
                    # Redimensionar proporcionalmente a máx 16% del ancho o máx 8% del alto
                    max_lw = int(ancho * 0.16)
                    max_lh = int(alto * 0.08)
                    logo_img.thumbnail((max_lw, max_lh), Image.Resampling.LANCZOS)
                    lw, lh = logo_img.size

                    margen_logo_x = int(ancho * 0.085)
                    if posicion_logo.lower() == "top_right":
                        lx = ancho - margen_logo_x - lw
                        ly = int(alto * 0.035)
                    elif posicion_logo.lower() == "top_center":
                        lx = (ancho - lw) // 2
                        ly = int(alto * 0.03)
                    else:  # top_left
                        lx = margen_logo_x
                        ly = int(alto * 0.035)

                    # Pegar respetando transparencia
                    img_compuesta.paste(logo_img, (lx, ly), mask=logo_img)
                except Exception as ex_logo:
                    print(f"[Subagente_Diseno] Advertencia logo: {ex_logo}")

        draw = ImageDraw.Draw(img_compuesta)

        rgba_acento = _hex_a_rgba(paleta_acento, 240)
        rgba_borde = _hex_a_rgba(paleta_acento, 200)

        margen_x = int(ancho * 0.085)
        max_w = ancho - (margen_x * 2)
        estilo = estilo_maquetacion.lower().strip()

        # ----------------------------------------------------------------------
        # ESTILO 1: BENTO GLASS (Tarjeta translúcida flotante tipo Apple/Linear)
        # ----------------------------------------------------------------------
        if estilo == "bento":
            card_x = margen_x
            card_w = max_w
            card_h = int(alto * 0.175)
            card_y = int(alto * 0.035)

            overlay_bento = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
            draw_bento = ImageDraw.Draw(overlay_bento)

            draw_bento.rounded_rectangle(
                [card_x, card_y, card_x + card_w, card_y + card_h],
                radius=16,
                fill=(15, 23, 42, 195),
                outline=rgba_borde,
                width=1
            )
            draw_bento.rounded_rectangle(
                [card_x + 14, card_y + 14, card_x + 18, card_y + card_h - 14],
                radius=2,
                fill=rgba_acento
            )

            font_b_eb = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.022))
            font_b_t = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.046))
            font_b_sub = _obtener_fuente_por_tipo("sans", int(ancho * 0.025))
            font_b_cta = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.024))

            eb_txt = eyebrow_categoria.upper() if eyebrow_categoria else "EDICIÓN ESPECIAL"
            draw_bento.text((card_x + 28, card_y + 14), eb_txt, font=font_b_eb, fill=rgba_acento)
            draw_bento.text((card_x + 28, card_y + 38), titular, font=font_b_t, fill=(255, 255, 255, 255))
            if precio_o_subtitulo:
                draw_bento.text((card_x + 28, card_y + 86), precio_o_subtitulo, font=font_b_sub, fill=(203, 213, 225, 220))

            btn_w = int(ancho * 0.26)
            btn_h = 38
            btn_x = card_x + card_w - btn_w - 16
            btn_y = card_y + card_h - btn_h - 14
            draw_bento.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=10, fill=rgba_acento)
            bb_c = draw_bento.textbbox((0, 0), cta, font=font_b_cta)
            c_w = bb_c[2] - bb_c[0]
            draw_bento.text((btn_x + ((btn_w - c_w) // 2), btn_y + 8), cta, font=font_b_cta, fill=(255, 255, 255, 255))

            img_compuesta = Image.alpha_composite(img_compuesta, overlay_bento)

        # ----------------------------------------------------------------------
        # ESTILO 2: MODERN ASYMMETRIC (Alineado a la izquierda con badge lateral)
        # ----------------------------------------------------------------------
        elif estilo == "modern":
            y_cur = y_base_cursor
            font_m_eb = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.024))
            font_m_t = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.054))
            font_m_sub = _obtener_fuente_por_tipo("sans", int(ancho * 0.027))
            font_m_cta = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.025))

            badge_sec = badge_lateral if badge_lateral else "4.9/5 EXCELENCIA"
            bb_bg = draw.textbbox((0, 0), badge_sec, font=font_m_eb)
            bg_w = bb_bg[2] - bb_bg[0]
            bg_x = ancho - margen_x - bg_w - 24
            draw.rounded_rectangle([bg_x, y_cur, bg_x + bg_w + 24, y_cur + 30], radius=15, fill=(20, 20, 20, 190), outline=rgba_borde, width=1)
            draw.text((bg_x + 12, y_cur + 6), badge_sec, font=font_m_eb, fill=rgba_acento)

            eb_txt = eyebrow_categoria.upper() if eyebrow_categoria else "SELECCIÓN PREMIUM"
            draw.text((margen_x, y_cur + 5), eb_txt, font=font_m_eb, fill=rgba_acento)
            y_cur += 40

            draw.text((margen_x + 2, y_cur + 2), titular, font=font_m_t, fill=(0, 0, 0, 180))
            draw.text((margen_x, y_cur), titular, font=font_m_t, fill=(255, 255, 255, 255))
            y_cur += int(font_m_t.size * 1.35)

            if precio_o_subtitulo:
                draw.text((margen_x, y_cur), precio_o_subtitulo, font=font_m_sub, fill=(203, 213, 225, 230))
                y_cur += int(font_m_sub.size * 1.45)

            btn_h = 44
            bb_c = draw.textbbox((0, 0), cta, font=font_m_cta)
            c_w = bb_c[2] - bb_c[0]
            btn_w = c_w + 44
            draw.rounded_rectangle([margen_x, y_cur, margen_x + btn_w, y_cur + btn_h], radius=22, fill=rgba_acento, outline=(255, 255, 255, 180), width=1)
            draw.text((margen_x + 22, y_cur + 11), cta, font=font_m_cta, fill=(255, 255, 255, 255))

        # ----------------------------------------------------------------------
        # ESTILO 3: EDITORIAL LUXURY (Centrado clásico con tipografía Serif)
        # ----------------------------------------------------------------------
        else:
            y_cur = y_base_cursor
            font_e_eb = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.026))
            font_e_t = _obtener_fuente_por_tipo("serif_bold", int(ancho * 0.056))
            font_e_sub = _obtener_fuente_por_tipo("sans", int(ancho * 0.028))
            font_e_cta = _obtener_fuente_por_tipo("sans_bold", int(ancho * 0.026))

            eb_txt = eyebrow_categoria.upper() if eyebrow_categoria else "COLD BREW ARTESANAL"
            bb_eb = draw.textbbox((0, 0), eb_txt, font=font_e_eb)
            eb_w = bb_eb[2] - bb_eb[0]
            eb_x = (ancho - eb_w) // 2
            draw.rounded_rectangle([eb_x - 16, y_cur - 4, eb_x + eb_w + 16, y_cur + 28], radius=14, fill=(25, 20, 16, 180), outline=rgba_borde, width=1)
            draw.text((eb_x, y_cur), eb_txt, font=font_e_eb, fill=rgba_acento)
            y_cur += 50

            bb_t = draw.textbbox((0, 0), titular, font=font_e_t)
            t_w = bb_t[2] - bb_t[0]
            t_x = (ancho - t_w) // 2
            draw.text((t_x + 2, y_cur + 2), titular, font=font_e_t, fill=(0, 0, 0, 200))
            draw.text((t_x, y_cur), titular, font=font_e_t, fill=(255, 255, 255, 255))
            y_cur += int(font_e_t.size * 1.35)

            if precio_o_subtitulo:
                bb_s = draw.textbbox((0, 0), precio_o_subtitulo, font=font_e_sub)
                s_w = bb_s[2] - bb_s[0]
                s_x = (ancho - s_w) // 2
                draw.text((s_x, y_cur), precio_o_subtitulo, font=font_e_sub, fill=(203, 213, 225, 240))
                y_cur += int(font_e_sub.size * 1.5)

            bb_c = draw.textbbox((0, 0), cta, font=font_e_cta)
            c_w = bb_c[2] - bb_c[0]
            btn_w = c_w + 50
            btn_h = 46
            btn_x = (ancho - btn_w) // 2
            draw.rounded_rectangle([btn_x, y_cur, btn_x + btn_w, y_cur + btn_h], radius=23, fill=rgba_acento, outline=(251, 191, 36, 255), width=2)
            draw.text((btn_x + ((btn_w - c_w) // 2), y_cur + 11), cta, font=font_e_cta, fill=(255, 255, 255, 255))

        res_guardado = _guardar_en_formatos(
            imagen_canvas=img_compuesta,
            destino_p=destino_p,
            formato_salida=formato_salida,
            descripcion=titular,
            tipo_diseno=f"Branding Publicitario ({estilo})"
        )

        return json.dumps({
            "status": "success",
            "ruta_archivo": res_guardado["ruta_principal"],
            "archivos": res_guardado["archivos"],
            "estilo_aplicado": estilo,
            "logo_superpuesto": bool(ruta_logo_png),
            "mensaje": f"Pieza publicitaria con branding de agencia generada en {res_guardado['ruta_principal']} con estilo '{estilo}'."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "mensaje": f"Fallo al superponer branding: {str(e)}"}, ensure_ascii=False)


HERRAMIENTAS_IMAGENES = [
    maquetar_carrusel_instagram,
    maquetar_carrusel_completo,
    superponer_branding_producto
]
