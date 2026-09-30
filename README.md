# Wochenkorb

Einkaufsliste mit Preisvergleich für Aldi Nord, Lidl, Netto, Kaufland, Combi, Edeka, Rewe und Rossmann.

- Artikel eintippen, auch mehrere auf einmal („2 Milch, Brot, Bier“). Sie landen sortiert in ihren Gängen.
- Für jeden Laden den eigenen Laufweg festlegen, Einkäufe als Tour über mehrere Läden planen und abhaken.
- Kassenbon mit geschätzter Summe, Pfand und Vergleich aller Läden. „Beste Wahl“ findet den günstigsten Laden oder die günstigste Kombination aus zwei Läden.
- Prospekt-Angebote und Preise werden zweimal pro Woche automatisch aktualisiert (GitHub Actions, `scripts/preise_holen.py`).

Die App läuft komplett im Browser und lässt sich auf dem Handy über „Zum Startbildschirm hinzufügen“ wie eine App installieren. Die Einkaufsliste bleibt nur auf dem jeweiligen Gerät gespeichert.

## Daten

| Datei | Inhalt |
|---|---|
| `daten/produkte.json` | Artikel der App mit Richtpreis |
| `daten/basis-preise.json` | online recherchierte Regalpreise (Stand siehe Datei) |
| `daten/zuordnung-aldi.json` | App-Artikel → Aldi-Nord-Produkt, für den wöchentlichen Preisabruf |
| `daten/einstellungen.json` | Postleitzahl für regionale Angebote |
| `daten/preise.json` | fertige Daten für die App, vom Wochenlauf geschrieben |

Alle Preise sind ohne Gewähr. Prospekt-Angebote stammen von marktguru.de und den Seiten der Händler, Regalpreise aus den Online-Auftritten der Händler. Nicht belegte Preise sind geschätzt und in der App ohne ✓ markiert.

## Lokal

```bash
bash bauen.sh                      # index.html aus wochenkorb.html erzeugen
python scripts/preise_holen.py     # Preise und Angebote holen
```
