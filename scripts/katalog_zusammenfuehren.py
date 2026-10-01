#!/usr/bin/env python3
"""Uebernimmt neue Katalog-Artikel (Format: siehe daten/katalog-erweiterung.json, zusaetzlich Feld "preise")
in daten/katalog-erweiterung.json und ihre echten Ladenpreise in daten/preise-katalog.json (Recherche-Datei fuer
scripts/basis_aus_recherche.py).

Aufruf: python scripts/katalog_zusammenfuehren.py <ausgabe1.json> [<ausgabe2.json> ...]
Danach: python scripts/katalog_einbauen.py && bash bauen.sh && python scripts/basis_aus_recherche.py
"""
import json
import pathlib
import re
import sys

DATEN = pathlib.Path(__file__).resolve().parent.parent / 'daten'
GAENGE = {'Obst', 'Gemüse', 'Brot & Backwaren', 'Milch, Käse & Eier', 'Fleisch, Wurst & Fisch', 'Tiefkühl',
          'Nudeln, Reis & Konserven', 'Öl, Gewürze & Backen', 'Frühstück & Aufstriche', 'Kaffee & Tee', 'Süßigkeiten',
          'Snacks & Knabbern', 'Getränke', 'Drogerie & Hygiene', 'Baby', 'Haushalt & Putzen', 'Tierbedarf'}
LAEDEN = {'aldi', 'lidl', 'netto', 'kaufland', 'combi', 'edeka', 'rewe', 'rossmann'}


def pid(name, einheit):
    s = f'{name} {einheit}'.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip().replace(' ', '-')


def main(dateien):
    katalog_pfad = DATEN / 'katalog-erweiterung.json'
    katalog = json.loads(katalog_pfad.read_text('utf-8'))
    vorhanden = {p['id'] for p in json.loads((DATEN / 'produkte.json').read_text('utf-8'))}
    vorhanden |= {pid(k['name'], k['einheit']) for k in katalog}
    preise_pfad = DATEN / 'preise-katalog.json'
    preise = json.loads(preise_pfad.read_text('utf-8')) if preise_pfad.exists() else {'stand': None, 'preise': {}}
    for datei in dateien:
        neu = doppelt = fehler = echte = 0
        for e in json.loads(pathlib.Path(datei).read_text('utf-8')):
            try:
                assert e['name'] and e['einheit'] and e['kat'] in GAENGE and float(e['preis']) > 0
            except (KeyError, AssertionError, TypeError, ValueError):
                fehler += 1
                continue
            i = pid(e['name'], e['einheit'])
            if i in vorhanden:
                doppelt += 1
                continue
            vorhanden.add(i)
            katalog.append({k: e.get(k) for k in ('name', 'einheit', 'kat', 'preis', 'flags', 'pfand', 'syn', 'aldi_slug', 'aldi_faktor', 'aldi_seite')})
            for laden, p in (e.get('preise') or {}).items():
                if laden in LAEDEN and isinstance(p, dict) and float(p.get('preis') or 0) > 0:
                    preise['preise'].setdefault(i, {})[laden] = {'preis': round(float(p['preis']), 2), 'quelle': p.get('quelle', ''),
                                                                 'datum': p.get('datum', ''), 'sicher': 'exakt'}
                    echte += 1
            neu += 1
        print(f'{pathlib.Path(datei).name}: {neu} neu, {doppelt} Dubletten, {fehler} fehlerhaft, {echte} echte Ladenpreise')
    katalog_pfad.write_text(json.dumps(katalog, ensure_ascii=False, indent=1), 'utf-8')
    preise_pfad.write_text(json.dumps(preise, ensure_ascii=False, indent=1), 'utf-8')
    print(f'Katalog-Erweiterung jetzt {len(katalog)} Artikel')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
