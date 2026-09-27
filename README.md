# notiemoji

API HTTP desarrollada con **FastAPI**, **Pydantic** y **Pillow** para generar
wallpapers PNG personalizados con texto y emojis 🎨.

El proyecto incluye validación tipada de requests, endpoints REST, generación
de imágenes en memoria, control de concurrencia, health check, documentación
OpenAPI, tests automatizados y despliegue en Render.

**Demo:** [https://notiemoji.onrender.com](https://notiemoji.onrender.com)

**Documentación de la API:**
[https://notiemoji.onrender.com/docs](https://notiemoji.onrender.com/docs)

## Características técnicas

- API REST con FastAPI.
- Validación de entrada mediante modelos Pydantic.
- Documentación automática con OpenAPI y Swagger.
- Generación de imágenes en memoria con Pillow.
- Health check para comprobar el estado de la aplicación y sus fuentes.
- Límite de concurrencia para controlar el uso de memoria.
- Respuestas HTTP diferenciadas para validación, saturación y errores.
- Tests unitarios y de integración con `unittest` y `TestClient`.
- Despliegue automatizado en Render mediante `render.yaml`.

## Ejemplos

El mismo script genera wallpapers en distintos formatos y estilos:

| Horizontal — `1920x1080` |
|---|
| ![Ejemplo horizontal de notiemoji: «notiemoji 🎨» sobre un fondo oscuro](docs/horizontal.png) |

| Vertical — `720x1080` | Cuadrado — `1080x1080` |
|---|---|
| ![Wallpaper vertical de notiemoji: «notiemoji 🌙» en cursiva sobre fondo azul oscuro](docs/vertical.png) | ![Wallpaper cuadrado de notiemoji: «notiemoji 🌈» en negrita sobre fondo claro](docs/cuadrado.png) |

## Requisitos

- Python 3.11 o superior.
- [uv](https://docs.astral.sh/uv/), para gestionar el entorno virtual y las
  dependencias.
- Pillow 10.1 o superior.
- FastAPI y `uvicorn`, el servidor ASGI que ejecuta `api.py`.
- En desarrollo, `httpx`, requerido por
  `fastapi.testclient.TestClient`.
- Fuentes del sistema:
  - DejaVu Sans para texto.
  - Noto Color Emoji para emojis.
  - Liberation Sans para cursivas cuando DejaVu Sans no incluye la variante
    Oblique.

En Debian/Ubuntu:

```bash
sudo apt install fonts-dejavu-core fonts-noto-color-emoji
```

## Instalación

Las dependencias están declaradas en `pyproject.toml` y se sincronizan con
`uv`:

```bash
uv sync
```

Esto crea el entorno virtual `.venv`, instala las dependencias de producción
(`Pillow`, `fastapi` y `uvicorn`) y las de desarrollo (`httpx`). La resolución
de dependencias queda fijada en `uv.lock`.

## API

`api.py` expone una API HTTP con FastAPI que reutiliza la lógica de
`notiemoji.py`. Las imágenes se generan en memoria y se devuelven como PNG sin
escribirse en disco.

### Arranque en desarrollo

```bash
uv run uvicorn api:app --reload
```

La API estará disponible en:

```text
http://notiemoji.onrender.com
```

La documentación interactiva está disponible en:

```text
http://notiemoji.onrender.com/docs
```

El esquema OpenAPI está disponible en:

```text
http://notiemoji.onrender.com/openapi.json
```

### Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/wallpaper` | Genera un wallpaper y lo devuelve como `image/png`. |
| `GET` | `/wallpaper` | Genera un wallpaper usando parámetros de query string. |
| `GET` | `/paletas` | Lista las 10 paletas disponibles. |
| `GET` | `/health` | Devuelve el estado de la aplicación y las fuentes disponibles. |
| `GET` | `/` | Sirve el probador interactivo en español. |

### Parámetros de `/wallpaper`

`POST /wallpaper` recibe un body JSON. `GET /wallpaper` acepta los mismos
campos mediante query string.

| Campo | Tipo | Defecto | Validación |
|---|---|---|---|
| `width` | entero | obligatorio | Mayor que 0 y máximo de 4000. |
| `height` | entero | obligatorio | Mayor que 0 y máximo de 4000. |
| `text` | string | `""` | Texto y/o emojis. |
| `palette` | string o `null` | `null` | Nombre de una paleta disponible. |
| `color` | string o `null` | `null` | Color hexadecimal o nombre CSS. |
| `text_color` | string o `null` | `null` | Color hexadecimal o nombre CSS. |
| `font_size` | entero | `96` | Mayor que 0 y máximo de 2000. |
| `bold` | booleano | `false` | Texto normal en negrita. |
| `italic` | booleano | `false` | Texto normal en cursiva. |

Si se combinan `palette` con `color` o `text_color`, los colores explícitos
tienen prioridad.

En la API solo se acepta el nombre exacto de una paleta, por ejemplo
`noche`. El sinónimo `ninguna`, disponible en la CLI, no existe en la API.
Para no utilizar una paleta, simplemente no envíes `palette`.

### Validaciones y límites

Cada lado de la imagen está limitado a 4000 píxeles.

Una imagen de `4000x4000` en RGB ocupa aproximadamente 48 MB. El pico medido
con emojis es de aproximadamente 90 MB. El límite mantiene controlado el uso
de memoria durante la generación.

La API permite un máximo de tres generaciones simultáneas. Las solicitudes
adicionales se rechazan inmediatamente y no se encolan.

### Códigos de respuesta

| Código | Descripción |
|---|---|
| `200` | Wallpaper generado correctamente. |
| `422` | Error de validación. Los mensajes se devuelven en español. |
| `429` | Demasiadas generaciones simultáneas. Incluye `Retry-After: 1`. |
| `503` | Falta la fuente `NotoColorEmoji.ttf`. |
| `500` | Error inesperado durante la generación. |

`GET /paletas` y `GET /health` responden con `200`. En `/health`, el estado
real se indica en el body mediante `estado`, que puede ser `ok` o
`degradado`.

### Ejemplo con `POST`

```bash
curl -X POST http://notiemoji.onrender.com/wallpaper \
  -H "Content-Type: application/json" \
  -d '{"width":1920,"height":1080,"palette":"noche","text":"hola 🚀"}' \
  -o wallpaper.png
```

### Ejemplo con `GET`

Los parámetros se envían mediante query string. El emoji debe estar codificado
en UTF-8:

```bash
curl -o wallpaper.png \
  "http://notiemoji.onrender.com/wallpaper?width=1920&height=1080\
&palette=noche&text=hola%20%f0%9f%9a%80&bold=true"
```

Para los mismos valores, `GET /wallpaper` devuelve el mismo PNG que
`POST /wallpaper`, byte por byte.

### Probador interactivo

Abre:

```text
http://notiemoji.onrender.com/
```

El probador:

- Obtiene las paletas mediante `GET /paletas`.
- Permite seleccionar colores de fondo y texto.
- Sincroniza los selectores de color con los campos de texto.
- Acepta colores hexadecimales y nombres CSS.
- Envía las solicitudes mediante `POST /wallpaper`.
- Permite visualizar o descargar el wallpaper generado.

Al seleccionar una paleta, los campos de color se rellenan automáticamente.
Con «ninguna», la API utiliza `#000000` como fondo y `#ffffff` como color
del texto.

## CLI

### Uso interactivo

El modo interactivo se inicia sin argumentos:

```bash
uv run python notiemoji.py
```

### Uso por línea de comandos

```bash
uv run python notiemoji.py \
  -r 1920x1080 \
  -p grafito \
  -f 96 \
  -t "notiemoji 🎨"
```

```bash
uv run python notiemoji.py \
  -r 720x1080 \
  -p noche \
  -f 96 \
  -i \
  -t "notiemoji 🌙"
```

```bash
uv run python notiemoji.py \
  -r 1080x1080 \
  -p papel \
  -f 140 \
  -b \
  -t "notiemoji 🌈"
```

La salida por defecto es `wallpaper.png`.

Para elegir otro archivo:

```bash
uv run python notiemoji.py \
  -r 1920x1080 \
  -p oceano \
  -t "hola 🚀" \
  -o images/fondo.png
```

### Opciones

| Opción | Alias | Descripción |
|---|---|---|
| `--resolution` | `-r` | Tamaño en formato `anchoxalto`. Obligatorio en modo CLI. |
| `--palette` | `-p` | Paleta que define el fondo y el color del texto. |
| `--color` | `-c` | Color de fondo en hexadecimal o nombre CSS. |
| `--text-color` | `-C` | Color del texto en hexadecimal o nombre CSS. |
| `--font-size` | `-f` | Tamaño de fuente en píxeles. Por defecto, `96`. |
| `--bold` | `-b` | Dibuja el texto normal en negrita. |
| `--italic` | `-i` | Dibuja el texto normal en cursiva. |
| `--text` | `-t` | Texto y/o emojis que se van a centrar. |
| `--output` | `-o` | Ruta del PNG de salida. Por defecto, `wallpaper.png`. |

Si el texto no cabe, el tamaño de fuente se reduce automáticamente hasta que
pueda entrar en la imagen.

## Paletas

| Paleta | Fondo | Texto |
|---|---|---|
| `papel` | `#f5f5f5` | `#151515` |
| `grafito` | `#101010` | `#f0f0f0` |
| `oceano` | `#003355` | `#aaeeff` |
| `noche` | `#10101f` | `#aaeeff` |
| `menta` | `#99ffaa` | `#115533` |
| `mate` | `#101f10` | `#6abe30` |
| `amor` | `#901010` | `#ffdddd` |
| `marte` | `#1f1010` | `#ff7777` |
| `uva` | `#1D001D` | `#ffaaff` |
| `nanana` | `#101010` | `#ff50ff` |

Las paletas están diseñadas para mantener un contraste alto entre el fondo y
el texto.

También se pueden utilizar nombres de colores CSS con `-c` y `-C`, como
`navy` o `hotpink`.

## Despliegue

El proyecto está configurado para desplegarse en Render mediante
[`render.yaml`](render.yaml).

### Build command

```bash
pip install uv && uv sync --no-dev
```

### Start command

```bash
uv run uvicorn api:app --host 0.0.0.0 --port $PORT
```

El probador interactivo queda disponible en la ruta `/`.

## Pruebas

La suite utiliza `unittest` de la biblioteca estándar e incluye 48 tests:

- 16 tests en `tests/test_notiemoji.py`.
- 32 tests en `tests/test_api.py`.

Para ejecutar todas las pruebas:

```bash
uv run python -m unittest discover -s tests -v
```

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).

Las fuentes no se distribuyen con el proyecto. Se utilizan las fuentes
instaladas en el sistema.
```
