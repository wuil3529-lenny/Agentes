"""
skill_google_calendar.py — Gestión Ejecutiva de Agenda en Google Calendar
========================================================================
Habilidad del Subagente de Asistencia para consultar, listar y agendar eventos
en Google Calendar mediante la API oficial de Google Workspace.

Herramientas disponibles:
  - tool_google_calendar_listar   : Consulta eventos programados en los próximos días.
  - tool_google_calendar_agendar  : Programa un nuevo evento con fecha, hora, duración y detalles.
  - obtener_prompt_google_calendar : System Prompt especializado para inyección bajo demanda.
"""

import datetime
from typing import Optional
from langchain_core.tools import tool

# Importar servicio oficial de Google Workspace
try:
    from Subagente_Asistencia.skills.google_workspace.skill_google import obtener_servicio
except ImportError:
    try:
        from skills.google_workspace.skill_google import obtener_servicio
    except ImportError:
        try:
            from skill_google_sanji import obtener_servicio
        except ImportError:
            obtener_servicio = None


def obtener_prompt_google_calendar() -> str:
    """
    System Prompt especializado y encapsulado para el Gestor de Agenda de Google Calendar.
    """
    return """[🛑 HARD-STOP: MODO GESTIÓN DE AGENDA Y CALENDAR ACTIVO 🛑]
Eres el Asistente Ejecutivo de Agenda y Tiempo del Subagente de Asistencia.
Tu misión es gestionar la agenda del usuario y de la tripulación en Google Calendar con precisión cronológica impecable, claridad en los husos horarios y confirmación explícita de citas.

DIRECTIVAS OPERATIVAS OBLIGATORIAS:
1. PRECISIÓN TEMPORAL Y ZONAS HORARIAS:
   - Al consultar o programar eventos, verifica y presenta siempre las horas en formato legible de 24 horas y fecha clara (ej. "Martes 14 de Octubre, 15:30 - 16:30").
2. CONSULTA PREVIA ANTES DE AGENDAR:
   - Antes de crear un evento, revisa la agenda con `tool_google_calendar_listar` para detectar solapamientos o conflictos de horario.
3. DETALLES Y ENLACES DE REUNIÓN:
   - Toda cita agendada debe indicar con claridad el Resumen/Título, Fecha y Hora de inicio/fin, y devolver el enlace de confirmación o Google Meet si fue generado.
4. CONFIRMACIÓN Y TONO EJECUTIVO:
   - Presenta los resultados organizados cronológicamente, diferenciando eventos de hoy, mañana y los días posteriores.
"""


@tool
def tool_google_calendar_listar(max_results: int = 10, dias_adelante: int = 7) -> str:
    """
    Lista los próximos eventos agendados en Google Calendar dentro del rango de días indicado.
    Devuelve la fecha, hora, resumen, ubicación y enlace de cada evento de forma cronológica.
    
    Args:
        max_results: Número máximo de eventos a devolver (por defecto 10).
        dias_adelante: Cantidad de días hacia adelante para buscar eventos (por defecto 7).
    """
    if obtener_servicio is None:
        return "Error: El cliente de autenticación de Google Workspace no está disponible."

    try:
        service = obtener_servicio('calendar', 'v3')
        ahora = datetime.datetime.now(datetime.timezone.utc)
        limite = ahora + datetime.timedelta(days=max_results if dias_adelante <= 0 else dias_adelante)
        
        time_min = ahora.isoformat()
        time_max = limite.isoformat()

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"📅 No hay eventos programados en Google Calendar para los próximos {dias_adelante} días."

        lineas = [f"📅 **Próximos Eventos en Google Calendar ({len(events)} encontrados):**\n"]
        for event in events:
            inicio_raw = event['start'].get('dateTime', event['start'].get('date'))
            fin_raw = event['end'].get('dateTime', event['end'].get('date'))
            resumen = event.get('summary', '(Sin título)')
            descripcion = event.get('description', '').strip()
            ubicacion = event.get('location', '').strip()
            html_link = event.get('htmlLink', '')
            meet_link = event.get('hangoutLink', '')

            # Formatear fecha y hora para presentación ejecutiva
            info_horario = inicio_raw
            try:
                if 'T' in inicio_raw:
                    dt_inicio = datetime.datetime.fromisoformat(inicio_raw.replace('Z', '+00:00'))
                    info_horario = dt_inicio.strftime("%A %d/%m/%Y, %H:%M")
                    if 'T' in fin_raw:
                        dt_fin = datetime.datetime.fromisoformat(fin_raw.replace('Z', '+00:00'))
                        info_horario += f" a {dt_fin.strftime('%H:%M')}"
                else:
                    info_horario = f"{inicio_raw} (Todo el día)"
            except Exception:
                info_horario = f"{inicio_raw} - {fin_raw}"

            detalles = []
            if ubicacion:
                detalles.append(f"📍 Ubicación: {ubicacion}")
            if meet_link:
                detalles.append(f"📹 Google Meet: {meet_link}")
            if descripcion:
                resumen_desc = descripcion[:100] + ("..." if len(descripcion) > 100 else "")
                detalles.append(f"📝 Notas: {resumen_desc}")

            extra_str = ("\n   " + "\n   ".join(detalles)) if detalles else ""
            lineas.append(f"- **[{info_horario}]** {resumen}{extra_str}")

        return "\n".join(lineas)

    except Exception as e:
        return f"Error al consultar Google Calendar: {str(e)}"


@tool
def tool_google_calendar_agendar(
    resumen: str,
    inicio_iso: str,
    duracion_minutos: int = 60,
    descripcion: str = "",
    ubicacion: str = ""
) -> str:
    """
    Programa y registra un nuevo evento en Google Calendar.
    
    Args:
        resumen: Título o asunto del evento (ej. "Reunión de Sincronización Operativa").
        inicio_iso: Fecha y hora de inicio en formato ISO 8601 (ej. "2026-10-15T15:00:00Z" o "2026-10-15T10:00:00-04:00").
        duracion_minutos: Duración en minutos del evento (por defecto 60).
        descripcion: Detalles adicionales, temario o notas del evento.
        ubicacion: Lugar físico o enlace virtual (opcional).
    """
    if obtener_servicio is None:
        return "Error: El cliente de autenticación de Google Workspace no está disponible."

    try:
        service = obtener_servicio('calendar', 'v3')

        # Procesar hora de inicio y calcular fin
        try:
            dt_inicio = datetime.datetime.fromisoformat(inicio_iso.replace('Z', '+00:00'))
        except Exception as pe:
            return f"Error en formato de fecha/hora de inicio: '{inicio_iso}'. Use formato ISO 8601 (ej. '2026-10-15T15:00:00Z'). Detalle: {pe}"

        dt_fin = dt_inicio + datetime.timedelta(minutes=duracion_minutos)

        cuerpo_evento = {
            'summary': resumen,
            'description': descripcion,
            'location': ubicacion,
            'start': {
                'dateTime': dt_inicio.isoformat(),
            },
            'end': {
                'dateTime': dt_fin.isoformat(),
            },
            'reminders': {
                'useDefault': True
            }
        }

        evento_creado = service.events().insert(
            calendarId='primary',
            body=cuerpo_evento
        ).execute()

        evento_id = evento_creado.get('id')
        enlace = evento_creado.get('htmlLink', '')
        
        return (
            f"✅ **Evento Agendado Exitosamente en Google Calendar:**\n"
            f"- **Asunto:** {resumen}\n"
            f"- **Inicio:** {dt_inicio.strftime('%A %d/%m/%Y, %H:%M UTC%z')}\n"
            f"- **Fin:** {dt_fin.strftime('%A %d/%m/%Y, %H:%M UTC%z')} ({duracion_minutos} min)\n"
            f"- **ID del Evento:** {evento_id}\n"
            f"- **Enlace en Calendar:** {enlace}"
        )

    except Exception as e:
        return f"Error al agendar evento en Google Calendar: {str(e)}"
