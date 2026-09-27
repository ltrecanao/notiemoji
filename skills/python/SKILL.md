# Skill de Python

Aplicá estas instrucciones cuando trabajes con código Python, tests o
dependencias del proyecto.

## Proyecto

- Python 3.11+
- Pillow
- Fuentes del sistema: DejaVu Sans (texto), Noto Color Emoji (emojis) y
  Liberation Sans para cursivas (si DejaVu no trae Oblique).
- Código principal: `notiemoji.py`
- Tests: `tests/test_notiemoji.py`
- Gestión de dependencias con `uv` (`pyproject.toml` + `uv.lock`)

## Alcance

`notiemoji` genera wallpapers PNG con fondo de color plano y texto o emojis
centrados.

Debe:

- Generar archivos PNG.
- Aceptar una paleta curada o un color personalizado.
- Centrar texto o emojis.
- Funcionar mediante CLI y modo interactivo.
- Reducir el tamaño de fuente si el texto no entra.

No debe:

- Generar múltiples líneas.
- Usar imágenes de fondo.
- Generar formatos distintos de PNG.
- Editar imágenes existentes.

## Código

### Python moderno

- Usá type hints en firmas de funciones (`def foo(bar: str) -> int:`).
- Usá `pathlib.Path` en lugar de `os.path`.
- Usá f-strings en lugar de `%` o `.format()`.
- Usá `dataclass` o `TypedDict` para estructuras de datos.
- Usá `enum.Enum` para constantes relacionadas.
- Usá `functools.cache` o `functools.lru_cache` para memoización.
- Usá `collections.namedtuple` o `dataclasses` en lugar de tuples anónimas.
- Usá `contextlib.contextmanager` para manejo de recursos.
- Usá `typing.Annotated` para metadata adicional en tipos.
- Preferí `dict` y `list` sobre `typing.Dict` y `typing.List` (Python 3.9+).
- Usá `str | None` sobre `Optional[str]` (Python 3.10+).

### Herramientas

- Usá `uv` para gestión de dependencias, entornos virtuales y ejecución.
- Usá `ruff` para linting y formateo (reemplaza flake8, black, isort).
- Usá `ty` para type checking estático.
- Usá `pyproject.toml` como fuente única de configuración.
- No agregues herramientas sin una justificación clara.

### Estilo

- Usá siempre la biblioteca estándar de Python cuando proporcione una solución
  adecuada.
- Usá dependencias externas únicamente cuando sean necesarias para el
  funcionamiento del proyecto. Las dependencias de producción actuales
  (`Pillow`, `fastapi` y `uvicorn`) están declaradas en `pyproject.toml`;
  las de desarrollo, en el grupo `dev` (`[dependency-groups]`).
- No agregues dependencias externas sin una justificación clara.
- Mantené el código modularizado, con funciones y responsabilidades bien
  separadas.
- Evitá funciones extensas, lógica duplicada y dependencias innecesarias entre
  componentes.
- Usá nombres de variables y funciones descriptivos.
- Documentá en español las funciones, clases y decisiones no obvias.
- Priorizá una estructura clara para facilitar una comprensión rápida.
- Conservá la compatibilidad con Python 3.11 o versiones posteriores.
- Seguí las convenciones y el estilo existentes en el proyecto.
- Actualizá los tests cuando modifiques el comportamiento existente.

## Tests

- Ejecutá los tests relacionados después de cada cambio relevante.
- Agregá o actualizá tests cuando incorpores o modifiques comportamiento.
- Priorizá tests para:
  - Validación de argumentos.
  - Resoluciones y colores.
  - Centrado del texto o los emojis.
  - Reducción del tamaño de fuente.
  - Generación correcta del archivo PNG.
- No modifiques tests para ocultar errores de implementación.

## Comandos

```bash
# Sincronizar el entorno y las dependencias (incluye el grupo de desarrollo)
uv sync

# Ejecutar en modo interactivo
uv run python notiemoji.py

# Ejecutar mediante CLI
uv run python notiemoji.py -r 1920x1080 -p grafito -t "hola 🎨"

# Ejecutar los tests
uv run python -m unittest discover -s tests -v
```

## Documentación

- Si cambiás opciones, paletas o comportamiento, actualizá `README.md` en el
  mismo cambio (ver skill de Markdown).

## Formato y calidad

- No hay linter ni formateador configurado.
- Mantené un estilo compatible con PEP 8.
- Preferí funciones simples y fáciles de probar.
- Mantené claras las responsabilidades de cada módulo y función.
- Manejá los errores de entrada de forma clara para el usuario.
- Evitá comentarios obvios.
- Documentá en español la intención y las decisiones no evidentes.
