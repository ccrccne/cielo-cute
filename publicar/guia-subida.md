# Cómo subir Cielo cute a Modrinth y CurseForge

Todo lo necesario está en esta carpeta y en `dist/`:

- `dist/26.3/` y `dist/1.21.1/`: 18 zips cada una (uno por tema), listos para subir tal cual.
- `publicar/galeria/`: capturas reales del juego, una por tema (inventario, menú de pausa, sol y luna).
- `publicar/avatar.png`: icono del proyecto, 512×512.
- `publicar/descripcion.md`: descripción en inglés y español, resumen de una frase, preguntas frecuentes y créditos.

## Reglas que hay que respetar (revisadas el 24 de octubre de 2026)

- **CurseForge:** las variantes de color de un mismo paquete van en **un solo proyecto con varios archivos**, no como proyectos separados. El zip debe tener `pack.mcmeta` en la raíz (así están). Necesita al menos una imagen de muestra del juego real y un avatar cuadrado de 400×400 o más. Los enlaces de donación (Ko-fi) van al final de la descripción.
- **Modrinth:** descripción con versión en inglés (la tiene), galería que no engañe (son capturas reales) y metadatos correctos. Cada tema se sube como una **versión** del mismo proyecto.
- **Inteligencia artificial:** el script que genera las texturas y los textos de la página los escribí yo (Claude, una IA). Modrinth pide marcar "Contains AI-generated content" cuando una parte importante viene de IA, y no acepta proyectos hechos principalmente con IA generativa. Hay que declararlo con la verdad. Puede que Modrinth no lo apruebe; CurseForge pide aviso solo si las imágenes de muestra fueron modificadas con IA (las capturas son reales, sin retoque).
- **Texturas de Mojang:** son recoloreos de las texturas originales del juego, lo mismo que hacen miles de paquetes de interfaz en ambas webs. La descripción incluye el aviso de que no es un producto oficial.

## Modrinth

1. modrinth.com → **Create a project** → tipo **Resource Pack**.
2. Nombre: `Cielo cute`. URL sugerida: `cielo-cute`.
3. Resumen: la frase de `descripcion.md`.
4. **Description**: pega todo el bloque "English" y luego "Español" de `descripcion.md`.
5. **Icon**: `publicar/avatar.png`.
6. **Categorías**: elige las que digan GUI, Themed y Simplistic (o las más parecidas que aparezcan). Resolución: 16x. Licencia: **MIT**.
7. **Gallery**: sube las 18 imágenes de `publicar/galeria/` (título = nombre del tema). Marca `cielo.png` como destacada.
8. **Versions**: una versión por zip.
   - Nombre: `Cielo 2.0.0 (26.3)` / `Cielo 2.0.0 (1.21.1)`, etc.
   - Número de versión: `2.0.0+cielo-26.3`, `2.0.0+cielo-1.21.1`, … (tiene que ser distinto en cada una).
   - Versiones del juego: los zips de `dist/26.3` → **26.3**; los de `dist/1.21.1` → **1.21** y **1.21.1**.
   - Loader: **Minecraft** (resource pack).
   - Changelog: "2.0.0: 18 temas de color, sol con carita, luna a juego y fondos decorados."
9. En **Moderation / AI disclosure**, marca la casilla de contenido generado con IA.
10. Envía a revisión.

## CurseForge

1. curseforge.com → Create Project → **Minecraft → Resource Packs**.
2. Nombre: `Cielo cute`. Resumen: la frase de `descripcion.md`.
3. Descripción: bloque "English" (y si quieres "Español") de `descripcion.md`. El enlace de Ko-fi va al final.
4. Avatar: `publicar/avatar.png`.
5. Categorías: **Miscellaneous**, **16x** (son texturas al tamaño original).
6. Licencia: MIT.
7. Imágenes: las de `publicar/galeria/`.
8. Archivos: sube los 36 zips al **mismo proyecto**.
   - Nombre visible: `Cielo cute 2.0.0 – Cielo (26.3)`, `Cielo cute 2.0.0 – Cotton Candy (1.21.1)`, etc.
   - Versión del juego según la carpeta, como en Modrinth.
   - Tipo: Release.
   - Changelog: el mismo de arriba.
9. Envía a revisión.

## Antes de subir: prueba rápida

- Abre Minecraft 26.3, pon dos o tres zips en la carpeta de paquetes y revisa que todo se vea bien.
- Si tienes 1.21.1, haz lo mismo con un zip de `dist/1.21.1`. Esa versión la revisé archivo por archivo (todas las texturas existen en 1.21.1 y tienen el mismo tamaño), pero no la vi dentro del juego.
