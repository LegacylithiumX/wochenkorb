// Schreibt daten/produkte.json aus DATEN und DATEN_PLUS in wochenkorb.html (Grundlage fuer die Python-Skripte).
// Aufruf: node scripts/produkte_exportieren.js
const fs = require('fs');
const path = require('path');
const wurzel = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(wurzel, 'wochenkorb.html'), 'utf8');
const teil = (von, bis) => html.slice(html.indexOf(von), html.indexOf(bis));
const DATEN = new Function(teil('const DATEN = {', '// Erweiterter Katalog') + ';return DATEN;')();
const DATEN_PLUS = JSON.parse(html.match(/\/\*KATALOG-ERWEITERUNG\*\/([\s\S]*?)\/\*ENDE\*\//)[1]);
const norm = s => String(s).toLowerCase().replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss').replace(/[^a-z0-9]+/g, ' ').trim();
const alle = [
  ...Object.keys(DATEN).flatMap(kat => DATEN[kat].map(e => [e[0], e[1], e[2], e[3] || '', e[4] || 0, e[5] || '', kat])),
  ...DATEN_PLUS
];
const out = alle.map(([name, einheit, preis, fl, pfand, syn, kat]) => ({
  id: norm(name + ' ' + einheit).replace(/ /g, '-'), name, einheit, kat, richtpreis: preis, marke: fl.includes('m'), syn
}));
const ids = new Set();
for (const p of out) { if (ids.has(p.id)) throw new Error('doppelte ID ' + p.id); ids.add(p.id); }
fs.writeFileSync(path.join(wurzel, 'daten', 'produkte.json'), JSON.stringify(out, null, 1));
console.log(out.length, 'Produkte nach daten/produkte.json');
