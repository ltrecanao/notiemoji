# AGENTS.md

## Reglas generales

- Respondé y documentá en español.
- Usá inglés solo para identificadores, nombres propios, comandos y contenido
  técnico literal.
- `skills/` contiene las habilidades e instrucciones específicas que deben
  aplicar los agentes según la tarea. Hoy hay skills de `python`,
  `container`, `markdown`, `git`, `frontend` y `uiux`. La skill de `uiux`
  define el *qué* y el *por qué* de cada decisión de interfaz (layout,
  desplegables, ciclo de vistas, notificaciones, foco, errores); la de
  `frontend` define el *cómo* (HTML/CSS/JS) y es **mobile-first**: el
  layout base es angosto y las media queries agregan columnas. Se
  retroalimentan: si una cambia un patrón, la otra se actualiza en el mismo
  cambio. **Son dominios separados**: una tarea de UI/UX se delega a un
  subagente con la skill de `uiux`; una tarea de implementación se delega a
  otro con la skill de `frontend`. Nunca se mezclan en el mismo subagente.
- El frontend vive en `docs/` y se despliega en GitHub Pages.
- Delegá las tareas a subagentes aplicando la skill de `skills/` que
  corresponda al dominio de la tarea. Coordiná vos: no ejecutas esas tareas
  directamente. Si una tarea no tiene skill aplicable, ejecutala vos
  directamente en lugar de delegar.
- No comitees secretos ni archivos generados.
- Leé las instrucciones aplicables de `skills/` y los archivos relevantes
  antes de modificarlos.
- Hacé cambios pequeños y enfocados.
- No amplíes el alcance de la tarea ni asumas decisiones faltantes.
- No hagas commits, pushes, merges, borrados ni renombres sin autorización
  explícita.

- Mantené una sola versión de Python en todo el proyecto. `render.yaml`
  (`PYTHON_VERSION`), el `Dockerfile` (`FROM python:X`) y
  `.github/workflows/ci.yml` (`PYTHON_VERSION`) tienen que decir lo mismo, y
  `pyproject.toml` (`requires-python`, `target-version`, `python-version`) no
  debe contradecirlos. El paso `Versiones` del CI falla si divergen.