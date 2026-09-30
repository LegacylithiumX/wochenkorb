#!/usr/bin/env python3
"""Wochenkorb: holt Prospekt-Angebote und Regalpreise und schreibt daten/preise.json.

Laeuft zweimal pro Woche per GitHub Actions (.github/workflows/preise.yml).
Lokal testen:  python scripts/preise_holen.py

Quellen
  - Regalpreise: daten/basis-preise.json (online recherchiert), ueberschrieben von frisch geholten Preisen
  - Prospekt-Angebote: marktguru (Lidl, Kaufland, Rewe, Combi, Netto, Rossmann) und Laden-Seiten
Faellt eine Quelle aus, bleiben ihre Daten aus dem letzten Lauf erhalten, solange sie noch gueltig sind.
"""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
from zoneinfo import ZoneInfo

import requests

WURZEL = pathlib.Path(__file__).resolve().parent.parent
DATEN = WURZEL / 'daten'
ZIEL = DATEN / 'preise.json'
BERLIN = ZoneInfo('Europe/Berlin')
HEUTE = dt.datetime.now(BERLIN).date()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'

SITZUNG = requests.Session()
SITZUNG.headers.update({'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9'})

PRODUKTE = json.loads((DATEN / 'produkte.json').read_text('utf-8'))
PMAP = {p['id']: p for p in PRODUKTE}
EINST = json.loads((DATEN / 'einstellungen.json').read_text('utf-8'))
LAEDEN = ['aldi', 'lidl', 'netto', 'kaufland', 'combi', 'edeka', 'rewe', 'rossmann']


def log(*teile):
    print(*teile, flush=True)


def norm(s):
    s = (s or '').lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


EINHEIT = {'kg': (1.0, 'kg'), 'g': (0.001, 'kg'), 'l': (1.0, 'l'), 'ml': (0.001, 'l')}


def menge(text):
    """'500 g' -> (0.5, 'kg'), '6 × 1,5 l' -> (9.0, 'l'), '10 Stück' -> (10.0, 'st'), 'Stück' -> (1.0, 'st')."""
    t = (text or '').lower().replace(',', '.')
    m = re.search(r'(?:(\d+)\s*[x×]\s*)?(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b', t)
    if m:
        f, e = EINHEIT[m.group(3)]
        return int(m.group(1) or 1) * float(m.group(2)) * f, e
    m = re.search(r'(\d+)\s*(stück|stk|rollen|beutel|päckchen|wl|pads|tabs)', t)
    if m:
        return float(m.group(1)), 'st'
    if 'stück' in t:
        return 1.0, 'st'
    return None


def pflichtwoerter(p):
    """Woerter aus dem Produktnamen, die in einem Angebot vorkommen muessen."""
    return [w for w in norm(p['name']).split() if len(w) >= 3 or w.isdigit()]


def lokales_datum(iso):
    return dt.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(BERLIN).date().isoformat()


# ---------------------------------------------------------------- marktguru

MG_HAENDLER = {'lidl': 'lidl', 'kaufland': 'kaufland', 'rewe': 'rewe', 'rewe center': 'rewe', 'combi': 'combi',
               'netto marken discount': 'netto', 'rossmann': 'rossmann', 'edeka': 'edeka', 'e center': 'edeka',
               'aldi nord': 'aldi'}


def mg_kopf():
    html = SITZUNG.get('https://www.marktguru.de/', timeout=25).text
    ak = re.search(r'"apiKey":"([^"]+)"', html)
    ck = re.search(r'"clientKey":"([^"]+)"', html)
    if not ak or not ck:
        raise RuntimeError('marktguru: Schluessel nicht gefunden')
    return {'x-apikey': ak.group(1), 'x-clientkey': ck.group(1), 'Origin': 'https://www.marktguru.de'}


def suchbegriffe():
    begriffe = set()
    for p in PRODUKTE:
        begriffe.add(re.sub(r'[^\wäöüÄÖÜß-]', '', p['name'].split()[0]))
        if p.get('syn'):
            begriffe.add(p['syn'].split()[0])
    return sorted(b for b in begriffe if len(b) >= 3)


LOSE_WARE = {'Obst', 'Gemüse', 'Fleisch, Wurst & Fisch'}  # wird oft je kg beworben, darf umgerechnet werden


ENDUNGEN = {'e', 'n', 'en', 'er', 's', 'es', 'ner', 'ener', 'chen'}


def passt_wort(w, woerter):
    """Deutsche Komposita: das Grundwort steht hinten (Tafel|aepfel = Aepfel, Tomaten|mark != Tomaten).
    Ein Wortanfang zaehlt daher nur mit harmloser Endung (Pils -> Pilsener)."""
    if w in woerter:
        return True
    if len(w) < 4:
        return False
    return any(x.endswith(w) or (x.startswith(w) and x[len(w):] in ENDUNGEN) for x in woerter)


def passt_produkt(pflicht, woerter):
    zusammen = ''.join(w for w in pflicht if not w.isdigit())
    if zusammen in woerter or any(x.endswith(zusammen) for x in woerter if len(zusammen) >= 6):
        return all(w in woerter for w in pflicht if w.isdigit())  # Butter-Croissant -> Buttercroissant
    return all(passt_wort(w, woerter) for w in pflicht)


def preis_fuer(p, groesse, preis, einheit_preis):
    """Preis des Angebots fuer die Packung der App, oder None wenn die Packung nicht vergleichbar ist."""
    unsere = menge(p['einheit'])
    lose = p['kat'] in LOSE_WARE and einheit_preis and unsere and einheit_preis[1] == unsere[1]
    if unsere is None or unsere == (1.0, 'st'):
        return preis if groesse is None or groesse[1] != 'kg' else None
    if groesse and groesse[1] == unsere[1] and 0.85 <= groesse[0] / unsere[0] <= 1.18:
        return preis
    return round(einheit_preis[0] * unsere[0], 2) if lose else None


def passendes_produkt(name_text, groesse, preis, einheit_preis):
    """Ordnet ein Angebot einem Produkt der App zu (nur ueber Produktname und Marke, nicht die Beschreibung).
    Gibt (produkt, preis_fuer_app_packung) oder (None, None)."""
    woerter = set(name_text.split())
    beste = None
    for p in PRODUKTE:
        pflicht = pflichtwoerter(p)
        if not pflicht or not passt_produkt(pflicht, woerter):
            continue
        umgerechnet = preis_fuer(p, groesse, preis, einheit_preis)
        if umgerechnet is None or not 0.4 * p['richtpreis'] <= umgerechnet <= 1.4 * p['richtpreis']:
            continue
        if beste is None or len(pflicht) > beste[2]:
            beste = (p, umgerechnet, len(pflicht))
    return (beste[0], beste[1]) if beste else (None, None)


def angebote_marktguru():
    cache = WURZEL / '_cache_marktguru.json'  # nur lokal zum Testen: WOCHENKORB_CACHE=1
    if os.environ.get('WOCHENKORB_CACHE') and cache.exists():
        roh = json.loads(cache.read_text('utf-8'))
    else:
        roh = mg_abrufen()
        if os.environ.get('WOCHENKORB_CACHE'):
            cache.write_text(json.dumps(roh), 'utf-8')
    return mg_auswerten(roh)


def mg_abrufen():
    kopf = mg_kopf()
    plz = EINST.get('plz', '26122')
    roh = {}
    for begriff in suchbegriffe():
        try:
            r = SITZUNG.get('https://api.marktguru.de/api/v1/offers/search', headers=kopf, timeout=25,
                            params={'as': 'web', 'limit': 100, 'offset': 0, 'q': begriff, 'zipCode': plz})
            r.raise_for_status()
            for o in r.json().get('results', []):
                roh[o['id']] = o
        except Exception as e:  # einzelner Begriff darf fehlschlagen
            log('  marktguru', begriff, 'Fehler:', e)
        time.sleep(0.25)
    log(f'  marktguru: {len(roh)} Angebote roh')
    return roh


def mg_auswerten(roh):
    angebote = []
    for o in roh.values():
        laeden = {MG_HAENDLER.get(norm(a.get('name'))) for a in o.get('advertisers') or []} - {None}
        if not laeden or not o.get('price') or not o.get('validityDates'):
            continue
        g = o['validityDates'][0]
        ab, bis = lokales_datum(g['from']), lokales_datum(g['to'])
        if bis < HEUTE.isoformat():
            continue
        produkt = (o.get('product') or {}).get('name') or ''
        marke = (o.get('brand') or {}).get('name') or ''
        if 'nobrand' in marke.lower():  # Platzhalter von marktguru fuer lose Ware
            marke = ''
        beschreibung = o.get('description') or ''
        text = norm(f'{produkt} {marke}')
        groesse = menge(beschreibung) or menge(produkt)
        einheit = (o.get('unit') or {}).get('shortName')
        einheit_preis = (o['referencePrice'], einheit) if o.get('referencePrice') and einheit in ('kg', 'l') else None
        if o.get('requiresLoyalityMembership'):
            beschreibung = (beschreibung + ' (nur mit Kundenkarte/App)').strip()
        p, preis = passendes_produkt(text, groesse, float(o['price']), einheit_preis)
        name = f'{marke} {produkt}'.strip() if marke and norm(marke) not in norm(produkt) else produkt
        for laden in laeden:
            angebote.append({
                'laden': laden, 'pid': p['id'] if p else None, 'name': name or beschreibung[:60],
                'einheit': p['einheit'] if p else re.sub(r'\s+', ' ', beschreibung)[:60],
                'preis': round(preis if p else float(o['price']), 2),
                'alt': round(float(o['oldPrice']) * (preis / float(o['price']) if p else 1), 2) if o.get('oldPrice') else None,
                'ab': ab, 'bis': bis, 'quelle': o.get('externalUrl') or '', 'q': 'marktguru'})
    return angebote


# ---------------------------------------------------------------- Aldi Nord

def aldi_treffer(seite):
    """Aldi Nord bettet die Artikel einer Sortimentsseite als JSON (__NEXT_DATA__) ein."""
    for versuch in range(3):  # der Aldi-Server antwortet zeitweise mit 502/504 oder gar nicht
        try:
            r = SITZUNG.get(f'https://www.aldi-nord.de{seite}.html', timeout=15)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(3 * (versuch + 1))
    else:
        raise RuntimeError(f'Aldi: {seite} nicht erreichbar')
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise RuntimeError(f'Aldi: keine Daten auf {seite}')
    pp = json.loads(m.group(1))['props']['pageProps']
    for idx in ((pp.get('algoliaState') or {}).get('initialResults') or {}).values():
        for r in idx.get('results') or []:
            yield from r.get('hits') or []


def aldi_datum(pr, feld):
    lokal = pr.get(feld + 'LocalDate')
    if lokal:
        return lokal
    ts = pr.get(feld)
    return dt.datetime.fromtimestamp(ts, BERLIN).date().isoformat() if ts else None


def aldi_nord():
    """Regalpreise der zugeordneten Artikel (daten/zuordnung-aldi.json) und alle Aktionen auf diesen Seiten."""
    zuordnung = json.loads((DATEN / 'zuordnung-aldi.json').read_text('utf-8'))
    nach_slug = {v['slug']: (pid, v['faktor']) for pid, v in zuordnung.items()}
    treffer, fehler, in_folge = {}, 0, 0
    for seite in sorted({v['seite'] for v in zuordnung.values()}):
        try:
            for h in aldi_treffer(seite):
                treffer[h.get('productSlug')] = h
            in_folge = 0
        except Exception as e:
            fehler += 1
            in_folge += 1
            log('  Aldi', seite, 'Fehler:', e)
            if in_folge >= 4:  # Server haengt: abbrechen, fehlende Artikel behalten ihren letzten Preis
                log('  Aldi: 4 Seiten in Folge ohne Antwort, Abbruch')
                break
        time.sleep(0.4)
    if not treffer:
        raise RuntimeError('Aldi: keine Seite lesbar')
    log(f'  Aldi Nord: {len(treffer)} Artikel gelesen, {fehler} Seiten mit Fehler')

    preise, angebote = {}, []
    for slug, h in treffer.items():
        pid, faktor = nach_slug.get(slug, (None, 1.0))
        cp = h.get('currentPrice') or {}
        regulaer = (cp.get('strikePrice') or {}).get('strikePriceValue') or cp.get('priceValue')
        if pid and regulaer and h.get('isAvailable', True):
            preise[pid] = {'aldi': round(regulaer * faktor, 2)}
        for pr in h.get('promotionPrices') or []:
            alt = (pr.get('strikePrice') or {}).get('strikePriceValue')
            bis, ab = aldi_datum(pr, 'validUntil'), aldi_datum(pr, 'validFrom')
            if not alt or not pr.get('priceValue') or not bis or bis < HEUTE.isoformat():
                continue
            angebote.append({
                'laden': 'aldi', 'pid': pid, 'name': h.get('name') or slug,
                'einheit': PMAP[pid]['einheit'] if pid else (h.get('salesUnit') or ''),
                'preis': round(pr['priceValue'] * faktor, 2), 'alt': round(alt * faktor, 2), 'ab': ab, 'bis': bis,
                'quelle': f'https://www.aldi-nord.de/produkt/{slug}.html', 'q': 'aldi'})
    return preise, angebote


# ---------------------------------------------------------------- Zusammenfuehren

def marktguru():
    return {}, angebote_marktguru()


# Quelle -> (Abruf, Laeden deren Angebote sie vollstaendig abdeckt)
QUELLEN = {
    'aldi': (aldi_nord, {'aldi'}),
    'marktguru': (marktguru, {'lidl', 'kaufland', 'rewe', 'combi', 'netto', 'rossmann'}),
}

def lade_json(pfad, standard):
    try:
        return json.loads(pfad.read_text('utf-8'))
    except Exception:
        return standard


def main():
    vorher = lade_json(ZIEL, {})
    basis = lade_json(DATEN / 'basis-preise.json', {'preise': {}})
    preise = {pid: dict(v) for pid, v in basis.get('preise', {}).items() if pid in PMAP}
    status = {}

    angebote, live = [], set()
    for name, (holen, laeden) in QUELLEN.items():
        try:
            neue_preise, neu = holen()
            for pid, je_laden in neue_preise.items():
                preise.setdefault(pid, {}).update(je_laden)
            angebote += neu
            live |= laeden
            status[name] = f'ok, {sum(len(v) for v in neue_preise.values())} Preise, {len(neu)} Angebote'
        except Exception as e:
            # Quelle ausgefallen: Preise des letzten Laufs behalten, noch gueltige Angebote auch
            for pid, je_laden in (vorher.get('preise') or {}).items():
                for laden in laeden & set(je_laden):
                    preise.setdefault(pid, {})[laden] = je_laden[laden]
            alt = [a for a in vorher.get('angebote', []) if a.get('q') == name and a.get('bis', '') >= HEUTE.isoformat()]
            angebote += alt
            status[name] = f'Fehler ({e}), {len(alt)} alte Angebote behalten'
        log(f'{name}: {status[name]}')
    # Recherche-Angebote nur fuer Laeden ohne erfolgreiche Live-Quelle (z. B. Edeka)
    angebote += [a for a in basis.get('angebote', []) if a['laden'] not in live and (a.get('bis') or '') >= HEUTE.isoformat()]

    # doppelte Angebote (gleicher Laden, Name, Preis) entfernen
    gesehen, eindeutig = set(), []
    for a in sorted(angebote, key=lambda a: (a['pid'] is None, a['laden'], a['name'])):
        k = (a['laden'], norm(a['name']), a['preis'], a['pid'])
        if k not in gesehen:
            gesehen.add(k)
            eindeutig.append(a)

    ergebnis = {'stand': HEUTE.isoformat(), 'plz': EINST.get('plz'), 'quellen': status,
                'preise': preise, 'angebote': eindeutig}
    ZIEL.write_text(json.dumps(ergebnis, ensure_ascii=False, separators=(',', ':')), 'utf-8')
    zugeordnet = sum(1 for a in eindeutig if a['pid'])
    log(f'geschrieben: {ZIEL.name} mit {sum(len(v) for v in preise.values())} Regalpreisen, '
        f'{len(eindeutig)} Angeboten ({zugeordnet} einem App-Artikel zugeordnet)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
