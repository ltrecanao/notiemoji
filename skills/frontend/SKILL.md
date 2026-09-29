# Skill de Frontend

Aplicá estas instrucciones cuando trabajes con el HTML, CSS o JavaScript del
probador interactivo de notiemoji.

## Proyecto

- Frontend en HTML, CSS y JavaScript vanilla, sin dependencias externas ni
  bundlers.
- Servido como sitio estático desde GitHub Pages (`docs/`).
- La API vive en Render (`https://notiemoji.onrender.com`); el frontend hace
  `fetch` cross-origin.
- Estructura: HTML en `docs/`, hojas de estilo en `docs/css/` y módulos
  JavaScript en `docs/js/`.
- `docs/js/config.js` exporta `API_URL`; es el único lugar donde cambia la
  URL del backend.
- El backend no sirve el frontend: `api.py` solo expone la API HTTP.

## Alcance

El frontend es el probador interactivo: permite elegir paleta, colores,
tamaño de fuente, texto y estilo, y genera un wallpaper PNG descargable.

## Mobile-first (regla de oro)

El proyecto es **mobile-first**: el layout base es para pantallas angostas y
las media queries (`min-width`) agregan columnas y paneles. Esto no es
opcional: es la regla de oro del layout.

### Cadena de grids

El layout es una cadena de grids: `body` → `.app` → `.zona` → `.panel`. Para
que las cajas ocupen todo el alto disponible, **cada eslabón necesita altura
definida**:

- `body`: `height: 100dvh; overflow: hidden` (sin scroll de página).
- `.app`: `min-height: 0` (para que el `1fr` de `body` funcione). **No** usar
  `height: 100dvh` — causa conflicto con el `minmax(0, 1fr)` de `body`.
- `.zona`: `min-height: 0` (para que el `1fr` de `.app` funcione). **No** usar
  `height: 100%` — causa conflicto.
- `.panel`: `min-height: 0; flex: 1` (para que se expandan dentro de `.zona`).

### Sin espacio desperdiciado

Las cajas (formulario, preview) ocupan **todo el alto disponible** en todo
viewport. No hay scroll de página; los paneles internos scrollean
individualmente. Verificar en navegador headless que no queda espacio vacío
abajo.

## Código

### HTML semántico y accesible

- Usá elementos semánticos (`header`, `main`, `form`, `button`, `label`).
- Asociá cada `input` a su `label`; no dependas del placeholder.
- Mantené un orden lógico de encabezados y la navegación por teclado.
- Regiones vivas: se crean **vacías** con su rol y se rellenan en un segundo
  paso (WCAG 2.2 SC 4.1.3, técnicas ARIA22/ARIA19: una región que nace junto
  con su texto puede no anunciarse). Por eso `#toasts` va sin `aria-live` —la
  región es cada toast— y los indicadores `<p role="status" aria-live="polite">`
  se conservan intactos.
- Dejá el foco visible y alcanzable con `Tab`; ningún aviso roba el foco
  y ningún elemento enfocado queda con `display:none` (WCAG 2.4.3).
- Usá atributos `aria-*` solo cuando el HTML semántico no alcanza.

### CSS moderno

- Usá custom properties para los tokens: colores, espaciado y tipografía.
- Usá grid para el layout y flex para alineación dentro de un bloque.
- Clases cortas y con propósito; sin frameworks CSS.
- Preferí unidades relativas (`rem`, `em`, `%`) a los valores fijos.

### JavaScript vanilla

- Módulos ES con `<script type="module">`; sin variables globales.
- Usá `fetch` con manejo de errores y mostralos en la interfaz.
- `mostrarToast(id, titulo, mensaje, tono = "ok")` es el único camino de
  los avisos transitorios. Contrato:
  - `ok` (default): el toast se crea con `role="status"` +
    `aria-live="polite"` y se auto-cierra a **6000 ms**.
  - `error`: se crea con `role="alert"`, **sin** `aria-live` y **sin**
    auto-cierre —solo lo cierra la X—.
  - Creación **en dos pasos**: la región vacía con su rol entra al DOM
    primero y el texto se escribe en el frame siguiente.
  - **Apilado**: la más reciente arriba (`prepend`), tope de **3**; al
    superarlo se descarta el más viejo que no sea error.
  - **Pausa**: `mouseenter`/`focusin` congelan el timer,
    `mouseleave`/`focusout` reanudan con el tiempo restante; la X lo
    cancela. El toast **nunca** llama a `focus()`.
- Escribí funciones pequeñas con una responsabilidad clara.
- Documentá los tipos con JSDoc: `@param {string} texto`,
  `@returns {string}`.
- Documentá en español las decisiones no obvias.
- No agregues librerías externas ni bundlers sin una justificación clara.

## Tests

- No hay suite de JavaScript: los tests de `tests/test_api.py` cubren los
  endpoints que usa el frontend.
- Verificá manualmente en el navegador cada cambio: generación, preview,
  descarga y errores visibles.
- Verificá la topbar a **~480px, ~800px y ~1280px**.
- Probá el manejo de errores con el backend apagado o devolviendo 500: la
  interfaz tiene que mostrarlo.
- No dejes comportamiento roto a cambio de "ya se va a arreglar".

## Comandos

```bash
# Sincronizar el entorno y las dependencias (incluye el grupo de desarrollo)
uv sync

# Levantar el servidor de API en desarrollo
uv run uvicorn api:app --reload

# Comprobar que la API responde
curl -s http://127.0.0.1:8000/health
```

## Documentación

- Si cambiás el comportamiento visible o la estructura de `docs/`,
  actualizá `README.md` en el mismo cambio (ver skill de Markdown).

## Relación con otras skills

- **UI/UX** (`skills/uiux/SKILL.md`): define el *qué* y el *por qué* de cada
  decisión de interfaz (layout, notificaciones, foco, errores). Cuando UI/UX
  cambie un patrón visible, esta skill se actualiza en el mismo cambio, y
  viceversa: si el *cómo* de frontend obliga a repensar un patrón, se refleja
  en UI/UX.
- **Markdown** (`skills/markdown/SKILL.md`): si cambiás el comportamiento
  visible, actualizá `README.md` en el mismo cambio.

## Formato y calidad

- No hay linter de HTML, CSS ni JS configurado; seguí el estilo de los
  archivos existentes en `docs/`.
- Mantené una responsabilidad por archivo y líneas cortas.
- Evitá comentarios obvios y código comentado.
- Documentá en español la intención y las decisiones no evidentes.
- Actualizá la documentación cuando cambie el comportamiento del frontend.