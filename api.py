#!/usr/bin/env python3
"""API HTTP de notiemoji: genera wallpapers PNG en memoria con FastAPI.

Reutiliza la lógica de notiemoji.py (paletas, colores y renderizado) para
que la CLI y la API compartan comportamiento. No escribe archivos en disco.
El frontend vive en GitHub Pages (docs/); la API se despliega en Render y
expone GET /paletas, GET /health y GET|POST /wallpaper.

Desarrollo local: uvicorn api:app --reload
"""

import io
import threading
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import ImageColor, ImageFont
from pydantic import BaseModel, ConfigDict, field_validator

import notiemoji

# Límite por lado en px. 4000x4000 en RGB ocupa ~48 MB: en el plan gratis de
# Render (512 MB) el pico admisible de imágenes en paralelo queda cómodo.
MAX_DIMENSION = 4000

# Tope de font_size: Pillow lanza OSError con tamaños extremos (que la API
# traduciría en un 500); con el tope la validación responde 422 limpio.
MAX_FONT_SIZE = 2000

# Generaciones simultáneas permitidas. Con el techo de 4000x4000 (~48 MB por
# imagen), 3 en paralelo suman ~144 MB de pico, holgado en los 512 MB del
# plan gratis de Render: el threadpool de FastAPI (~40 workers) ejecuta estos
# endpoints síncronos en paralelo y sin este límite varios requests grandes
# terminarían en un OOM.
GENERACIONES_SIMULTANEAS = 3

# Semáforo de módulo compartido por GET y POST /wallpaper. Se adquiere sin
# bloquear (ver _generar_wallpaper): esperar encolaría peticiones y acumularía
# memoria, que es justo lo que el límite busca evitar.
SEMAFORO_GENERACION = threading.BoundedSemaphore(GENERACIONES_SIMULTANEAS)

# Etiqueta legible de cada estilo de notiemoji.TEXT_FONTS, para /health.
ESTILOS_TEXTO = {
    (False, False): "normal",
    (True, False): "negrita",
    (False, True): "cursiva",
    (True, True): "negrita+cursiva",
}

app = FastAPI(
    title="notiemoji",
    description="Genera wallpapers PNG con fondo de color plano y texto o emojis centrados.",
)

# CORS: el frontend vive en GitHub Pages y la API en Render.
# En desarrollo, el frontend corre en localhost con otro puerto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.github.io"],
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class WallpaperRequest(BaseModel):
    """Parámetros para generar un wallpaper."""

    # extra="forbid": un campo mal escrito (p. ej. "fondo" en vez de "color")
    # responde 422 en vez de descartarse en silencio y usar el valor por defecto.
    model_config = ConfigDict(extra="forbid")

    width: int
    height: int
    text: str = ""
    palette: str | None = None
    color: str | None = None
    text_color: str | None = None
    font_size: int = 96
    bold: bool = False
    italic: bool = False

    @field_validator("width", "height")
    @classmethod
    def _validate_dimension(cls, value: int) -> int:
        """Acota cada lado a (0, MAX_DIMENSION] para evitar agotar la memoria."""
        if value <= 0:
            raise ValueError(f"debe ser mayor a 0, no {value}")
        if value > MAX_DIMENSION:
            raise ValueError(f"no puede superar {MAX_DIMENSION} px por lado, no {value}")
        return value

    @field_validator("font_size")
    @classmethod
    def _validate_font_size(cls, value: int) -> int:
        """Acota font_size a (0, MAX_FONT_SIZE] (ver MAX_FONT_SIZE)."""
        if value <= 0:
            raise ValueError(f"debe ser mayor a 0, no {value}")
        if value > MAX_FONT_SIZE:
            raise ValueError(f"no puede superar {MAX_FONT_SIZE}, no {value}")
        return value

    @field_validator("palette")
    @classmethod
    def _validate_palette(cls, value: str | None) -> str | None:
        """Solo None o un nombre de PALETTES; se normaliza a minúsculas."""
        if value is None:
            return value
        name = value.lower()
        if name not in notiemoji.PALETTES:
            raise ValueError(
                f"paleta inválida: {value!r} (opciones: {', '.join(notiemoji.PALETTES)})"
            )
        return name

    @field_validator("color", "text_color")
    @classmethod
    def _validate_color(cls, value: str | None) -> str | None:
        """Acepta solo valores válidos para PIL.ImageColor.getrgb."""
        if value is None:
            return value
        try:
            ImageColor.getrgb(value)
        except ValueError:
            raise ValueError(
                f"color inválido: {value!r} (ej.: #0d1117 o navy)"
            ) from None
        return value


class Paleta(BaseModel):
    """Una paleta curada de notiemoji.PALETTES."""

    nombre: str
    color: str
    texto: str


class FuenteEmoji(BaseModel):
    """Disponibilidad de NotoColorEmoji.ttf, con su ruta si está."""

    disponible: bool
    ruta: str | None = None


class FuenteTexto(BaseModel):
    """Disponibilidad de las fuentes de un estilo de texto."""

    estilo: str
    disponible: bool
    # Primer archivo de TEXT_FONTS que resuelve Pillow para ese estilo.
    fuente: str | None = None


class Fuentes(BaseModel):
    """Recursos que la generación de wallpapers necesita en el sistema."""

    emoji: FuenteEmoji
    texto: list[FuenteTexto]


class HealthResponse(BaseModel):
    """Estado del servicio: siempre HTTP 200, el estado real va en el body."""

    estado: Literal["ok", "degradado"]
    version: str
    fuentes: Fuentes


@app.get("/paletas", response_model=list[Paleta])
def paletas() -> list[Paleta]:
    """Lista las paletas curadas en el orden de notiemoji.PALETTES."""
    return [
        Paleta(nombre=nombre, color=fondo, texto=txt)
        for nombre, (fondo, txt) in notiemoji.PALETTES.items()
    ]


def _chequear_fuente_emoji() -> FuenteEmoji:
    """Busca la fuente de emoji sin dejar propagar errores si falta.

    /health es un healthcheck: debe responder siempre, así que cualquier
    fallo de búsqueda (FileNotFoundError/OSError) o de lectura del archivo
    (ValueError) se traduce en "no disponible" y nunca en una excepción.
    """
    try:
        ruta = notiemoji.find_emoji_font()
    except (FileNotFoundError, OSError, ValueError):
        return FuenteEmoji(disponible=False)
    return FuenteEmoji(disponible=True, ruta=str(ruta))


def _chequear_fuentes_texto() -> list[FuenteTexto]:
    """Indica si alguna fuente de cada estilo de TEXT_FONTS resuelve en Pillow."""
    resultado = []
    for estilo, nombres in notiemoji.TEXT_FONTS.items():
        resuelta = None
        for nombre in nombres:
            try:
                ImageFont.truetype(nombre, 16)
            except (OSError, ValueError):
                continue
            resuelta = nombre
            break
        resultado.append(
            FuenteTexto(
                estilo=ESTILOS_TEXTO[estilo],
                disponible=resuelta is not None,
                fuente=resuelta,
            )
        )
    return resultado


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Reporta versión y recursos disponibles; responde 200 siempre.

    Si falta alguna fuente, el estado pasa a "degradado" pero la respuesta
    sigue siendo 200: el estado real vive en el body, no en el código HTTP.
    """
    emoji = _chequear_fuente_emoji()
    texto = _chequear_fuentes_texto()
    completo = emoji.disponible and all(fuente.disponible for fuente in texto)
    return HealthResponse(
        estado="ok" if completo else "degradado",
        version=notiemoji.VERSION,
        fuentes=Fuentes(emoji=emoji, texto=texto),
    )


def _generar_wallpaper(params: WallpaperRequest) -> Response:
    """Genera el PNG en memoria y lo devuelve; lo comparten GET y POST.

    Misma precedencia de colores que la CLI: color explícito > paleta >
    defecto (#000000/#ffffff). Devuelve 503 si falta la fuente de emoji.

    Acquire sin bloquear: si no hay lugar responde 429 de inmediato en vez
    de encolar (las colas acumulan memoria y empeoran el problema que el
    semáforo viene a resolver). El release va en un finally para que el
    semáforo nunca quede trabado, ni siquiera si la generación falla.
    """
    if not SEMAFORO_GENERACION.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail=(
                "demasiadas generaciones simultáneas; probá de nuevo en un momento"
            ),
            headers={"Retry-After": "1"},
        )
    try:
        background, foreground = notiemoji.resolve_colors(
            params.palette, params.color, params.text_color
        )
        image = notiemoji.render_wallpaper(
            params.width,
            params.height,
            background,
            params.text,
            foreground,
            params.font_size,
            params.bold,
            params.italic,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    except notiemoji.EmojiFontError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Fallo inesperado: 500 genérico, sin exponer el stack trace.
        raise HTTPException(
            status_code=500, detail="no se pudo generar el wallpaper"
        ) from exc
    finally:
        SEMAFORO_GENERACION.release()
    return Response(content=buffer.getvalue(), media_type="image/png")


@app.post("/wallpaper")
def wallpaper_post(params: WallpaperRequest) -> Response:
    """Genera el wallpaper en memoria y lo devuelve como PNG."""
    return _generar_wallpaper(params)


@app.get("/wallpaper")
def wallpaper_get(
    params: Annotated[WallpaperRequest, Query()],
) -> Response:
    """Misma generación que POST /wallpaper pero consultando por URL.

    FastAPI modela WallpaperRequest como query params: mismos nombres,
    tipos, defaults y validaciones (y por lo tanto mismos 422) que el POST.
    """
    return _generar_wallpaper(params)
