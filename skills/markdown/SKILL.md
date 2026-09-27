# Skill de Markdown

Aplicá estas instrucciones cuando escribas o modifiques documentación del
proyecto en Markdown: `README.md`, `AGENTS.md` y los archivos de `skills/`.

## Alcance

La documentación presenta el proyecto, sus opciones y sus reglas de trabajo.

Debe:

- Reflejar el comportamiento real de `notiemoji.py`.
- Estar en español, con el mismo voseo de los archivos existentes.
- Mantener tablas para opciones, paletas y comparaciones.
- Usar texto alternativo descriptivo en las imágenes.

No debe:

- Documentar funcionalidades que no existan.
- Incluir secretos, rutas absolutas ni archivos generados.
- Qedar desactualizada: al cambiar el comportamiento, actualizá la
  documentación en el mismo cambio.

## Estructura

- Un solo `#` por archivo: el título del documento.
- Secciones con `##`; no saltes niveles de encabezado.
- Listas para instrucciones y pasos; párrafos cortos para explicaciones.
- Bloques de código con el lenguaje indicado (`bash`, `text`, `python`).
- Líneas de ancho aproximado de 80 caracteres.
- Enlaces e imágenes con rutas relativas al archivo.
- No hay linter de Markdown configurado; seguí el estilo de los archivos
  existentes.

## Estilo

- Usá inglés solo para identificadores, nombres propios, comandos y contenido
  técnico literal.
- Redactá en voz activa y con frases directas.
- Evitá redundancias: cada regla o dato vive en un solo archivo.
- Documentá las decisiones no obvias; no comentes lo evidente.

## Sincronización

- Los comandos y ejemplos deben poder ejecutarse tal como se muestran.
- Verificá rutas, opciones y valores antes de documentarlos.
- Si cambiás opciones, paletas o comportamiento, actualizá `README.md` en el
  mismo cambio.
