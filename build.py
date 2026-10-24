"""Genera todas las variantes de Cielo cute a partir de las texturas originales de Minecraft.

Uso: python build.py <carpeta con una subcarpeta por versión: 26.3/assets/..., 1.21.1/assets/...>

Por cada tema de themes.py y cada versión:
- tiñe los grises de la interfaz con la paleta del tema (el relieve de botones y casillas se mantiene),
- pinta la casilla seleccionada, los corazones y el cuadro de descripciones,
- dibuja un sol propio, tiñe las fases de la luna y decora el fondo de los menús,
- crea el icono del paquete y lo guarda todo en dist/<versión>/cielo-cute-<tema>-<versión>.zip
"""
import colorsys
import json
import math
import pathlib
import sys
import zipfile

import numpy as np
from PIL import Image

from themes import THEMES

PACK_VERSION = "2.0.1"
ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
VERSIONS = {
    "26.3": dict(mcmeta={"min_format": 97, "max_format": 97}, moon="celestial"),
    "1.21.1": dict(mcmeta={"pack_format": 34}, moon="sheet"),
}
GUI_LUM = [0, 55, 93, 139, 198, 255]
ACCENT_LUM = [0, 95, 160, 215, 255]
SUN_BRIGHTNESS = .55  # el sol se suma al cielo: más bajo conserva el color
GROUPS = ["container", "sprites/container", "sprites/widget", "sprites/recipe_book", "sprites/advancements",
          "sprites/world_list", "sprites/server_list", "sprites/toast", "sprites/pause_menu", "sprites/dialog"]
MOON_PHASES = ["full_moon", "waning_gibbous", "third_quarter", "waning_crescent",
               "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous"]

# Dibujitos de 5x5 (o menos) que se repiten en el fondo de los menús
MOTIFS = {
    "star": ["..#..", ".###.", "#####", ".#.#.", "#...#"],
    "sparkle": ["..#..", "..#..", "##.##", "..#..", "..#.."],
    "heart": [".#.#.", "#####", "#####", ".###.", "..#.."],
    "flower": [".#.#.", "##.##", ".#.#."],
    "leaf": ["...##", "..###", ".###.", "###..", "#...."],
    "dot": ["##", "##"],
    "cloud": [".##..", "####.", "#####"],
    "moon": [".###", "##..", "#...", "##..", ".###"],
    "bubble": [".##.", "#..#", "#..#", ".##."],
    "sun": ["#.#.#", ".###.", "#####", ".###.", "#.#.#"],
    "none": [],
}


# ---------- utilidades de color ----------
def lum_of(rgb):
    return .299 * rgb[0] + .587 * rgb[1] + .114 * rgb[2]


def ramp(colors, points, lum):
    return tuple(float(np.interp(lum, points, [c[i] for c in colors])) for i in range(3))


def rel_lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    r, g, b = (ch(float(v)) for v in rgb)
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    la, lb = sorted((rel_lum(a), rel_lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def darker(colors, f):
    return [tuple(round(v * f) for v in c) for c in colors]


def button_ramp(gui):
    """El texto de los botones es blanco y fijo: si el botón queda muy claro, se oscurece su paleta."""
    colors = gui
    while contrast((255, 255, 255), ramp(colors, GUI_LUM, 112)) < 3.0:
        colors = [colors[0]] + darker(colors[1:-1], .92) + [colors[-1]]
    return colors


# ---------- texturas ----------
def tint(path, colors, points=GUI_LUM, only_grey=True):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3]
    lum = rgb @ np.array([.299, .587, .114], np.float32)
    mask = alpha > 0
    if only_grey:
        mask &= (rgb.max(-1) - rgb.min(-1)) < 40
    out = a.copy()
    for i in range(3):
        out[..., i] = np.where(mask, np.interp(lum, points, [c[i] for c in colors]), rgb[..., i])
    return Image.fromarray(out.round().astype(np.uint8), "RGBA")


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
            nr, ng, nb = colorsys.hls_to_rgb(hue / 360, min(l + light_add, 1), min(s * sat_scale, 1))
            px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return im


def shape_inside(kind, x, y):
    """x, y entre -1 y 1. Formas del sol."""
    r, t = math.hypot(x, y), math.atan2(y, x)
    if kind == "round":
        return r <= .82
    if kind == "square":
        return max(abs(x), abs(y)) <= .7
    if kind == "heart":
        X, Y = x * 1.25, -y * 1.25 + .25
        return (X * X + Y * Y - 1) ** 3 - X * X * Y ** 3 <= 0
    if kind == "star":
        k = (math.cos(5 * (t + math.pi / 2)) + 1) / 2
        return r <= .42 + .5 * k ** 3
    if kind == "flower":
        return r <= .58 + .3 * abs(math.cos(2.5 * (t + math.pi / 2)))
    raise ValueError(kind)


def draw_sun(kind, rim, core):
    n = 16
    inside = np.zeros((n, n), bool)
    for j in range(n):
        for i in range(n):
            inside[j, i] = shape_inside(kind, (i + .5) / n * 2 - 1, (j + .5) / n * 2 - 1)
    img = np.zeros((n, n, 4), np.float32)
    img[..., 3] = 255
    pad = np.pad(inside, 1)
    edge = inside & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    near = ~inside & (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:])
    for j in range(n):
        for i in range(n):
            if edge[j, i]:
                img[j, i, :3] = rim
            elif inside[j, i]:
                d = math.hypot(i + .5 - n / 2, j + .5 - n / 2) / (n / 2)
                img[j, i, :3] = [c + (r_ - c) * min(d * 1.3, 1) for c, r_ in zip(core, rim)]
            elif near[j, i]:
                img[j, i, :3] = [v * .35 for v in rim]  # brillo suave alrededor (el sol se suma al cielo)
    if kind != "square":
        # Carita: los píxeles negros dejan ver el cielo (el sol se suma), así que los ojos y la sonrisa se notan
        for x, y in [(5, 6), (10, 6), (6, 9), (7, 10), (8, 10), (9, 9)]:
            if inside[y, x]:
                img[y, x, :3] = 0
        for x, y in [(4, 8), (11, 8)]:
            if inside[y, x]:
                img[y, x, :3] = (255, 110, 150)
    img[..., :3] *= SUN_BRIGHTNESS
    # En el cielo la textura se ve de cabeza, así que se voltea
    im = Image.fromarray(img[::-1].round().astype(np.uint8), "RGBA").resize((32, 32), Image.NEAREST)
    return im


def tint_moon(im, color):
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    lum = a[..., :3] @ np.array([.299, .587, .114], np.float32) / 255
    boost = np.clip(lum * 1.15, 0, 1)[..., None]
    a[..., :3] = boost * np.array(color, np.float32)
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


def menu_tile(base, motif, motif_color, alpha, motif_alpha):
    im = Image.new("RGBA", (16, 16), (*base, alpha))
    px = im.load()
    pat = MOTIFS[motif]
    for dy, row in enumerate(pat):
        for dx, ch in enumerate(row):
            if ch == "#":
                px[2 + dx, 2 + dy] = (*motif_color, motif_alpha)
    if pat:
        px[11, 11] = (*motif_color, motif_alpha // 2)
        px[13, 7] = (*motif_color, motif_alpha // 3)
    return im


def pack_icon(t):
    s = 128
    top, bottom = np.array(t["gui"][4], np.float32), np.array(t["gui"][3], np.float32)
    grad = top + (bottom - top) * np.linspace(0, 1, s, dtype=np.float32)[:, None, None]
    im = Image.fromarray(np.repeat(grad, s, axis=1).astype(np.uint8), "RGB").convert("RGBA")
    if t["menu"][1] != "none":
        tile = menu_tile(t["gui"][4], t["menu"][1], t["gui"][3], 0, 255).resize((32, 32), Image.NEAREST)
        for y in range(0, s, 32):
            for x in range(0, s, 32):
                im.alpha_composite(tile, (x, y))
    sun = draw_sun(t["sun"][0], t["sun"][1], t["sun"][2]).transpose(Image.FLIP_TOP_BOTTOM)
    a = np.asarray(sun).copy()
    a[..., :3] = np.clip(a[..., :3] / SUN_BRIGHTNESS, 0, 255)
    a[..., 3] = np.where(a[..., :3].sum(-1) > 60, 255, 0)  # en el icono el negro es transparente
    im.alpha_composite(Image.fromarray(a).resize((64, 64), Image.NEAREST), (32, 14))
    # Barra rápida de 5 casillas, la del medio con el color de acento
    slot_dark, slot_mid, slot_light = (tuple(int(v) for v in ramp(t["gui"], GUI_LUM, l)) for l in (55, 139, 255))
    for k in range(5):
        x0, y0 = 14 + k * 20, 92
        accent = k == 2
        im.paste(slot_dark if not accent else tuple(int(v) for v in ramp(t["accent"], ACCENT_LUM, 95)), (x0, y0, x0 + 20, y0 + 20))
        im.paste(slot_mid if not accent else tuple(int(v) for v in ramp(t["accent"], ACCENT_LUM, 215)), (x0 + 2, y0 + 2, x0 + 18, y0 + 18))
        im.paste(slot_light if not accent else (255, 255, 255), (x0 + 2, y0 + 2, x0 + 4, y0 + 4))
    return im


# ---------- construcción ----------
def build(theme, version, src):
    gui_src = src / "assets/minecraft/textures/gui"
    env_src = src / "assets/minecraft/textures/environment"
    files = {}

    def put(rel, im):
        files[f"assets/minecraft/textures/{rel}"] = im

    btn = button_ramp(theme["gui"])
    for group in GROUPS:
        d = gui_src / group
        if not d.exists():
            continue
        colors = btn if group == "sprites/widget" else theme["gui"]
        for f in sorted(d.rglob("*.png")):
            put(f"gui/{f.relative_to(gui_src).as_posix()}", tint(f, colors))
    put("gui/recipe_book.png", tint(gui_src / "recipe_book.png", theme["gui"]))
    for name in ["hotbar.png", "hotbar_offhand_left.png", "hotbar_offhand_right.png"]:
        put(f"gui/sprites/hud/{name}", tint(gui_src / "sprites/hud" / name, theme["gui"]))
    put("gui/sprites/hud/hotbar_selection.png", tint(gui_src / "sprites/hud/hotbar_selection.png", theme["accent"], ACCENT_LUM))

    hue, sat, light = theme["heart"]
    for f in sorted((gui_src / "sprites/hud/heart").glob("*.png")):
        if f.stem.split("_")[0] in ("full", "half", "hardcore"):
            put(f"gui/sprites/hud/heart/{f.name}", hue_shift(f, hue, sat, light, reds_only=True))
    for name in ["background.png", "frame.png"]:
        if (gui_src / "sprites/tooltip" / name).exists():  # 1.21.1 dibuja las descripciones sin textura
            put(f"gui/sprites/tooltip/{name}", hue_shift(gui_src / "sprites/tooltip" / name, theme["tooltip"]))

    base, motif, motif_color = theme["menu"]
    put("gui/menu_background.png", menu_tile(base, motif, motif_color, 120, 110))
    put("gui/inworld_menu_background.png", menu_tile(base, motif, motif_color, 90, 70))
    list_base = tuple(round(v * .7) for v in base)
    put("gui/menu_list_background.png", menu_tile(list_base, motif, motif_color, 150, 110))
    put("gui/inworld_menu_list_background.png", menu_tile(list_base, motif, motif_color, 130, 100))

    sun = draw_sun(*theme["sun"])
    if VERSIONS[version]["moon"] == "celestial":
        put("environment/celestial/sun.png", sun)
        for p in MOON_PHASES:
            put(f"environment/celestial/moon/{p}.png", tint_moon(Image.open(env_src / f"celestial/moon/{p}.png"), theme["moon"]))
    else:
        put("environment/sun.png", sun)
        put("environment/moon_phases.png", tint_moon(Image.open(env_src / "moon_phases.png"), theme["moon"]))

    # Las .mcmeta (cómo se estiran los botones y paneles) se copian tal cual
    extra = {}
    for f in gui_src.rglob("*.png.mcmeta"):
        rel = f"assets/minecraft/textures/gui/{f.relative_to(gui_src).as_posix()}"
        if rel[:-len(".mcmeta")] in files:
            extra[rel] = f.read_bytes()

    desc = f"§bCielo cute §e✦ §f{theme['name']}\n§7por ccrccne"
    mcmeta = {"pack": {"description": desc, **VERSIONS[version]["mcmeta"]}}
    out = DIST / version / f"cielo-cute-{theme['id']}-{PACK_VERSION}+{version}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps(mcmeta, ensure_ascii=False, indent=4))
        z.write(ROOT / "LICENSE", "LICENSE.txt")
        z.writestr("CREDITOS.txt", "Cielo cute por ccrccne - https://ccrccne.github.io\n"
                   "Texturas basadas en las originales de Minecraft (Mojang), recoloreadas con build.py.\n"
                   "No es un producto oficial de Minecraft. No está aprobado ni asociado con Mojang o Microsoft.\n")
        icon = pack_icon(theme)
        for rel, im in [("pack.png", icon), *files.items()]:
            buf = __import__("io").BytesIO()
            im.save(buf, "PNG", optimize=True)
            z.writestr(rel, buf.getvalue())
        for rel, data in extra.items():
            z.writestr(rel, data)
    return out, len(files)


def check(theme):
    """Avisos de legibilidad: los títulos de los inventarios son gris oscuro fijo (#404040)."""
    panel = ramp(theme["gui"], GUI_LUM, 198)
    warn = []
    if contrast(panel, (64, 64, 64)) < 4.5:
        warn.append(f"títulos poco legibles ({contrast(panel, (64, 64, 64)):.1f})")
    btn = ramp(button_ramp(theme["gui"]), GUI_LUM, 112)
    if contrast(btn, (255, 255, 255)) < 3.0:
        warn.append("texto de botones poco legible")
    return warn


if __name__ == "__main__":
    vanilla = pathlib.Path(sys.argv[1])
    only = sys.argv[2:] or [t["id"] for t in THEMES]
    for t in THEMES:
        if t["id"] not in only:
            continue
        w = check(t)
        for v in VERSIONS:
            out, n = build(t, v, vanilla / v)
            print(f"{t['id']:12} {v:7} {n} texturas  {'AVISO: ' + ', '.join(w) if w else ''}")
            pack_icon(t).save(DIST / f"icono-{t['id']}.png")
