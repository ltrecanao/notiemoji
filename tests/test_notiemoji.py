import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import notiemoji


class ValidationTests(unittest.TestCase):
    def test_resolution(self):
        self.assertEqual(notiemoji.parse_resolution("1920X1080"), (1920, 1080))
        for value in ("1920", "1920*1080", "0x1080", "1920x-1", "x"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                notiemoji.parse_resolution(value)

    def test_color_and_palette(self):
        self.assertEqual(notiemoji.parse_color("navy"), "navy")
        self.assertEqual(notiemoji.parse_color("#0d1117"), "#0d1117")
        self.assertEqual(notiemoji.parse_palette("GRAFITO"), "grafito")
        self.assertEqual(notiemoji.parse_palette("NINGUNA"), "ninguna")
        with self.assertRaises(argparse.ArgumentTypeError):
            notiemoji.parse_color("no-es-un-color")
        with self.assertRaises(argparse.ArgumentTypeError):
            notiemoji.parse_palette("arcoíris")

    def test_positive_int(self):
        self.assertEqual(notiemoji.positive_int("96"), 96)
        for value in ("abc", "1.5", "0", "-1"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                notiemoji.positive_int(value)

    def test_output_requires_png_extension(self):
        self.assertEqual(notiemoji.parse_output("nested/wallpaper.PNG"), "nested/wallpaper.PNG")
        for value in ("wallpaper.jpg", "wallpaper", "wallpaper.png.txt"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                notiemoji.parse_output(value)


class PaletteTests(unittest.TestCase):
    @staticmethod
    def luminance(color):
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def test_every_palette_has_wcag_aaa_contrast(self):
        for name, (background, foreground) in notiemoji.PALETTES.items():
            with self.subTest(palette=name):
                light, dark = sorted(
                    (self.luminance(background), self.luminance(foreground)),
                    reverse=True,
                )
                self.assertGreaterEqual((light + 0.05) / (dark + 0.05), 7.0)


class TextRunTests(unittest.TestCase):
    def test_plain_text_and_common_emoji(self):
        self.assertEqual(
            notiemoji.split_runs("hola 🎨"),
            [("hola ", False), ("🎨", True)],
        )
        family = "👨‍👩‍👧‍👦"
        self.assertEqual(notiemoji.split_runs(family), [(family, True)])

    def test_flags(self):
        flag = "🇦🇷"
        self.assertEqual(notiemoji.split_runs(flag), [(flag, True)])
        self.assertEqual(
            notiemoji.split_runs("Argentina 🇦🇷!"),
            [("Argentina ", False), (flag, True), ("!", False)],
        )

    def test_keycaps(self):
        for keycap in ("#️⃣", "*️⃣", "1️⃣"):
            with self.subTest(keycap=keycap):
                self.assertEqual(notiemoji.split_runs(keycap), [(keycap, True)])

    def test_flag_stays_together(self):
        argentina = "🇦🇷"
        self.assertEqual(notiemoji.split_runs(argentina), [(argentina, True)])


class ResourceTests(unittest.TestCase):
    def test_emoji_font_is_found_on_system(self):
        path = notiemoji.find_emoji_font()
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "NotoColorEmoji.ttf")
        self.assertGreater(notiemoji.emoji_strike_size(path), 0)

    def test_text_fonts_resolve_to_existing_system_files(self):
        for bold, italic in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(bold=bold, italic=italic):
                font = notiemoji.load_text_font(48, bold, italic)
                path = getattr(font, "path", None)
                self.assertIsNotNone(path)
                self.assertTrue(Path(str(path)).is_file())


class InteractiveTests(unittest.TestCase):
    def test_invalid_values_are_asked_again(self):
        answers = iter(
            [
                "1920x1080",
                "grafito",
                "",
                "",
                "abc",
                "72",
                "quizás",
                "sí",
                "tal vez",
                "sí",
                "hola 🎨",
                "wallpaper.jpg",
                "resultado.png",
            ]
        )
        output = io.StringIO()
        with patch("builtins.input", side_effect=lambda _: next(answers)):
            with contextlib.redirect_stdout(output):
                args = notiemoji.interactive_params()

        self.assertEqual(args.resolution, (1920, 1080))
        self.assertEqual(args.font_size, 72)
        self.assertTrue(args.bold)
        self.assertTrue(args.italic)
        self.assertEqual(args.output, "resultado.png")
        self.assertIn("número entero positivo", output.getvalue())
        self.assertIn("respondé sí o no", output.getvalue())
        self.assertIn("debe terminar en .png", output.getvalue())


class MainTests(unittest.TestCase):
    def test_generates_png_with_text_and_emoji(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "wallpaper.png"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = notiemoji.main(
                    [
                        "-r",
                        "480x270",
                        "-p",
                        "grafito",
                        "-f",
                        "48",
                        "--bold",
                        "--italic",
                        "-t",
                        "hola 🇦🇷 #️⃣ 👨‍👩‍👧‍👦",
                        "-o",
                        str(output),
                    ]
                )

            self.assertEqual(result, 0)
            self.assertIn("Wallpaper guardado", stdout.getvalue())
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (480, 270))
                self.assertEqual(image.getpixel((0, 0)), (16, 16, 16))
                self.assertGreater(len(image.getcolors(maxcolors=1_000_000) or []), 1)

    def test_explicit_colors_override_palette(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "wallpaper.png"
            with contextlib.redirect_stdout(io.StringIO()):
                result = notiemoji.main(
                    [
                        "-r",
                        "32x32",
                        "-p",
                        "oceano",
                        "-c",
                        "navy",
                        "-C",
                        "tomato",
                        "-o",
                        str(output),
                    ]
                )
            self.assertEqual(result, 0)
            with Image.open(output) as image:
                self.assertEqual(image.getpixel((0, 0)), (0, 0, 128))

    def test_shrinks_font_when_text_does_not_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "wallpaper.png"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = notiemoji.main(
                    [
                        "-r",
                        "320x80",
                        "-f",
                        "300",
                        "-t",
                        "hola 🎨",
                        "-o",
                        str(output),
                    ]
                )
            self.assertEqual(result, 0)
            self.assertIn("se usó", stderr.getvalue())
            self.assertNotIn("no cabe en la imagen", stderr.getvalue())
            with Image.open(output) as image:
                self.assertGreater(len(image.getcolors(maxcolors=1_000_000) or []), 1)

    def test_save_error_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "blocked"
            blocker.write_text("no soy un directorio", encoding="utf-8")
            output = blocker / "wallpaper.png"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = notiemoji.main(["-r", "16x16", "-o", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("no se pudo guardar", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
