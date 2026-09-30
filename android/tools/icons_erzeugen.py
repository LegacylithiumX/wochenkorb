"""Erzeugt die Launcher-Icons der Android-Huelle aus icons/maskable-512.png und icons/icon-512.png.

Aufruf (aus dem Repo-Wurzelordner oder android/):  python android/tools/icons_erzeugen.py
- adaptiv: Vordergrund = weisser Korb mit Alpha (aus maskable-512), Hintergrund = Farbe #0b6b5d (colors.xml)
- Fallback (API 24/25): ic_launcher.png (quadratisch) und ic_launcher_round.png (Kreis) aus icon-512
"""
from pathlib import Path

from PIL import Image, ImageDraw

WURZEL = Path(__file__).resolve().parents[2]
RES = WURZEL / "android" / "app" / "src" / "main" / "res"
HINTERGRUND = (11, 107, 93)

# Dichte -> (Kantenlaenge Fallback-Icon 48dp, Kantenlaenge Vordergrund 108dp)
DICHTEN = {
    "mdpi": (48, 108),
    "hdpi": (72, 162),
    "xhdpi": (96, 216),
    "xxhdpi": (144, 324),
    "xxxhdpi": (192, 432),
}
SICHERE_ZONE_DP = 66  # adaptive Icons: innerer Kreis, der auf jeder Maske sichtbar bleibt
EBENE_DP = 108
MASTER = 1728  # 108dp * 16, danach verlustarm herunterrechnen


def korb_mit_alpha(pfad: Path) -> Image.Image:
    """Weisser Korb mit Alpha: Deckkraft = Abstand der Pixelfarbe von der Hintergrundfarbe."""
    bild = Image.open(pfad).convert("RGB")
    alpha = Image.new("L", bild.size)
    daten = []
    for r, g, b in bild.getdata():
        t = sum((c - h) / (255 - h) for c, h in zip((r, g, b), HINTERGRUND)) / 3
        daten.append(max(0, min(255, round(t * 255))))
    alpha.putdata(daten)
    ebene = Image.new("RGBA", bild.size, (255, 255, 255, 0))
    ebene.putalpha(alpha)
    return ebene


def vordergrund_master() -> Image.Image:
    korb = korb_mit_alpha(WURZEL / "icons" / "maskable-512.png")
    alpha = korb.getchannel("A")
    kasten = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    mitte = (korb.width / 2, korb.height / 2)
    # Groesster Abstand eines sichtbaren Pixels von der Bildmitte (in Quellpixeln)
    maxr = 0.0
    breite = alpha.width
    for i, v in enumerate(alpha.getdata()):
        if v > 40:
            x, y = i % breite, i // breite
            maxr = max(maxr, ((x - mitte[0]) ** 2 + (y - mitte[1]) ** 2) ** 0.5)
    # Korb so gross wie moeglich, aber vollstaendig im sicheren Kreis (mit 1dp Reserve), hoechstens 1,15-fach
    dp_pro_px = EBENE_DP / korb.width
    zoom = min(1.15, (SICHERE_ZONE_DP / 2 - 1) / (maxr * dp_pro_px))
    kante = round(MASTER * zoom)
    skaliert = korb.resize((kante, kante), Image.LANCZOS)
    if kante >= MASTER:  # Rand abschneiden (enthaelt nur Transparenz)
        versatz = (kante - MASTER) // 2
        ebene = skaliert.crop((versatz, versatz, versatz + MASTER, versatz + MASTER))
    else:
        ebene = Image.new("RGBA", (MASTER, MASTER), (255, 255, 255, 0))
        ebene.alpha_composite(skaliert, ((MASTER - kante) // 2, (MASTER - kante) // 2))
    print(f"Korb-Kasten {kasten}, maxr {maxr:.0f}px, zoom {zoom:.3f}, Ebene {kante}px")
    return ebene


def rund(bild: Image.Image) -> Image.Image:
    maske = Image.new("L", (bild.width * 4, bild.height * 4), 0)
    ImageDraw.Draw(maske).ellipse((0, 0, maske.width - 1, maske.height - 1), fill=255)
    maske = maske.resize(bild.size, Image.LANCZOS)
    ergebnis = bild.convert("RGBA")
    ergebnis.putalpha(maske)
    return ergebnis


def main() -> None:
    master = vordergrund_master()
    legacy = Image.open(WURZEL / "icons" / "icon-512.png").convert("RGBA")
    for dichte, (legacy_px, vorder_px) in DICHTEN.items():
        ordner = RES / f"mipmap-{dichte}"
        ordner.mkdir(parents=True, exist_ok=True)
        master.resize((vorder_px, vorder_px), Image.LANCZOS).save(ordner / "ic_launcher_foreground.png", optimize=True)
        klein = legacy.resize((legacy_px, legacy_px), Image.LANCZOS)
        klein.save(ordner / "ic_launcher.png", optimize=True)
        rund(klein).save(ordner / "ic_launcher_round.png", optimize=True)

    adaptiv = RES / "mipmap-anydpi-v26"
    adaptiv.mkdir(parents=True, exist_ok=True)
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background" />\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
        '    <monochrome android:drawable="@mipmap/ic_launcher_foreground" />\n'
        "</adaptive-icon>\n"
    )
    (adaptiv / "ic_launcher.xml").write_text(xml, encoding="utf-8")
    (adaptiv / "ic_launcher_round.xml").write_text(xml, encoding="utf-8")

    # Vorschau (nicht im Projekt): Vordergrund auf Hintergrund, Kreis- und Rundmaske 72dp von 108dp
    vorschau = Image.new("RGBA", (432 * 3, 432), (255, 255, 255, 255))
    flaeche = Image.new("RGBA", (432, 432), HINTERGRUND + (255,))
    flaeche.alpha_composite(master.resize((432, 432), Image.LANCZOS))
    vorschau.paste(flaeche, (0, 0))
    kreis = Image.new("L", (432, 432), 0)
    ImageDraw.Draw(kreis).ellipse((72, 72, 360, 360), fill=255)  # 72dp-Maske = 288px
    zweit = Image.new("RGBA", (432, 432), (255, 255, 255, 255))
    zweit.paste(flaeche, (0, 0), kreis)
    vorschau.paste(zweit, (432, 0))
    sicher = flaeche.copy()
    ImageDraw.Draw(sicher).ellipse((216 - 132, 216 - 132, 216 + 132, 216 + 132), outline=(255, 0, 0, 255), width=2)
    vorschau.paste(sicher, (864, 0))
    vorschau.convert("RGB").save(Path(__file__).with_name("_vorschau.png"))
    print("Icons geschrieben nach", RES)


if __name__ == "__main__":
    main()
