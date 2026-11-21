# EC Design

Dimensioneringsprogram enligt Eurokoderna med svenska nationella val (EKS).
Fokus: tydligt arbetsflöde, visuella vyer och en lösningsgång som går att jämföra med
handberäkning, steg för steg med normhänvisning.

Första delen: **armerade betongbalkar** (EN 1992-1-1).

## Kom igång

Kräver Python 3.12+ och Node 20+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,app]"
pytest

cd ui
npm install
npm run build
cd ..
ecdesign                           # startar skrivbordsappen
```

Utveckla gränssnittet i webbläsaren med `python -m ecdesign.devserver` i en terminal och
`npm run dev` i `ui/` i en annan, och öppna http://localhost:5173.

Se [CLAUDE.md](CLAUDE.md) för arkitektur, regler och plan.
