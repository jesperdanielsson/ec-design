# Handberäkningar som testfall

Här läggs kompletta exempel ur kurslitteraturen eller egna handberäkningar.
Varje fall är en fil (YAML eller JSON) med:

- `source`: bok, kapitel och sida (t.ex. "Bärande konstruktioner del 1, ex. 4.2, s. 87")
- `input`: indata (geometri, material, laster)
- `expected`: **alla mellanresultat**, inte bara slutsvaret, med tillåten avvikelse

Testet jämför varje mellanresultat mot beräkningsloggen, så att det syns exakt
var programmet och handräkningen skiljer sig åt.
