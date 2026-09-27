# Skill de Git

Aplicá estas instrucciones cuando trabajes con ramas, commits, pull requests,
tags o releases.

## Autorización

- No hagas commits, pushes, merges, borrados ni renombres sin autorización
  explícita. Prepará todo y esperá el OK antes de aplicarlo.

## Ramas

- `main` es la rama de integración y release.
- Creá ramas `feature/<descripción>` o `bugfix/<descripción>` desde un `main`
  actualizado.
- No trabajes directamente sobre `main`.
- No uses `develop`, `release` ni `hotfix/<descripción>`.
- No reescribas `main` con `rebase`, `reset` o `push --force`.

## Commits

- Usá Conventional Commits, con el tipo en inglés y el mensaje en español.
- Mantené los mensajes claros, concisos y fieles a los cambios realizados.
- No describas cambios inexistentes ni mezcles cambios no relacionados.

Ejemplo:

```text
feat: agregar soporte para colores personalizados
```

## Pull requests

- Apuntá siempre a main.
- Verificá explícitamente las ramas base y head.
- Requerí un CI exitoso antes del merge.
- Usá títulos y descripciones claros y concisos.
- Describí únicamente los cambios realmente realizados.
- No incluyas información irrelevante ni atribuyas cambios inexistentes.
- Entregá siempre el título, la descripción, base y head listos para usar.

## Tags y releases

- Creá tags y releases únicamente mediante el workflow manual definido por el repositorio.
- No las generes automáticamente al integrar código.
