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
