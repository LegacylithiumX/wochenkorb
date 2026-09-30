#!/usr/bin/env python3
"""Fuehrt die Recherche-Dateien daten/preise-<laden>.json zu daten/basis-preise.json zusammen.

Die Recherche wird von Hand (bzw. von Claude) angestossen; das Ergebnis ist die Grundlage,
auf die scripts/preise_holen.py jede Woche die frischen Angebote setzt.
"""
import datetime as dt
import json
import pathlib

DATEN = pathlib.Path(__file__).resolve().parent.parent / 'daten'
PRODUKTE = {p['id']: p for p in json.loads((DATEN / 'produkte.json').read_text('utf-8'))}
HEUTE = dt.date.today().isoformat()


def uebernehmen(p, e):
    """Nur belastbare Eintraege: nichts Veraltetes, keine Online-Shop-Aufpreise, aehnliche Produkte nur in plausibler Spanne."""
    preis = e.get('preis')
    if not isinstance(preis, (int, float)) or preis <= 0 or e.get('veraltet'):
        return False
    if e.get('quelle_typ') == 'edeka24-onlineshop':  # Versandshop, deutlich teurer als der Markt
        return False
    grenzen = (0.5, 2.0) if e.get('sicher') == 'aehnlich' else (0.3, 3.0)
    return grenzen[0] * p['richtpreis'] <= preis <= grenzen[1] * p['richtpreis']


def main():
    preise, angebote, bericht = {}, [], []
    for datei in sorted(DATEN.glob('preise-*.json')):
        d = json.loads(datei.read_text('utf-8'))
        laden = d.get('laden') or datei.stem.split('-', 1)[1]
        n = 0
        # Online-Shop-Preise (z. B. combi.de) weichen vom Markt ab: nur die Angebote uebernehmen
        nur_shop = 'online' in json.dumps(d.get('preisbasis', ''), ensure_ascii=False).lower()
        for pid, e in ({} if nur_shop else d.get('preise') or {}).items():
            if pid in PRODUKTE and uebernehmen(PRODUKTE[pid], e):
                preise.setdefault(pid, {})[laden] = round(float(e['preis']), 2)
                n += 1
        m = 0
        for a in d.get('angebote') or []:
            if not a.get('preis') or (a.get('bis') or '') < HEUTE:
                continue
            pid = a.get('id') if a.get('id') in PRODUKTE else None
            angebote.append({'laden': laden, 'pid': pid, 'name': a.get('name') or '', 'einheit': a.get('menge') or '',
                             'preis': round(float(a['preis']), 2), 'alt': a.get('alt'), 'ab': a.get('ab'), 'bis': a['bis'],
                             'quelle': a.get('quelle') or '', 'q': 'recherche'})
            m += 1
        bericht.append(f'{laden}: {n} Preise, {m} gueltige Angebote')
    ziel = DATEN / 'basis-preise.json'
    ziel.write_text(json.dumps({'stand': HEUTE, 'preise': preise, 'angebote': angebote}, ensure_ascii=False, indent=1), 'utf-8')
    print('\n'.join(bericht))
    print(f'{ziel.name}: {sum(len(v) for v in preise.values())} Preise fuer {len(preise)} Artikel, {len(angebote)} Angebote')


if __name__ == '__main__':
    main()
