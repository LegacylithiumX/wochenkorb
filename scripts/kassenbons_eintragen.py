#!/usr/bin/env python3
"""Traegt ausgelesene Kassenbons in daten/kassenbon-preise.json ein (oeffentlich, nur Preise).

Eingabe: JSON-Datei mit einer Liste von Bons, so wie Claude sie aus den Fotos abschreibt:
[{"laden": "lidl", "datum": "2026-10-02",
  "posten": [{"text": "MILBONA H-MILCH 1,5%", "preis": 0.99, "pid": "h-milch-1-5-1-l"},
             {"text": "BIO GURKE", "preis": 0.79, "pid": null}]}]
- preis = Preis je Packung (bei "2 x 0,99" also 0.99), nach Rabatt nur wenn der Rabatt fest zum Artikel gehoert
- pid   = Artikel-ID aus daten/produkte.json oder null (landet dann unter "unbekannt")
Nicht uebernommen werden Uhrzeit, Filialadresse, Zahlungsart, Kartennummern, Pfandrueckgabe.

Aufruf: python scripts/kassenbons_eintragen.py <auslese.json>
"""
import datetime as dt
import json
import pathlib
import sys

DATEN = pathlib.Path(__file__).resolve().parent.parent / 'daten'
ZIEL = DATEN / 'kassenbon-preise.json'
PRODUKTE = {p['id']: p for p in json.loads((DATEN / 'produkte.json').read_text('utf-8'))}
LAEDEN = {'aldi', 'lidl', 'netto', 'kaufland', 'combi', 'edeka', 'rewe', 'rossmann'}


def main(pfad):
    bons = json.loads(pathlib.Path(pfad).read_text('utf-8'))
    d = json.loads(ZIEL.read_text('utf-8')) if ZIEL.exists() else {}
    d.setdefault('preise', {})
    d.setdefault('unbekannt', [])
    d.setdefault('bons', [])
    neu = ersetzt = unbekannt = 0
    for bon in bons:
        laden, datum = bon['laden'], bon['datum']
        if laden not in LAEDEN:
            raise SystemExit(f'Unbekannter Laden: {laden}')
        dt.date.fromisoformat(datum)  # wirft bei falschem Datum
        for p in bon.get('posten', []):
            preis = p.get('preis')
            if not isinstance(preis, (int, float)) or preis <= 0:
                continue
            pid = p.get('pid')
            if pid in PRODUKTE:
                alt = d['preise'].get(pid, {}).get(laden)
                if alt and alt['datum'] > datum:
                    continue  # es gibt schon einen neueren Bon
                ersetzt += bool(alt)
                neu += not alt
                d['preise'].setdefault(pid, {})[laden] = {'preis': round(float(preis), 2), 'datum': datum, 'text': p.get('text', '')}
            else:
                d['unbekannt'].append({'laden': laden, 'datum': datum, 'text': p.get('text', ''), 'preis': round(float(preis), 2)})
                unbekannt += 1
        d['bons'].append({'laden': laden, 'datum': datum, 'posten': len(bon.get('posten', []))})
    d['unbekannt'] = d['unbekannt'][-400:]
    d['stand'] = max((b['datum'] for b in d['bons']), default=None)
    ZIEL.write_text(json.dumps(d, ensure_ascii=False, indent=1), 'utf-8')
    print(f'{len(bons)} Bons: {neu} neue Preise, {ersetzt} aktualisiert, {unbekannt} Posten ohne App-Artikel')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
