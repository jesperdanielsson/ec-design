# CLAUDE.md

Instruktioner för Claude Code (och andra AI-verktyg, se `AGENTS.md`) i det här repot.

## Mål

Ett vackert, intuitivt och lärorikt dimensioneringsprogram enligt Eurokoderna med svenska
nationella val (EKS). Första konstruktionsdelen är **armerad betongbalk** (EN 1992-1-1).
Senare: plattor, grunder, kantbalkar, trappor, väggar; stål, trä och tegel.

Grundprincip: en junior konstruktör ska tycka att programmet är tydligare än befintliga
program, och varje resultat ska gå att jämföra siffra för siffra mot en handberäkning.

## Arkitektur

```
src/ecdesign/
  core/               Python, ren beräkning. Vet ingenting om GUI.
    units.py          pint: alla fysiska storheter är Q_-storheter
    calclog.py        CalcLog/CalcStep: formel, insatta värden, resultat, normref
    national/         nationella val som TOML-data (eks.toml, recommended.toml)
    materials/        betong (tabell 3.1, σ-ε), armering
    loads/            lastfall, laster (kombinationer: steg 3)
    analysis/         snittkrafter (fritt upplagd balk än så länge)
    members/beam/     betongbalkens kontroller (steg 5–6)
  api/                tunt lager kärna -> GUI, returnerar JSON-vänliga dict:ar
  app.py              skrivbordsappen (pywebview)
  devserver.py        HTTP-brygga för GUI-utveckling i webbläsare
  report/, export/    platshållare (steg 9–10)
ui/                   React + TypeScript + three.js (Vite)
tests/                pytest; tests/handcalcs/ för handberäkningsfall
```

Flöde: GUI -> `window.pywebview.api.<metod>` (eller `POST /api/<metod>` via devserver)
-> `ecdesign.api.Api` -> `core`. Svaret innehåller alltid beräkningsloggen.

## Regler

1. **Kärnan importerar aldrig** `api`, `app`, `report`, `export` eller GUI-bibliotek.
   `tests/test_architecture.py` kontrollerar detta.
2. **Allt loggas.** Varje beräkningssteg går genom `CalcLog.step(...)` med symbol, kort
   svensk beskrivning, formel i LaTeX, insatta värden, resultat och normhänvisning
   (t.ex. `EN 1992-1-1 6.2.2(1)`). Rapport, GUI-förklaringar och tester läser samma logg.
3. **Enheter:** alltid pint-storheter (`Q_`) för fysiska värden i kärnan, aldrig nakna
   floats. Dimensionslösa tal (töjning i ‰, koefficienter) får vara float, och enheten ska
   då stå i namnet eller docstringen. API-lagret översätter till tal i fasta enheter
   (mm, m, kN, kNm, MPa, GPa) och enheten står i fältnamnet.
4. **Nationella val är data.** Partialkoefficienter, ψ-faktorer, γ_d osv. läses från
   `core/national/data/*.toml` via `national.load("eks")`. Hårdkoda dem aldrig i formler.
   Varje värde i TOML-filen har en källkommentar.
5. **Normreferens i docstring:** varje beräkningsfunktion anger paragraf/tabell/ekvation.
6. **Testkrav:** ingen ny beräkning utan ett testfall från normtabell, handberäkning
   eller lärobok, med källa i testet. Testa mellanresultat (`log.find(symbol)`), inte
   bara slutsvaret.
7. **Språk:** kod, variabel- och funktionsnamn på engelska. GUI-texter, loggbeskrivningar,
   rapport och felmeddelanden till användaren på svenska. Symboler som i normen
   (`fck`, `fctm`, `eps_cu2`, `gamma_c`).
8. **LaTeX i loggen:** svenskt decimalkomma (`0{,}30`), sköts av `calclog._fmt`.

## Kommandon

```bash
# Python (en gång)
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev,app]"

pytest                      # alla tester
ruff check . && ruff format .

# Gränssnitt (en gång)
cd ui && npm install

# Utveckla gränssnittet i webbläsaren (två terminaler)
python -m ecdesign.devserver          # API-brygga på :8765
cd ui && npm run dev                  # http://localhost:5173

# Skrivbordsappen
cd ui && npm run build && cd ..
ecdesign                               # öppnar fönstret med ui/dist
ecdesign --dev                         # laddar Vite-servern i stället (hot reload)

cd ui && npm run typecheck            # TypeScript-kontroll
```

## Arbetsflöde per funktion

1. Lägg in handberäkningen som testfall (källa och sida) i `tests/`.
2. Planera: vilken paragraf gäller och varför?
3. Skriv koden mot testet. Granska beräkningsloggen, inte bara att testet är grönt.
4. En commit och en pull request per funktion.

## Plan (stegvis)

1. ✅ Grund: struktur, enheter, beräkningslogg, testfall, GUI-skelett med menyn.
2. Material och nationella val: hela tabell 3.1, vct per exponeringsklass, kryptal och
   krympning (bilaga B), armering.
3. Laster och lastkombinationer (6.10a/b med γ_d, bruks: karakteristisk/frekvent/kvasipermanent).
4. Snittkrafter: konsol, kontinuerliga balkar, punktlaster; M-, V- och nedböjningskurvor.
5. Brottgräns: böjning (enkel/dubbel, T-tvärsnitt), tvärkraft 6.2.2/6.2.3, minimiarmering.
6. Bruksgräns: spänningsbegränsning, sprickor 7.3.2/7.3.4, nedböjning.
7. GUI v1 med direkt uppdatering. 8. 3D med byglar. 9. Rapport (HTML/KaTeX -> PDF). 10. Export.

## GUI-principer

Menyn är ett flöde i fyra steg (Geometri och tvärsnitt, Material, Laster, Analys och
resultat) med bock när steget är komplett. Varje fält har en kort förklaring med
normhänvisning vid hovring. Panelen "Lösningsgång" till höger visar beräkningsloggen
för aktuellt steg med KaTeX.
