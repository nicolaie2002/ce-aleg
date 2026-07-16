# Runbook: import si calitate catalog

## Scop

Procedura acopera importul din Open Food Facts, importul CSV de la parteneri,
prewarm-ul targetat pentru Romania si recategorizarea. Sursa externa nu devine
automat adevar verificat: licenta, provenienta, campurile si calitatea trebuie
revizuite inainte de productie.

Documentatia de context existenta este `docs/catalog-import.md`; acest runbook se
concentreaza pe executie operationala si revenire.

## Reguli obligatorii

1. Un singur import/scris masiv ruleaza la un moment dat pe baza de productie.
2. Fa backup si verifica restaurabilitatea inainte de un lot mare.
3. Ruleaza intai dry-run cu aceleasi filtre si limite.
4. Incepe cu un lot mic, verifica rezultatele, apoi creste gradual.
5. Nu importa date fara licenta/provenienta clara sau feed trimis pe un canal
   neautentificat.
6. Nu importa XLSX direct; converteste si inspecteaza un CSV UTF-8.
7. Nu include fisierul sursa, credentialele sau backup-ul in Git.
8. Nu folosi `--allow-no-barcode` fara o decizie explicita: sunt generate identitati
   sintetice si deduplicarea devine mai dificila.

## Pregatire

Inregistreaza privat:

- operatorul, sursa, URL/numele fisierului, hash SHA-256 si data obtinerii;
- licenta/permisiunea si restrictiile;
- numarul estimat de randuri, tara, categorii si magazin;
- backup ID/timestamp si commit SHA;
- parametrii dry-run si parametrii aprobati pentru apply;
- criteriile de oprire si persoana care aproba.

Verifica spatiul, conexiunile Supabase, Render metrics si ca nu exista incident activ.

## 1. Backup

Urmeaza `docs/supabase-backup.md`. Minimum:

```powershell
New-Item -ItemType Directory -Force backups
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
pg_dump "$env:DATABASE_URL" --format=custom --no-owner --no-acl `
  --file "backups\cealeg-$stamp.dump"
pg_restore --list "backups\cealeg-$stamp.dump" | Select-Object -First 20
```

Directorul de backup este local/privat; confirma ca nu va fi adaugat in commit.
Pentru productie, valoarea `DATABASE_URL` se furnizeaza temporar printr-un canal
sigur si nu se afiseaza in istoric/capturi.

## 2. Prewarm targetat Open Food Facts

Wrapperul este dry-run implicit:

```powershell
Set-Location D:\proiecte\ce_aleg
.\scripts\prewarm-romania-focus.ps1 `
  -Categories "en:yogurts,en:cold-cuts" `
  -LimitPerCategory 20
```

Verifica sumarul `existing`, `skipped`, `dry-run` si `failed`. Dupa aprobare:

```powershell
.\scripts\prewarm-romania-focus.ps1 `
  -Categories "en:yogurts,en:cold-cuts" `
  -LimitPerCategory 20 `
  -Apply
```

`-WorldFallback` elimina filtrul strict Romania si mareste riscul de produse
irelevante; foloseste-l numai pentru categorii/branduri verificate.

## 3. Export mare Open Food Facts

Dry-run limitat:

```powershell
Set-Location D:\proiecte\ce_aleg
powershell -ExecutionPolicy Bypass -File scripts\import-romania-catalog.ps1 `
  -Country romania `
  -Limit 20 `
  -MaxScan 20000 `
  -RequireBarcode `
  -DryRun
```

Lot persistent initial:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\import-romania-catalog.ps1 `
  -Country romania `
  -Limit 200 `
  -MaxScan 100000 `
  -RequireBarcode `
  -NoRecategorize
```

Scriptul de baza suporta `--source`, `--format`, `--delimiter`, `--skip-rows`,
`--batch-size`, `--progress-every` si `--dry-run`. Pentru reluare, noteaza exact
`scanned` si foloseste `--skip-rows`/`-SkipRows`; nu ghici offsetul dupa numarul de
produse importate, deoarece exista skipped/duplicates.

Nu porni cu limita de mii pana cand loturile 20, 200 si apoi 1000 au fost verificate.

## 4. Feed CSV retailer/partener

Pune fisierul intr-o locatie locala ignorata, de exemplu
`backend\data_imports\`, apoi calculeaza hash-ul:

```powershell
Get-FileHash .\backend\data_imports\partener.csv -Algorithm SHA256
```

Inspecteaza headerele si cateva randuri fara a publica fisierul. Dry-run:

```powershell
Set-Location D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe import_retailer_feed.py `
  --source .\data_imports\partener.csv `
  --store "Nume partener" `
  --max-rows 100 `
  --max-file-mb 100 `
  --dry-run
```

Dupa aprobare, elimina `--dry-run` pastrand aceleasi limite. Scriptul accepta nume,
barcode, magazin, categorie, ingrediente, nutritie, pret si imagine prin headerele
recunoscute. Valorile numerice imposibile sunt sarite, dar validarea tehnica nu
inlocuieste verificarea continutului.

CSV security:

- deschide fisierele neautentificate intr-un viewer sigur, nu cu macro-uri;
- trateaza celulele care incep cu `=`, `+`, `-` sau `@` ca potentiale formule la
  export/revizuire;
- nu accepta cai locale/URL-uri de imagini care expun resurse private;
- elimina coloanele cu date personale nenecesare.

## 5. Recategorizare

Dry-run explicit:

```powershell
Set-Location D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe recategorize_catalog.py --limit 200
```

Aplica doar dupa inspectarea schimbarilor:

```powershell
.\venv\Scripts\python.exe recategorize_catalog.py --limit 200 --apply
```

Optiunile `--min-id`, `--category` si `--include-all` extind scopul. Noteaza
`lastScannedId`/offsetul operational si continua in batch-uri. Nu aplica
`--include-all` pe tot catalogul fara esantion, backup si fereastra aprobata.

Admin-ul are `GET/POST /admin/catalog/recategorize`, iar cron-ul maintenance ruleaza
un batch controlat. Nu porni manual scriptul si cron-ul in paralel.

## 6. Monitorizare in timpul importului

Opreste importul daca apare oricare:

- crestere sustinuta de erori DB/5xx sau connection pool saturation;
- rata `failed` neasteptata ori crestere brusca de produse `Altele`;
- duplicate/barcode-uri sintetice peste pragul aprobat;
- valori nutritionale sau preturi evident incorecte in esantion;
- sursa schimba formatul/coloanele in timpul rularii;
- latenta afecteaza utilizatorii;
- lipsa spatiu, timeout sau incident provider.

Oprirea procesului poate lasa batch-urile deja comise. Nu presupune tranzactie unica
pentru intreg fisierul.

## 7. Verificare dupa lot

1. Compara numarul `imported/saved`, `duplicates`, `skipped`, `failed` cu raportul.
2. Verifica 20-50 produse alese aleator si toate randurile cu erori.
3. Verifica barcode, nume, categorie, magazin, nutritie, imagine, scor si ingrediente.
4. Cauta duplicate dupa barcode si identitate nume/magazin.
5. Verifica distributia categoriilor si procentul `Altele` in admin/Catalog Romania.
6. Testeaza scanarea pentru minimum 10 barcode-uri noi.
7. Testeaza alternativele pentru familii diferite; un produs prezent nu este util
   daca recomandarile sunt incompatibile.
8. Monitorizeaza latenta si erorile 30 minute dupa lot.
9. Pastreaza raportul si hash-ul sursei conform retentiei aprobate; sterge fisierul
   brut cand nu mai este necesar.

## 8. Revenire

Nu exista un rollback sigur prin "sterge ultimele N produse" fara provenienta
persistenta verificata. Daca lotul este gresit:

1. Opreste toate importurile/recategorizarea.
2. Identifica exact randurile prin interval ID, source/store, timestamp si raport.
3. Fa un nou backup al starii defecte pentru investigatie.
4. Preferabil scrie si revizuieste un script de remediere idempotent care afiseaza
   dry-run si numarul exact de randuri.
5. Daca afectarea este extinsa, restaureaza backup-ul intr-o baza izolata, compara
   datele create legitim dupa backup si planifica reconcilierea.
6. Nu restaura peste productie fara aprobarea procedurii DB.

## Informatii externe necesare

Proprietarul trebuie sa completeze: licentele si permisiunile surselor, contractele
retailerilor, pragurile de calitate, fereastra de import, persoana care aproba,
locatia backupurilor, RPO/RTO, retentia fisierelor brute si metoda de identificare a
provenientei fiecarui lot.
