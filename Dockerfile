# syntax=docker/dockerfile:1
#
# Imagen de notiemoji en tres etapas:
#
#   deps   -> solo pyproject.toml + uv.lock. La capa se cachea mientras no
#             cambien las dependencias.
#   build  -> agrega el código e instala el proyecto (install editable con
#             rutas absolutas, por eso WORKDIR es /app en ambas etapas).
#   final  -> Python slim + fuentes del sistema. Sin uv, sin toolchains.
#
# Las fuentes van por apt en vez de bajarse a mano: python:3.13-slim-trixie
# es la misma base que python:3.13-slim y trae fonts-noto-color-emoji 2.051,
# cuyo NotoColorEmoji.ttf es CBDT/CBLC — el único formato que sabe leer
# emoji_strike_size(). En el buildpack de Render esto era imposible por el
# filesystem de solo lectura; en el contenedor somos root y apt funciona.

FROM python:3.13-slim-trixie AS deps

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# uv fijado a la versión con la que se desarrolla el proyecto: el lockfile
# declara version = 1, revision = 3, y el binario del build tiene que poder
# leerlo. --frozen hace que el build falle si el lockfile no está sincronizado.
RUN pip install --no-cache-dir uv==0.12.19

WORKDIR /app

# Primero el manifiesto: si solo cambia el código, esta capa queda entera.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project


FROM deps AS build

# README.md entra porque pyproject.toml lo declara como `readme`.
COPY README.md api.py notiemoji.py index.html ./
RUN uv sync --no-dev --frozen


FROM python:3.13-slim-trixie AS final

# fonts-dejavu-extra trae DejaVuSans-Oblique / BoldOblique (los estilos
# cursivos de TEXT_FONTS); sin él, la cursiva cae al fallback regular.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        fonts-dejavu-extra \
        fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios: la app solo lee su /app y las fuentes del sistema.
RUN useradd --create-home --uid 10001 notiemoji

# Misma ruta que en `build`: el install editable apunta a /app/api y
# /app/notiemoji por ruta absoluta.
WORKDIR /app

COPY --from=build --chown=notiemoji:notiemoji /app /app

USER notiemoji

# .venv/bin primero para resolver uvicorn y python; sin bytecode en runtime
# (el FS del contenedor se descarta igual, y arranca más limpio).
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Sonda de salud que lee el runtime. Requiere `podman build --format docker`:
# en formato OCI (el default de Podman) se descarta con un warning.
# PORT lo inyecta Render (10000 por defecto); fuera de Render cae a 8000.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request as u; u.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=4)"

# `exec` deja a uvicorn como PID 1 para que reciba SIGTERM de Render y
# cierre limpio en vez de morir con timeout.
CMD ["sh", "-c", "exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
