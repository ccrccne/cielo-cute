"""Genera el paquete Cielo cute a partir de las texturas originales de Minecraft.

Uso: python build.py <carpeta con assets/minecraft/textures/gui sacada del .jar del juego>
Tiñe los grises de la interfaz con una escala de azul cielo, vuelve rosados los corazones
y deja dorada la casilla seleccionada de la barra rápida.
"""
import colorsys
import pathlib
import sys

from PIL import Image

SRC = pathlib.Path(sys.argv[1]) / "assets/minecraft/textures/gui"
OUT = pathlib.Path(__file__).parent / "pack/assets/minecraft/textures/gui"

# Luminosidad del gris original -> color nuevo
SKY = [(0, (27, 47, 99)), (55, (47, 85, 150)), (93, (74, 127, 192)), (139, (124, 184, 230)), (198, (205, 234, 251)), (255, (255, 255, 255))]
GOLD = [(0, (92, 58, 0)), (95, (196, 128, 20)), (160, (255, 201, 60)), (215, (255, 232, 140)), (255, (255, 250, 225))]


def ramp(stops, lum):
    for (l0, c0), (l1, c1) in zip(stops, stops[1:]):
        if lum <= l1:
            t = (lum - l0) / (l1 - l0)
            return tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))
    return stops[-1][1]


def is_grey(r, g, b):
    return max(r, g, b) - min(r, g, b) < 40


def tint(path, stops=SKY, only_grey=True):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0 or (only_grey and not is_grey(r, g, b)):
                continue
            lum = round(.299 * r + .587 * g + .114 * b)
            px[x, y] = (*ramp(stops, lum), a)
    return im


def hue_shift(path, hue, sat_scale=1.0, light_add=0.0, reds_only=False):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if reds_only and not (s > .3 and (h < .06 or h > .94)):
                continue
            nr, ng, nb = colorsys.hls_to_rgb(hue / 360, min(l + light_add, 1), s * sat_scale)
            px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return im


def save(im, rel):
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)


count = 0
groups = ["container", "sprites/container", "sprites/widget", "sprites/recipe_book", "sprites/advancements", "sprites/world_list", "sprites/server_list", "sprites/toast"]
for group in groups:
    for f in sorted((SRC / group).rglob("*.png")):
        rel = f.relative_to(SRC)
        save(tint(f), rel)
        count += 1

save(tint(SRC / "recipe_book.png"), "recipe_book.png")
count += 1

for name in ["hotbar.png", "hotbar_offhand_left.png", "hotbar_offhand_right.png"]:
    save(tint(SRC / "sprites/hud" / name), f"sprites/hud/{name}")
    count += 1
save(tint(SRC / "sprites/hud/hotbar_selection.png", GOLD), "sprites/hud/hotbar_selection.png")
count += 1

# Corazones rosados (solo los normales y los de hardcore; los envenenados, congelados, etc. se quedan igual)
for f in sorted((SRC / "sprites/hud/heart").glob("*.png")):
    n = f.stem
    if n.split("_")[0] in ("full", "half", "hardcore"):
        save(hue_shift(f, 335, sat_scale=.85, light_add=.12, reds_only=True), f"sprites/hud/heart/{f.name}")
        count += 1

# Cuadro de las descripciones: de morado a azul noche
for name in ["background.png", "frame.png"]:
    save(hue_shift(SRC / "sprites/tooltip" / name, 215), f"sprites/tooltip/{name}")
    count += 1

# Fondo oscuro de los menús, con un toque azul noche
for name in ["menu_background.png", "inworld_menu_background.png", "menu_list_background.png", "inworld_menu_list_background.png"]:
    im = Image.open(SRC / name).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            lum = round(.299 * r + .587 * g + .114 * b)
            px[x, y] = (min(255, 18 + lum // 3), min(255, 32 + lum // 2), min(255, 78 + lum), a)
    save(im, name)
    count += 1

# Las .mcmeta (cómo se estiran los botones) se copian tal cual
for f in SRC.rglob("*.png.mcmeta"):
    rel = f.relative_to(SRC)
    if (OUT / rel.with_suffix("")).exists():
        (OUT / rel).write_bytes(f.read_bytes())

print(f"{count} texturas generadas")
