# Skill de UI/UX

Aplicá estas instrucciones cuando tomes decisiones de interfaz, layout o
experiencia de usuario. Define el *qué* y el *por qué* de cada decisión
visible; el *cómo* (HTML, CSS, JS) vive en la skill de Frontend.

Esta skill es **reutilizable**: los patrones generales sirven para cualquier
proyecto web; los específicos de notiemoji están al final y son de referencia.

## Principios generales (reutilizables)

- **Mobile-first.** El layout base es angosto; las media queries
  (`min-width`) agregan columnas y paneles. Nunca al revés.
- **Sin espacio desperdiciado.** Las cajas (formulario, preview) ocupan
  **todo el alto disponible** en todo viewport. No hay scroll de
  página (`overflow: hidden` en `body`); los paneles internos scrollean
  individualmente. Verificar en navegador headless que no queda espacio
  vacío abajo.
- **Texto de botones corto y directo.** Hasta tres palabras. Las acciones
  se dicen como «verbo + objeto» («Generar wallpaper», «Descargar .png») y
  las opciones, como un sintagma nominal paralelo entre sí. Nada de
  «Mostrar/Ocultar X» cuando alcanza con «X».
- **Estado visible.** El control que abre o cierra algo refleja su estado
  con `aria-expanded` (o `aria-current` para selección); un conjunto de
  opciones exclusivas, con `aria-checked` en cada opción. El texto del
  botón o de la opción nombra la vista actual o la acción, de forma
  consistente en todo el editor.
- **Foco visible y devuelto.** Todo control tiene `:focus-visible` claro. Al
  cerrar un panel o desplegable, el foco vuelve al control que lo abrió.
- **Resultado visible: éxito efímero (toast), error persistente junto al
  control.** Cada operación muestra su resultado: el éxito se avisa con
  un toast que desaparece solo; el error y el estado «trabajando» quedan
  en el indicador con `role="status"` y `aria-live="polite"` del
  elemento que los provocó (o en un `role="alert"` sin auto-cierre
  cuando la acción no tiene control propio en pantalla).

## Patrones generales (reutilizables)

### Notificaciones (toast)

Estándar de la industria (Carbon, Material 3, GitHub, Notion, Slack,
react-toastify, sonner):

- **Posición por corte**: contenedor fijo. En angosto (<48rem) **abajo**
  (Material: el snackbar va abajo en móvil, y así no choca con la topbar);
  desde 48rem, **arriba a la derecha y por debajo de la topbar**, nunca
  tapado por ella.
- **Agrupamiento**: vertical, la más reciente arriba (`flex-direction:
  column`) y **tope de 3** en pantalla; al superarlo se descarta el más
  viejo que no sea error y, si los tres son error, el más viejo.
- **Auto-cierre**: 6 segundos para el éxito, **en pausa** con
  `mouseenter`/`focusin` y reanudado con el **tiempo restante** al salir
  (WCAG 2.2.1 + G4, igual que react-toastify y sonner). La X cancela el
  timer y cierra en el acto. El toast **nunca roba el foco**.
- **Roles**: éxito → `role="status"` con `aria-live="polite"` y
  auto-cierre; error → `role="alert"` (asertivo por ARIA, sin
  `aria-live` adicional) y **sin auto-cierre**: solo lo cierra la X.
- **Creación en dos pasos**: la región viva se inserta **vacía** con su
  rol y el texto se escribe recién después (WCAG 2.2 SC 4.1.3, técnicas
  ARIA22/ARIA19); `#toasts` no lleva `aria-live`.
- **Cierre manual**: botón X con `aria-label="Cerrar notificación"`.
- **No bloquean**: contenedor con `pointer-events: none`, cada toast con
  `pointer-events: auto`.
- **Tono**: `ok` para éxitos y para las notificaciones del backend;
  `error` (clase `.toast-error`) solo para fallos sin control propio.

### Desplegables

- **Angosto**: arranca oculto, es un desplegable superpuesto (no empuja el
  contenido). Se abre con un botón, cae ancho completo justo debajo de la
  barra superior, con scroll interno y sombra. Se cierra con `Escape`, con el
  botón, o al abrir una nota.
- **Ancho**: el contenido es una columna lateral, siempre visible. El botón
  desplegable no se ve.
- **Regla de oro**: el desplegable debe ocupar **todo el alto disponible**
  desde la topbar hasta el fondo de la pantalla. Usar `top` + `bottom: 0`
  (no `height: calc()`), porque `--topbar-alto` puede no fijarse correctamente
  y el desplegable queda con altura menor a la esperada. Verificar en
  navegador headless que el desplegable ocupa todo el alto.

### Convención de formatos

- El formato se escribe como la extensión del archivo: en minúsculas y
  con punto (`.png`); el resto de la etiqueta, sentence case. Nunca «PNG»
  ni la extensión suelta en texto visible.
- Ejemplos: «Descargar .png».

## Patrones específicos de notiemoji (referencia)

El frontend vive en `docs/` y se despliega en GitHub Pages.

- **Layout**: formulario arriba, preview abajo (regla de ejes cartesianos:
  izquierda→abajo, derecha→arriba).
- **Paletas**: selector que rellena automáticamente los campos de color de
  fondo y texto.
- **Color pickers**: cada campo de color lleva su picker nativo; el picker
  solo admite hex y el campo además acepta nombres CSS (navy, tomato, ...).
- **Preview**: el wallpaper generado se muestra en un `<img>` con opción de
  descarga.

## Verificación

- Todo cambio de UI se verifica en navegador headless a **~480px, ~800px
  y ~1280px**.
- Antes de cada cambio de interfaz, preguntate: **¿esto cumple con la skill?
  Si no, ¿la skill está desactualizada o el cambio es una excepción?** Si es
  excepción, documentala en la skill.
- Probá el manejo de errores con el backend apagado o devolviendo 500: la
  interfaz tiene que mostrarlo.
- **Toasts**: medí el auto-cierre con `performance.now()` (6000 ms
  ±100); comprobá la pausa por hover y por foco (reanuda con el tiempo
  restante, no desde cero), el cierre inmediato con X, el tope de 3 con
  el más reciente arriba y que un **error siga en pantalla a los 30 s**.
- **Sin residuos**: tras un éxito los indicadores quedan **vacíos** y
  `.estado:empty` mide 0 px; tras un error persiste al menos 10 s.
- **Foco**: ninguna operación lleva el foco al toast.
- No dejes comportamiento roto a cambio de «ya se va a arreglar».

## Relación con otras skills

- **Frontend** (`skills/frontend/SKILL.md`): define el *cómo* — HTML
  semántico, CSS con custom properties, JS vanilla con `fetch` y debounce.
  Cuando UI/UX cambie un patrón visible, la skill de frontend se actualiza en
  el mismo cambio, y viceversa: si el *cómo* de frontend obliga a repensar
  un patrón, se refleja en UI/UX.
- **Markdown** (`skills/markdown/SKILL.md`): si cambiás el comportamiento
  visible, actualizá `README.md` en el mismo cambio.

## Comandos

```bash
# Levantar el servidor de API en desarrollo
uv run uvicorn api:app --reload

# Comprobar que la API responde
curl -s http://127.0.0.1:8000/health
```