import io
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image, ImageColor

import notiemoji
from api import GENERACIONES_SIMULTANEAS, SEMAFORO_GENERACION, app


class WallpaperEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def post(self, **payload):
        return self.client.post("/wallpaper", json=payload)

    def get(self, **params):
        return self.client.get("/wallpaper", params=params)

    @staticmethod
    def open_png(content: bytes) -> Image.Image:
        """Abre el cuerpo como imagen y fuerza la decodificación."""
        image = Image.open(io.BytesIO(content))
        image.load()
        return image

    def test_returns_real_png_with_requested_size(self):
        response = self.post(width=64, height=48, text="hola")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        with self.open_png(response.content) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (64, 48))

    def test_empty_text_returns_valid_png(self):
        response = self.post(width=32, height=32)
        self.assertEqual(response.status_code, 200)
        with self.open_png(response.content) as image:
            self.assertEqual(image.size, (32, 32))
            # Sin texto solo queda el fondo plano.
            colors = image.getcolors(maxcolors=16) or []
            self.assertEqual(len(colors), 1)
            self.assertEqual(colors[0][1], (0, 0, 0))

    def test_missing_required_fields_return_422(self):
        response = self.client.post("/wallpaper", json={})
        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())

    def test_unknown_field_returns_422_instead_of_default(self):
        # Un typo (p. ej. "fondo" en vez de "color") debe avisar, no
        # descartarse en silencio y generar un wallpaper con otro fondo.
        response = self.post(width=32, height=32, fondo="grafito")
        self.assertEqual(response.status_code, 422)
        self.assertIn("fondo", response.text)

    def test_invalid_dimensions_return_422(self):
        invalid_payloads = (
            {"width": 0, "height": 32},
            {"width": 32, "height": 0},
            {"width": -1, "height": 32},
            {"width": 4001, "height": 32},
            {"width": 32, "height": 4001},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.post(**payload)
                self.assertEqual(response.status_code, 422)
                self.assertIn("detail", response.json())

    def test_dimension_at_maximum_returns_200(self):
        # 4000 es el tope permitido: tiene que seguir generando con normalidad.
        response = self.post(width=4000, height=16, text="hola")
        self.assertEqual(response.status_code, 200)
        with self.open_png(response.content) as image:
            self.assertEqual(image.size, (4000, 16))

    def test_invalid_palette_returns_422_with_spanish_message(self):
        response = self.post(width=32, height=32, palette="arcoiris")
        self.assertEqual(response.status_code, 422)
        self.assertIn("paleta inválida", str(response.json()["detail"]))

    def test_invalid_color_returns_422_with_spanish_message(self):
        for field in ("color", "text_color"):
            with self.subTest(field=field):
                response = self.post(width=32, height=32, **{field: "no-es-un-color"})
                self.assertEqual(response.status_code, 422)
                self.assertIn("color inválido", str(response.json()["detail"]))

    def test_invalid_font_size_returns_422(self):
        for font_size in (0, -1, 2001):
            with self.subTest(font_size=font_size):
                response = self.post(width=32, height=32, font_size=font_size)
                self.assertEqual(response.status_code, 422)
                self.assertIn("detail", response.json())

    def test_font_size_above_maximum_returns_422_with_spanish_message(self):
        # Sin este tope Pillow lanzaba OSError y la API respondía 500.
        response = self.post(width=32, height=32, font_size=2001)
        self.assertEqual(response.status_code, 422)
        self.assertIn("2000", str(response.json()["detail"]))

    def test_palette_background_is_applied(self):
        for name, (background, _) in notiemoji.PALETTES.items():
            with self.subTest(palette=name):
                response = self.post(width=32, height=32, palette=name)
                self.assertEqual(response.status_code, 200)
                with self.open_png(response.content) as image:
                    self.assertEqual(
                        image.getpixel((0, 0)), ImageColor.getrgb(background)
                    )

    def test_explicit_colors_override_palette(self):
        response = self.post(
            width=32,
            height=32,
            palette="oceano",
            color="navy",
            text_color="tomato",
        )
        self.assertEqual(response.status_code, 200)
        with self.open_png(response.content) as image:
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 128))

    def test_bold_and_italic_generate_image(self):
        response = self.post(
            width=320,
            height=180,
            text="hola 🎨",
            font_size=64,
            bold=True,
            italic=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.open_png(response.content) as image:
            self.assertEqual(image.size, (320, 180))
            self.assertGreater(len(image.getcolors(maxcolors=1_000_000) or []), 1)

    def test_missing_emoji_font_returns_503(self):
        with patch(
            "notiemoji.find_emoji_font", side_effect=FileNotFoundError("sin fuente")
        ):
            response = self.post(width=64, height=64, text="🎨")
        self.assertEqual(response.status_code, 503)
        self.assertIn("NotoColorEmoji", str(response.json()["detail"]))

    def test_unexpected_error_returns_500_without_leaking_details(self):
        with patch(
            "notiemoji.render_wallpaper", side_effect=RuntimeError("secreto interno")
        ):
            response = self.post(width=64, height=64, text="hola")
        self.assertEqual(response.status_code, 500)
        detail = str(response.json()["detail"])
        self.assertNotIn("secreto interno", detail)
        self.assertNotIn("Traceback", detail)

    def test_semaphore_exhausted_returns_429_with_retry_after(self):
        # Ocupo todos los cupos de generación simultánea: la API debe
        # rechazar de inmediato (sin encolar) con 429 y Retry-After.
        cupos_tomados = 0
        try:
            for _ in range(GENERACIONES_SIMULTANEAS):
                self.assertTrue(
                    SEMAFORO_GENERACION.acquire(blocking=False),
                    "el semáforo debía arrancar libre",
                )
                cupos_tomados += 1
            response = self.post(width=64, height=64, text="hola")
        finally:
            # Nunca dejar cupos tomados: afectaría al resto de la suite.
            for _ in range(cupos_tomados):
                SEMAFORO_GENERACION.release()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "1")
        self.assertIn("simultáneas", str(response.json()["detail"]))

    def test_semaphore_is_released_after_a_failed_generation(self):
        # Si el fallo dejara el cupo ocupado, la petición siguiente
        # (con el semáforo lleno) respondería 429 en vez de 200.
        with patch(
            "notiemoji.render_wallpaper", side_effect=RuntimeError("fallo")
        ):
            response = self.post(width=64, height=64, text="hola")
        self.assertEqual(response.status_code, 500)
        siguiente = self.post(width=64, height=64, text="hola")
        self.assertEqual(siguiente.status_code, 200)

    def test_get_returns_real_png_with_requested_size(self):
        response = self.get(width=64, height=48, text="hola")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        with self.open_png(response.content) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (64, 48))

    def test_get_invalid_palette_returns_422_with_spanish_message(self):
        response = self.get(width=32, height=32, palette="arcoiris")
        self.assertEqual(response.status_code, 422)
        self.assertIn("paleta inválida", str(response.json()["detail"]))

    def test_get_invalid_dimension_returns_422(self):
        # GET y POST comparten el modelo: mismos límites y mismos 422.
        response = self.get(width=4001, height=32)
        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())

    def test_get_missing_required_params_return_422(self):
        response = self.client.get("/wallpaper")
        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())

    def test_get_matches_post_byte_for_byte(self):
        params = {
            "width": 320,
            "height": 180,
            "text": "hola 🚀",
            "palette": "noche",
            "font_size": 32,
            "bold": True,
        }
        post_response = self.post(**params)
        get_response = self.get(**params)
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(post_response.content, get_response.content)

    def test_get_is_documented_in_openapi(self):
        operations = self.client.get("/openapi.json").json()["paths"]["/wallpaper"]
        self.assertIn("get", operations)


class PaletasEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_returns_ten_palettes_in_order_as_json(self):
        response = self.client.get("/paletas")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["content-type"].startswith("application/json")
        )
        payload = response.json()
        self.assertEqual(len(payload), 10)
        self.assertEqual(
            [entrada["nombre"] for entrada in payload],
            list(notiemoji.PALETTES),
        )

    def test_palettes_match_notiemoji_palettes(self):
        payload = self.client.get("/paletas").json()
        esperado = [
            {"nombre": nombre, "color": fondo, "texto": txt}
            for nombre, (fondo, txt) in notiemoji.PALETTES.items()
        ]
        self.assertEqual(payload, esperado)


class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_reports_version_state_and_resources(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["version"], notiemoji.VERSION)
        self.assertIn(body["estado"], {"ok", "degradado"})
        self.assertIn("fuentes", body)
        self.assertIn("emoji", body["fuentes"])
        # Un bloque por estilo de TEXT_FONTS (normal, negrita, cursiva, ...).
        self.assertEqual(
            len(body["fuentes"]["texto"]), len(notiemoji.TEXT_FONTS)
        )

    def test_missing_emoji_font_still_returns_200_degraded(self):
        with patch(
            "notiemoji.find_emoji_font", side_effect=FileNotFoundError("sin fuente")
        ):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado"], "degradado")
        self.assertFalse(response.json()["fuentes"]["emoji"]["disponible"])

    def test_emoji_font_search_failures_do_not_break_health(self):
        # Cualquier fallo al consultar la fuente (permisos, archivo corrupto)
        # degrada el estado pero nunca rompe el healthcheck.
        for error in (OSError("sin permisos"), ValueError("fuente corrupta")):
            with self.subTest(error=type(error).__name__):
                with patch("notiemoji.find_emoji_font", side_effect=error):
                    response = self.client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["estado"], "degradado")


class IndexEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_serves_html_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/html"))
        self.assertIn("<title>notiemoji", response.text)
        self.assertIn("API_URL", response.text)

    def test_index_form_posts_json_to_wallpaper_endpoint(self):
        body = self.client.get("/").text
        # El formulario sigue enviando el mismo JSON al mismo endpoint.
        self.assertIn("fetch(`${API_URL}/wallpaper`", body)
        self.assertIn('method: "POST"', body)
        self.assertIn('"Content-Type": "application/json"', body)
        self.assertIn("JSON.stringify(armarPayload())", body)

    def test_root_is_hidden_from_openapi_schema(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertNotIn("/", paths)

    def test_index_fetches_palettes_from_endpoint(self):
        # Las paletas ya no se inyectan en el HTML: el probador las pide
        # con fetch(`${API_URL}/paletas`) y arma el select en el navegador.
        body = self.client.get("/").text
        self.assertIn("fetch(`${API_URL}/paletas`)", body)

    def test_palette_select_keeps_none_option(self):
        body = self.client.get("/").text
        self.assertIn('<option value="">ninguna</option>', body)


if __name__ == "__main__":
    unittest.main()
