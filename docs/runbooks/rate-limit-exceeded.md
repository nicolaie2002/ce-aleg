# Runbook: rate limit depasit

## Simptome

- raspunsuri `429` si header `Retry-After` pentru utilizatori legitimi;
- crestere brusca pe login, OCR, alternative sau rute admin;
- Redis indisponibil si limitare locala diferita intre workeri.

## Diagnostic

1. Identifica endpointul, intervalul, IP-ul pseudonimizat si user ID-ul intern.
2. Separa trafic legitim, client care repeta cererea si abuz automatizat.
3. Verifica disponibilitatea Redis si fallbackul local in `/admin/monitoring`.
4. Confirma valorile `GLOBAL_RATE_LIMIT`, `AUTH_RATE_LIMIT` si ferestrele lor.

## Remediere

1. Pentru abuz, blocheaza sursa la margine daca platforma gratuita permite.
2. Pentru retry necontrolat, corecteaza clientul si respecta `Retry-After`.
3. Mareste limitele numai pe baza volumului observat si cu test de regresie.
4. Nu dezactiva limitarea pe login, resetare parola, AI sau admin.
5. Dupa schimbare, monitorizeaza `429`, `5xx` si latenta minimum 30 minute.
