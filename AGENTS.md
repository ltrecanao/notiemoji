# AGENTS.md

## Reglas generales

- Respondé y documentá en español.
- Usá inglés solo para identificadores, nombres propios, comandos y contenido
  técnico literal.
- `skills/` contiene las habilidades e instrucciones específicas que deben
  aplicar los subagentes según la tarea.
- Delegá las tareas a subagentes aplicando la skill de `skills/` que
  corresponda al dominio de la tarea. Coordiná vos: no ejecutes esas tareas
  directamente. Si una tarea no tiene skill aplicable, ejecutala vos
  directamente en lugar de delegar.
- No comitees secretos ni archivos generados.
- Leé las instrucciones aplicables de `skills/` y los archivos relevantes antes
  de modificarlos.
- Hacé cambios pequeños y enfocados.
- No amplíes el alcance de la tarea ni asumas decisiones faltantes.
- No hagas commits, pushes, merges, borrados ni renombres sin autorización
  explícita.

- Mantené una sola versión de Python en todo el proyecto. `render.yaml`
  (`PYTHON_VERSION`), el `Dockerfile` (`FROM python:X`) y
  `.github/workflows/ci.yml` (`PYTHON_VERSION`) tienen que decir lo mismo, y
  `pyproject.toml` (`requires-python`, `target-version`, `python-version`) no
  debe contradecirlos. El paso `Versiones` del CI falla si divergen.
