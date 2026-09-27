# Skill de Contenedores

Aplicá estas instrucciones cuando trabajes con el `Dockerfile`, el
`.dockerignore` o la imagen contenedorizada de un proyecto.

## Herramientas

- Usá **Podman**, no Docker: corre sin daemon, rootless, con `crun` y
  `overlay`.
- Usá `hadolint` para lint del `Dockerfile`.
- No agregues herramientas sin una justificación clara.

## Alcance

El contenedor empaqueta la aplicación para correrla de forma aislada y
reproducible, con la misma imagen en todos los entornos.

Debe:

- Buildear la imagen con Podman en formato `docker`.
- Instalar los recursos del sistema que la app necesita (fuentes, libs
  nativas).
- Exponer un `HEALTHCHECK` que refleje el estado real del servicio.
- Respetar `PORT` y apagar el proceso con SIGTERM.

No debe:

- Agregar herramientas a la imagen solo para que la sonda funcione.
- Confiar en que el build pase como única verificación.
- Copiar archivos que el build no necesita.

## HEALTHCHECK

La sonda tiene trampas no obvias:

- Podman genera imágenes en formato OCI por defecto y ahí `HEALTHCHECK` se
  descarta con el warning `HEALTHCHECK is not supported for OCI image format
  and will be ignored. Must use 'docker' format`. Buildeá siempre con
  `podman build --format docker`.
- Verificado: con `--format docker`, `podman inspect` devuelve
  `State.Health = {"Status":"healthy", ...}`; en formato OCI devuelve `null`.
- La primera sonda suele fallar porque el proceso todavía no escuchó. Lo
  absorbe `--start-period`.
- Si el endpoint devuelve `200` siempre, una sonda que solo mira el código
  HTTP daría verde aunque todo esté mal. Leé el body y comprobá el estado
  que declara.

## Imagen multi-etapa

- Separá la capa de dependencias de la capa de código para que cambie solo lo
  que cambió: copiá primero el manifiesto de dependencias y su lockfile,
  instalá y recién después copiá el código.
- Mantené el `WORKDIR` idéntico entre etapas cuando el install es editable y
  escribe rutas absolutas: si cambia, el import falla en runtime.
- Fijá versiones: las de la base, las de las dependencias y las de las
  herramientas de build.
- Con un gestor de dependencias tipo `uv`, seteá `UV_LINK_MODE=copy`,
  `UV_PYTHON_DOWNLOADS=never` y `UV_COMPILE_BYTECODE=1`.
- Creá un usuario sin privilegios: la app solo debe leer su directorio y los
  recursos del sistema.
- Dejá el `CMD` con `exec` para que el proceso quede como PID 1 y reciba
  SIGTERM, y con `${PORT:-8000}` porque los entornos de hosting inyectan
  `PORT`.
- Escribí el `HEALTHCHECK` sin `curl` (la imagen no lo trae): usá `python -c`
  con `urllib`.

## Recursos del sistema

- Instalá los recursos en la etapa final, cuando el contenedor corre como
  root: fuentes, libs nativas y lo que la app necesite en runtime.
- Verificá dentro de la imagen que el recurso existe y tiene el formato
  esperado: el build exitoso no garantiza que el recurso sea usable en
  runtime.

## .dockerignore

- Excluí `.venv/`, `.git/`, las cachés, `docs/` y `tests/`.
- No excluyas archivos que el build necesita.
- Antes de cerrar, comprobá que ningún archivo que el `Dockerfile` copia
  quede bloqueado.

## Verificación

No confíes solo en que el build pase:

- Levantá el contenedor y probá el comportamiento real del servicio.
- Medí algo observable que no se pueda falsear: colores únicos de un PNG,
  tiempo de arranque o tamaño de la imagen.
- Dejá esa medición como referencia para detectar regresiones.

## Lint

- `hadolint` marca DL3008 (fijar versiones en `apt-get install`).
- Tradeoff: fijar la versión da reproducibilidad, pero rompe el build si
  Debian retira esa versión.

## Comandos

```bash
# Buildear: sin --format docker, HEALTHCHECK se descarta
podman build --format docker -t miapp:local .

# Levantar el contenedor
podman run -d --name miapp -p 8000:8000 -e PORT=8000 miapp:local

# Estado del health (esperado: healthy)
podman inspect miapp --format '{{.State.Health.Status}}'

# Probar el servicio. Usá 127.0.0.1 y no localhost: localhost resuelve a
# ::1 y el forwarder de red de Podman solo escucha en IPv4, así que curl
# falla con code 000.
curl -s http://127.0.0.1:8000/

# Lint del Dockerfile
hadolint Dockerfile
```
