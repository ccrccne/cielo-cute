"""Tarjetas de vista previa de cada variante, armadas con las texturas reales del paquete (26.3).

Uso: python preview.py  -> images/variantes/<tema>.png y images/variantes.png (todas juntas)
No son capturas del juego: muestran el inventario, la barra, los corazones, el sol y la luna del paquete.
"""
import io
import pathlib
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build import DIST, PACK_VERSION
from themes import COLLECTIONS, THEMES

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "images/variantes"
FONT = "C:/Windows/Fonts/segoeuib.ttf"
FONT_R = "C:/Windows/Fonts/segoeui.ttf"


def tex(z, rel):
    return Image.open(io.BytesIO(z.read(f"assets/minecraft/textures/{rel}"))).convert("RGBA")


def additive_on(bg, im, pos):
    """El sol y la luna se suman al cielo, como en el juego."""
    a = np.asarray(bg).astype(np.int32)
    s = np.asarray(im.convert("RGB")).astype(np.int32)
    x, y = pos
    h, w = s.shape[:2]
    a[y:y + h, x:x + w, :3] = np.clip(a[y:y + h, x:x + w, :3] + s, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def card(t):
    z = zipfile.ZipFile(DIST / "26.3" / f"cielo-cute-{t['id']}-{PACK_VERSION}+26.3.zip")
    W, H = 1280, 720
    top, bottom = np.array(t["menu"][0], np.float32) * .55, np.array(t["gui"][2], np.float32)
    grad = top + (bottom - top) * np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    im = Image.fromarray(np.repeat(grad, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
    # fondo de menú repetido, como se ve detrás de las pantallas
    tile = tex(z, "gui/menu_background.png").resize((64, 64), Image.NEAREST)
    layer = Image.new("RGBA", (W, H))
    for y in range(0, H, 64):
        for x in range(0, W, 64):
            layer.alpha_composite(tile, (x, y))
    im.alpha_composite(layer)
    # sol y luna
    im = additive_on(im, tex(z, "environment/celestial/sun.png").transpose(Image.FLIP_TOP_BOTTOM).resize((160, 160), Image.NEAREST), (930, 70))
    for k, p in enumerate(["waxing_crescent", "first_quarter", "full_moon", "third_quarter"]):
        im = additive_on(im, tex(z, f"environment/celestial/moon/{p}.png").resize((64, 64), Image.NEAREST), (880 + k * 72, 270))
    # inventario
    inv = tex(z, "gui/container/inventory.png").crop((0, 0, 176, 166)).resize((528, 498), Image.NEAREST)
    im.alpha_composite(inv, (70, 150))
    # barra rápida, casilla seleccionada y corazones
    hotbar = tex(z, "gui/sprites/hud/hotbar.png").resize((546, 66), Image.NEAREST)
    im.alpha_composite(hotbar, (660, 600))
    sel = tex(z, "gui/sprites/hud/hotbar_selection.png").resize((72, 69), Image.NEAREST)
    im.alpha_composite(sel, (657 + 3 * 60, 597))
    heart = tex(z, "gui/sprites/hud/heart/full.png").resize((27, 27), Image.NEAREST)
    half = tex(z, "gui/sprites/hud/heart/half.png").resize((27, 27), Image.NEAREST)
    for k in range(10):
        im.alpha_composite(heart if k < 8 else half, (660 + k * 26, 560))
    button = tex(z, "gui/sprites/widget/button.png").resize((400, 40), Image.NEAREST)
    im.alpha_composite(button, (760, 470))
    d = ImageDraw.Draw(im)
    f_btn = ImageFont.truetype(FONT, 20)
    d.text((960, 490), "Volver al juego", font=f_btn, fill="white", anchor="mm", stroke_width=1, stroke_fill=(40, 40, 40))
    # textos
    col = COLLECTIONS[t["collection"]][0]
    d.text((70, 44), t["name"], font=ImageFont.truetype(FONT, 54), fill="white", stroke_width=2, stroke_fill=tuple(int(v * .5) for v in t["menu"][0]))
    d.text((72, 108), f"Cielo cute · {col}", font=ImageFont.truetype(FONT_R, 24), fill=(255, 255, 255, 220))
    icon = Image.open(io.BytesIO(z.read("pack.png"))).convert("RGBA").resize((96, 96), Image.NEAREST)
    im.alpha_composite(icon, (W - 126, H - 236))
    return im.convert("RGB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cards = []
    for t in THEMES:
        c = card(t)
        c.save(OUT / f"{t['id']}.png", optimize=True)
        cards.append(c.resize((426, 240), Image.LANCZOS))
    cols = 3
    sheet = Image.new("RGB", (cols * 426 + (cols + 1) * 12, ((len(cards) + cols - 1) // cols) * 252 + 12), (24, 28, 48))
    for i, c in enumerate(cards):
        sheet.paste(c, (12 + (i % cols) * 438, 12 + (i // cols) * 252))
    sheet.save(ROOT / "images/variantes.png", optimize=True)
    print(len(cards), "tarjetas")
