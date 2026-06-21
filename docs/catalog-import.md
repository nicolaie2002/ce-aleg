# Catalog import

Catalogul mare se tine in baza cloud configurata prin `DATABASE_URL`.
Importatorul foloseste Open Food Facts si salveaza produsele gasite in tabela
`products`, fara sa dubleze codurile de bare existente.

## Comenzi utile

Import controlat pentru lansare:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe prewarm_openfoodfacts_catalog.py --preset launch --limit-per-category 40 --page-size 40 --delay 0.6
```

Import mare, rulat in batch-uri:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe prewarm_openfoodfacts_catalog.py --preset large --limit-per-category 80 --page-size 40 --delay 0.8
```

Import extins pentru lansare publica, cu multe familii de produse:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe prewarm_openfoodfacts_catalog.py --preset retail --limit-per-category 120 --page-size 50 --delay 1.2
```

Import foarte mare, de rulat doar cand vrei sa cresti baza peste 10.000-30.000 produse:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe prewarm_openfoodfacts_catalog.py --preset massive --limit-per-category 250 --page-size 50 --delay 1.8
```

Import doar pentru Romania:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe prewarm_openfoodfacts_catalog.py --preset launch --country romania --limit-per-category 40
```

Test fara sa scrie in baza:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe prewarm_openfoodfacts_catalog.py --preset starter --limit-per-category 5 --dry-run
```

## Recomandare practica

- Pentru acoperire mare foloseste `--country world`, fiindca multe produse din Romania
  sunt inregistrate cu branduri internationale sau cu tari multiple.
- Daca apar raspunsuri `503`, lasa comanda sa continue. Scriptul sare peste pagina
  temporar indisponibila si continua categoria.
- Nu porni mai multe importuri in paralel pe aceeasi baza. Mai bine rulezi batch-uri
  consecutive cu `--delay 1.2` sau `--delay 1.8`, ca sa nu primesti rate-limit.
- Dupa 10.000 produse, calitatea recomandarilor conteaza mai mult decat volumul brut:
  verifica produse reale scanate si adauga categorii unde vezi lipsuri.
