# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Tripulación IA (Luffy, Zoro, Robin, Nami, Usop)
# Base: python:3.11-slim  (Debian Bookworm thin)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── Metadatos ────────────────────────────────────────────────────────────────
LABEL maintainer="Wuilfredo"
LABEL description="Sandbox aislado para el ecosistema multiagente de la Tripulación"

# ── Variables de entorno base ─────────────────────────────────────────────────
# Evita prompts interactivos de apt y mejora salida de logs Python
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Las rutas internas del contenedor (sobreescriben las rutas Windows en los .py)
    AGENTES_ROOT=/app \
    SHARED_MEMORY_PATH=/app/memoria_compartida \
    PYTHONPATH=/app/Luffy:/app/Zoro:/app/Robin:/app/Nami:/app/Usop

# ── Dependencias del Sistema Operativo ───────────────────────────────────────
# git         → habilidades de Zoro (skill_git.py)
# nodejs/npm  → auditorías de Robin (npm audit, escaneos JS)
# curl        → herramienta auxiliar para depuración y health checks
# procps      → ps, kill — control de procesos en start.sh
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        procps \
        ca-certificates \
        gnupg \
    # ── Instalar Node.js 20 LTS desde el repositorio oficial de NodeSource ──
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g n8n ngrok \
    # ── Limpiar cache de apt para reducir el tamaño de la imagen ──────────
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ─────────────────────────────────────────────────────
WORKDIR /app

# ── Dependencias Python ───────────────────────────────────────────────────────
# Copiamos solo requirements.txt primero para aprovechar la caché de Docker:
# si el archivo no cambia, esta capa no se reconstruye.
COPY Luffy/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    # Instalar dependencias del requirements.txt del proyecto
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    # Paquetes adicionales usados por los agentes pero no declarados en requirements.txt
    && pip install --no-cache-dir \
        openai \
        langchain-openai \
        langchain-community \
        python-telegram-bot \
        requests \
        python-dotenv \
    # Dependencias Google Workspace (Gmail, Docs, Drive, Calendar) — Luffy
    && pip install --no-cache-dir \
        google-api-python-client \
        google-auth-httplib2 \
        google-auth-oauthlib

# ── El código fuente se monta como volumen en tiempo de ejecución ─────────────
# (No hacemos COPY . /app aquí para que los cambios en Windows
#  sean inmediatos sin reconstruir la imagen)

# ── Usuario sin privilegios (principio de mínimo privilegio) ─────────────────
# Creamos un usuario no-root para que los agentes no puedan dañar el sistema
RUN groupadd --gid 1001 tripulacion \
    && useradd --uid 1001 --gid tripulacion --shell /bin/bash --create-home tripulacion \
    && chown -R tripulacion:tripulacion /app

USER tripulacion

# ── Puerto expuesto (informativo — no se usa activamente por ahora) ───────────
# Reservado por si se agrega un health-check HTTP en el futuro
EXPOSE 8080

# El CMD real lo define docker-compose.yml vía el script start.sh
CMD ["/bin/bash"]
