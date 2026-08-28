import datetime
from langchain_core.tools import tool
from skill_google_sanji import obtener_servicio

@tool
def tool_google_calendar_listar(max_results: int = 10) -> str:
    """
    Lista los próximos eventos agendados en Google Calendar.
    Devuelve la fecha, hora y resumen de cada evento.
    """
    try:
        service = obtener_servicio('calendar', 'v3')
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No hay eventos próximos en Google Calendar."
            
        lines = ["Próximos Eventos en Calendar:"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            lines.append(f"- [{start}] {event['summary']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error en Google Calendar: {str(e)}"
