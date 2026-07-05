# Catalog import

Catalogul mare se tine in baza cloud configurata prin `DATABASE_URL`.
Importatorul foloseste Open Food Facts si salveaza produsele gasite in tabela
`products`, fara sa dubleze codurile de bare existente.

## Comenzi utile

Import din exportul mare Open Food Facts, filtrat pentru Romania si cu deduplicare mai buna.
Acesta este preferat pentru crestere mare a catalogului, fiindca nu apasa API-ul public:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe import_openfoodfacts_export.py --country romania --limit 5000 --max-scan 800000 --allow-no-barcode --progress-every 5000
```

Test fara sa scrie in baza:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe import_openfoodfacts_export.py --country romania --limit 20 --max-scan 20000 --allow-no-barcode --dry-run
```

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

## Import CSV de la magazine sau parteneri

Daca un retailer trimite un fisier CSV, pune-l local in `backend\data_imports\`
si ruleaza:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe import_retailer_feed.py --source .\data_imports\kaufland.csv --store Kaufland
```

Coloane acceptate automat: `barcode`, `ean`, `gtin`, `name`, `product_name`,
`denumire`, `brand`, `store`, `category`, `categorie`, `image_url`, `poza`,
`price`, `pret`, `calories`, `kcal`, `protein`, `sugar`, `fat`, `ingredients`.

Pentru fisiere primite de la GetRealPrice sau retaileri, exporta mai intai in CSV.
Nu importa XLSX direct in productie; converteste-l in CSV ca sa fie clar ce coloane
intra in baza.

## Recomandare practica

- Pentru acoperire mare foloseste `--country world`, fiindca multe produse din Romania
  sunt inregistrate cu branduri internationale sau cu tari multiple.
- Pentru acoperire romaneasca foloseste mai intai `import_openfoodfacts_export.py`
  cu `--country romania`, apoi completeaza cu CSV-uri de la magazine sau parteneri.
- Daca apar raspunsuri `503`, lasa comanda sa continue. Scriptul sare peste pagina
  temporar indisponibila si continua categoria.
- Nu porni mai multe importuri in paralel pe aceeasi baza. Mai bine rulezi batch-uri
  consecutive cu `--delay 1.2` sau `--delay 1.8`, ca sa nu primesti rate-limit.
- Dupa 10.000 produse, calitatea recomandarilor conteaza mai mult decat volumul brut:
  verifica produse reale scanate si adauga categorii unde vezi lipsuri.
