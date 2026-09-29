#!/usr/bin/env python3
"""notiemoji: genera wallpapers con fondo de color plano y texto/emojis centrados."""

import argparse
import os
import struct
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

# Versión del proyecto; la expone GET /health de la API.
VERSION = "0.1.0"

# Las fuentes viven en el sistema; el repo no incluye archivos de fuentes.
EMOJI_FONT_NAME = "NotoColorEmoji.ttf"

# Primera opción y fallbacks por estilo para el texto.
TEXT_FONTS = {
    (False, False): ("DejaVuSans.ttf", "LiberationSans-Regular.ttf"),
    (True, False): ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "DejaVuSans.ttf"),
    (False, True): ("DejaVuSans-Oblique.ttf", "LiberationSans-Italic.ttf", "DejaVuSans.ttf"),
    (True, True): (
        "DejaVuSans-BoldOblique.ttf",
        "LiberationSans-BoldItalic.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ),
}


def find_emoji_font() -> Path:
    """Devuelve la ruta de NotoColorEmoji.ttf en los directorios del sistema.

    Busca en los mismos directorios que Pillow: XDG en Linux, las rutas de
    sistema en macOS y %WINDIR%\\fonts en Windows. Hace falta la ruta real
    para leer el tamaño del bitmap (CBDT/CBLC) antes de abrir la fuente.
    """
    if sys.platform == "darwin":
        dirs = (
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        )
    elif sys.platform == "win32":
        dirs = (Path(os.environ.get("WINDIR", "C:\\Windows")) / "fonts",)
    else:
        data_home = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
        data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
        dirs = tuple(
            Path(base).expanduser() / "fonts"
            for base in (data_home, *data_dirs.split(":"))
        )
    for directory in dirs:
        found = next(directory.rglob(EMOJI_FONT_NAME), None)
        if found:
            return found
    raise FileNotFoundError(
        f"{EMOJI_FONT_NAME} no está en los directorios de fuentes del sistema"
    )

# Indicadores regionales (banderas), emojis principales y símbolos frecuentes.
EMOJI_RANGES = (
    (0x1F1E6, 0x1F1FF),  # indicadores regionales para banderas
    (0x1F300, 0x1FAFF),  # emojis principales (objetos, caras, ...)
    (0x2600, 0x27BF),    # símbolos sol/luna y dingbats
    (0x2B00, 0x2BFF),    # símbolos varios (⭐, ➕, ...)
)
# ZWJ, selectores de presentación y etiquetas de las banderas subdivided.
EMOJI_CONTINUATIONS = {0x200D, 0xFE0E, 0xFE0F}
KEYCAP = 0x20E3
TAG_RANGE = range(0xE0020, 0xE0080)

# Paletas curadas: pareja (fondo, texto) con contraste garantizado (WCAG AAA).
PALETTES = {
    "papel":     ("#f5f5f5", "#151515"),
    "grafito":   ("#101010", "#f0f0f0"),
    "oceano":    ("#003355", "#aaeeff"),
    "noche":     ("#10101f", "#aaeeff"),
    "menta":     ("#99ffaa", "#115533"),
    "mate":      ("#101f10", "#6abe30"),
    "amor":      ("#901010", "#ffdddd"),
    "marte":     ("#1f1010", "#ff7777"),
    "uva":       ("#f6f4fd", "#5b21b6"),
    "nanana":    ("#101010", "#ff50ff"),
}


def is_emoji(ch: str) -> bool:
    code = ord(ch)
    return any(low <= code <= high for low, high in EMOJI_RANGES)


def keycap_end(text: str, start: int) -> int:
    """Devuelve el fin de un keycap (#️⃣) o el índice inicial si no lo es."""
    if text[start] not in "#*0123456789":
        return start
    end = start + 1
    if end < len(text) and ord(text[end]) == 0xFE0F:
        end += 1
    if end < len(text) and ord(text[end]) == KEYCAP:
        return end + 1
    return start


def split_runs(text: str) -> list[tuple[str, bool]]:
    """Agrupa el texto en corridas seguidas de (texto, ¿es emoji?)."""
    runs: list[list] = []
    index = 0
    while index < len(text):
        end = keycap_end(text, index)
        if end > index:
            # El signo, número o asterisco inicial no es emoji por sí solo, pero
            # forma parte de la secuencia keycap que debe usar Noto Color Emoji.
            content = text[index:end]
            emoji = True
            index = end
        else:
            ch = text[index]
            code = ord(ch)
            if (code in EMOJI_CONTINUATIONS or code in TAG_RANGE) and runs:
                emoji = runs[-1][1]
            else:
                emoji = is_emoji(ch)
            content = ch
            index += 1

        if runs and runs[-1][1] == emoji:
            runs[-1][0] += content
        else:
            runs.append([content, emoji])
    return [(content, emoji) for content, emoji in runs]


def emoji_strike_size(path: str | Path) -> int:
    """Tamaño nativo (ppem) del bitmap de una fuente CBDT/CBLC.

    Las fuentes de emoji traen bitmaps de tamaño fijo y solo se pueden abrir
    en ese tamaño exacto; después escalamos el resultado al --font-size.
    """
    data = Path(path).read_bytes()
    if len(data) < 12:
        raise ValueError(f"{path} no es una fuente TrueType válida")

    num_tables = struct.unpack_from(">H", data, 4)[0]
    for i in range(num_tables):
        offset = 12 + 16 * i
        if data[offset : offset + 4] in (b"CBLC", b"EBLC"):
            table = struct.unpack_from(">I", data, offset + 8)[0]
            num_strikes = struct.unpack_from(">I", data, table + 4)[0]
            if num_strikes:
                # Registro 0: ppem x/y en los bytes 44/45 (tabla de 48 bytes).
                return data[table + 8 + 45]
    raise ValueError(f"{path} no es una fuente de bitmap (CBDT/CBLC)")


def parse_resolution(value: str) -> tuple[int, int]:
    try:
        width_s, height_s = value.lower().split("x")
        width, height = int(width_s), int(height_s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"resolución inválida: {value!r} (uso: 1920x1080)"
        ) from None
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError(
            f"resolución inválida: {value!r} (debe ser positiva)"
        )
    return width, height


def parse_color(value: str) -> str:
    try:
        ImageColor.getrgb(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"color inválido: {value!r} (ej.: #0d1117 o navy)"
        ) from None
    return value


def parse_palette(value: str) -> str:
    name = value.lower()
    if name != "ninguna" and name not in PALETTES:
        raise argparse.ArgumentTypeError(
            f"paleta inválida: {value!r} (ninguna, {', '.join(PALETTES)})"
        )
    return name


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"debe ser un número entero positivo, no {value!r}"
        ) from None
    if number <= 0:
        raise argparse.ArgumentTypeError(f"debe ser positivo, no {value!r}")
    return number


def parse_output(value: str) -> str:
    if Path(value).expanduser().suffix.lower() != ".png":
        raise argparse.ArgumentTypeError(
            f"la salida debe terminar en .png, no {value!r}"
        )
    return value


def ask(label: str, default: str, validate) -> str:
    """Pide un valor por stdin; vacío = default; re-pregunta si no valida."""
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        value = raw or default
        try:
            validate(value)
            return value
        except argparse.ArgumentTypeError as exc:
            print(f"  ✗ {exc}")


def ask_bool(label: str, default: bool = False) -> bool:
    """Pide una opción booleana; vacío = default; re-pregunta si no valida."""
    default_text = "sí" if default else "no"
    while True:
        raw = input(f"{label} [{default_text}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"s", "si", "sí", "y", "yes", "true", "1"}:
            return True
        if raw in {"n", "no", "false", "0"}:
            return False
        print("  ✗ respondé sí o no")


def interactive_params() -> argparse.Namespace:
    """Modo interactivo: guía paso a paso y devuelve los parámetros."""
    print("notiemoji — generá tu wallpaper (Enter = valor por defecto)\n")
    resolution = ask("Resolución (anchoxalto)", "1920x1080", parse_resolution)
    palette = ask(
        f"Paleta (ninguna, {', '.join(PALETTES)})", "ninguna", parse_palette
    )
    bg_default, fg_default = PALETTES.get(palette, ("#000000", "#ffffff"))
    color = ask("Color de fondo (hex o nombre CSS)", bg_default, parse_color)
    text_color = ask("Color del texto", fg_default, parse_color)
    font_size = ask("Tamaño de fuente", "96", positive_int)
    bold = ask_bool("¿Usar texto en negrita?")
    italic = ask_bool("¿Usar texto en cursiva?")
    text = input("Texto y/o emojis (Enter para omitir): ").strip()
    output = ask("Archivo de salida", "wallpaper.png", parse_output)
    return argparse.Namespace(
        resolution=parse_resolution(resolution),
        palette=palette,
        color=color,
        text_color=text_color,
        font_size=positive_int(font_size),
        bold=bold,
        italic=italic,
        text=text,
        output=output,
    )


def load_text_font(
    size: int,
    bold: bool = False,
    italic: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Carga la fuente de texto del sistema; usa fallbacks si falta el estilo."""
    for path in TEXT_FONTS[(bold, italic)]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def make_tile(
    content: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    scale: float = 1.0,
    embedded_color: bool = False,
) -> tuple[Image.Image, int]:
    """Dibuja una corrida en su propia imagen RGBA y devuelve (tile, línea base).

    La línea base es la posición del baseline de la fuente dentro del tile;
    al compartirla entre runs, el texto y los emojis quedan alineados como en
    un editor de texto (el corazón no se desploma hacia abajo).
    """
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    kwargs = {"embedded_color": True} if embedded_color else {}
    ink = probe.textbbox((0, 0), content, font=font, **kwargs)
    advance = probe.textlength(content, font=font)
    width = max(1, int(round(advance)), int(ink[2]))
    height = max(1, int(ink[3]) - int(ink[1]))
    tile = Image.new("RGBA", (width, height))
    ImageDraw.Draw(tile).text((0, -ink[1]), content, font=font, fill=fill, **kwargs)
    getmetrics = getattr(font, "getmetrics", None)
    baseline = int(getmetrics()[0] - ink[1]) if getmetrics else int(-ink[1])
    if scale != 1.0:
        size = (max(1, round(tile.width * scale)), max(1, round(tile.height * scale)))
        tile = tile.resize(size, Image.Resampling.LANCZOS)
        baseline = round(baseline * scale)
    return tile, baseline


class EmojiFontError(RuntimeError):
    """Falta Noto Color Emoji en el sistema y no se puede dibujar el texto.

    La lanza draw_centered; la CLI la convierte en mensaje por stderr con
    código de salida 1 y la API en una respuesta HTTP 503, para que el
    servidor no se caiga.
    """


def draw_centered(
    image: Image.Image,
    runs: list[tuple[str, bool]],
    text_color: str,
    font_size: int,
    bold: bool = False,
    italic: bool = False,
) -> None:
    """Dibuja las corridas centradas.

    Si el texto no cabe en la imagen, reduce font_size hasta que quepa
    (mínimo 1 px); si ni así cabe, dibuja igual y avisa.
    Lanza EmojiFontError si el texto usa emojis y falta la fuente de emoji.
    """
    requested = font_size
    needs_emoji = any(emoji for _, emoji in runs)
    emoji_font = None
    strike = 1
    if needs_emoji:
        try:
            emoji_path = find_emoji_font()
            strike = emoji_strike_size(emoji_path)
            emoji_font = ImageFont.truetype(emoji_path, strike, index=0)
        except (OSError, ValueError) as exc:
            raise EmojiFontError(
                f"error: no se encontró {EMOJI_FONT_NAME} en el sistema; "
                f"instalala (ej.: sudo apt install fonts-noto-color-emoji)\n{exc}"
            ) from exc
        assert emoji_font is not None

    while True:
        text_font = load_text_font(font_size, bold, italic)
        emoji_scale = font_size / strike
        tiles = [
            make_tile(content, emoji_font, text_color, emoji_scale, embedded_color=True)
            if emoji and emoji_font is not None
            else make_tile(content, text_font, text_color)
            for content, emoji in runs
        ]
        # Los runs comparten línea base (la fila se acomoda al baseline común)
        # y la fila completa queda centrada en la imagen.
        ref = max(baseline for _, baseline in tiles)
        total_w = sum(tile.width for tile, _ in tiles)
        line_h = max(ref - baseline + tile.height for tile, baseline in tiles)
        if font_size <= 1 or (total_w <= image.width and line_h <= image.height):
            break
        # Las métricas escalan casi lineal: bajar por factor converge en 1-2 pasadas.
        factor = min(image.width / total_w, image.height / line_h)
        font_size = max(1, int(font_size * factor))

    if font_size < requested:
        print(
            f"nota: el texto no cabía a {requested} px; se usó {font_size} px",
            file=sys.stderr,
        )
    if total_w > image.width or line_h > image.height:
        print(
            f"aviso: el texto ({total_w}x{line_h}px) no cabe en la imagen "
            f"({image.width}x{image.height}px); agrandá --resolution o acortá el texto",
            file=sys.stderr,
        )
    x = (image.width - total_w) // 2
    y = (image.height - line_h) // 2
    for tile, baseline in tiles:
        image.paste(tile, (x, y + ref - baseline), tile)
        x += tile.width


def resolve_colors(
    palette: str | None,
    color: str | None,
    text_color: str | None,
) -> tuple[str, str]:
    """Resuelve la pareja (fondo, texto) con la precedencia de la CLI.

    Precedencia: color explícito (-c/-C) > paleta (-p) > defecto
    (#000000/#ffffff). La usan tanto la CLI como la API.
    """
    default_bg, default_fg = PALETTES.get(palette, ("#000000", "#ffffff"))
    background = default_bg if color is None else color
    foreground = default_fg if text_color is None else text_color
    return background, foreground


def render_wallpaper(
    width: int,
    height: int,
    color: str,
    text: str,
    text_color: str,
    font_size: int,
    bold: bool = False,
    italic: bool = False,
) -> Image.Image:
    """Crea el wallpaper en memoria: fondo de color plano y texto centrado.

    Si text está vacío, devuelve solo el fondo. Puede lanzar EmojiFontError
    si el texto usa emojis y falta la fuente de emoji en el sistema.
    """
    image = Image.new("RGB", (width, height), ImageColor.getrgb(color))
    if text:
        draw_centered(image, split_runs(text), text_color, font_size, bold, italic)
    return image


class Help(argparse.ArgumentDefaultsHelpFormatter):
    """ArgumentDefaultsHelpFormatter sin el "(default: None)" de -c, -C y -p.

    Sus defaults son None porque se resuelven recién en main(): los llena la
    paleta (-p) o quedan en negro/blanco.
    """

    def _get_help_string(self, action):
        if action.default is None:
            return action.help
        return super()._get_help_string(action)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un wallpaper: fondo de color plano con texto/emojis "
        "centrados. Sin argumentos, inicia un modo interactivo.",
        formatter_class=Help,
    )
    parser.add_argument(
        "-r", "--resolution", required=True, type=parse_resolution, metavar="WxH",
        help="tamaño de la imagen en px (ej.: 1920x1080)",
    )
    parser.add_argument(
        "-c", "--color", type=parse_color, default=None,
        help="color de fondo: hex (#0d1117) o nombre CSS (navy, tomato, ...); "
        "por defecto #000000 o el de la paleta (-p)",
    )
    parser.add_argument(
        "-C", "--text-color", type=parse_color, default=None,
        help="color del texto: hex o nombre CSS; "
        "por defecto #ffffff o el de la paleta (-p)",
    )
    parser.add_argument(
        "-p", "--palette", type=parse_palette, default=None,
        help=f"paleta curada (fondo+texto): {', '.join(PALETTES)}; "
        "por defecto ninguna",
    )
    parser.add_argument(
        "-f", "--font-size", type=positive_int, default=96,
        help="tamaño de la fuente en px",
    )
    parser.add_argument(
        "-b", "--bold", action="store_true",
        help="dibujar el texto normal en negrita",
    )
    parser.add_argument(
        "-i", "--italic", action="store_true",
        help="dibujar el texto normal en cursiva",
    )
    parser.add_argument(
        "-t", "--text", default="",
        help="texto y/o emojis a dibujar en el centro (puede venir vacío)",
    )
    parser.add_argument(
        "-o", "--output", type=parse_output, default="wallpaper.png",
        help="ruta del archivo de salida (debe terminar en .png)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        args = build_parser().parse_args(argv)
    else:
        try:
            args = interactive_params()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelado.")
            return 1

    # Precedencia de colores: -c/-C explícitos > paleta (-p) > defecto.
    args.color, args.text_color = resolve_colors(
        args.palette, args.color, args.text_color
    )
    width, height = args.resolution

    try:
        image = render_wallpaper(
            width,
            height,
            args.color,
            args.text,
            args.text_color,
            args.font_size,
            args.bold,
            args.italic,
        )
    except EmojiFontError as exc:
        # Mismo mensaje y código de salida que el sys.exit de antes.
        print(exc, file=sys.stderr)
        return 1

    output = Path(args.output).expanduser()
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output, format="PNG")
    except OSError as exc:
        print(f"error: no se pudo guardar {output}: {exc}", file=sys.stderr)
        return 1
    print(f"Wallpaper guardado en {output} ({width}x{height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
