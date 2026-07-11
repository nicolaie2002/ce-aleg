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

Continuare dupa un batch deja rulat:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe import_openfoodfacts_export.py --country romania --skip-rows 701639 --limit 5000 --max-scan 900000 --allow-no-barcode --progress-every 5000
```

Test fara sa scrie in baza:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe import_openfoodfacts_export.py --country romania --limit 20 --max-scan 20000 --allow-no-barcode --dry-run
```

Dupa import, recategorizeaza produsele care au ramas la `Altele`:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe recategorize_catalog.py --limit 1000
.\venv\Scripts\python.exe recategorize_catalog.py --limit 1000 --apply
```

Comanda cap-coada pentru un batch Romania, cu preview de recategorizare:

```powershell
cd D:\proiecte\ce_aleg
powershell -ExecutionPolicy Bypass -File scripts\import-romania-catalog.ps1 -Limit 5000 -MaxScan 800000
```

Cand preview-ul arata bine, ruleaza acelasi batch cu aplicarea recategorizarii:

```powershell
cd D:\proiecte\ce_aleg
powershell -ExecutionPolicy Bypass -File scripts\import-romania-catalog.ps1 -Limit 5000 -MaxScan 800000 -ApplyRecategorize
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

## Surse externe verificate

Nu orice dataset alimentar trebuie importat in `products`. Catalogul principal trebuie
sa contina produse de raft, ideal cu barcode, brand, imagine si categorie. Dataseturile
generice pot strica recomandarile daca intra in aceeasi tabela cu produsele scanabile.

Surse bune pentru catalog:

- Open Food Facts export: bun pentru produse de raft, coduri de bare, imagini si
  ingrediente. Este sursa principala pentru cresterea catalogului.
- Feed-uri CSV de la magazine, parteneri sau surse romanesti: cele mai valoroase
  pentru produse locale si preturi reale.
- Nutritionix API: interesant pentru produse branduite si cautare dupa UPC, dar
  trebuie verificat costul, limita API si drepturile comerciale inainte de integrare.
  Nu il folosi ca dependenta obligatorie pentru scanare pana nu avem termenii si
  pretul clar.

Surse bune doar ca referinta nutritionala:

- USDA FoodData Central Foundation Foods: alimente generale, fara produse romanesti
  de raft si fara barcode. Bun pentru o tabela separata de referinte nutritionale,
  nu pentru `products`.
- Dataseturi nutritionale generale, cum ar fi fisiere cu categorii si valori
  nutritionale pe 100 g: utile pentru validari si scoruri orientative, dar doar
  daca licenta este clara.

Surse de evitat pentru import direct:

- Dataseturi de imagini pentru clasificare, cum ar fi Food-101N. Sunt utile pentru
  cercetare sau antrenare vizuala, dar nu identifica sigur produse de raft romanesti
  si nu contin barcode, preturi sau date comerciale.
- Open Beauty Facts: foloseste acelasi ecosistem ca Open Food Facts, dar este pentru
  cosmetice. Poate fi util mai tarziu daca Ce aleg? se extinde in zona de produse
  cosmetice sau ingrijire, nu pentru catalogul alimentar actual.
- Liste fara licenta clara. Nu le importa in productie pana nu este clar ca pot fi
  folosite comercial.

Model de crestere recomandat, inspirat de Yuka: pornim din Open Food Facts, apoi
crestem baza proprie prin produse contribuite de utilizatori, validare admin si
feed-uri oficiale de la retaileri, producatori sau parteneri locali.

## Recomandare practica

- Pentru acoperire mare foloseste `--country world`, fiindca multe produse din Romania
  sunt inregistrate cu branduri internationale sau cu tari multiple.
- Pentru acoperire romaneasca foloseste mai intai `import_openfoodfacts_export.py`
  cu `--country romania`, apoi completeaza cu CSV-uri de la magazine sau parteneri.
- Dupa fiecare batch mare ruleaza `recategorize_catalog.py --limit 1000 --apply`,
  apoi verifica in admin sectiunea Catalog Romania pentru procentul ramas la `Altele`.
- Daca apar raspunsuri `503`, lasa comanda sa continue. Scriptul sare peste pagina
  temporar indisponibila si continua categoria.
- Nu porni mai multe importuri in paralel pe aceeasi baza. Mai bine rulezi batch-uri
  consecutive cu `--delay 1.2` sau `--delay 1.8`, ca sa nu primesti rate-limit.
- Dupa 10.000 produse, calitatea recomandarilor conteaza mai mult decat volumul brut:
  verifica produse reale scanate si adauga categorii unde vezi lipsuri.
