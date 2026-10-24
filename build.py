"""Genera todas las variantes de Cozy GUI a partir de las texturas originales de Minecraft.

Uso: python build.py <carpeta con una subcarpeta por versión: 26.3/assets/..., 1.21.1/assets/...>

Por cada tema de themes.py y cada versión:
- tiñe los grises de la interfaz con la paleta del tema (el relieve de botones y casillas se mantiene),
- pinta la casilla seleccionada, los corazones y el cuadro de descripciones,
- decora el fondo de los menús con un dibujito repetido,
- crea el icono del paquete y lo guarda todo en dist/<versión>/cozy-gui-<tema>-<versión>.zip
"""
import colorsys
import json
import pathlib
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw

from themes import THEMES

PACK_VERSION = "2.1.1"
ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
VERSIONS = {
    "26.3": dict(mcmeta={"min_format": 97, "max_format": 97}),
    "1.21.1": dict(mcmeta={"pack_format": 34}),
}
GUI_LUM = [0, 55, 93, 139, 198, 255]
ACCENT_LUM = [0, 95, 160, 215, 255]
GROUPS = ["container", "sprites/container", "sprites/widget", "sprites/recipe_book", "sprites/advancements",
          "sprites/world_list", "sprites/server_list", "sprites/toast", "sprites/pause_menu", "sprites/dialog"]

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
    """Una ventanita de inventario con los colores del tema, sobre el fondo de sus menús."""
    n = 32
    base, motif, motif_color = t["menu"]
    im = Image.new("RGBA", (n, n), (*base, 255))
    tile = menu_tile(base, motif, motif_color, 255, 255)
    for y in range(0, n, 16):
        for x in range(0, n, 16):
            im.alpha_composite(tile, (x, y))
    d = ImageDraw.Draw(im)
    c = {l: tuple(int(v) for v in ramp(t["gui"], GUI_LUM, l)) for l in (0, 55, 139, 198, 255)}
    acc = {l: tuple(int(v) for v in ramp(t["accent"], ACCENT_LUM, l)) for l in (95, 215, 255)}
    d.rectangle((4, 5, 27, 27), fill=c[0])
    d.rectangle((5, 6, 26, 26), fill=c[198])
    d.line((5, 6, 25, 6), fill=c[255]); d.line((5, 6, 5, 25), fill=c[255])
    d.line((6, 26, 26, 26), fill=c[55]); d.line((26, 7, 26, 26), fill=c[55])
    hue, sat, light = t["heart"]
    r, g, b = colorsys.hls_to_rgb(hue / 360, .62 + light / 3, min(.9 * sat + .1, 1))
    heart = (round(r * 255), round(g * 255), round(b * 255))
    for x, y in [(8, 8), (10, 8), (7, 9), (8, 9), (9, 9), (10, 9), (11, 9), (8, 10), (9, 10), (10, 10), (9, 11)]:
        d.point((x, y), fill=heart)
    d.point((8, 9), fill=(255, 255, 255))
    for row in range(2):
        for col in range(3):
            x0, y0 = 8 + col * 6, 14 + row * 6
            accent = (row, col) == (0, 1)
            dark, mid, light_ = (acc[95], acc[215], acc[255]) if accent else (c[55], c[139], c[255])
            d.rectangle((x0, y0, x0 + 4, y0 + 4), fill=mid)
            d.line((x0, y0, x0 + 4, y0), fill=dark); d.line((x0, y0, x0, y0 + 4), fill=dark)
            d.line((x0 + 1, y0 + 4, x0 + 4, y0 + 4), fill=light_); d.line((x0 + 4, y0 + 1, x0 + 4, y0 + 4), fill=light_)
    return im.resize((128, 128), Image.NEAREST)


# ---------- construcción ----------
def build(theme, version, src):
    gui_src = src / "assets/minecraft/textures/gui"
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

    # Las .mcmeta (cómo se estiran los botones y paneles) se copian tal cual
    extra = {}
    for f in gui_src.rglob("*.png.mcmeta"):
        rel = f"assets/minecraft/textures/gui/{f.relative_to(gui_src).as_posix()}"
        if rel[:-len(".mcmeta")] in files:
            extra[rel] = f.read_bytes()

    desc = f"§bCozy GUI §e✦ §f{theme['name']}\n§7por ccrccne"
    mcmeta = {"pack": {"description": desc, **VERSIONS[version]["mcmeta"]}}
    out = DIST / version / f"cozy-gui-{theme['id']}-{PACK_VERSION}+{version}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps(mcmeta, ensure_ascii=False, indent=4))
        z.write(ROOT / "LICENSE", "LICENSE.txt")
        z.writestr("CREDITOS.txt", "Cozy GUI por ccrccne - https://ccrccne.github.io\n"
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
