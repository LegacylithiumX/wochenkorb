#!/usr/bin/env python3
"""Baut daten/katalog-erweiterung.json in wochenkorb.html ein (Block DATEN_PLUS),
ergaenzt daten/zuordnung-aldi.json um die Aldi-Produkte der neuen Artikel und erzeugt daten/produkte.json neu.

Aufruf: python scripts/katalog_einbauen.py   (danach bash bauen.sh)
"""
import json
import pathlib
import re
import subprocess

WURZEL = pathlib.Path(__file__).resolve().parent.parent
DATEN = WURZEL / 'daten'


def norm(s):
    s = s.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    katalog = json.loads((DATEN / 'katalog-erweiterung.json').read_text('utf-8'))
    zeilen = [[k['name'], k['einheit'], k['preis'], k.get('flags') or '', k.get('pfand') or 0, k.get('syn') or '', k['kat']] for k in katalog]
    block = '[\n' + ',\n'.join('  ' + json.dumps(z, ensure_ascii=False) for z in zeilen) + '\n]'

    html_pfad = WURZEL / 'wochenkorb.html'
    html = html_pfad.read_text('utf-8')
    neu, n = re.subn(r'/\*KATALOG-ERWEITERUNG\*/.*?/\*ENDE\*/', lambda m: f'/*KATALOG-ERWEITERUNG*/{block}/*ENDE*/', html, flags=re.S)
    if n != 1:
        raise SystemExit('Marke /*KATALOG-ERWEITERUNG*/ ... /*ENDE*/ nicht gefunden')
    html_pfad.write_text(neu, 'utf-8')

    zuordnung_pfad = DATEN / 'zuordnung-aldi.json'
    zuordnung = json.loads(zuordnung_pfad.read_text('utf-8'))
    belegt = {v['slug'] for v in zuordnung.values()}
    dazu = 0
    for k in katalog:
        if not k.get('aldi_slug') or k['aldi_slug'] in belegt:
            continue
        pid = norm(k['name'] + ' ' + k['einheit']).replace(' ', '-')
        zuordnung[pid] = {'slug': k['aldi_slug'], 'seite': k['aldi_seite'], 'faktor': k.get('aldi_faktor') or 1.0}
        belegt.add(k['aldi_slug'])
        dazu += 1
    zuordnung_pfad.write_text(json.dumps(zuordnung, ensure_ascii=False, indent=1), 'utf-8')

    subprocess.run(['node', str(WURZEL / 'scripts' / 'produkte_exportieren.js')], check=True)
    print(f'{len(zeilen)} Artikel eingebaut, {dazu} neue Aldi-Zuordnungen ({len(zuordnung)} gesamt)')


if __name__ == '__main__':
    main()
