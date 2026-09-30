#!/usr/bin/env bash
# Erzeugt index.html (Webseite/GitHub Pages, installierbar als App) aus wochenkorb.html (Artifact-Quelle ohne doctype/head/body).
cd "$(dirname "$0")" || exit 1
{
  printf '<!doctype html><html lang="de"><head><meta charset="utf-8">'
  printf '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
  printf '<meta name="theme-color" content="#0b6b5d"><link rel="manifest" href="manifest.webmanifest">'
  printf '<link rel="icon" type="image/png" href="icons/icon-192.png"><link rel="apple-touch-icon" href="icons/apple-touch-icon.png">'
  printf '</head><body>\n'
  cat wochenkorb.html
  printf '\n</body></html>\n'
} > index.html
node -e "const h=require('fs').readFileSync('wochenkorb.html','utf8');new Function(h.split('<script>')[1].split('</script>')[0]);console.log('index.html gebaut, JS-Syntax ok')"
